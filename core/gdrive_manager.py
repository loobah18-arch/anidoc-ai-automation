"""
Google Drive Ingestion, Archive Unpacker & Smart Action Moments Slicer for AniDoc.

Features:
1. Downloads full Google Drive folders or individual files via gdown.
2. Automatically extracts archives (.zip, .rar, .7z, .tar, .tar.gz).
3. Handles weird/cryptic filenames ([SubsPlease] S02E09 [9A8C].mkv, mov_123.mp4, etc.)
   using fuzzy keyword matching to map them to characters (Gojo, Sukuna, Spiderman, etc.).
4. Runs FFmpeg audio energy analysis to cut out the top 15+ action scenes in 9:16 portrait.
"""
import os
import re
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS
from core.clip_manager import CHARACTER_THEMES

SUPPORTED_VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".m4v"}
SUPPORTED_ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}

# Character keyword matching dictionary (case-insensitive)
CHARACTER_KEYWORDS = {
    "gojo": ["gojo", "satoru", "hollow purple", "infinite void", "limitless"],
    "sukuna": ["sukuna", "ryomen", "malevolent shrine", "cleave", "dismantle", "itadori vs"],
    "toji": ["toji", "fushiguro toji", "hidden inventory", "heavenly restriction"],
    "yuji": ["yuji", "itadori", "divergent fist", "black flash"],
    "megumi": ["megumi", "fushiguro megumi", "mahoraga", "shadow puppet", "chimera"],
    "spiderman": ["spider", "spiderman", "peter", "parker", "no way home", "homecoming", "far from home", "web-slinger"],
    "ironman": ["iron man", "ironman", "tony", "stark", "mark 85", "arc reactor"],
    "thor": ["thor", "odinson", "ragnarok", "mjolnir", "stormbreaker", "god of thunder"],
    "thanos": ["thanos", "infinity war", "endgame", "mad titan", "snap"],
    "wolverine": ["wolverine", "logan", "weapon x", "adamantium", "x-men", "deadpool"],
    "loki": ["loki", "god of stories", "god of mischief", "tva", "asgard"],
}

UNIVERSE_KEYWORDS = {
    "jjk": ["jjk", "jujutsu", "kaisen", "shibuya", "cursed"],
    "marvel": ["marvel", "mcu", "avengers", "marvel studios"],
}


def extract_archive_if_needed(file_path: Path, extract_dir: Path) -> List[Path]:
    """
    Extracts zip/tar/7z/rar archives if applicable, returning all extracted video files.
    """
    extracted_videos = []
    suffix = file_path.suffix.lower()

    if suffix not in SUPPORTED_ARCHIVE_EXTS:
        return [file_path] if suffix in SUPPORTED_VIDEO_EXTS else []

    extract_dir.mkdir(parents=True, exist_ok=True)
    print(f"📦 [GDownloader] Extracting archive: {file_path.name}...")

    # 1. Try standard zipfile
    if suffix == ".zip":
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        except Exception as e:
            print(f"⚠️ Zip extraction error: {e}, attempting system unzip...")
            subprocess.run(["unzip", "-q", "-o", str(file_path), "-d", str(extract_dir)], capture_output=True)

    # 2. Try tarfile or 7z / unrar
    elif suffix in {".tar", ".gz", ".tgz"}:
        try:
            shutil.unpack_archive(str(file_path), str(extract_dir))
        except Exception as e:
            subprocess.run(["tar", "-xf", str(file_path), "-C", str(extract_dir)], capture_output=True)
    elif suffix in {".7z", ".rar"}:
        if shutil.which("7z"):
            subprocess.run(["7z", "x", f"-o{extract_dir}", "-y", str(file_path)], capture_output=True)
        elif shutil.which("unrar"):
            subprocess.run(["unrar", "x", "-o+", str(file_path), str(extract_dir)], capture_output=True)

    # Walk extracted folder and collect all video files
    for root, _, files in os.walk(extract_dir):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in SUPPORTED_VIDEO_EXTS and p.stat().st_size > 100_000:
                extracted_videos.append(p)

    print(f"✅ Extracted {len(extracted_videos)} video files from {file_path.name}")
    return extracted_videos


