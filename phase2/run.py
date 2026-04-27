"""
Phase 2 orchestrator — runs on JarvisLabs GPU instance.
  1. Piano WAV → MIDI (piano_transcription_inference)
  2. Original WAV → Vocals + BGM (audio-separator / Mel-Band-Roformer)
  3. Upload everything to Cloudflare R2

Prerequisites:
  uv sync --group phase2
  Copy .env with S3 credentials to this machine.
  Copy data/ directory from Phase 1 (or mount the same volume).

Run:
  python phase2/run.py
  python phase2/run.py --limit 1   (smoke test)
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import SONGS_CSV, PIANO_WAVS_DIR, ORIGINAL_WAVS_DIR, MIDI_DIR, SEPARATED_DIR, S3_BUCKET_NAME
from phase2.transcribe import transcribe_to_midi
from phase2.separate import separate_vocals_bgm
from phase2.upload import upload_song


def main(limit: int | None = None):
    print("=== Phase 2 ===")

    if not SONGS_CSV.exists():
        print(f"[error] {SONGS_CSV} not found. Run Phase 1 first.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(SONGS_CSV)

    if "phase2_done" not in df.columns:
        df["phase2_done"] = False

    pending = df[(df["phase1_done"] == True) & (df["phase2_done"] != True)]
    if limit:
        pending = pending.head(limit)

    print(f"{len(pending)} songs pending Phase 2 processing.")

    for idx, row in pending.iterrows():
        slug = row["slug"]
        print(f"\n[{idx+1}/{len(df)}] {row['song_name']} — {row['artist']}")

        piano_wav = Path(row["piano_wav"]) if pd.notna(row.get("piano_wav")) else None
        orig_wav = Path(row["original_wav"]) if pd.notna(row.get("original_wav")) else None
        meta_txt = Path(str(PIANO_WAVS_DIR).replace("piano_wavs", "metadata_txts")) / f"{slug}_metadata.txt"
        if not meta_txt.exists():
            meta_txt = None

        # 1. Piano → MIDI
        midi_path = None
        if piano_wav and piano_wav.exists():
            midi_path = transcribe_to_midi(piano_wav, MIDI_DIR)

        # 2. Original → Vocals + BGM
        vocals_path, bgm_path = None, None
        if orig_wav and orig_wav.exists():
            vocals_path, bgm_path = separate_vocals_bgm(orig_wav, SEPARATED_DIR)

        # 3. Upload to S3
        uploaded = upload_song(
            slug=slug,
            piano_wav=piano_wav,
            midi_file=midi_path,
            vocals_wav=vocals_path,
            bgm_wav=bgm_path,
            metadata_txt=meta_txt,
            bucket=S3_BUCKET_NAME,
        )

        phase2_ok = bool(midi_path and vocals_path and bgm_path and uploaded)
        df.at[idx, "phase2_done"] = phase2_ok
        df.at[idx, "s3_piano_wav"] = uploaded.get(f"{slug}/piano/{slug}.wav")
        df.at[idx, "s3_midi"] = uploaded.get(f"{slug}/piano/{slug}.mid")
        df.at[idx, "s3_vocals"] = uploaded.get(f"{slug}/original_song/{slug}_vocals.wav")
        df.at[idx, "s3_bgm"] = uploaded.get(f"{slug}/original_song/{slug}_bgm.wav")
        df.to_csv(SONGS_CSV, index=False)

    done = df["phase2_done"].sum()
    print(f"\nPhase 2 complete. {done}/{len(df)} songs fully processed.")
    print(f"Updated CSV: {SONGS_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Process only N songs (smoke test)")
    args = parser.parse_args()
    main(limit=args.limit)
