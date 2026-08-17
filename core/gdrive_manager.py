"""
High-Speed Google Drive Ingestion, Smart Episode Selector & Action Moments Slicer for AniDoc.

Optimized for Large Libraries (20GB+ folders):
1. Instead of downloading all 25+ episodes at once, it parses the folder index in 1 second.
2. Selects the BEST matching episode/movie for the chosen character:
   - Gojo     -> JJK S02E09 (Sealing / 0.2s Domain) or S02E04 (Gojo Awakened)
   - Sukuna   -> JJK S02E17 (Sukuna vs Mahoraga) or S02E16 (Sukuna vs Jogo)
   - Toji     -> JJK S02E03 or S02E04 (Toji vs Gojo)
   - Yuji     -> JJK S02E20 or S02E21 (Yuji & Todo vs Mahito)
   - Megumi   -> JJK S02E15 or S02E16 (Mahoraga Summon)
   - Spider-Man -> Spider-Man No Way Home Extended
   - Thor     -> Thor Ragnarok IMAX
3. Downloads ONLY that single file (~300MB - 1GB) in ~15-30 seconds via direct Google Drive API / gdown.
4. Uses FFmpeg audio energy analysis to cut out 15+ high-energy 9:16 portrait action clips with original audio.
"""
import os
import re
import random
import shutil
import zipfile
import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS

SUPPORTED_VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".m4v"}
SUPPORTED_ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}

# Character priority episode mapping for Jujutsu Kaisen Season 2 & Marvel
CHARACTER_EPISODE_PREFERENCES = {
    "gojo": ["e09", "e04", "e03", "e08", "e01", "e02", "e05"],
    "sukuna": ["e17", "e16", "e15", "e18", "e20"],
    "toji": ["e03", "e04", "e02", "e14", "e15"],
    "yuji": ["e20", "e21", "e22", "e13", "e19"],
    "megumi": ["e15", "e16", "e12", "e14"],
    "spiderman": ["spider", "no way home", "homecoming", "far from home", "peter"],
    "thor": ["thor", "ragnarok", "odinson"],
    "ironman": ["iron", "stark", "avengers"],
    "thanos": ["infinity war", "endgame", "thanos"],
    "wolverine": ["wolverine", "logan", "x-men", "deadpool"],
    "loki": ["loki", "thor"],
}


def list_gdrive_folder_items(folder_url_or_id: str) -> List[Dict[str, str]]:
    """
    Parses a public Google Drive folder in ~1 second via HTTP and extracts all file names & clean file IDs.
    """
    # Extract folder ID
    match = re.search(r"folders/([a-zA-Z0-9_-]+)", folder_url_or_id)
    folder_id = match.group(1) if match else folder_url_or_id.strip()
    url = f"https://drive.google.com/drive/folders/{folder_id}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"⚠️ [GoogleDrive] HTTP error {r.status_code} fetching folder index.")
            return []

        text = r.text
        # Regex extracting filename and ssk file ID
        matches = re.findall(
            r'aria-label=\"([^\"]+?)\s+(?:Video|Shared|Archive|Zip|Audio).*?ssk=[\'\"][^:]+:[^:]+:([a-zA-Z0-9_-]{25,})',
            text
        )

        results = []
        seen = set()
        for name, raw_fid in matches:
            # Clean file id
            clean_fid = raw_fid.split("-")[0]
            if clean_fid not in seen:
                seen.add(clean_fid)
                results.append({
                    "name": name,
                    "id": clean_fid,
                    "url": f"https://drive.google.com/uc?id={clean_fid}"
                })

        print(f"📋 [GoogleDrive] Found {len(results)} items in Google Drive folder index.")
        return results
    except Exception as e:
        print(f"⚠️ [GoogleDrive] Failed to parse folder index: {e}")
        return []


