"""
Phase 1 orchestrator.
  1. Fetch top N piano covers from @sing2piano by view count
  2. Download each as WAV
  3. Find + download the original song as WAV
  4. Detect tempo & key from original
  5. Write per-song metadata .txt and update data/songs.csv

Run:  python phase1/run.py
      python phase1/run.py --limit 3   (smoke test with 3 songs)
"""
import sys
import argparse
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import (
    CHANNEL_URL, TOP_N,
    PIANO_WAVS_DIR, ORIGINAL_WAVS_DIR, SONGS_CSV,
)
from phase1.scraper import fetch_top_songs
from phase1.downloader import download_piano_wav
from phase1.original_finder import find_and_download_original
from phase1.metadata import detect_tempo_and_key, write_metadata_txt, get_duration


def load_or_init_csv(songs: list[dict]) -> pd.DataFrame:
    if SONGS_CSV.exists():
        df = pd.read_csv(SONGS_CSV)
        # Merge in any new columns added later without losing existing data
        for col in ("phase1_done", "phase2_done"):
            if col not in df.columns:
                df[col] = False
        return df

    df = pd.DataFrame(songs)
    for col in ("yt_original_url", "tempo_bpm", "key", "duration_s",
                "piano_wav", "original_wav", "phase1_done", "phase2_done"):
        df[col] = None
    df["phase1_done"] = False
    df["phase2_done"] = False
    df.to_csv(SONGS_CSV, index=False)
    return df


def save_csv(df: pd.DataFrame) -> None:
    df.to_csv(SONGS_CSV, index=False)


def process_song(row: pd.Series) -> dict:
    slug = row["slug"]
    updates = {}

    # 1. Download piano cover
    piano_path = download_piano_wav(row["yt_piano_url"], slug, PIANO_WAVS_DIR)
    if piano_path:
        updates["piano_wav"] = str(piano_path)

    # 2. Find + download original
    yt_orig_url, orig_path = find_and_download_original(
        row["song_name"], row["artist"], slug, ORIGINAL_WAVS_DIR
    )
    if yt_orig_url:
        updates["yt_original_url"] = yt_orig_url
    if orig_path:
        updates["original_wav"] = str(orig_path)

    # 3. Detect tempo + key from original (fall back to piano cover)
    analysis_path = orig_path or piano_path
    if analysis_path and Path(analysis_path).exists():
        try:
            bpm, key = detect_tempo_and_key(Path(analysis_path))
            updates["tempo_bpm"] = bpm
            updates["key"] = key
            updates["duration_s"] = get_duration(Path(analysis_path))
        except Exception as e:
            print(f"  [warn] Audio analysis failed for {slug}: {e}", file=sys.stderr)

    # 4. Write per-song metadata .txt
    full_row = {**row.to_dict(), **updates}
    meta_dir = ORIGINAL_WAVS_DIR.parent / "metadata_txts"
    meta_dir.mkdir(exist_ok=True)
    write_metadata_txt(full_row, meta_dir / f"{slug}_metadata.txt")

    updates["phase1_done"] = bool(piano_path and orig_path)
    return updates


def main(limit: int | None = None):
    print("=== Phase 1 ===")

    # Fetch song list (always, so we can add new songs if TOP_N grows)
    songs = fetch_top_songs(CHANNEL_URL, TOP_N)
    if limit:
        songs = songs[:limit]

    df = load_or_init_csv(songs)

    # Sync any new songs into the DataFrame
    existing_slugs = set(df["slug"])
    new_rows = [s for s in songs if s["slug"] not in existing_slugs]
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        for col in df.columns:
            if col not in new_df.columns:
                new_df[col] = None
        new_df["phase1_done"] = False
        new_df["phase2_done"] = False
        df = pd.concat([df, new_df], ignore_index=True)

    pending = df[df["phase1_done"] != True]
    print(f"{len(pending)} songs pending Phase 1 processing.")

    for idx, row in pending.iterrows():
        print(f"\n[{int(idx)+1}/{len(df)}] {row['song_name']} — {row['artist']}")
        try:
            updates = process_song(row)
        except Exception as e:
            print(f"  [error] Unexpected failure: {e}", file=sys.stderr)
            continue

        for k, v in updates.items():
            df.at[idx, k] = v
        save_csv(df)

    done = df["phase1_done"].sum()
    print(f"\nPhase 1 complete. {done}/{len(df)} songs processed successfully.")
    print(f"Master CSV: {SONGS_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Process only N songs (smoke test)")
    args = parser.parse_args()
    main(limit=args.limit)
