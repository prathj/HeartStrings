from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import asyncio
import websockets
import json
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import secrets
import certifi
import ssl
import pprint as pprint
from hume import HumeStreamClient
from hume.models.config import LanguageConfig

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

async def get_hume_response(text):
    client = HumeStreamClient(HUME_API_KEY)
    config = LanguageConfig()
    try:
        print("12")
        async with client.connect([config]) as socket:
            print('34')
            result = await socket.send_text(text)
            max_emotion = (max(result['language']['predictions'][-1]['emotions'], key=lambda x: x['score']))['name']
            return max_emotion
    except Exception as e:
        logging.error(f"Error in get_hume_response: {e}")
        return ['neutral']

def get_spotify_recommendations(emotion):

    emotion_genres = {
        'Admiration': 'classical',
        'Adoration': 'romance',
        'Aesthetic Appreciation': 'ambient',
        'Amusement': 'comedy',
        'Anger': 'metal',
        'Annoyance': 'punk',
        'Anxiety': 'ambient',
        'Awe': 'classical',
        'Awkwardness': 'emo',
        'Boredom': 'ambient',
        'Calmness': 'acoustic',
        'Concentration': 'study',
        'Confusion': 'experimental',
        'Contemplation': 'ambient',
        'Contempt': 'punk',
        'Contentment': 'chill',
        'Craving': 'dance',
        'Determination': 'rock',
        'Disappointment': 'blues',
        'Disapproval': 'punk',
        'Disgust': 'death-metal',
        'Distress': 'emo',
        'Doubt': 'indie',
        'Ecstasy': 'edm',
        'Embarrassment': 'comedy',
        'Empathic Pain': 'gospel',
        'Enthusiasm': 'dance',
        'Entrancement': 'trance',
        'Envy': 'hip-hop',
        'Excitement': 'pop',
        'Fear': 'industrial',
        'Gratitude': 'gospel',
        'Guilt': 'blues',
        'Horror': 'black-metal',
        'Interest': 'indie',
        'Joy': 'pop',
        'Love': 'romance',
        'Nostalgia': 'retro',
        'Pain': 'emo',
        'Pride': 'rock',
        'Realization': 'ambient',
        'Relief': 'acoustic',
        'Romance': 'romance',
        'Sadness': 'sad',
        'Sarcasm': 'punk',
        'Satisfaction': 'soul',
        'Desire': 'latin',
        'Shame': 'emo',
        'Surprise (negative)': 'experimental',
        'Surprise (positive)': 'pop',
        'Sympathy': 'folk',
        'Tiredness': 'sleep',
        'Triumph': 'power-pop'
    }

    genre = emotion_genres[emotion]

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
        user_id = request.form.get('user_id')  # Ensure user_id is provided in the form
        if not user_id:
            return "User ID is required", 400
        try:
            emotion = asyncio.run(get_hume_response(entry))
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