import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load Client ID and Secret from environment variables
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Hardcode the Redirect URI so we don't rely on environment variables for it
REDIRECT_URI = "http://127.0.0.1:8000/callback"

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is missing in environment variables!")

# Authenticate with Spotify using OAuth
scope = "playlist-read-private playlist-read-collaborative"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope,
    open_browser=True
))

def get_spotify_tracks(url):
    parts = url.split("/")
    if len(parts) < 5:
        raise ValueError("Invalid Spotify URL")
    
    resource_type = parts[3]
    resource_id = parts[4].split("?")[0]

    tracks = []

    if resource_type == "playlist":
        print("Detected: Playlist")
        results = sp.playlist_items(resource_id, limit=100)
        for item in results["items"]:
            track = item["track"]
            if track:
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

# Example usage
spotify_url = "https://open.spotify.com/playlist/37i9dQZF1E393PuWkPIAWl"
songs = get_spotify_tracks(spotify_url)
for song in songs:
    print(song)
