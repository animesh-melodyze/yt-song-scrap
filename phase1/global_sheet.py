"""
One-time script: scrape the ENTIRE @sing2piano channel, sort all videos by
view count descending, and write data/global_songs.csv.

After running, open global_songs.csv and manually adjust the 'rank' column
to reorder songs. Phase 1 processes songs in rank order (ascending rank = higher priority).

Run:  python phase1/global_sheet.py
      python phase1/global_sheet.py --force   (overwrite existing file)
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import CHANNEL_URL, GLOBAL_SONGS_CSV
from phase1.scraper import fetch_top_songs


def generate(force: bool = False) -> None:
    if GLOBAL_SONGS_CSV.exists() and not force:
        print(f"global_songs.csv already exists at {GLOBAL_SONGS_CSV}")
        print("Edit it manually to adjust rankings, or re-run with --force to regenerate.")
        return

    # Fetch ALL videos from the channel (top_n=None)
    songs = fetch_top_songs(CHANNEL_URL, top_n=None)

    df = pd.DataFrame(songs)
    # rank 1 = highest view count (already sorted desc by fetch_top_songs)
    df.insert(0, "rank", range(1, len(df) + 1))
    df = df[["rank", "slug", "song_name", "artist", "yt_piano_url", "view_count", "raw_title"]]

    GLOBAL_SONGS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(GLOBAL_SONGS_CSV, index=False)
    print(f"\nWrote {len(df)} songs → {GLOBAL_SONGS_CSV}")
    print("Open the CSV, adjust 'rank' to your preferred order, then run phase1/run.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing global_songs.csv")
    args = parser.parse_args()
    generate(force=args.force)
