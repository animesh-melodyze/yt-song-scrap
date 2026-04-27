"""
Download piano cover videos from yt-dlp and convert to WAV.
Skips files that already exist (resume-safe).
"""
import subprocess
import sys
from pathlib import Path


def download_piano_wav(yt_url: str, slug: str, output_dir: Path) -> Path:
    out_path = output_dir / f"{slug}.wav"
    if out_path.exists():
        print(f"  [skip] {slug}.wav already exists")
        return out_path

    print(f"  Downloading piano cover: {slug} …")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--no-warnings",
        "-o", str(output_dir / f"{slug}.%(ext)s"),
        yt_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [error] Failed to download {slug}:\n{result.stderr}", file=sys.stderr)
        return None

    # yt-dlp may produce a different extension first before conversion
    # ensure .wav is present
    if not out_path.exists():
        candidates = list(output_dir.glob(f"{slug}.*"))
        if candidates:
            print(f"  [warn] Expected .wav but got {candidates[0].name}", file=sys.stderr)
            return candidates[0]
        return None

    return out_path
