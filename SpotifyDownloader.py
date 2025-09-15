import os
import requests
import yt_dlp
import ffmpeg
import stat
import zipfile
import pandas as pd
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from SpotifyPlaylistGrabber import get_spotify_tracks, save_tracks_to_csv

# === CONFIG ===
base_download_dir = "/Volumes/Mibao-M500/Music"
ffmpeg_dir = os.path.expanduser("~/ffmpeg-bin")
ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg")
ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe")
os.makedirs(base_download_dir, exist_ok=True)

# URLs for macOS binaries
ffmpeg_url = "https://evermeet.cx/ffmpeg/ffmpeg-6.1.1.zip"
ffprobe_url = "https://evermeet.cx/ffmpeg/ffprobe-6.1.1.zip"

# === 1. Ensure ffmpeg + ffprobe installed ===
def download_and_extract(name, url):
    os.makedirs(ffmpeg_dir, exist_ok=True)
    zip_path = os.path.join(ffmpeg_dir, name + ".zip")
    binary_path = os.path.join(ffmpeg_dir, name)

    if not os.path.exists(binary_path):
        print(f"Downloading {name}...")
        r = requests.get(url)
        with open(zip_path, "wb") as f:
            f.write(r.content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        os.remove(zip_path)
        os.chmod(binary_path, os.stat(binary_path).st_mode | stat.S_IEXEC)

    return binary_path

def ensure_ffmpeg():
    if not os.path.exists(ffmpeg_path):
        download_and_extract("ffmpeg", ffmpeg_url)
    if not os.path.exists(ffprobe_path):
        download_and_extract("ffprobe", ffprobe_url)

# === 2. Add Metadata Function ===
def add_metadata(mp3_file, title, artist, album, cover_url=None):
    try:
        audio = EasyID3(mp3_file)
    except Exception:
        audio = EasyID3()
    
    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    audio.save(mp3_file)

    if cover_url:
        try:
            img_data = requests.get(cover_url).content
            tags = ID3(mp3_file)
            tags.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=img_data
            ))
            tags.save(mp3_file)
        except Exception as e:
            print(f"Could not add album art: {e}")

# === 3. Download + Convert + Tag one song ===
def download_song_youtube(query, title, artist, album, album_dir, cover_url=None):
    ensure_ffmpeg()

    # Build safe filename from Spotify metadata
    safe_filename = "".join(c for c in f"{title} - {artist}" if c.isalnum() or c in " -_").strip()
    mp3_output = os.path.join(album_dir, f"{safe_filename}.mp3")
    webm_output = os.path.join(album_dir, f"{safe_filename}.webm")

    # Search or use direct URL
    url = query if "https://" in query else f"ytsearch:{query}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': webm_output,
        'quiet': False,
        'no_warnings': True
    }

    # Download from YouTube
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'entries' in info:  # Search result returns list
            info = info['entries'][0]

    # Convert to MP3 with ffmpeg
    print(f"Converting {webm_output} → {mp3_output}")
    ffmpeg.input(webm_output).output(mp3_output, format='mp3').run(cmd=ffmpeg_path)
    os.remove(webm_output)

    # Add metadata from Spotify
    add_metadata(mp3_output, title, artist, album, cover_url)

    print(f"Downloaded + tagged: {mp3_output}")

# === 4. Full Pipeline: Spotify → YouTube → MP3 ===
def run_pipeline(spotify_url):
    print("Fetching Spotify tracks...")
    tracks = get_spotify_tracks(spotify_url)
    save_tracks_to_csv(tracks, "spotify_tracks.csv")

    df = pd.read_csv("spotify_tracks.csv")
    for _, row in df.iterrows():
        title = row.get("title", "Unknown Title")
        artist = row.get("artist", "Unknown Artist")
        album = row.get("album", "Spotify Playlist")
        cover_url = row.get("cover_art", "")

        # Create album folder
        album_dir = os.path.join(base_download_dir, "".join(c for c in album if c.isalnum() or c in " -_").strip())
        os.makedirs(album_dir, exist_ok=True)

        # Build YouTube query from title + artist
        query = f"{title} {artist} audio"
        download_song_youtube(query, title, artist, album, album_dir, cover_url)

# === 5. Run ===
if __name__ == "__main__":
    spotify_url = "https://open.spotify.com/playlist/37i9dQZF1E352QNAnHB0B1"
    run_pipeline(spotify_url)
