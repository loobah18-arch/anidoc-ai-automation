#!/usr/bin/env python3
"""
JJK Episode Timestamp Database Scanner - Technical Analysis Only
Analyzes episodes using FFmpeg to build objective technical scene database.
Designed for GitHub Actions with source-stable Drive IDs and resumable scans.

NO SEMANTIC ASSUMPTIONS: Audio intensity is NOT character/action/event proof.
"""
import os
import sys
import json
import hashlib
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse

# Default configuration (overrideable via CLI/env)
DEFAULT_FOOTAGE_DIR = Path("/storage/emulated/0/Download/AniDoc-Footage")
DEFAULT_OUTPUT_DB = Path(__file__).parent.parent / "data" / "jjk_timestamp_database.json"
DEFAULT_MANIFEST = Path(__file__).parent.parent / "data" / "gdrive_source_manifest.json"
SCENE_CHANGE_THRESHOLD = 0.35
MIN_SCENE_DURATION = 2.0


def get_video_duration(video_path: Path) -> float:
    """Get total duration of video file in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"  ⚠️ Could not get duration for {video_path.name}: {e}")
        return 0.0


def detect_scene_changes(video_path: Path) -> List[float]:
    """
    Use FFmpeg scene detection to find all scene change timestamps.
    Returns list of timestamps in seconds.
    """
    print(f"  🔍 Detecting scene changes in {video_path.name}...")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-filter:v", f"select='gt(scene,{SCENE_CHANGE_THRESHOLD})',showinfo",
        "-f", "null", "-"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        timestamps = []

        # Parse ffmpeg output for pts_time values
        for line in result.stderr.split('\n'):
            if 'pts_time:' in line:
                match = re.search(r'pts_time:([\d.]+)', line)
                if match:
                    timestamps.append(float(match.group(1)))

        print(f"    ✓ Found {len(timestamps)} scene changes")
        return sorted(timestamps)
    except subprocess.TimeoutExpired:
        print(f"    ⚠️ Scene detection timed out for {video_path.name}")
        return []
    except Exception as e:
        print(f"    ⚠️ Scene detection failed: {e}")
        return []


def analyze_audio_energy(video_path: Path, timestamp: float, duration: float = 3.0) -> Dict[str, float]:
    """
    Analyze audio energy at a specific timestamp.
    Returns dict with mean_volume, max_volume, and intensity score (0-10).
    """
    cmd = [
        "ffmpeg", "-ss", str(timestamp), "-t", str(duration),
        "-i", str(video_path),
        "-af", "volumedetect",
        "-vn", "-f", "null", "-"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        mean_volume = -60.0
        max_volume = -60.0

        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                match = re.search(r'mean_volume:\s*([-\d.]+)', line)
                if match:
                    mean_volume = float(match.group(1))
            elif 'max_volume:' in line:
                match = re.search(r'max_volume:\s*([-\d.]+)', line)
                if match:
                    max_volume = float(match.group(1))

        # Convert dB to 0-10 intensity scale
        # -60dB = 0, -20dB = 5, -10dB+ = 10
        intensity = max(0.0, min(10.0, (mean_volume + 60.0) / 5.0))

        return {
            "mean_volume_db": round(mean_volume, 2),
            "max_volume_db": round(max_volume, 2),
            "intensity": round(intensity, 2)
        }
    except Exception as e:
        return {
            "mean_volume_db": -60.0,
            "max_volume_db": -60.0,
            "intensity": 0.0
        }


def classify_audio_energy_band(intensity: float) -> str:
    """
    TECHNICAL ONLY: Classify audio energy into objective bands.
    This is NOT semantic proof of action/dialogue/characters.
    """
    if intensity >= 7.0:
        return "very_high"
    elif intensity >= 5.0:
        return "high"
    elif intensity >= 3.0:
        return "medium"
    else:
        return "low"


def generate_source_id(drive_file_id: Optional[str], filename: str, file_size: int) -> str:
    """Generate deterministic source_id from Drive ID or filename+size hash."""
    if drive_file_id:
        return f"gdrive_{drive_file_id}"
    else:
        content = f"{filename}:{file_size}".encode()
        digest = hashlib.sha256(content).hexdigest()[:16]
        return f"local_{digest}"


def scan_episode(
    video_path: Path,
    drive_file_id: Optional[str] = None,
    original_filename: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Technical scan: FFmpeg probe + scene boundaries + audio energy.
    NO SEMANTIC LABELS unless verified externally.
    """
    print(f"\n📹 Scanning: {video_path.name}")

    duration = get_video_duration(video_path)
    if duration == 0.0:
        print(f"  ❌ Failed: cannot probe duration")
        return {
            "scan_status": "failed",
            "scan_error": "duration_probe_failed",
            "file_name": video_path.name
        }

    file_size = video_path.stat().st_size if video_path.exists() else 0
    source_id = generate_source_id(drive_file_id, video_path.name, file_size)

    print(f"  ⏱️  Duration: {duration:.1f}s, Size: {file_size // (1024*1024)} MB")
    print(f"  🆔 Source ID: {source_id}")

    # Detect scene changes
    scene_timestamps = detect_scene_changes(video_path)

    if not scene_timestamps:
        print(f"  ⚠️ No scenes detected, using fallback sampling every 15s")
        scene_timestamps = [float(i) for i in range(90, int(duration) - 90, 15)]

    # Build technical scene windows
    scenes = []
    for i, start_time in enumerate(scene_timestamps):
        end_time = scene_timestamps[i + 1] if i + 1 < len(scene_timestamps) else duration
        scene_duration = end_time - start_time

        if scene_duration < MIN_SCENE_DURATION:
            continue

        # Technical audio measurement
        audio_data = analyze_audio_energy(video_path, start_time, min(scene_duration, 3.0))
        audio_band = classify_audio_energy_band(audio_data["intensity"])

        scenes.append({
            "id": f"{source_id}_{i:04d}",
            "start": round(start_time, 2),
            "end": round(end_time, 2),
            "duration": round(scene_duration, 2),
            "audio_energy_band": audio_band,
            "audio_technical": audio_data,
            "scene_boundary_method": "ffmpeg_scene_detect",
            "scene_boundary_confidence": 0.8,
            "semantic": {
                "status": "unverified",
                "characters": [],
                "action": None,
                "tags": []
            }
        })

    print(f"  ✅ Extracted {len(scenes)} technical scene windows")

    # Defensive episode parsing
    season_match = re.search(r'S(\d+)E(\d+)', video_path.name, re.IGNORECASE)
    season = int(season_match.group(1)) if season_match else None
    episode = int(season_match.group(2)) if season_match else None

    return {
        "scan_status": "success",
        "source_id": source_id,
        "drive_file_id": drive_file_id,
        "original_filename": original_filename or video_path.name,
        "canonical_filename": video_path.name,
        "file_size_bytes": file_size,
        "season": season,
        "episode": episode,
        "duration": round(duration, 2),
        "total_scenes": len(scenes),
        "scenes": scenes,
        "scan_version": "1.0.0",
        "scanned_at": datetime.utcnow().isoformat() + "Z"
    }


