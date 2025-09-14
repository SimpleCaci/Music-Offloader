import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load credentials
load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
))

def get_spotify_tracks(url):
    # Detect resource type and ID
    parts = url.split("/")
    if len(parts) < 5:
        raise ValueError("Invalid Spotify URL")
    
    resource_type = parts[3]  # 'playlist' or 'album'
    resource_id = parts[4].split("?")[0]

    tracks = []

    if resource_type == "playlist":
        print("Detected: Playlist")
        results = sp.playlist_tracks(resource_id, limit=100)
        for item in results["items"]:
            track = item["track"]
            name = track["name"]
            artist = track["artists"][0]["name"]
            tracks.append(f"{name} by {artist}")

    elif resource_type == "album":
        print("Detected: Album")
        results = sp.album_tracks(resource_id, limit=50)
        for item in results["items"]:
            name = item["name"]
            artist = item["artists"][0]["name"]
            tracks.append(f"{name} by {artist}")
    else:
        raise ValueError("URL must be a Spotify playlist or album link.")

    return tracks


spotify_url = "https://open.spotify.com/playlist/37i9dQZF1E393PuWkPIAWl"
songs = get_spotify_tracks(spotify_url)
for song in songs:
    print(song)
