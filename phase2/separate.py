"""
Split original song WAV into vocals and BGM using audio-separator (Mel-Band-Roformer).
Requires GPU (run on JarvisLabs).
"""
import sys
import traceback
from pathlib import Path

# Mel-Band-Roformer vocal model filename in audio-separator's registry
_MODEL = "MelBandRoformer.ckpt"


def separate_vocals_bgm(original_wav: Path, separated_dir: Path) -> tuple[Path | None, Path | None]:
    slug = original_wav.stem
    vocals_path = separated_dir / f"{slug}_vocals.wav"
    bgm_path = separated_dir / f"{slug}_bgm.wav"

    if vocals_path.exists() and bgm_path.exists():
        print(f"  [skip] {slug} separation already done")
        return vocals_path, bgm_path

    print(f"  Separating vocals/BGM: {original_wav.name} …")
    try:
        from audio_separator.separator import Separator

        # model_name moved from __init__() to load_model() in audio-separator >=0.17
        sep = Separator(
            output_dir=str(separated_dir),
            output_format="wav",
        )
        sep.load_model(model_filename=_MODEL)
        output_files = sep.separate(str(original_wav))
    except ImportError:
        print("  [error] audio-separator not installed. Run: pip install audio-separator[gpu]", file=sys.stderr)
        return None, None
    except Exception:
        print(f"  [error] Separation failed for {original_wav.name}:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None, None

    # audio-separator names outputs like "<slug>_(Vocals)_<model>.wav"
    # Rename to our convention
    found_vocals, found_bgm = None, None
    for f in output_files:
        fp = Path(f)
        lower = fp.name.lower()
        if "vocals" in lower or "(vocals)" in lower:
            fp.rename(vocals_path)
            found_vocals = vocals_path
        elif "instrumental" in lower or "no vocals" in lower or "bgm" in lower:
            fp.rename(bgm_path)
            found_bgm = bgm_path

    return found_vocals, found_bgm
