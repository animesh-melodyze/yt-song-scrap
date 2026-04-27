"""
Fetch all videos from @sing2piano, sort by view count, return top N.
Deduplicates by song+artist slug so a song covered twice only counts once.
"""
import re
import json
import subprocess
import sys
from typing import Optional


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text


def _parse_title(title: str) -> tuple[Optional[str], Optional[str]]:
    """Extract (song_name, artist) from titles like 'Perfect - Ed Sheeran | Piano Cover'."""
    patterns = [
        r"^(.+?)\s*[-–]\s*(.+?)\s*[|\(]",   # Song - Artist | ...  or Song - Artist (...)
        r"^(.+?)\s*[-–]\s*(.+?)$",            # Song - Artist
    ]
    for pat in patterns:
        m = re.match(pat, title, re.IGNORECASE)
        if m:
            song = m.group(1).strip()
            artist = m.group(2).strip()
            # Filter out common noise words that end up as "artist"
            if len(artist) > 1 and not re.match(r"^(piano|cover|tutorial|sheet)$", artist, re.I):
                return song, artist
    return None, None


def fetch_top_songs(channel_url: str, top_n: int = 100) -> list[dict]:
    print(f"Fetching video list from {channel_url} …")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s\t%(view_count)s\t%(duration)s\t%(webpage_url)s",
        "--no-warnings",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"yt-dlp error:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError("Failed to fetch playlist")

    rows = []
    seen_slugs: set[str] = set()

    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        vid_id, title, view_str, duration_str, url = parts[:5]

        try:
            views = int(view_str)
        except ValueError:
            views = 0

        song_name, artist = _parse_title(title)
        if not song_name or not artist:
            continue

        slug = _slugify(f"{song_name}_{artist}")
        if slug in seen_slugs:
            continue  # deduplicate covers of the same song
        seen_slugs.add(slug)

        rows.append({
            "slug": slug,
            "song_name": song_name,
            "artist": artist,
            "yt_piano_url": url,
            "yt_video_id": vid_id,
            "view_count": views,
            "raw_title": title,
        })

    rows.sort(key=lambda r: r["view_count"], reverse=True)
    top = rows[:top_n]
    print(f"Found {len(rows)} unique songs, keeping top {len(top)} by view count.")
    return top


if __name__ == "__main__":
    from config import CHANNEL_URL, TOP_N
    songs = fetch_top_songs(CHANNEL_URL, TOP_N)
    for i, s in enumerate(songs[:5], 1):
        print(f"{i:>3}. {s['song_name']} — {s['artist']}  ({s['view_count']:,} views)")
