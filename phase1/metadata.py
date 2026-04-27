"""
Extract tempo and musical key from an audio file using librosa.
Build per-song metadata text files and update the master songs.csv.
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path

_KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_MODE_NAMES = ["major", "minor"]

# Krumhansl-Schmuckler key profiles
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def detect_tempo_and_key(wav_path: Path) -> tuple[float, str]:
    """Return (bpm, key_string) for a WAV file. key_string e.g. 'A major'."""
    y, sr = librosa.load(str(wav_path), mono=True, duration=120)  # first 2 min is enough

    # Tempo
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])

    # Key via Krumhansl-Schmuckler
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    mean_chroma = chroma.mean(axis=1)

    best_score, best_key = -np.inf, "C major"
    for root in range(12):
        rotated = np.roll(mean_chroma, -root)
        for profile, mode in [(_MAJOR_PROFILE, "major"), (_MINOR_PROFILE, "minor")]:
            score = np.corrcoef(rotated, profile)[0, 1]
            if score > best_score:
                best_score = score
                best_key = f"{_KEY_NAMES[root]} {mode}"

    return round(bpm, 1), best_key


def write_metadata_txt(
    song: dict,
    output_path: Path,
) -> None:
    lines = [
        f"Song Name: {song.get('song_name', '')}",
        f"Artist: {song.get('artist', '')}",
        f"Tempo (BPM): {song.get('tempo_bpm', '')}",
        f"Key: {song.get('key', '')}",
        f"Duration (s): {song.get('duration_s', '')}",
        f"YouTube Piano Cover: {song.get('yt_piano_url', '')}",
        f"YouTube Original: {song.get('yt_original_url', '')}",
    ]
    output_path.write_text("\n".join(lines) + "\n")


def get_duration(wav_path: Path) -> float:
    info = sf.info(str(wav_path))
    return round(info.duration, 1)
