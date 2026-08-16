"""
Public API & GitHub Repository Video Clip Fetcher for AniDoc.
Fetches high-quality anime and MCU action scenes from GitHub repos, public video APIs, and scenepack archives.
"""
import os
import re
import json
import urllib.request
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import MARVEL_DIR, JJK_DIR, SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT

# Curated High-Action Scenepack Queries for Marvel, JJK, and Anime
CURATED_CLIP_QUERIES = {
    # Marvel Cinematic Universe
    "spiderman": "Spider-Man No Way Home 4K 60FPS Scenepack no music no subs",
    "ironman": "Iron Man Mark 85 Endgame 4K 60FPS Scenepack logless",
    "thor": "Thor Wakanda Infinity War 4K 60FPS Scenepack",
    "thanos": "Thanos vs Avengers Endgame 4K 60FPS Scenepack",
    "wolverine": "Deadpool and Wolverine 4K 60FPS Scenepack no music",
    "loki": "Loki God of Stories Season 2 4K 60FPS Scenepack",
    # Jujutsu Kaisen
    "gojo": "Gojo Satoru Hollow Purple Shibuya 4K 60FPS Scenepack no text",
    "sukuna": "Ryomen Sukuna Malevolent Shrine Shibuya 4K 60FPS Scenepack",
    "toji": "Toji Fushiguro vs Gojo 4K 60FPS Scenepack",
    "yuji": "Yuji Itadori Black Flash Shibuya 4K 60FPS Scenepack",
    "megumi": "Megumi Fushiguro Mahoraga Summon 4K 60FPS Scenepack",
    "maki": "Maki Zenin Awakened 4K 60FPS Scenepack"
}

# Public GitHub Repositories hosting curated open video clips & anime datasets
KNOWN_PUBLIC_GITHUB_REPOS = [
    "https://github.com/intel-isl/OpenDriveDataset",
    "https://github.com/loobah18-arch/anidoc-ai-automation"
]


def slice_scenepack_into_clips(
    raw_video_path: Path,
    output_dir: Path,
    clip_prefix: str,
    seg_duration: float = 2.5,
    max_clips: int = 12
) -> List[Path]:
    """
    Slices raw footage into punchy 1.5s - 3.5s action clips formatted for 9:16 vertical shorts.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Probe duration
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(raw_video_path)
    ]
    try:
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        total_dur = float(res.stdout.strip())
    except Exception:
        total_dur = 20.0
        
    print(f"✂️ Slicing '{raw_video_path.name}' ({total_dur:.1f}s) into {seg_duration}s action cuts...")
    
    generated_clips = []
    t = 0.5  # Skip first 0.5s of potential logo/fade
    count = 0
    
    while t + seg_duration <= total_dur and count < max_clips:
        out_clip = output_dir / f"{clip_prefix}_clip_{count:02d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{t:.2f}",
            "-i", str(raw_video_path),
            "-t", f"{seg_duration:.2f}",
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-an",  # Strip audio for phonk synchronization
            "-pix_fmt", "yuv420p",
            str(out_clip)
        ]
        subprocess.run(cmd, capture_output=True)
        if out_clip.exists() and out_clip.stat().st_size > 15000:
            generated_clips.append(out_clip)
            count += 1
        t += seg_duration
        
    print(f"🎬 Successfully sliced {len(generated_clips)} action clips in {output_dir}")
    return generated_clips


def fetch_from_github_repo(
    repo_url: str,
    target_dir: Path,
    character_filter: Optional[str] = None
) -> List[Path]:
    """
    Fetches raw video clips from a public GitHub repository (using GitHub API or raw content).
    repo_url format: 'https://github.com/owner/repo' or 'owner/repo'
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    clean_repo = repo_url.replace("https://github.com/", "").strip("/")
    parts = clean_repo.split("/")
    if len(parts) < 2:
        print(f"⚠️ Invalid GitHub repository format: {repo_url}")
        return []
        
    owner, repo = parts[0], parts[1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/assets/video"
    
    print(f"🌐 Querying GitHub API for clips: {owner}/{repo}...")
    headers = {"User-Agent": "AniDoc-ClipFetcher/2.0"}
    downloaded_clips = []
    
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                items = json.loads(response.read().decode("utf-8"))
                for item in items:
                    name = item.get("name", "")
                    download_url = item.get("download_url")
                    if download_url and name.endswith((".mp4", ".mov", ".mkv")):
                        if character_filter and character_filter.lower() not in name.lower():
                            continue
                        dest = target_dir / name
                        print(f"📥 Downloading GitHub clip: {name}...")
                        urllib.request.urlretrieve(download_url, dest)
                        if dest.exists() and dest.stat().st_size > 10000:
                            downloaded_clips.append(dest)
    except Exception as e:
        print(f"⚠️ Notice accessing GitHub API ({api_url}): {e}")
        
    return downloaded_clips


def fetch_character_scenepack(
    character_key: str,
    custom_query_or_url: Optional[str] = None,
    max_clips: int = 10
) -> List[Path]:
    """
    Downloads and slices real 4K/1080p footage for a character.
    Saves to the appropriate universe directory (marvel or jjk).
    """
    is_marvel = character_key in ["spiderman", "ironman", "thor", "thanos", "wolverine", "loki"]
    universe_dir = MARVEL_DIR if is_marvel else JJK_DIR
    universe_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we already have clips for this character
    existing_clips = list(universe_dir.glob(f"*{character_key}*.mp4"))
    if len(existing_clips) >= 4:
        print(f"✨ Found {len(existing_clips)} existing clips for '{character_key}' in {universe_dir.name}")
        return existing_clips
        
    temp_raw = SCRATCH_DIR / f"raw_scenepack_{character_key}.mp4"
    query = custom_query_or_url or CURATED_CLIP_QUERIES.get(character_key, f"{character_key} 4K 60FPS scenepack")
    
    target = query if (query.startswith("http://") or query.startswith("https://")) else f"ytsearch1:{query}"
    
    print(f"📥 Downloading Scenepack for '{character_key}' via public streamer...")
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "-f", "b[ext=mp4]/b",
        "-o", str(temp_raw),
        target,
        "--max-downloads", "1"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if temp_raw.exists() and temp_raw.stat().st_size > 50000:
        clips = slice_scenepack_into_clips(
            raw_video_path=temp_raw,
            output_dir=universe_dir,
            clip_prefix=character_key,
            seg_duration=2.5,
            max_clips=max_clips
        )
        temp_raw.unlink(missing_ok=True)
        return clips
    else:
        print(f"⚠️ Scenepack download returned status: {res.returncode}")
        return []