def pick_best_file_for_character(
    files: List[Dict[str, str]],
    character_key: str
) -> Optional[Dict[str, str]]:
    """
    Selects the most cinematic episode or movie for the target character.
    """
    prefs = CHARACTER_EPISODE_PREFERENCES.get(character_key, [character_key])

    # 1. Match character preferences
    for pref in prefs:
        for f in files:
            clean_name = re.sub(r"[_\.\-\[\]\(\)]+", " ", f["name"]).lower()
            # Check if pref (e.g. 'e09' or 'spider') is in clean_name
            if pref in clean_name or pref in f["name"].lower():
                print(f"🎯 [GoogleDrive] Selected best match for '{character_key}': {f['name']}")
                return f

    # 2. General universe fallback
    if character_key in {"gojo", "sukuna", "toji", "yuji", "megumi"}:
        jjk_files = [f for f in files if "jujutsu" in f["name"].lower() or "jjk" in f["name"].lower()]
        if jjk_files:
            chosen = random.choice(jjk_files)
            print(f"🎯 [GoogleDrive] Picked random JJK episode for '{character_key}': {chosen['name']}")
            return chosen
    else:
        marvel_files = [f for f in files if any(k in f["name"].lower() for k in ["spider", "thor", "iron", "marvel"])]
        if marvel_files:
            chosen = random.choice(marvel_files)
            print(f"🎯 [GoogleDrive] Picked Marvel movie for '{character_key}': {chosen['name']}")
            return chosen

    # 3. Last resort: any file
    if files:
        chosen = random.choice(files)
        print(f"🎯 [GoogleDrive] Using available file: {chosen['name']}")
        return chosen

    return None


def download_single_gdrive_file(file_info: Dict[str, str], download_dir: Path) -> Optional[Path]:
    """
    Downloads a single targeted movie or episode from Google Drive in seconds.
    Triple-fallback:
      1. High-speed direct streaming with large-file confirmation token handling
      2. Python gdown downloader
      3. yt-dlp Google Drive extractor
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    file_id = file_info["id"]
    safe_name = re.sub(r"[^\w\.-]", "_", file_info["name"])
    out_path = download_dir / safe_name

    if out_path.exists() and out_path.stat().st_size > 1_000_000:
        print(f"⚡ [GoogleDrive] File already cached: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
        return out_path

    print(f"🚀 [GoogleDrive] Downloading '{file_info['name']}' ({file_id})...")

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 1: Direct requests streaming with confirmation token handling
    # ─────────────────────────────────────────────────────────────────────────
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        init_url = "https://drive.google.com/uc?export=download"
        r = session.get(init_url, params={"id": file_id, "confirm": "t"}, stream=True, timeout=30)
        
        download_url = init_url
        download_params = {"id": file_id, "confirm": "t"}
        
        # If Google returns an HTML warning/confirmation page, extract the action & hidden inputs
        content_type = r.headers.get("content-type", "").lower()
        if "text/html" in content_type or "text/plain" in content_type:
            form_match = re.search(r'<form [^>]*action=\"([^\"]+)\"', r.text)
            if form_match:
                download_url = form_match.group(1)
                inputs = re.findall(r'<input type=\"hidden\" name=\"([^\"]+)\" value=\"([^\"]+)\"', r.text)
                download_params = dict(inputs)
            elif "confirm=" in r.text:
                c_match = re.search(r'confirm=([0-9A-Za-z_-]+)', r.text)
                if c_match:
                    download_params["confirm"] = c_match.group(1)
            
            # Follow download link
            r = session.get(download_url, params=download_params, stream=True, timeout=180)

        if r.status_code == 200:
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):  # 2MB chunks
                    if chunk:
                        f.write(chunk)
            
            if out_path.exists() and out_path.stat().st_size > 1_000_000:
                print(f"✅ [GoogleDrive] Direct stream downloaded: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
                return out_path
            else:
                print(f"⚠️ [GoogleDrive] Direct stream file too small ({out_path.stat().st_size if out_path.exists() else 0} bytes). Trying fallback...")
                if out_path.exists():
                    out_path.unlink()
    except Exception as e:
        print(f"⚠️ [GoogleDrive] Direct stream error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 2: Python gdown module
    # ─────────────────────────────────────────────────────────────────────────
    try:
        import gdown
        print(f"🔄 [GoogleDrive] Trying gdown for file {file_id}...")
        downloaded = gdown.download(id=file_id, output=str(out_path), quiet=False)
        if downloaded and Path(downloaded).exists() and Path(downloaded).stat().st_size > 1_000_000:
            print(f"✅ [GoogleDrive] gdown downloaded: {out_path.name} ({Path(downloaded).stat().st_size // (1024*1024)} MB)")
            return Path(downloaded)
    except Exception as e:
        print(f"⚠️ [GoogleDrive] gdown module error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 3: yt-dlp Google Drive extractor
    # ─────────────────────────────────────────────────────────────────────────
    try:
        print(f"🔄 [GoogleDrive] Trying yt-dlp for file {file_id}...")
        cmd = [
            "yt-dlp",
            f"https://drive.google.com/file/d/{file_id}/view",
            "-o", str(out_path),
            "--no-playlist",
            "--quiet"
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        if out_path.exists() and out_path.stat().st_size > 1_000_000:
            print(f"✅ [GoogleDrive] yt-dlp downloaded: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
            return out_path
    except Exception as e:
        print(f"⚠️ [GoogleDrive] yt-dlp error: {e}")

    return None


def slice_action_moments_from_source(
    video_path: Path,
    character_key: str,
    output_dir: Path,
    n_clips: int = 15,
    clip_duration: float = 2.4
) -> List[Path]:
    """
    Scans a raw episode/movie from Google Drive using FFmpeg audio energy analysis
    and cuts the top N loudest, most energetic action moments into 9:16 portrait clips.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
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

    print(f"🔍 [ActionSlicer] Scanning '{video_path.name}' ({total_duration:.1f}s) for best action scenes...")

    step = 2.0 if total_duration > 600 else 1.0
    segments = []
    t = 20.0  # Skip intro logos / OP
    
    while t + clip_duration <= (total_duration - 20.0):
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

    segments.sort(key=lambda x: x[1], reverse=True)
    selected_starts = []
    for start, energy in segments:
        if not any(abs(start - s) < (clip_duration * 1.3) for s in selected_starts):
            selected_starts.append(start)
        if len(selected_starts) >= n_clips:
            break

    selected_starts.sort()

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
                print(f"  ✂️ Clip {idx+1}/{len(selected_starts)} sliced ({start:.1f}s - {start+clip_duration:.1f}s)")
        except Exception as e:
            print(f"  ⚠️ Error cutting clip at {start}s: {e}")

    print(f"✅ Generated {len(generated_clips)} unique high-definition action clips with original audio.")
    return generated_clips


