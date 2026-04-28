"""Split original song WAV into vocals and BGM using audio-separator (Mel-Band-Roformer)."""
import sys
import traceback
from pathlib import Path


def _model_pairs(sep) -> list[tuple[str, str]]:
    registry = sep.list_supported_model_files()
    pairs = []
    for v in registry.values():
        if isinstance(v, dict):
            for friendly, model_info in v.items():
                filename = model_info.get("filename", friendly) if isinstance(model_info, dict) else str(model_info)
                pairs.append((friendly, filename))
        elif isinstance(v, list):
            pairs.extend((n, n) for n in v)
    return pairs


def _find_model(sep) -> str:
    pairs = _model_pairs(sep)
    for friendly, filename in pairs:
        lower = friendly.lower()
        if ("melband" in lower or "roformer" in lower) and "vocal" in lower:
            return filename
    for friendly, filename in pairs:
        if "roformer" in friendly.lower():
            return filename
    for friendly, filename in pairs:
        if "vocal" in friendly.lower():
            return filename
    raise ValueError(f"No vocal model found. Available: {[f for f, _ in pairs]}")


def separate_vocals_bgm(
    original_wav: Path, song_dir: Path
) -> tuple[Path | None, Path | None]:
    slug = original_wav.stem.replace("_original", "")
    vocals_path = song_dir / f"{slug}_vocals.wav"
    bgm_path = song_dir / f"{slug}_bgm.wav"

    if vocals_path.exists() and bgm_path.exists():
        print(f"  [skip] separation already done")
        return vocals_path, bgm_path

    print(f"  Separating vocals / BGM …")
    try:
        from audio_separator.separator import Separator

        sep = Separator(output_dir=str(song_dir), output_format="wav")
        model_name = _find_model(sep)
        print(f"  Using model: {model_name}")
        sep.load_model(model_filename=model_name)
        output_files = sep.separate(str(original_wav))
    except ImportError:
        print("  [error] audio-separator not installed.", file=sys.stderr)
        return None, None
    except Exception:
        print(f"  [error] Separation failed:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None, None

    found_vocals, found_bgm = None, None
    for f in output_files:
        fp = Path(f) if Path(f).is_absolute() else song_dir / f
        lower = fp.name.lower()
        if "(vocals)" in lower:
            fp.rename(vocals_path)
            found_vocals = vocals_path
        elif "(other)" in lower or "(instrumental)" in lower or "(no vocals)" in lower:
            fp.rename(bgm_path)
            found_bgm = bgm_path

    return found_vocals, found_bgm
