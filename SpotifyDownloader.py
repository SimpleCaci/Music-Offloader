import os, sys, requests, zipfile, shutil, stat, platform
import yt_dlp
import ffmpeg
import pandas as pd
from urllib.parse import urlparse
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from SpotifyPlaylistGrabber import get_spotify_tracks, save_tracks_to_csv

# === CONFIG ===
MP3_PLAYER_NAME = "Mibao-M500"
local_fallback_dir = os.path.expanduser("~/Music/SpotifyDownloads")
ffmpeg_dir = os.path.expanduser("~/ffmpeg-bin")
os.makedirs(ffmpeg_dir, exist_ok=True)

# OS-specific URLs
if sys.platform == "win32":
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
elif sys.platform == "darwin":
    ffmpeg_url = "https://evermeet.cx/ffmpeg/ffmpeg-6.1.1.zip"
else:
    ffmpeg_url = ""  # Linux users should install via apt/brew

# Paths for ffmpeg & ffprobe
ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe.exe" if sys.platform == "win32" else "ffprobe")

# === Detect MP3 Player Path ===
def find_mp3_player(mount_name):
    if sys.platform == "darwin":  # macOS
        base_path = "/Volumes"
        for device in os.listdir(base_path):
            if mount_name in device:
                return os.path.join(base_path, device, "Music")
    elif sys.platform == "win32":  # Windows
        from string import ascii_uppercase
        drives = [f"{d}:/" for d in ascii_uppercase if os.path.exists(f"{d}:/")]
        for drive in drives:
            if mount_name.lower() in drive.lower():
                return os.path.join(drive, "Music")
    return None

base_download_dir = find_mp3_player(MP3_PLAYER_NAME) or local_fallback_dir
os.makedirs(base_download_dir, exist_ok=True)

# === Download & Install FFmpeg if Missing ===
def ensure_ffmpeg():
    if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
        return  # Already installed

    if not ffmpeg_url:
        print("Linux detected — please install ffmpeg manually (e.g., sudo apt install ffmpeg)")
        return

    print(f"Downloading FFmpeg for {platform.system()}...")
    zip_path = os.path.join(ffmpeg_dir, "ffmpeg.zip")
    r = requests.get(ffmpeg_url)
    with open(zip_path, "wb") as f:
        f.write(r.content)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(ffmpeg_dir)
    os.remove(zip_path)

    # Windows builds: binaries live in a subfolder/bin
    if sys.platform == "win32":
        subfolders = [f for f in os.listdir(ffmpeg_dir) if os.path.isdir(os.path.join(ffmpeg_dir, f))]
        for folder in subfolders:
            bin_path = os.path.join(ffmpeg_dir, folder, "bin")
            if os.path.exists(bin_path):
                for exe in ["ffmpeg.exe", "ffprobe.exe"]:
                    shutil.move(os.path.join(bin_path, exe), os.path.join(ffmpeg_dir, exe))
                shutil.rmtree(os.path.join(ffmpeg_dir, folder))

    # Make executables runnable on macOS/Linux
    if sys.platform != "win32":
        for binary in [ffmpeg_path, ffprobe_path]:
            if os.path.exists(binary):
                os.chmod(binary, os.stat(binary).st_mode | stat.S_IEXEC)

# === URL Checker ===
def is_valid_url(url):
    try:
        if not isinstance(url, str) or url.lower() == "nan" or not url.strip():
            return False
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

# === Add Metadata ===
def add_metadata(mp3_file, title, artist, album, cover_url=None, yt_thumbnail=None):
    try:
        audio = EasyID3(mp3_file)
    except Exception:
        audio = EasyID3()

    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    audio.save(mp3_file)

    final_cover_url = cover_url if is_valid_url(cover_url) else yt_thumbnail
    if final_cover_url:
        try:
            img_data = requests.get(final_cover_url).content
            tags = ID3(mp3_file)
            tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=img_data))
            tags.save(mp3_file)
        except Exception as e:
            print(f"Could not add album art: {e}")

# === Download + Convert + Tag One Song ===
def download_song_youtube(query, title, artist, album, album_dir, cover_url=None):
    ensure_ffmpeg()

    safe_filename = "".join(c for c in f"{title} - {artist}" if c.isalnum() or c in " -_").strip()
    mp3_output = os.path.join(album_dir, f"{safe_filename}.mp3")
    webm_output = os.path.join(album_dir, f"{safe_filename}.webm")

    url = query if "https://" in query else f"ytsearch:{query}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': webm_output,
        'quiet': False,
        'no_warnings': True
    }

    # Download audio
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'entries' in info:
            info = info['entries'][0]
    yt_thumbnail = info.get("thumbnail", None)

    # Convert to MP3
    print(f"Converting {webm_output} → {mp3_output}")
    ffmpeg.input(webm_output).output(mp3_output, format='mp3').run(cmd=ffmpeg_path)
    os.remove(webm_output)

    # Add metadata
    add_metadata(mp3_output, title, artist, album, cover_url, yt_thumbnail)
    print(f"Downloaded + tagged: {mp3_output}")

# === Full Pipeline ===
def run_pipeline(spotify_url):
    print("Fetching Spotify tracks...")
    tracks = get_spotify_tracks(spotify_url)
    save_tracks_to_csv(tracks, "spotify_tracks.csv")

    df = pd.read_csv("spotify_tracks.csv")
    for _, row in df.iterrows():
        title = str(row.get("title") or "Unknown Title")
        artist = str(row.get("artist") or "Unknown Artist")
        album = str(row.get("album") or "Unknown Album")
        cover_url = row.get("cover_art", "")

        album_dir = os.path.join(base_download_dir, "".join(c for c in album if c.isalnum() or c in " -_").strip())
        os.makedirs(album_dir, exist_ok=True)

        query = f"{title} {artist} audio"
        download_song_youtube(query, title, artist, album, album_dir, cover_url)

# === Run ===
if __name__ == "__main__":
    spotify_url = "https://open.spotify.com/playlist/37i9dQZF1E393PuWkPIAWl?si=PaUSpi3pRhyK5-4XOrKRRw"
    run_pipeline(spotify_url)
