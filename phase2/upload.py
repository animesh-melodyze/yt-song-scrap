"""
Upload processed files to AWS S3 with the bucket structure:
  {slug}/piano/{slug}.wav
  {slug}/piano/{slug}.mid
  {slug}/original_song/{slug}_vocals.wav
  {slug}/original_song/{slug}_bgm.wav
  {slug}/song_metadata/{slug}_metadata.txt
"""
import sys
from pathlib import Path
from typing import Optional


def _get_s3_client():
    try:
        import boto3
        from config import S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_REGION
        return boto3.client(
            "s3",
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            region_name=S3_REGION,
        )
    except ImportError:
        print("[error] boto3 not installed. Run: pip install boto3", file=sys.stderr)
        return None


def upload_file(client, bucket: str, local_path: Path, s3_key: str) -> bool:
    print(f"  Uploading {s3_key} …")
    try:
        client.upload_file(str(local_path), bucket, s3_key)
        return True
    except Exception as e:
        print(f"  [error] Upload failed for {s3_key}: {e}", file=sys.stderr)
        return False


def upload_song(
    slug: str,
    piano_wav: Optional[Path],
    midi_file: Optional[Path],
    vocals_wav: Optional[Path],
    bgm_wav: Optional[Path],
    metadata_txt: Optional[Path],
    bucket: str,
) -> dict[str, str]:
    """Upload all files for one song. Returns dict of {asset: s3_url}."""
    client = _get_s3_client()
    if client is None:
        return {}

    from config import S3_REGION
    assets = {
        f"{slug}/piano/{slug}.wav": piano_wav,
        f"{slug}/piano/{slug}.mid": midi_file,
        f"{slug}/original_song/{slug}_vocals.wav": vocals_wav,
        f"{slug}/original_song/{slug}_bgm.wav": bgm_wav,
        f"{slug}/song_metadata/{slug}_metadata.txt": metadata_txt,
    }

    uploaded: dict[str, str] = {}
    for s3_key, local_path in assets.items():
        if local_path and Path(local_path).exists():
            ok = upload_file(client, bucket, Path(local_path), s3_key)
            if ok:
                uploaded[s3_key] = f"https://{bucket}.s3.{S3_REGION}.amazonaws.com/{s3_key}"

    return uploaded
