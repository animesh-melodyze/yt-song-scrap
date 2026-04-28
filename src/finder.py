"""Find and download the official original song from YouTube as WAV."""
import subprocess
import sys
from pathlib import Path

_SEARCH_SUFFIXES = [
    "official lyric video",
    "official audio",
    "official music video",
    "lyrics",
]

_REJECT_KEYWORDS = [
    "karaoke", "cover", "piano", "instrumental", "backing track",
    "minus one", "sing along", "singalong", "accompaniment",
    "no vocal", "without vocal",
]


def _search_candidates(query: str, n: int = 5) -> list[dict]:
    cmd = [
        "yt-dlp", f"ytsearch{n}:{query}",
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
        candidates.append({"url": parts[0], "title": parts[1], "channel": parts[2]})
    return candidates


def _is_clean(c: dict) -> bool:
    haystack = (c["title"] + " " + c["channel"]).lower()
    return not any(kw in haystack for kw in _REJECT_KEYWORDS)


def _score(c: dict) -> int:
    ch = c["channel"].lower()
    return 2 if "vevo" in ch else (1 if "official" in ch else 0)


def find_and_download_original(
    song_name: str, artist: str, slug: str, song_dir: Path
) -> tuple[str | None, Path | None]:
    from config import FFMPEG_LOCATION

    out_path = song_dir / f"{slug}_original.wav"
    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        url_file = song_dir / f"{slug}_original.url"
        url = url_file.read_text().strip() if url_file.exists() else None
        return url, out_path

    chosen = None
    for suffix in _SEARCH_SUFFIXES:
        query = f"{song_name} {artist} {suffix}"
        print(f"  Searching: {query!r} …")
        candidates = [c for c in _search_candidates(query, n=5) if _is_clean(c)]
        if candidates:
            chosen = max(candidates, key=_score)
            print(f"  Selected: {chosen['title']!r} [{chosen['channel']}]")
            break

    if not chosen:
        print(f"  [error] No clean original found for {song_name} — {artist}", file=sys.stderr)
        return None, None

    yt_url = chosen["url"]
    print(f"  Downloading original …")
    cmd = [
        "yt-dlp", "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--ffmpeg-location", FFMPEG_LOCATION,
        "--no-warnings",
        "-o", str(song_dir / f"{slug}_original.%(ext)s"),
        yt_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [error] Download failed:\n{result.stderr}", file=sys.stderr)
        return yt_url, None

    if not out_path.exists():
        candidates_on_disk = list(song_dir.glob(f"{slug}_original.*"))
        if not candidates_on_disk:
            return yt_url, None
        out_path = candidates_on_disk[0]

    (song_dir / f"{slug}_original.url").write_text(yt_url)
    return yt_url, out_path
