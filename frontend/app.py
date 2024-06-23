from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import asyncio
import websockets
import json
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googletrans import Translator
import logging
import secrets

app = Flask(__name__)

# Generate and set the secret key
app.secret_key = secrets.token_hex(16)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mood_tracker.db'
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Hume AI and Spotify API credentials
HUME_API_KEY = '5RAMpbJ8EeCRqa9enS41mCDQ8zodQdmZEUt2v3eyHFcvYFae'
SPOTIPY_CLIENT_ID = 'f5d053f6cb124139a3d1e505d26635fc'
SPOTIPY_CLIENT_SECRET = '735bba397f424b49b387b56d264e7ed9'

# Configure Spotipy
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))

translator = Translator()

# Define MoodEntry model with user_id
class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    emotion = db.Column(db.String, nullable=False)
    journal_entry = db.Column(db.String, nullable=False)

# Create tables
with app.app_context():
    db.create_all()

async def get_hume_response(text, lang='en'):
    uri = f"wss://api.hume.ai/v0/evi/chat?api_key={HUME_API_KEY}"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({'text': text}))
            response = await websocket.recv()
            response_data = json.loads(response)
            emotion = response_data.get('emotion', 'neutral')
            if lang != 'en':
                emotion = translator.translate(emotion, dest=lang).text
            return emotion
    except Exception as e:
        logging.error(f"Error in get_hume_response: {e}")
        return 'neutral'

def get_spotify_recommendations(emotion):
    genre = 'pop'  # Default genre
    if 'happy' in emotion.lower():
        genre = 'happy'
    elif 'sad' in emotion.lower():
        genre = 'sad'
    elif 'angry' in emotion.lower():
        genre = 'metal'
    elif 'calm' in emotion.lower():
        genre = 'chill'
    
    try:
        results = sp.recommendations(seed_genres=[genre], limit=10)
        tracks = results['tracks']
        recommendations = [{'name': track['name'], 'artist': track['artists'][0]['name'], 'url': track['external_urls']['spotify']} for track in tracks]
        return recommendations
    except Exception as e:
        logging.error(f"Error in get_spotify_recommendations: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/journal', methods=['GET', 'POST'])
def journal():
    if request.method == 'POST':
        entry = request.form['entry']
        lang = request.form.get('lang', 'en')
        user_id = request.form.get('user_id')  # Ensure user_id is provided in the form
        if not user_id:
            return "User ID is required", 400
        try:
            emotion = asyncio.run(get_hume_response(entry, lang))
            recommendations = get_spotify_recommendations(emotion)
            
            # Save the mood entry in the database
            mood_entry = MoodEntry(user_id=user_id, date=datetime.today().date(), emotion=emotion, journal_entry=entry)
            db.session.add(mood_entry)
            db.session.commit()

            return render_template('journal.html', emotion=emotion, recommendations=recommendations, entry=entry)
        except Exception as e:
            logging.error(f"Error in /journal route: {e}")
            return "There was an error processing your request.", 500
    return render_template('journal.html')

@app.route('/calendar')
def calendar():
    try:
        mood_entries = MoodEntry.query.all()
        return render_template('calendar.html', mood_entries=mood_entries)
    except Exception as e:
        logging.error(f"Error in /calendar route: {e}")
        return "There was an error loading the calendar.", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
