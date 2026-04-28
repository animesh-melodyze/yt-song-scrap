import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Channel
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
TOP_N = int(os.getenv("TOP_N", "100"))

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SONGS_CSV = DATA_DIR / "songs.csv"
GLOBAL_SONGS_CSV = DATA_DIR / "global_songs.csv"

DATA_DIR.mkdir(exist_ok=True)

# ffmpeg (system install path)
FFMPEG_LOCATION = os.getenv("FFMPEG_LOCATION", str(Path.home() / "bin"))

# LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-nano")

# AWS S3
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "")
S3_REGION = os.getenv("S3_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
