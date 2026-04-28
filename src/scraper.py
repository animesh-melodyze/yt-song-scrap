"""
Fetch all videos from a YouTube channel, parse titles via LLM,
sort by view count descending. Pass top_n=None for the full channel.
"""
import re
import subprocess
import sys


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text


def fetch_channel_songs(channel_url: str, top_n: int | None = None) -> list[dict]:
    from config import LLM_MODEL
    from src.title_parser import parse_titles

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

    raw_rows = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        vid_id, title, view_str, _, url = parts[:5]
        try:
            views = int(view_str)
        except ValueError:
            views = 0
        raw_rows.append({"yt_video_id": vid_id, "raw_title": title,
                         "view_count": views, "yt_piano_url": url})

    print(f"Fetched {len(raw_rows)} videos. Parsing with LLM ({LLM_MODEL}) …")
    parsed = parse_titles([r["raw_title"] for r in raw_rows], model=LLM_MODEL)

    rows, seen_slugs = [], set()
    for raw, meta in zip(raw_rows, parsed):
        if not meta:
            continue
        song_name = (meta.get("song_name") or "").strip()
        artist = (meta.get("artist") or "").strip()
        if not song_name or not artist or meta.get("confidence") == "low":
            continue

        slug = _slugify(f"{song_name}_{artist}")
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        rows.append({
            "slug": slug,
            "song_name": song_name,
            "artist": artist,
            "is_cover": meta.get("is_cover", True),
            "genre": meta.get("genre"),
            "llm_key": meta.get("key"),
            "llm_scale": meta.get("scale"),
            "llm_tempo_bpm": meta.get("tempo_bpm"),
            "llm_time_signature": meta.get("time_signature"),
            "yt_piano_url": raw["yt_piano_url"],
            "yt_video_id": raw["yt_video_id"],
            "view_count": raw["view_count"],
            "raw_title": raw["raw_title"],
        })

    rows.sort(key=lambda r: r["view_count"], reverse=True)
    top = rows if top_n is None else rows[:top_n]
    label = "all" if top_n is None else f"top {len(top)}"
    print(f"Returning {label} unique songs sorted by view count (desc).")
    return top
