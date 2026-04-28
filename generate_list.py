"""
One-time script: scrape the full channel, parse titles via LLM,
write data/global_songs.csv sorted by view count (rank 1 = most viewed).

After running, open global_songs.csv and adjust the 'rank' column manually
if needed. pipeline.py processes songs in rank order.

Run:
  python generate_list.py
  python generate_list.py --force   (overwrite existing file)
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from config import CHANNEL_URL, GLOBAL_SONGS_CSV
from src.scraper import fetch_channel_songs


def main(force: bool = False) -> None:
    if not CHANNEL_URL:
        print("[error] CHANNEL_URL is not set in .env", file=sys.stderr)
        sys.exit(1)

    if GLOBAL_SONGS_CSV.exists() and not force:
        print(f"global_songs.csv already exists at {GLOBAL_SONGS_CSV}")
        print("Adjust 'rank' manually if needed, or re-run with --force to regenerate.")
        return

    songs = fetch_channel_songs(CHANNEL_URL, top_n=None)

    df = pd.DataFrame(songs)
    df.insert(0, "rank", range(1, len(df) + 1))
    cols = ["rank", "slug", "song_name", "artist", "genre",
            "llm_key", "llm_scale", "llm_tempo_bpm", "llm_time_signature",
            "yt_piano_url", "view_count", "raw_title"]
    df = df[[c for c in cols if c in df.columns]]

    GLOBAL_SONGS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(GLOBAL_SONGS_CSV, index=False)
    print(f"\nWrote {len(df)} songs → {GLOBAL_SONGS_CSV}")
    print("Review/adjust 'rank', then run:  python pipeline.py --limit 10")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing global_songs.csv")
    args = parser.parse_args()
    main(force=args.force)
