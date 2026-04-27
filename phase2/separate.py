"""
Split original song WAV into vocals and BGM using audio-separator (Mel-Band-Roformer).
Requires GPU (run on JarvisLabs).
"""
import sys
import shutil
from pathlib import Path

# Mel-Band-Roformer model name in audio-separator's registry
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

        sep = Separator(
            model_name=_MODEL,
            output_dir=str(separated_dir),
            output_format="wav",
            use_cuda=True,
        )
        sep.load_model()
        output_files = sep.separate(str(original_wav))
    except ImportError:
        print("  [error] audio-separator not installed. Run: pip install audio-separator[gpu]", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"  [error] Separation failed for {original_wav.name}: {e}", file=sys.stderr)
        return None, None

    # audio-separator names outputs like "<slug>_(Vocals)_<model>.wav"
    # Rename to our convention
    found_vocals, found_bgm = None, None
    for f in output_files:
        fp = Path(f)
        if "Vocals" in fp.name or "vocals" in fp.name.lower():
            fp.rename(vocals_path)
            found_vocals = vocals_path
        elif "Instrumental" in fp.name or "bgm" in fp.name.lower() or "No Vocals" in fp.name:
            fp.rename(bgm_path)
            found_bgm = bgm_path

    return found_vocals, found_bgm
