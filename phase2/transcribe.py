"""
Convert piano cover WAVs to MIDI using piano_transcription_inference.
Requires GPU (run on JarvisLabs).

Loads audio via soundfile + torchaudio instead of piano_transcription_inference's
own load_audio(), which breaks on librosa >= 0.10.
"""
import sys
import traceback
from pathlib import Path


def _load_audio(wav_path: Path, target_sr: int = 16000):
    """Load WAV and resample to target_sr using soundfile + torchaudio."""
    import soundfile as sf
    import torch
    import torchaudio.functional as F_audio
    import numpy as np

    audio, orig_sr = sf.read(str(wav_path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)  # stereo → mono
    if orig_sr != target_sr:
        tensor = torch.from_numpy(audio).unsqueeze(0)
        tensor = F_audio.resample(tensor, orig_sr, target_sr)
        audio = tensor.squeeze(0).numpy()
    return audio.astype("float32")


def transcribe_to_midi(piano_wav: Path, midi_dir: Path) -> Path | None:
    out_path = midi_dir / f"{piano_wav.stem}.mid"
    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        return out_path

    print(f"  Transcribing {piano_wav.name} → MIDI …")
    try:
        from piano_transcription_inference import PianoTranscription, sample_rate

        audio = _load_audio(piano_wav, target_sr=sample_rate)
        transcriptor = PianoTranscription(device="cuda", checkpoint_path=None)
        transcriptor.inference(audio=audio, midi_path=str(out_path))
    except ImportError:
        print("  [error] piano_transcription_inference not installed.", file=sys.stderr)
        return None
    except Exception:
        print(f"  [error] Transcription failed for {piano_wav.name}:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

    return out_path
