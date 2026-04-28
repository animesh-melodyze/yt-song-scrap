"""
Fetch all videos from a YouTube channel via yt-dlp.
Sort by view count descending. No LLM — raw list only.
LLM title parsing happens per-song in pipeline.py.
"""
import re
import subprocess
import sys


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:80]  # cap length


def fetch_channel_songs(channel_url: str, top_n: int | None = None) -> list[dict]:
    print(f"Fetching video list from {channel_url} …")
    print("(This may take a few minutes for large channels — one-time operation)")
    cmd = [
        "yt-dlp",
        "--no-download",
        "--print", "%(id)s\t%(title)s\t%(view_count)s\t%(webpage_url)s",
        "--no-warnings",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"yt-dlp error:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError("Failed to fetch playlist")

    rows, seen_slugs = [], set()
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        vid_id, title, view_str, url = parts[:4]
        try:
            views = int(view_str)
        except (ValueError, TypeError):
            views = 0

        slug = _slugify(title)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        rows.append({
            "slug": slug,
            "raw_title": title,
            "yt_piano_url": url,
            "yt_video_id": vid_id,
            "view_count": views,
        })

    rows.sort(key=lambda r: r["view_count"], reverse=True)
    result_rows = rows if top_n is None else rows[:top_n]
    print(f"Fetched {len(rows)} unique videos, returning {len(result_rows)} sorted by views (desc).")
    return result_rows
