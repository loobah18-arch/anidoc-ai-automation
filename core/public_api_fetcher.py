"""
Public API & GitHub Repository Video Clip Fetcher for AniDoc.
Fetches high-quality anime and MCU action scenes from GitHub repos, public video APIs, and scenepack archives.
Preserves original scene audio/SFX, supports multiple search catalogs, and applies watermark-removal crops.
"""
import os
import re
import json
import random
import shutil
import urllib.request
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import MARVEL_DIR, JJK_DIR, SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT

# Multi-Catalog Scenepack Queries for Maximum Visual Diversity
MULTI_CLIP_CATALOG = {
    # Marvel Cinematic Universe
    "spiderman": [
        "Spider-Man No Way Home Final Battle 4K 60FPS scenepack logless",
        "Spider-Man Infinity War Q-Ship Titan 4K scenepack logless",
        "Spider-Man vs Electro Green Goblin 4K 60FPS scenepack logless",
        "Spider-Man Far From Home Mysterio Drone Battle 4K scenepack logless"
    ],
    "ironman": [
        "Iron Man vs Thanos Titan Infinity War 4K 60FPS scenepack logless",
        "Iron Man Mark 85 Endgame Final Stand 4K 60FPS scenepack logless",
        "Iron Man Mark 50 Nanotech Suit-up 4K 60FPS scenepack logless"
    ],
    "thor": [
        "Thor Wakanda Stormbreaker Entry Infinity War 4K 60FPS scenepack logless",
        "Thor vs Hela Immigrant Song Ragnarok 4K 60FPS scenepack logless",
        "Thor vs Thanos Endgame Final Battle 4K 60FPS scenepack logless"
    ],
    "thanos": [
        "Thanos vs Avengers Endgame 4K 60FPS Scenepack logless no watermark",
        "Thanos Titan Battle Infinity War 4K 60FPS scenepack logless"
    ],
    "wolverine": [
        "Deadpool and Wolverine Highway Car Fight 4K 60FPS scenepack logless",
        "Wolverine vs Deadpool Forest Battle 4K 60FPS scenepack logless",
        "Logan Wolverine Berserker Rage 4K 60FPS scenepack logless"
    ],
    "loki": [
        "Loki God of Stories Season 2 Finale 4K 60FPS Scenepack logless",
        "Loki Holding the Multiverse Timeline 4K scenepack logless"
    ],
    # Jujutsu Kaisen
    "gojo": [
        "Gojo Satoru Hollow Purple Shibuya 4K 60FPS Scenepack logless",
        "Gojo vs Toji Fushiguro Hidden Inventory 4K 60FPS scenepack logless",
        "Gojo Satoru Domain Expansion Infinite Void 4K 60FPS scenepack",
        "Gojo vs Miguel JJK 0 4K 60FPS scenepack logless"
    ],
    "sukuna": [
        "Ryomen Sukuna vs Mahoraga Shibuya 4K 60FPS scenepack logless",
        "Ryomen Sukuna vs Jogo Shibuya Fire Arrow 4K 60FPS scenepack logless",
        "Sukuna Malevolent Shrine Domain Expansion 4K 60FPS scenepack logless"
    ],
    "toji": [
        "Toji Fushiguro vs Gojo Satoru 4K 60FPS scenepack logless",
        "Toji Fushiguro vs Dagon Shibuya 4K 60FPS scenepack logless",
        "Toji Fushiguro vs Megumi 4K 60FPS scenepack logless"
    ],
    "yuji": [
        "Yuji Itadori Black Flash Shibuya 4K 60FPS Scenepack logless",
        "Yuji and Todo vs Mahito Shibuya 4K 60FPS scenepack logless"
    ],
    "megumi": [
        "Megumi Fushiguro Mahoraga Summon Shibuya 4K 60FPS Scenepack logless",
        "Megumi Chimera Shadow Garden Domain Expansion 4K scenepack logless"
    ]
}


