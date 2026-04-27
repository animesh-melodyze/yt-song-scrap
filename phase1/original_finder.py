"""
Search YouTube for the original (lyrical/official) version of a song and download as WAV.
Searches for "{song} {artist} official lyric video" and takes the top result.
Skips if already downloaded.
"""
import subprocess
import sys
from pathlib import Path


_SEARCH_SUFFIXES = [
    "official lyric video",
    "official audio",
    "official music video",
]


def _yt_search_url(query: str) -> str | None:
    """Return the URL of the top YouTube search result for a query."""
    cmd = [
        "yt-dlp",
        f"ytsearch1:{query}",
        "--flat-playlist",
        "--print", "%(webpage_url)s",
        "--no-warnings",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip().splitlines()[0]


def find_and_download_original(song_name: str, artist: str, slug: str, output_dir: Path) -> tuple[str | None, Path | None]:
    """
    Returns (youtube_url, local_wav_path) or (None, None) on failure.
    """
    out_path = output_dir / f"{slug}.wav"
    if out_path.exists():
        print(f"  [skip] original {slug}.wav already exists")
        # Try to recover the URL from a sidecar file
        url_file = output_dir / f"{slug}.url"
        url = url_file.read_text().strip() if url_file.exists() else None
        return url, out_path

    yt_url = None
    for suffix in _SEARCH_SUFFIXES:
        query = f"{song_name} {artist} {suffix}"
        print(f"  Searching: {query!r} …")
        yt_url = _yt_search_url(query)
        if yt_url:
            break

    if not yt_url:
        print(f"  [error] Could not find original for {song_name} — {artist}", file=sys.stderr)
        return None, None

    print(f"  Downloading original: {slug} from {yt_url} …")
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
        print(f"  [error] Download failed for {slug}:\n{result.stderr}", file=sys.stderr)
        return yt_url, None

    if not out_path.exists():
        candidates = list(output_dir.glob(f"{slug}.*"))
        if not candidates:
            return yt_url, None
        out_path = candidates[0]

    # Save URL alongside the file for resume
    (output_dir / f"{slug}.url").write_text(yt_url)
    return yt_url, out_path
