import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotify_scraper import SpotifyClient

# === Spotify API Setup ===
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8000/callback"

scope = "playlist-read-private playlist-read-collaborative"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope,
    cache_path="token_cache.json",
    open_browser=True
))

# === SpotifyScraper Setup (Backup) ===
scraper_client = SpotifyClient()

# === Unified Track Fetch Function ===
def get_spotify_tracks(url):
    parts = url.split("/")
    if len(parts) < 5:
        raise ValueError("Invalid Spotify URL")

    resource_type = parts[3]
    resource_id = parts[4].split("?")[0]

    # 1. Try Spotify API
    try:
        if resource_type == "playlist":
            print("Using Spotify API...")
            results = sp.playlist_items(resource_id, limit=100)
            tracks = []
            for i in results["items"]:
                track = i.get("track")
                if track:
                    tracks.append({
                        "title": track.get("name", ""),
                        "artist": ", ".join(a["name"] for a in track["artists"]),
                        "album": track.get("album", {}).get("name", ""),
                        "duration_ms": track.get("duration_ms", 0),
                        "preview_url": track.get("preview_url", ""),
                        "cover_art": track.get("album", {}).get("images", [{}])[0].get("url", "")
                    })
            return tracks
        elif resource_type == "album":
            print("Using Spotify API for album...")
            results = sp.album_tracks(resource_id, limit=50)
            tracks = []
            album_data = sp.album(resource_id)
            cover_art = album_data.get("images", [{}])[0].get("url", "")
            for i in results["items"]:
                tracks.append({
                    "title": i.get("name", ""),
                    "artist": ", ".join(a["name"] for a in i["artists"]),
                    "album": album_data.get("name", ""),
                    "duration_ms": i.get("duration_ms", 0),
                    "preview_url": i.get("preview_url", ""),
                    "cover_art": cover_art
                })
            return tracks
        else:
            raise ValueError("URL must be a playlist or album link.")
    except Exception as e:
        print(f"API failed: {e}")
        print("Trying SpotifyScraper backup...")

    # 2. Fallback: SpotifyScraper
    try:
        if resource_type == "playlist":
            playlist_data = scraper_client.get_playlist_info(url)
            return [
                {
                    "title": t.get("name", ""),
                    "artist": ", ".join(a["name"] for a in t.get("artists", [])),
                    "album": t.get("album", {}).get("name", ""),
                    "duration_ms": t.get("duration_ms", 0),
                    "preview_url": t.get("preview_url", ""),
                    "cover_art": t.get("album", {}).get("images", [{}])[0].get("url", "")
                }
                for t in playlist_data.get("tracks", [])
            ]
        elif resource_type == "album":
            album_data = scraper_client.get_album_info(url)
            cover_art = album_data.get("images", [{}])[0].get("url", "")
            return [
                {
                    "title": t.get("name", ""),
                    "artist": ", ".join(a["name"] for a in t.get("artists", [])),
                    "album": album_data.get("name", ""),
                    "duration_ms": t.get("duration_ms", 0),
                    "preview_url": t.get("preview_url", ""),
                    "cover_art": cover_art
                }
                for t in album_data.get("tracks", [])
            ]
    except Exception as e:
        print(f"SpotifyScraper backup failed: {e}")
        return []

# === Save to CSV ===
def save_tracks_to_csv(tracks, filename="spotify_tracks.csv"):
    if tracks:
        df = pd.DataFrame(tracks)
        df.to_csv(filename, index=False)
        print(f"Saved {len(tracks)} tracks to {filename}")
    else:
        print("No tracks to save.")

# === Example Usage ===
if __name__ == "__main__":
    spotify_url = "https://open.spotify.com/playlist/37i9dQZF1E393PuWkPIAWl"  # Daily Mix example
    tracks = get_spotify_tracks(spotify_url)
    save_tracks_to_csv(tracks, "spotify_tracks.csv")
    scraper_client.close()
