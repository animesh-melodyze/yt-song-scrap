"""
Convert piano cover WAVs to MIDI using piano_transcription_inference.
Requires GPU (run on JarvisLabs).
"""
import sys
from pathlib import Path


def transcribe_to_midi(piano_wav: Path, midi_dir: Path) -> Path | None:
    out_path = midi_dir / f"{piano_wav.stem}.mid"
    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        return out_path

    print(f"  Transcribing {piano_wav.name} → MIDI …")
    try:
        from piano_transcription_inference import PianoTranscription, sample_rate, load_audio

        audio, _ = load_audio(str(piano_wav), sr=sample_rate, mono=True)
        transcriptor = PianoTranscription(device="cuda", checkpoint_path=None)
        transcriptor.inference(audio=audio, midi_path=str(out_path))
    except ImportError:
        print("  [error] piano_transcription_inference not installed. Run: pip install piano-transcription-inference", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [error] Transcription failed for {piano_wav.name}: {e}", file=sys.stderr)
        return None

    return out_path
