"""
Fetch all videos from a YouTube channel via yt-dlp.
Uses --flat-playlist --dump-json for speed while capturing real view counts.
Sort by view count descending. No LLM — raw list only.
"""
import json
import re
import subprocess
import sys


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:80]


def fetch_channel_songs(channel_url: str, top_n: int | None = None) -> list[dict]:
    print(f"Fetching video list from {channel_url} …")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"yt-dlp error:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError("Failed to fetch playlist")

    rows, seen_slugs = [], set()
    for line in result.stdout.strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        title = entry.get("title") or ""
        if not title:
            continue

        slug = _slugify(title)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        rows.append({
            "slug": slug,
            "raw_title": title,
            "yt_piano_url": entry.get("webpage_url") or entry.get("url") or "",
            "yt_video_id": entry.get("id") or "",
            "view_count": int(entry.get("view_count") or 0),
        })

    rows.sort(key=lambda r: r["view_count"], reverse=True)
    result_rows = rows if top_n is None else rows[:top_n]
    print(f"Fetched {len(rows)} unique videos, returning {len(result_rows)} sorted by view count (desc).")
    return result_rows