def check_clip_has_audio(path: Path) -> bool:
    """Checks if a video file has an active audio stream."""
    if not path.exists():
        return False
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_name",
        "-of", "csv=p=0",
        str(path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        return bool(res.stdout.strip())
    except Exception:
        return False


def slice_scenepack_into_clips(
    raw_video_path: Path,
    output_dir: Path,
    clip_prefix: str,
    seg_duration: float = 2.5,
    max_clips: int = 15
) -> List[Path]:
    """
    Slices raw footage into punchy 1.5s - 3.5s action clips formatted for 9:16 vertical shorts.
    Preserves original dialogue & SFX audio, and crops out edge watermarks/logos.
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
        
    print(f"✂️ Slicing '{raw_video_path.name}' ({total_dur:.1f}s) into {seg_duration}s action cuts with audio & watermark removal...")
    
    # Check if raw input has audio
    has_audio = check_clip_has_audio(raw_video_path)
    
    generated_clips = []
    # Randomized start jitter for dynamic scene sampling
    t = random.uniform(0.5, max(0.6, total_dur * 0.05))
    count = len(list(output_dir.glob(f"{clip_prefix}_clip_*.mp4")))
    added = 0
    
    # Watermark-free 9:16 crop filter (trims 24px off edges then centers)
    vf_filter = (
        f"crop=w=iw-48:h=ih-48:x=24:y=24,"
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1"
    )
    
    while t + seg_duration <= total_dur and added < max_clips:
        out_clip = output_dir / f"{clip_prefix}_clip_{count:02d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{t:.2f}",
            "-i", str(raw_video_path),
            "-t", f"{seg_duration:.2f}",
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p"
        ]
        
        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.extend(["-an"])
            
        cmd.append(str(out_clip))
        
        subprocess.run(cmd, capture_output=True)
        if out_clip.exists() and out_clip.stat().st_size > 15000:
            generated_clips.append(out_clip)
            count += 1
            added += 1
        t += seg_duration
        
    print(f"🎬 Successfully sliced {len(generated_clips)} action clips in {output_dir}")
    return generated_clips


def fetch_character_scenepack(
    character_key: str,
    custom_query_or_url: Optional[str] = None,
    max_clips: int = 12
) -> List[Path]:
    """
    Downloads and slices real 4K/1080p footage for a character with multi-query rotation.
    """
    is_marvel = character_key in ["spiderman", "ironman", "thor", "thanos", "wolverine", "loki"]
    universe_dir = MARVEL_DIR if is_marvel else JJK_DIR
    universe_dir.mkdir(parents=True, exist_ok=True)
    
    # Pick a random query from catalog to guarantee diverse scene coverage
    catalog = MULTI_CLIP_CATALOG.get(character_key, [f"{character_key} 4K 60FPS logless scenepack"])
    query = custom_query_or_url or random.choice(catalog)
    
    target = query if (query.startswith("http://") or query.startswith("https://")) else f"ytsearch1:{query}"
    
    if not shutil.which("yt-dlp"):
        print(f"⚠️ yt-dlp binary not found in PATH. Skipping online scenepack download.")
        return list(universe_dir.glob(f"*{character_key}*.mp4"))

    temp_raw = SCRATCH_DIR / f"raw_scenepack_{character_key}_{random.randint(100, 999)}.mp4"
    print(f"📥 Downloading Scenepack for '{character_key}' (Query: '{query}')...")
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "-f", "b[ext=mp4]/b",
        "-o", str(temp_raw),
        target,
        "--max-downloads", "1"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if temp_raw.exists() and temp_raw.stat().st_size > 50000:
            clips = slice_scenepack_into_clips(
                raw_video_path=temp_raw,
                output_dir=universe_dir,
                clip_prefix=character_key,
                seg_duration=2.4,
                max_clips=max_clips
            )
            temp_raw.unlink(missing_ok=True)
            return clips
    except Exception as e:
        print(f"⚠️ Scenepack download exception: {e}")
        
    return list(universe_dir.glob(f"*{character_key}*.mp4"))
