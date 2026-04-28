"""Piano cover WAV → MIDI using piano_transcription_inference."""
import sys
import traceback
from pathlib import Path


def transcribe_to_midi(piano_wav: Path, song_dir: Path) -> Path | None:
    slug = piano_wav.stem.replace("_piano", "")
    out_path = song_dir / f"{slug}_piano.mid"
    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        return out_path

    print(f"  Transcribing piano WAV → MIDI …")
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
        print(f"  [error] Transcription failed:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

    return out_path
