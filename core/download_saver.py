"""
Local Device Download Saver for Termux / Android.
Saves rendered anime edits directly to the user's Downloads folder (/sdcard/Download)
so they appear immediately in the Gallery, Files, and Video Player apps with zero cloud upload.
"""
import os
import shutil
from pathlib import Path
from typing import Optional


def get_device_download_dir() -> Path:
    """
    Finds the user's active Android/Termux Download directory.
    Checks symlinks and system mount points in order of preference.
    """
    candidates = [
        Path("/data/data/com.termux/files/home/storage/downloads"),
        Path("/data/data/com.termux/files/home/storage/shared/Download"),
        Path("/sdcard/Download"),
        Path("/storage/emulated/0/Download"),
        Path.home() / "downloads",
        Path.home() / "Download",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p

    # Fallback to home/downloads
    fallback = Path.home() / "downloads"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def save_to_downloads(source_video: Path, custom_name: Optional[str] = None) -> Optional[Path]:
    """
    Copies the rendered video file to the user's Download directory.
    Returns the destination Path on success.
    """
    if not source_video.exists():
        print(f"⚠️ [DownloadSaver] Source video not found: {source_video}")
        return None

    download_dir = get_device_download_dir()
    download_dir.mkdir(parents=True, exist_ok=True)

    if custom_name:
        clean_name = custom_name if custom_name.endswith(".mp4") else f"{custom_name}.mp4"
    else:
        clean_name = source_video.name

    dest_path = download_dir / clean_name
    shutil.copy2(source_video, dest_path)

    size_mb = dest_path.stat().st_size / (1024 * 1024)
    print(f"💾 [DownloadSaver] Successfully saved to device Download folder:")
    print(f"   📁 Path: {dest_path}")
    print(f"   📊 Size: {size_mb:.2f} MB")
    return dest_path
