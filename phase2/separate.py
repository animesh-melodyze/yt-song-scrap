"""
Split original song WAV into vocals and BGM using audio-separator (Mel-Band-Roformer).
Requires GPU (run on JarvisLabs).

Model name is resolved from the audio-separator registry at runtime to avoid
hardcoding a name that may differ across package versions.
"""
import sys
import traceback
from pathlib import Path


def _find_model(sep) -> str:
    """Return the first Mel-Band-Roformer vocal model name from the registry."""
    models: dict = sep.list_supported_model_files()
    # Prefer a vocals-specific Mel-Band-Roformer model
    for name in models:
        lower = name.lower()
        if ("melband" in lower or "mel_band" in lower) and "vocal" in lower:
            return name
    # Fall back to any Mel-Band-Roformer model
    for name in models:
        if "melband" in name.lower() or "mel_band" in name.lower():
            return name
    available = ", ".join(list(models)[:10])
    raise ValueError(f"No Mel-Band-Roformer model found in registry. First 10 available: {available}")


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

        sep = Separator(
            output_dir=str(separated_dir),
            output_format="wav",
        )
        model_name = _find_model(sep)
        print(f"  Using model: {model_name}")
        sep.load_model(model_filename=model_name)
        output_files = sep.separate(str(original_wav))
    except ImportError:
        print("  [error] audio-separator not installed. Run: pip install audio-separator[gpu]", file=sys.stderr)
        return None, None
    except Exception:
        print(f"  [error] Separation failed for {original_wav.name}:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None, None

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
