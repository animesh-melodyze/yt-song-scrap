"""Download piano cover from YouTube and save as WAV."""
import subprocess
import sys
from pathlib import Path


def download_piano_wav(yt_url: str, slug: str, song_dir: Path) -> Path | None:
    from config import FFMPEG_LOCATION

    out_path = song_dir / f"{slug}_piano.wav"
    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        return out_path

    print(f"  Downloading piano cover …")
    cmd = [
        "yt-dlp", "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--ffmpeg-location", FFMPEG_LOCATION,
        "--no-warnings",
        "-o", str(song_dir / f"{slug}_piano.%(ext)s"),
        yt_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [error] Download failed:\n{result.stderr}", file=sys.stderr)
        return None

    if not out_path.exists():
        candidates = list(song_dir.glob(f"{slug}_piano.*"))
        return candidates[0] if candidates else None
    return out_path