def identify_character_from_filename(filename: str, fallback_char: Optional[str] = None) -> str:
    """
    Smart fuzzy matcher: identifies character key even from weird/cryptic release names.
    Examples:
      - '[SubsPlease] Jujutsu Kaisen S02 - 09 (1080p) [9A8C].mkv' -> 'gojo' or 'jjk'
      - 'Spider-Man.No.Way.Home.2021.1080p.WEBRip.x264.mkv' -> 'spiderman'
      - 'iron_man_edit_4k.mp4' -> 'ironman'
      - 'clip_01_random.mp4' -> fallback_char or random JJK/Marvel
    """
    clean_name = re.sub(r"[_\.\-\[\]\(\)]+", " ", filename).lower()

    # Check specific character keywords
    for char_key, kws in CHARACTER_KEYWORDS.items():
        for kw in kws:
            if kw in clean_name:
                return char_key

    # Check universe keywords
    for univ_key, kws in UNIVERSE_KEYWORDS.items():
        for kw in kws:
            if kw in clean_name:
                if univ_key == "jjk":
                    return "gojo" if not fallback_char else fallback_char
                else:
                    return "spiderman" if not fallback_char else fallback_char

    return fallback_char if fallback_char else "gojo"


def download_from_google_drive(gdrive_url_or_id: str, download_dir: Path) -> List[Path]:
    """
    Downloads full folder or individual file from Google Drive via gdown.
    Automatically handles weird names and unzips any archives.
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    raw_files_dir = download_dir / "raw_downloads"
    raw_files_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📥 [GoogleDrive] Connecting to Google Drive source...")
    
    # Run gdown
    url = gdrive_url_or_id.strip()
    is_folder = "folders" in url or "/folders/" in url or len(url) > 20 and not url.startswith("http")

    try:
        import gdown
    except ImportError:
        subprocess.run(["pip", "install", "gdown"], capture_output=True)
        import gdown

    try:
        if is_folder or "/folders/" in url:
            print(f"📁 [GoogleDrive] Downloading entire shared folder...")
            gdown.download_folder(url=url, output=str(raw_files_dir), quiet=False, use_cookies=False)
        else:
            print(f"📄 [GoogleDrive] Downloading shared file...")
            gdown.download(url=url, output=str(raw_files_dir), quiet=False, fuzzy=True)
    except Exception as e:
        print(f"⚠️ [GoogleDrive] gdown standard download error: {e}, trying CLI command...")
        if is_folder:
            subprocess.run(["gdown", "--folder", url, "-O", str(raw_files_dir)], capture_output=True)
        else:
            subprocess.run(["gdown", url, "-O", str(raw_files_dir), "--fuzzy"], capture_output=True)

    # Process all downloaded files (including nested archives)
    all_raw_videos: List[Path] = []
    unzip_dir = download_dir / "unpacked"

    for root, _, files in os.walk(raw_files_dir):
        for f in files:
            file_p = Path(root) / f
            if file_p.suffix.lower() in SUPPORTED_ARCHIVE_EXTS:
                videos = extract_archive_if_needed(file_p, unzip_dir / file_p.stem)
                all_raw_videos.extend(videos)
            elif file_p.suffix.lower() in SUPPORTED_VIDEO_EXTS and file_p.stat().st_size > 100_000:
                all_raw_videos.append(file_p)

    print(f"🎬 [GoogleDrive] Found {len(all_raw_videos)} raw video source files ready for editing.")
    return all_raw_videos


def slice_action_moments_from_source(
    video_path: Path,
    character_key: str,
    output_dir: Path,
    n_clips: int = 15,
    clip_duration: float = 2.4
) -> List[Path]:
    """
    Scans a raw full episode/movie from Google Drive using FFmpeg audio energy analysis
    and cuts the top N loudest, most energetic action moments into 9:16 portrait clips.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Probe duration
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path)
    ]
    try:
        res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=20)
        import json
        info = json.loads(res.stdout)
        total_duration = float(info["format"].get("duration", 120.0))
    except Exception:
        total_duration = 120.0

    print(f"🔍 [ActionSlicer] Scanning '{video_path.name}' ({total_duration:.1f}s) for best combat & dialogue scenes...")

    # 2. Sliding window energy analysis
    step = 2.0 if total_duration > 600 else 1.0
    segments = []
    t = 10.0  # Skip intro logos / credits
    
    while t + clip_duration <= (total_duration - 15.0):
        cmd = [
            "ffmpeg", "-ss", str(t), "-t", str(clip_duration),
            "-i", str(video_path),
            "-af", "volumedetect",
            "-vn", "-f", "null", "-"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            mean_vol = -60.0
            for line in res.stderr.split("\n"):
                if "mean_volume" in line:
                    try:
                        mean_vol = float(line.split(":")[1].strip().split(" ")[0])
                    except Exception:
                        pass
            segments.append((t, mean_vol))
        except Exception:
            segments.append((t, -60.0))
        t += step

    # Pick top N non-overlapping loudest segments
    segments.sort(key=lambda x: x[1], reverse=True)
    selected_starts = []
    for start, energy in segments:
        if not any(abs(start - s) < (clip_duration * 1.2) for s in selected_starts):
            selected_starts.append(start)
        if len(selected_starts) >= n_clips:
            break

    selected_starts.sort()

    # 3. Cut & crop to 9:16 portrait with original audio
    generated_clips = []
    for idx, start in enumerate(selected_starts):
        out_clip = output_dir / f"{character_key}_gdrive_{idx:02d}_{int(start)}s.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(clip_duration),
            "-i", str(video_path),
            "-vf", (
                f"crop=in_h*9/16:in_h:(in_w-in_h*9/16)/2:0,"
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
                f"setsar=1,fps={FPS}"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(out_clip)
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            if out_clip.exists() and out_clip.stat().st_size > 40_000:
                generated_clips.append(out_clip)
                print(f"  ✂️ Clip {idx+1}/{len(selected_starts)} extracted ({start:.1f}s - {start+clip_duration:.1f}s)")
        except Exception as e:
            print(f"  ⚠️ Error cutting clip at {start}s: {e}")

    print(f"✅ Extracted {len(generated_clips)} unique high-definition action clips with original audio.")
    return generated_clips


def fetch_and_prepare_gdrive_footage(
    gdrive_url_or_id: str,
    target_character: str,
    output_dir: Path,
    n_clips: int = 15
) -> List[Path]:
    """
    End-to-end pipeline:
    1. Downloads Google Drive folder/file (including zip extraction).
    2. Identifies relevant video files for target character (or uses available videos).
    3. Slices top action moments into 9:16 portrait clips with original audio.
    """
    gdrive_workdir = SCRATCH_DIR / "gdrive_workspace"
    raw_videos = download_from_google_drive(gdrive_url_or_id, gdrive_workdir)
    
    if not raw_videos:
        print("⚠️ [GoogleDrive] No video files found in Google Drive download.")
        return []

    # Match raw videos to target character
    matched_videos = []
    for v in raw_videos:
        detected_char = identify_character_from_filename(v.name, fallback_char=target_character)
        if detected_char == target_character:
            matched_videos.append(v)

    # If no strict match found (e.g. generic names like 'movie.mp4'), use all available videos
    if not matched_videos:
        print(f"ℹ️ [GoogleDrive] Using all available {len(raw_videos)} videos for character '{target_character}'.")
        matched_videos = raw_videos

    all_sliced_clips = []
    clips_per_video = max(3, n_clips // len(matched_videos) + 2)

    for v in matched_videos:
        sliced = slice_action_moments_from_source(
            video_path=v,
            character_key=target_character,
            output_dir=output_dir,
            n_clips=clips_per_video
        )
        all_sliced_clips.extend(sliced)

    return all_sliced_clips
