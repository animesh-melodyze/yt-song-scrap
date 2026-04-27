"""
Search YouTube for the official original song (lyrical/audio) and download as WAV.

Strategy:
  - Fetch top 5 results per query (not just 1)
  - Reject any result whose title/channel contains karaoke/cover/instrumental keywords
  - Prefer VEVO or official artist channels
  - Fall back through multiple query suffixes before giving up
"""
import subprocess
import sys
from pathlib import Path

from config import FFMPEG_LOCATION

_SEARCH_SUFFIXES = [
    "official lyric video",
    "official audio",
    "official music video",
    "lyrics",
]

# Titles/channels containing any of these are rejected
_REJECT_KEYWORDS = [
    "karaoke",
    "cover",
    "piano",
    "instrumental",
    "backing track",
    "minus one",
    "sing along",
    "singalong",
    "accompaniment",
    "no vocal",
    "without vocal",
]


def _search_candidates(query: str, n: int = 5) -> list[dict]:
    """Return up to n results for a YouTube search query with title, channel, url."""
    cmd = [
        "yt-dlp",
        f"ytsearch{n}:{query}",
        "--flat-playlist",
        "--print", "%(webpage_url)s\t%(title)s\t%(channel)s",
        "--no-warnings",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []

    candidates = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        url, title, channel = parts
        candidates.append({"url": url, "title": title, "channel": channel})
    return candidates


def _is_clean(candidate: dict) -> bool:
    """Return True if the result looks like an official track (not karaoke/cover)."""
    haystack = (candidate["title"] + " " + candidate["channel"]).lower()
    return not any(kw in haystack for kw in _REJECT_KEYWORDS)


def _score(candidate: dict) -> int:
    """Higher score = more likely to be the official upload."""
    channel = candidate["channel"].lower()
    if "vevo" in channel:
        return 2
    if "official" in channel:
        return 1
    return 0


def _pick_best(candidates: list[dict]) -> dict | None:
    clean = [c for c in candidates if _is_clean(c)]
    if not clean:
        return None
    return max(clean, key=_score)


def find_and_download_original(
    song_name: str, artist: str, slug: str, output_dir: Path
) -> tuple[str | None, Path | None]:
    """Returns (youtube_url, local_wav_path) or (None, None) on failure."""
    out_path = output_dir / f"{slug}.wav"
    if out_path.exists():
        print(f"  [skip] original {slug}.wav already exists")
        url_file = output_dir / f"{slug}.url"
        url = url_file.read_text().strip() if url_file.exists() else None
        return url, out_path

    chosen = None
    for suffix in _SEARCH_SUFFIXES:
        query = f"{song_name} {artist} {suffix}"
        print(f"  Searching: {query!r} …")
        candidates = _search_candidates(query, n=5)
        chosen = _pick_best(candidates)
        if chosen:
            print(f"  Selected: {chosen['title']!r} [{chosen['channel']}]")
            break

    if not chosen:
        print(f"  [error] No clean original found for {song_name} — {artist}", file=sys.stderr)
        return None, None

    yt_url = chosen["url"]
    print(f"  Downloading: {slug} …")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--ffmpeg-location", FFMPEG_LOCATION,
        "--no-warnings",
        "-o", str(output_dir / f"{slug}.%(ext)s"),
        yt_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [error] Download failed for {slug}:\n{result.stderr}", file=sys.stderr)
        return yt_url, None

    if not out_path.exists():
        candidates_on_disk = list(output_dir.glob(f"{slug}.*"))
        if not candidates_on_disk:
            return yt_url, None
        out_path = candidates_on_disk[0]

    (output_dir / f"{slug}.url").write_text(yt_url)
    return yt_url, out_path
