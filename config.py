import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Channel
CHANNEL_URL = "https://www.youtube.com/@sing2piano/videos"
TOP_N = 100

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PIANO_WAVS_DIR = DATA_DIR / "piano_wavs"
ORIGINAL_WAVS_DIR = DATA_DIR / "original_wavs"
MIDI_DIR = DATA_DIR / "midi"
SEPARATED_DIR = DATA_DIR / "separated"
SONGS_CSV = DATA_DIR / "songs.csv"

for _d in (PIANO_WAVS_DIR, ORIGINAL_WAVS_DIR, MIDI_DIR, SEPARATED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# AWS S3
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "")
S3_REGION = os.getenv("S3_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
