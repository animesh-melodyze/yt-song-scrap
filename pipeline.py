"""
Production pipeline — single GPU instance, single process.

For each song (in rank order from global_songs.csv):
  1. Download piano cover WAV
  2. Find + download original song WAV
  3. Analyse audio (librosa tempo / key / duration)
  4. Write metadata.txt
  5. Transcribe piano WAV → MIDI
  6. Separate original → vocals + BGM
  7. Zip all assets → upload to S3: {bucket}/{DD-MM-YYYY}/{slug}.zip
  8. Delete local song directory

Run:
  python pipeline.py                        # all pending
  python pipeline.py --skip 0  --limit 10  # ranks 1–10
  python pipeline.py --skip 10 --limit 10  # ranks 11–20
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from config import (
    CHANNEL_URL, DATA_DIR, SONGS_CSV, GLOBAL_SONGS_CSV, S3_BUCKET_NAME
)
from src.title_parser import parse_title
from src.downloader import download_piano_wav
from src.finder import find_and_download_original
from src.metadata import analyse_audio, write_metadata_txt
from src.transcriber import transcribe_to_midi
from src.separator import separate_vocals_bgm
from src.uploader import upload_and_cleanup


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_global_sheet() -> pd.DataFrame:
    if not GLOBAL_SONGS_CSV.exists():
        print(
            "[error] global_songs.csv not found.\n"
            "Run first:  python generate_list.py",
            file=sys.stderr,
        )
        sys.exit(1)
    return pd.read_csv(GLOBAL_SONGS_CSV).sort_values("rank").reset_index(drop=True)


_STRING_COLS = [
    "slug", "raw_title", "yt_piano_url", "yt_video_id",
    "song_name", "artist", "genre", "llm_key", "llm_scale",
    "llm_time_signature", "yt_original_url", "s3_url", "librosa_key",
]


def _cast_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col in _STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype(object)
    return df


def _load_or_init_songs_csv(global_df: pd.DataFrame) -> pd.DataFrame:
    all_output_cols = [
        "song_name", "artist", "genre", "llm_key", "llm_scale",
        "llm_tempo_bpm", "llm_time_signature",
        "yt_original_url", "librosa_tempo_bpm", "librosa_key",
        "duration_s", "s3_url", "done",
    ]

    if SONGS_CSV.exists():
        df = pd.read_csv(SONGS_CSV)
        for col in all_output_cols:
            if col not in df.columns:
                df[col] = None
        df["done"] = df["done"].fillna(False)
        new_rows = global_df[~global_df["slug"].isin(set(df["slug"]))].copy()
        if not new_rows.empty:
            for col in df.columns:
                if col not in new_rows.columns:
                    new_rows[col] = None
            new_rows["done"] = False
            df = pd.concat([df, new_rows], ignore_index=True)
        return _cast_dtypes(df)

    df = global_df.copy()
    for col in all_output_cols:
        df[col] = None
    df["done"] = False
    df.to_csv(SONGS_CSV, index=False)
    return _cast_dtypes(df)


def _save(df: pd.DataFrame) -> None:
    _cast_dtypes(df)
    df.to_csv(SONGS_CSV, index=False)


# ── per-song processing ───────────────────────────────────────────────────────

def process_song(row: pd.Series) -> dict:
    from config import LLM_MODEL

    slug = row["slug"]
    song_dir = DATA_DIR / slug
    song_dir.mkdir(parents=True, exist_ok=True)
    updates = {}

    # 1. LLM: parse title → song metadata (only for this one song)
    print(f"  [LLM] Parsing title …")
    meta = parse_title(row["raw_title"], model=LLM_MODEL) or {}
    song_name = (meta.get("song_name") or "").strip()
    artist = (meta.get("artist") or "").strip()
    if not song_name or not artist:
        print(f"  [error] LLM could not extract song/artist from: {row['raw_title']!r}", file=sys.stderr)
        return {"done": False}

    updates.update({
        "song_name": song_name,
        "artist": artist,
        "genre": meta.get("genre"),
        "llm_key": meta.get("key"),
        "llm_scale": meta.get("scale"),
        "llm_tempo_bpm": meta.get("tempo_bpm"),
        "llm_time_signature": meta.get("time_signature"),
    })

    # 2. Piano cover
    piano_wav = download_piano_wav(row["yt_piano_url"], slug, song_dir)

    # 3. Original song
    yt_orig_url, orig_wav = find_and_download_original(
        song_name, artist, slug, song_dir
    )
    if yt_orig_url:
        updates["yt_original_url"] = yt_orig_url

    # 4. Audio analysis (from original, fall back to piano)
    analysis_src = orig_wav or piano_wav
    if analysis_src and analysis_src.exists():
        try:
            audio_meta = analyse_audio(analysis_src)
            updates.update(audio_meta)
        except Exception as e:
            print(f"  [warn] Audio analysis failed: {e}", file=sys.stderr)

    # 5. Metadata txt
    write_metadata_txt(
        {**row.to_dict(), **updates, "yt_original_url": yt_orig_url},
        song_dir / f"{slug}_metadata.txt",
    )

    # 6. MIDI transcription
    midi = None
    if piano_wav and piano_wav.exists():
        midi = transcribe_to_midi(piano_wav, song_dir)

    # 7. Vocal / BGM separation
    vocals, bgm = None, None
    if orig_wav and orig_wav.exists():
        vocals, bgm = separate_vocals_bgm(orig_wav, song_dir)

    # 7. Zip + upload + cleanup
    s3_url = upload_and_cleanup(slug, song_dir, S3_BUCKET_NAME)
    if s3_url:
        updates["s3_url"] = s3_url

    updates["done"] = bool(piano_wav and orig_wav and midi and vocals and bgm and s3_url)
    return updates


# ── main ─────────────────────────────────────────────────────────────────────

def main(skip: int = 0, limit: int | None = None) -> None:
    if not CHANNEL_URL:
        print("[error] CHANNEL_URL is not set in .env", file=sys.stderr)
        sys.exit(1)
    if not S3_BUCKET_NAME:
        print("[error] S3_BUCKET_NAME is not set in .env", file=sys.stderr)
        sys.exit(1)

    print("=== Pipeline ===")
    global_df = _load_global_sheet()
    window = global_df.iloc[skip: (skip + limit) if limit else None]
    print(f"Global sheet: {len(global_df)} songs | batch: ranks {skip + 1}–{skip + len(window)}")

    songs_df = _load_or_init_songs_csv(global_df)
    window_slugs = set(window["slug"])
    pending = songs_df[songs_df["slug"].isin(window_slugs) & (songs_df["done"] != True)]
    print(f"{len(pending)} songs pending.\n")

    for idx, row in pending.iterrows():
        rank = global_df.loc[global_df["slug"] == row["slug"], "rank"].values
        rank_str = str(int(rank[0])) if len(rank) else "?"
        print(f"[rank {rank_str}/{len(global_df)}] {row['raw_title']}")
        try:
            updates = process_song(row)
        except Exception as e:
            print(f"  [error] Unexpected failure: {e}", file=sys.stderr)
            continue

        for k, v in updates.items():
            songs_df.at[idx, k] = v
        _save(songs_df)
        status = "✓" if updates.get("done") else "✗ partial"
        print(f"  → {status}\n")

    done = int(songs_df["done"].sum())
    print(f"Batch complete. {done}/{len(songs_df)} songs fully processed.")
    print(f"State: {SONGS_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(skip=args.skip, limit=args.limit)
