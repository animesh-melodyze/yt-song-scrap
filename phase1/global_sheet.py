"""
One-time script: scrape @sing2piano, sort by view count, write data/global_songs.csv.

After running, open global_songs.csv and manually adjust the 'rank' column
to your preferred order. Phase 1 will process songs in rank order.

Run:  python phase1/global_sheet.py
      python phase1/global_sheet.py --top 200   (fetch more candidates before curating)
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import CHANNEL_URL, TOP_N, GLOBAL_SONGS_CSV
from phase1.scraper import fetch_top_songs


def generate(top_n: int, force: bool = False) -> None:
    if GLOBAL_SONGS_CSV.exists() and not force:
        print(f"global_songs.csv already exists at {GLOBAL_SONGS_CSV}")
        print("Edit it manually to adjust rankings, or re-run with --force to regenerate.")
        return

    songs = fetch_top_songs(CHANNEL_URL, top_n)

    df = pd.DataFrame(songs)
    # Add rank column (1-based, descending by view count — highest views = rank 1)
    df.insert(0, "rank", range(1, len(df) + 1))
    df = df[["rank", "slug", "song_name", "artist", "yt_piano_url", "view_count", "raw_title"]]

    GLOBAL_SONGS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(GLOBAL_SONGS_CSV, index=False)
    print(f"\nWrote {len(df)} songs → {GLOBAL_SONGS_CSV}")
    print("Open the CSV, adjust 'rank' to your preferred order, then run phase1/run.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=TOP_N, help="Number of songs to fetch")
    parser.add_argument("--force", action="store_true", help="Overwrite existing global_songs.csv")
    args = parser.parse_args()
    generate(top_n=args.top, force=args.force)
