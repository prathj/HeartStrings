from flask import Flask, request, render_template, jsonify, redirect, url_for
import requests
import asyncio
import websockets
import json
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googletrans import Translator
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import asyncio
from hume import HumeStreamClient
from hume.models.config import LanguageConfig

app = Flask(__name__)

# Hume AI and Spotify API credentials
HUME_API_KEY = '5RAMpbJ8EeCRqa9enS41mCDQ8zodQdmZEUt2v3eyHFcvYFae'
SPOTIPY_CLIENT_ID = 'YOUR_SPOTIPY_CLIENT_ID'
SPOTIPY_CLIENT_SECRET = 'YOUR_SPOTIPY_CLIENT_SECRET'

# Configure Spotipy
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))

# Configure SQLAlchemy
engine = create_engine('sqlite:///mood_tracker.db')
Base = declarative_base()

class MoodEntry(Base):
    __tablename__ = 'mood_entries'
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True)
    emotion = Column(String)
    journal_entry = Column(String)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

translator = Translator()

async def get_hume_response(text, lang='en'):
    uri = f"wss://api.hume.ai/v0/evi/chat?api_key={HUME_API_KEY}"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({'text': text}))
        response = await websocket.recv()
        response_data = json.loads(response)
        emotion = response_data.get('emotion', 'neutral')
        if lang != 'en':
            emotion = translator.translate(emotion, dest=lang).text
        return emotion

def get_spotify_playlist(emotion):
    genre = 'pop'  # Default genre
    if 'happy' in emotion.lower():
        genre = 'happy'
    elif 'sad' in emotion.lower():
        genre = 'sad'
    elif 'angry' in emotion.lower():
        genre = 'metal'
    elif 'calm' in emotion.lower():
        genre = 'chill'
    
    results = sp.recommendations(seed_genres=[genre], limit=10)
    tracks = results['tracks']
    recommendations = [{'name': track['name'], 'artist': track['artists'][0]['name'], 'url': track['external_urls']['spotify']} for track in tracks]
    return recommendations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/journal', methods=['GET', 'POST'])
def journal():
    if request.method == 'POST':
        entry = request.form['entry']
        lang = request.form.get('lang', 'en')
        emotion = asyncio.run(get_hume_response(entry, lang))
        playlist = get_spotify_playlist(emotion)
        
        # Save the mood entry in the database
        mood_entry = MoodEntry(date=datetime.today().date(), emotion=emotion, journal_entry=entry)
        session.add(mood_entry)
        session.commit()

        return render_template('journal.html', emotion=emotion, playlist=playlist, entry=entry)
    return render_template('journal.html')

@app.route('/calendar')
def calendar():
    entries = session.query(MoodEntry).all()
    return render_template('calendar.html', entries=entries)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

