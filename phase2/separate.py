"""
Split original song WAV into vocals and BGM using audio-separator (Mel-Band-Roformer).
Requires GPU (run on JarvisLabs).

Model name is resolved from the audio-separator registry at runtime to avoid
hardcoding a name that may differ across package versions.
"""
import sys
import traceback
from pathlib import Path


def _model_pairs(sep) -> list[tuple[str, str]]:
    """Return (friendly_name, actual_filename) pairs from the registry.

    Registry structure: {category: {friendly_name: model_info_dict}}
    where model_info_dict contains {'filename': 'actual.ckpt', ...}
    load_model() needs the filename; we search by friendly_name.
    """
    registry = sep.list_supported_model_files()
    pairs = []
    for v in registry.values():
        if isinstance(v, dict):
            for friendly, model_info in v.items():
                if isinstance(model_info, dict):
                    filename = model_info.get("filename", friendly)
                else:
                    filename = str(model_info)
                pairs.append((friendly, filename))
        elif isinstance(v, list):
            pairs.extend((n, n) for n in v)
    return pairs


def _find_model(sep) -> str:
    """Return the actual filename of the best vocal separation model."""
    pairs = _model_pairs(sep)

    # Prefer Mel-Band-Roformer vocal model (match on friendly name)
    for friendly, filename in pairs:
        lower = friendly.lower()
        if ("melband" in lower or "mel_band" in lower or "roformer" in lower) and "vocal" in lower:
            return filename
    # Any Roformer
    for friendly, filename in pairs:
        if "roformer" in friendly.lower():
            return filename
    # Fall back to any vocal model
    for friendly, filename in pairs:
        if "vocal" in friendly.lower():
            return filename

    all_friendly = [f for f, _ in pairs]
    raise ValueError(f"No vocal model found. Available: {all_friendly}")


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
