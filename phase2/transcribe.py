"""
Convert piano cover WAVs to MIDI using piano_transcription_inference.
Requires GPU (run on JarvisLabs).

Loads audio via soundfile + torchaudio instead of piano_transcription_inference's
own load_audio(), which breaks on librosa >= 0.10.
"""
import sys
import traceback
from pathlib import Path


def transcribe_to_midi(piano_wav: Path, midi_dir: Path) -> Path | None:
    out_path = midi_dir / f"{piano_wav.stem}.mid"
    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        return out_path

    print(f"  Transcribing {piano_wav.name} → MIDI …")
    try:
        import librosa
        from piano_transcription_inference import PianoTranscription, sample_rate

        audio, _ = librosa.load(str(piano_wav), sr=sample_rate, mono=True)
        transcriptor = PianoTranscription(device="cuda", checkpoint_path=None)
        transcriptor.transcribe(audio, str(out_path))
    except ImportError:
        print("  [error] piano_transcription_inference not installed.", file=sys.stderr)
        return None
    except Exception:
        print(f"  [error] Transcription failed for {piano_wav.name}:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

    return out_path
