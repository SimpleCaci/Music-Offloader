import os
import requests
import yt_dlp
import ffmpeg
import stat
import zipfile
import shutil
import sys
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
# === CONFIG ===
download_dir = os.path.expanduser("~/Music")
ffmpeg_dir = os.path.expanduser("~/ffmpeg-bin")

# OS-specific URLs
if sys.platform == "win32":  # Windows build
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    ffprobe_url = ffmpeg_url  # ffprobe comes with ffmpeg in same zip
elif sys.platform == "darwin":  # macOS build
    ffmpeg_url = "https://evermeet.cx/ffmpeg/ffmpeg-6.1.1.zip"
    ffprobe_url = "https://evermeet.cx/ffmpeg/ffprobe-6.1.1.zip"
else:  # Linux or others
    ffmpeg_url = ""
    ffprobe_url = ""

# Correct paths depending on OS
ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe.exe" if sys.platform == "win32" else "ffprobe")

# === 1. Ensure ffmpeg + ffprobe installed ===
def download_and_extract(name, url):
    if not url:
        print("Please install ffmpeg manually via apt or brew for this OS.")
        return None

    os.makedirs(ffmpeg_dir, exist_ok=True)
    zip_path = os.path.join(ffmpeg_dir, name + ".zip")

    # Only download if not already present
    if not os.path.exists(ffmpeg_path):
        print(f"Downloading {name} for {platform.system()}...")
        r = requests.get(url)
        with open(zip_path, "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        os.remove(zip_path)

        # Windows builds: binaries are inside "ffmpeg-xxx/bin"
        if sys.platform == "win32":
            subfolders = [f for f in os.listdir(ffmpeg_dir) if os.path.isdir(os.path.join(ffmpeg_dir, f))]
            if subfolders:
                bin_path = os.path.join(ffmpeg_dir, subfolders[0], "bin")
                for exe in ["ffmpeg.exe", "ffprobe.exe"]:
                    src = os.path.join(bin_path, exe)
                    dst = os.path.join(ffmpeg_dir, exe)
                    if os.path.exists(src):
                        shutil.move(src, dst)
                shutil.rmtree(os.path.join(ffmpeg_dir, subfolders[0]))

        # Mark binary executable
        if os.path.exists(ffmpeg_path):
            os.chmod(ffmpeg_path, os.stat(ffmpeg_path).st_mode | stat.S_IEXEC)

    return ffmpeg_path

def ensure_ffmpeg():
    download_and_extract("ffmpeg", ffmpeg_url)
    if sys.platform == "darwin":  # Mac gets ffprobe separately
        download_and_extract("ffprobe", ffprobe_url)

# Call this before using ffmpeg
ensure_ffmpeg()

# === 2. Add Metadata Function ===
def add_metadata(mp3_file, title, uploader, thumbnail_url=None):
    try:
        audio = EasyID3(mp3_file)
    except Exception:
        audio = EasyID3()
    
    audio["title"] = title
    audio["artist"] = uploader
    audio["album"] = "YouTube Downloads"
    audio.save(mp3_file)

    # Add album art if available
    if thumbnail_url:
        try:
            img_data = requests.get(thumbnail_url).content
            tags = ID3(mp3_file)
            tags.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc=u"Cover",
                    data=img_data
                )
            )
            tags.save(mp3_file)
        except Exception as e:
            print(f"Could not add album art: {e}")

# === 3. Function to download + convert + tag ===
def download_and_convert(urlOrName):
    ensure_ffmpeg()

    # Check if it's a link or name
    if "https://y" in urlOrName:
        url = urlOrName
    else:
        url = f"ytsearch:{urlOrName}"  # Search instead of direct link

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

        if 'entries' in info:  # if searching by name
            info = info['entries'][0]

        webm_file = ydl.prepare_filename(info)

    # Convert to MP3 using ffmpeg binary
    mp3_file = os.path.splitext(webm_file)[0] + ".mp3"
    print(f"Converting {webm_file} → {mp3_file}")
    ffmpeg.input(webm_file).output(mp3_file, format='mp3').run(cmd=ffmpeg_path)

    # Remove original .webm
    os.remove(webm_file)

    # Add metadata: title, uploader, album art
    title = info.get("title", "Unknown Title")
    uploader = info.get("uploader", "Unknown Artist")
    thumbnail_url = info.get("thumbnail")
    add_metadata(mp3_file, title, uploader, thumbnail_url)

    print(f"Done! MP3 saved to: {mp3_file}")

download_and_convert("https://youtu.be/VOiag6G_zsM?si=1Sjy30VATUpr3Kz_")