def fetch_and_prepare_gdrive_footage(
    gdrive_url_or_id: str,
    target_character: str,
    output_dir: Path,
    n_clips: int = 15
) -> List[Path]:
    """
    Lightning-Fast Google Drive Ingestion:
    1. Parses Google Drive folder index in 1s.
    2. Downloads ONLY the 1 best matching episode/movie for the character (~15-30s).
    3. Slices top action moments into 9:16 portrait clips with original audio.
    """
    gdrive_workdir = SCRATCH_DIR / "gdrive_workspace"
    gdrive_workdir.mkdir(parents=True, exist_ok=True)

    # 1. Parse folder items
    items = list_gdrive_folder_items(gdrive_url_or_id)
    if not items:
        print("⚠️ [GoogleDrive] No files retrieved from Google Drive folder index.")
        return []

    # 2. Pick the best episode/movie
    best_file = pick_best_file_for_character(items, target_character)
    if not best_file:
        print(f"⚠️ [GoogleDrive] No matching file found for '{target_character}'.")
        return []

    # 3. Download the single targeted video
    raw_video = download_single_gdrive_file(best_file, gdrive_workdir)
    if not raw_video:
        print(f"⚠️ [GoogleDrive] Failed to download {best_file['name']}.")
        return []

    # 4. Slice action moments
    sliced_clips = slice_action_moments_from_source(
        video_path=raw_video,
        character_key=target_character,
        output_dir=output_dir,
        n_clips=n_clips
    )

    return sliced_clips
