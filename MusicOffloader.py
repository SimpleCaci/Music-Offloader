import os
import requests
import yt_dlp
import ffmpeg
import stat
import zipfile

# === CONFIG ===
download_dir = os.path.expanduser("~/Music")
ffmpeg_dir = os.path.expanduser("~/ffmpeg-bin")
ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg")
ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe")

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

# === 2. Function to download + convert ===
def download_and_convert(url):
    ensure_ffmpeg()

    # Download audio with yt-dlp
    webm_path_template = os.path.join(download_dir, "%(title)s.%(ext)s")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': webm_path_template,
        'quiet': False,
        'no_warnings': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        webm_file = ydl.prepare_filename(info)

    # Convert to MP3 using ffmpeg binary
    mp3_file = os.path.splitext(webm_file)[0] + ".mp3"
    print(f"Converting {webm_file} → {mp3_file}")
    ffmpeg.input(webm_file).output(mp3_file, format='mp3').run(cmd=ffmpeg_path)

    # Remove original .webm
    os.remove(webm_file)
    print(f"Done! MP3 saved to: {mp3_file}")

