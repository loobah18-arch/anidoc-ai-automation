#!/usr/bin/env python3
"""
Automated Scenepack Downloader & Scene Slicer for Marvel & Jujutsu Kaisen 4K Edits.
Downloads raw 1080p/4K scenepacks using yt-dlp and slices them into high-action cut clips.
"""
import sys
import subprocess
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MARVEL_DIR = BASE_DIR / "assets" / "video" / "marvel"
JJK_DIR = BASE_DIR / "assets" / "video" / "jjk"

# Curated High-Quality Scenepack Search Queries for Marvel & JJK
SCENEPACK_QUERIES = {
    "spiderman": "Spider-Man Infinity War 4K 60FPS Scenepack no music no subs",
    "ironman": "Iron Man Endgame 4K 60FPS Scenepack logless",
    "thor": "Thor Infinity War Wakanda 4K 60FPS Scenepack",
    "thanos": "Thanos Infinity War 4K 60FPS Scenepack",
    "gojo": "Gojo Satoru Hollow Purple 4K 60FPS Scenepack no text",
    "sukuna": "Sukuna Malevolent Shrine Shibuya 4K 60FPS Scenepack",
    "toji": "Toji Fushiguro Shibuya 4K 60FPS Scenepack",
    "yuji": "Yuji Itadori Black Flash 4K 60FPS Scenepack"
}

def slice_video_into_action_clips(video_path: Path, output_dir: Path, clip_prefix: str, seg_duration: float = 3.0, max_clips: int = 15):
    """
    Slices a downloaded raw scenepack video into individual 2-4 second action clips.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Probe duration
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    try:
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        total_dur = float(res.stdout.strip())
    except Exception:
        total_dur = 30.0
        
    print(f"✂️ Slicing {video_path.name} (Total: {total_dur:.1f}s) into {seg_duration}s action clips...")
    
    clip_count = 0
    t = 0.0
    while t < total_dur - seg_duration and clip_count < max_clips:
        out_clip = output_dir / f"{clip_prefix}_clip_{clip_count:02d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{t:.2f}",
            "-i", str(video_path),
            "-t", f"{seg_duration:.2f}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-an",  # Remove original audio
            "-pix_fmt", "yuv420p",
            str(out_clip)
        ]
        subprocess.run(cmd, capture_output=True)
        if out_clip.exists() and out_clip.stat().st_size > 10000:
            clip_count += 1
        t += seg_duration
        
    print(f"✅ Generated {clip_count} ready-to-use clips in {output_dir}")

def fetch_scenepack_for_character(character_key: str, custom_url: str = None):
    """
    Downloads scenepack via yt-dlp and automatically slices it into action clips.
    """
    universe_dir = MARVEL_DIR if character_key in ["spiderman", "ironman", "thor", "thanos"] else JJK_DIR
    universe_dir.mkdir(parents=True, exist_ok=True)
    
    tmp_raw = universe_dir / f"raw_scenepack_{character_key}.mp4"
    
    if custom_url:
        target = custom_url
    else:
        query = SCENEPACK_QUERIES.get(character_key, f"{character_key} 4K 60FPS scenepack")
        target = f"ytsearch1:{query}"
        
    print(f"📥 Downloading raw scenepack for '{character_key}' ({target})...")
    dl_cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4][height<=1080]/best[ext=mp4]",
        "--no-playlist",
        "-o", str(tmp_raw),
        target
    ]
    res = subprocess.run(dl_cmd)
    if res.returncode == 0 and tmp_raw.exists():
        print(f"✅ Downloaded raw scenepack: {tmp_raw.name} ({tmp_raw.stat().st_size // 1024} KB)")
        slice_video_into_action_clips(tmp_raw, universe_dir, clip_prefix=character_key)
        tmp_raw.unlink(missing_ok=True)
    else:
        print(f"⚠️ Notice: yt-dlp download skipped or completed without raw file.")

def main():
    parser = argparse.ArgumentParser(description="Fetch and slice 4K scenepacks for Marvel & JJK edits")
    parser.add_argument("--character", type=str, required=True, help="Character key (e.g. spiderman, gojo, sukuna, thor, ironman)")
    parser.add_argument("--url", type=str, default=None, help="Custom YouTube URL for a specific scenepack")
    args = parser.parse_args()
    
    fetch_scenepack_for_character(args.character.lower(), args.url)

if __name__ == "__main__":
    main()
