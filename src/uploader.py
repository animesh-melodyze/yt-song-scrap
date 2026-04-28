"""Zip a song directory, upload to S3 under today's date folder, then delete local files."""
import shutil
import sys
import traceback
import zipfile
from datetime import datetime
from pathlib import Path


def _s3_client():
    try:
        import boto3
    except ImportError:
        print("[error] boto3 not installed.", file=sys.stderr)
        return None
    from config import S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_REGION
    return boto3.client(
        "s3",
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION,
    )


def _zip_dir(song_dir: Path) -> Path:
    zip_path = song_dir.parent / f"{song_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(song_dir.rglob("*")):
            if file.is_file():
                zf.write(file, file.relative_to(song_dir))
    return zip_path


def upload_and_cleanup(slug: str, song_dir: Path, bucket: str) -> str | None:
    """
    Zip song_dir → upload to {bucket}/{DD-MM-YYYY}/{slug}.zip → delete local files.
    Returns the S3 URL or None on failure.
    """
    from config import S3_REGION

    client = _s3_client()
    if not client:
        return None

    print(f"  Zipping {song_dir.name}/ …")
    try:
        zip_path = _zip_dir(song_dir)
    except Exception:
        print("  [error] Zip failed:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

    today = datetime.now().strftime("%d-%m-%Y")
    s3_key = f"{today}/{slug}.zip"
    print(f"  Uploading → s3://{bucket}/{s3_key} …")
    try:
        client.upload_file(str(zip_path), bucket, s3_key)
    except Exception:
        print("  [error] Upload failed:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        zip_path.unlink(missing_ok=True)
        return None

    # Cleanup local files
    shutil.rmtree(song_dir, ignore_errors=True)
    zip_path.unlink(missing_ok=True)
    print(f"  Cleaned up local files.")

    return f"https://{bucket}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
