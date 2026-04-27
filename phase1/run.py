"""
Phase 1 orchestrator — reads from data/global_songs.csv (curated ranking).

  1. Download piano cover WAV
  2. Find + download official original song WAV
  3. Detect tempo & key from original
  4. Write per-song metadata .txt and update data/songs.csv

Generate global_songs.csv first (one-time):
  python phase1/global_sheet.py

Run:
  python phase1/run.py                        # process all pending
  python phase1/run.py --skip 0 --limit 10   # process ranks 1-10
  python phase1/run.py --skip 10 --limit 10  # process ranks 11-20
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import PIANO_WAVS_DIR, ORIGINAL_WAVS_DIR, SONGS_CSV, GLOBAL_SONGS_CSV
from phase1.downloader import download_piano_wav
from phase1.original_finder import find_and_download_original
from phase1.metadata import detect_tempo_and_key, write_metadata_txt, get_duration


def load_global_sheet() -> pd.DataFrame:
    if not GLOBAL_SONGS_CSV.exists():
        print(
            f"[error] {GLOBAL_SONGS_CSV} not found.\n"
            "Run first:  python phase1/global_sheet.py",
            file=sys.stderr,
        )
        sys.exit(1)
    df = pd.read_csv(GLOBAL_SONGS_CSV)
    return df.sort_values("rank").reset_index(drop=True)


def load_or_init_songs_csv(global_df: pd.DataFrame) -> pd.DataFrame:
    if SONGS_CSV.exists():
        df = pd.read_csv(SONGS_CSV)
        for col in ("phase1_done", "phase2_done"):
            if col not in df.columns:
                df[col] = False
        # Merge in any new slugs added to the global sheet
        existing_slugs = set(df["slug"])
        new_rows = global_df[~global_df["slug"].isin(existing_slugs)].copy()
        if not new_rows.empty:
            for col in df.columns:
                if col not in new_rows.columns:
                    new_rows[col] = None
            new_rows["phase1_done"] = False
            new_rows["phase2_done"] = False
            df = pd.concat([df, new_rows], ignore_index=True)
        return df

    df = global_df.copy()
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
    if analysis_path and Path(str(analysis_path)).exists():
        try:
            bpm, key = detect_tempo_and_key(Path(str(analysis_path)))
            updates["tempo_bpm"] = bpm
            updates["key"] = key
            updates["duration_s"] = get_duration(Path(str(analysis_path)))
        except Exception as e:
            print(f"  [warn] Audio analysis failed for {slug}: {e}", file=sys.stderr)

    # 4. Write per-song metadata .txt
    full_row = {**row.to_dict(), **updates}
    meta_dir = ORIGINAL_WAVS_DIR.parent / "metadata_txts"
    meta_dir.mkdir(exist_ok=True)
    write_metadata_txt(full_row, meta_dir / f"{slug}_metadata.txt")

    updates["phase1_done"] = bool(piano_path and orig_path)
    return updates


def main(skip: int = 0, limit: int | None = None) -> None:
    print("=== Phase 1 ===")

    global_df = load_global_sheet()

    # Apply skip/limit window against the ranked global sheet
    window = global_df.iloc[skip: (skip + limit) if limit else None]
    print(f"Global sheet: {len(global_df)} songs | processing ranks {skip+1}–{skip+len(window)}")

    songs_df = load_or_init_songs_csv(global_df)

    # Filter to songs in this window that aren't done yet
    window_slugs = set(window["slug"])
    pending = songs_df[
        songs_df["slug"].isin(window_slugs) & (songs_df["phase1_done"] != True)
    ]
    print(f"{len(pending)} songs pending in this batch.")

    for idx, row in pending.iterrows():
        rank = global_df.loc[global_df["slug"] == row["slug"], "rank"].values
        rank_str = str(rank[0]) if len(rank) else "?"
        print(f"\n[rank {rank_str}] {row['song_name']} — {row['artist']}")
        try:
            updates = process_song(row)
        except Exception as e:
            print(f"  [error] Unexpected failure: {e}", file=sys.stderr)
            continue

        for k, v in updates.items():
            songs_df.at[idx, k] = v
        save_csv(songs_df)

    done = songs_df["phase1_done"].sum()
    print(f"\nPhase 1 batch done. {done}/{len(songs_df)} songs processed in total.")
    print(f"Master CSV: {SONGS_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", type=int, default=0, help="Skip first N songs in global sheet")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N songs")
    args = parser.parse_args()
    main(skip=args.skip, limit=args.limit)