def load_existing_database(db_path: Path) -> Dict[str, Any]:
    """Load existing database for merge/resume."""
    if db_path.exists():
        try:
            with open(db_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load existing database: {e}")

    return {
        "version": "1.0.0",
        "generated_at": None,
        "total_episodes": 0,
        "total_scenes": 0,
        "episodes": {},
        "events": []
    }


def build_database(
    footage_dir: Path,
    output_db: Path,
    manifest_path: Optional[Path] = None,
    episodes_limit: Optional[int] = None,
    resume: bool = True
):
    """
    Main scanner: technical analysis with stable source IDs and resumable operation.
    """
    print("=" * 80)
    print("🎬 JJK Technical Timestamp Scanner v1.0")
    print("=" * 80)

    # Load manifest if provided
    manifest = None
    if manifest_path and manifest_path.exists():
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        print(f"📋 Loaded manifest with {len(manifest.get('sources', []))} sources")

    # Load existing DB for resume
    database = load_existing_database(output_db) if resume else {
        "version": "1.0.0",
        "generated_at": None,
        "total_episodes": 0,
        "total_scenes": 0,
        "episodes": {},
        "events": []
    }

    if not footage_dir.exists():
        print(f"❌ Footage directory not found: {footage_dir}")
        return

    # Find video files
    video_files = []
    for ext in ['.mkv', '.mp4', '.avi']:
        video_files.extend(sorted(footage_dir.glob(f"*{ext}")))

    if episodes_limit:
        video_files = video_files[:episodes_limit]

    print(f"\n📂 Found {len(video_files)} video files")

    # Scan each episode
    scanned_count = 0
    failed_count = 0
    skipped_count = 0

    for video_path in video_files:
        # Check if already scanned successfully
        existing_entry = None
        for ep_data in database["episodes"].values():
            if ep_data.get("canonical_filename") == video_path.name:
                if ep_data.get("scan_status") == "success":
                    existing_entry = ep_data
                    break

        if existing_entry:
            print(f"\n⏭️  Skipping {video_path.name} (already scanned)")
            skipped_count += 1
            continue

        # Find Drive ID from manifest
        drive_file_id = None
        original_filename = None
        if manifest:
            for source in manifest.get("sources", []):
                if source.get("canonical_filename") == video_path.name:
                    drive_file_id = source.get("drive_file_id")
                    original_filename = source.get("original_filename")
                    break

        episode_data = scan_episode(video_path, drive_file_id, original_filename)

        if episode_data:
            if episode_data.get("scan_status") == "success":
                source_id = episode_data["source_id"]
                database["episodes"][source_id] = episode_data
                scanned_count += 1
            else:
                failed_count += 1
                database["episodes"][f"failed_{video_path.stem}"] = episode_data

    # Update totals
    database["generated_at"] = datetime.utcnow().isoformat() + "Z"
    database["total_episodes"] = len([e for e in database["episodes"].values() if e.get("scan_status") == "success"])
    database["total_scenes"] = sum(e.get("total_scenes", 0) for e in database["episodes"].values() if e.get("scan_status") == "success")

    # Save
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with open(output_db, "w") as f:
        json.dump(database, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ Database saved: {output_db}")
    print(f"📊 Scanned: {scanned_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    print(f"📊 Total Episodes: {database['total_episodes']}")
    print(f"📊 Total Scenes: {database['total_scenes']}")
    print(f"📊 Database Size: {output_db.stat().st_size / 1024:.1f} KB")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="JJK Technical Timestamp Scanner")
    parser.add_argument("--footage-dir", type=str, default=str(DEFAULT_FOOTAGE_DIR),
                        help="Directory containing video files")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DB),
                        help="Output database JSON path")
    parser.add_argument("--manifest", type=str, default=None,
                        help="Source manifest JSON (with Drive IDs)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of episodes to scan")
    parser.add_argument("--no-resume", action="store_true",
                        help="Start fresh (don't merge with existing DB)")

    args = parser.parse_args()

    build_database(
        footage_dir=Path(args.footage_dir),
        output_db=Path(args.output),
        manifest_path=Path(args.manifest) if args.manifest else None,
        episodes_limit=args.limit,
        resume=not args.no_resume
    )


if __name__ == "__main__":
    main()
