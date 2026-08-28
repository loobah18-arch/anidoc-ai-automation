"""
Verified Event Clip Fetcher
Fetches clips from exact verified event timestamps with Drive source resolution.
NO fallback sources - only cuts verified windows from verified events.
"""
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.gdrive_manager import list_gdrive_folder_items, download_single_gdrive_file, get_english_audio_map


def resolve_and_download_source(
    source_id: str,
    drive_file_id: str,
    canonical_filename: str,
    gdrive_folder_url: str,
    cache_dir: Path
) -> Optional[Path]:
    """
    Resolve and download exact source by Drive ID.

    Args:
        source_id: Database source_id for validation
        drive_file_id: Google Drive file ID
        canonical_filename: Expected filename for validation
        gdrive_folder_url: Drive folder URL (for listing if needed)
        cache_dir: Local cache directory

    Returns:
        Path to downloaded/cached source file
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check cache first
    cached = cache_dir / canonical_filename
    if cached.exists() and cached.stat().st_size > 1_000_000:
        print(f"⚡ [VerifiedFetcher] Using cached source: {canonical_filename}")
        return cached

    print(f"📥 [VerifiedFetcher] Downloading verified source: {canonical_filename}")
    print(f"   Drive ID: {drive_file_id}")

    # Construct file info for downloader
    file_info = {
        "id": drive_file_id,
        "name": canonical_filename,
        "url": f"https://drive.google.com/uc?id={drive_file_id}"
    }

    downloaded = download_single_gdrive_file(file_info, cache_dir)

    if not downloaded or not downloaded.exists():
        raise RuntimeError(f"Failed to download source {canonical_filename} (Drive ID: {drive_file_id})")

    # Validate downloaded file matches expected
    if downloaded.name != canonical_filename:
        print(f"⚠️  [VerifiedFetcher] Filename mismatch: {downloaded.name} != {canonical_filename}")

    print(f"✅ [VerifiedFetcher] Source ready: {downloaded.name} ({downloaded.stat().st_size // (1024*1024)} MB)")

    return downloaded


def cut_verified_event_clips(
    event: Dict[str, Any],
    source_path: Path,
    output_dir: Path,
    segment_durations: List[float],
    character_key: str
) -> Dict[str, Any]:
    """
    Cut clips from verified event windows only.

    Args:
        event: Verified event with cut_windows
        source_path: Downloaded source file path
        output_dir: Output directory for clips
        segment_durations: Target durations for each beat segment
        character_key: Character for naming

    Returns:
        Dict with clip_paths and clip_manifest
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cut_windows = event.get("cut_windows", [])
    event_id = event.get("event_id", "unknown")

    if not cut_windows:
        raise RuntimeError(f"Event {event_id} has no cut_windows")

    print(f"\n✂️  [VerifiedFetcher] Cutting {len(segment_durations)} clips from {len(cut_windows)} verified windows")
    print(f"   Event: {event_id}")
    print(f"   Source: {source_path.name}")

    # Get English audio mapping
    audio_map = get_english_audio_map(source_path)

    clip_paths = []
    clip_manifest = []

    # Allocate windows to segments
    # Simple strategy: cycle through windows, prefer longer windows for longer segments
    window_idx = 0

    for seg_idx, target_duration in enumerate(segment_durations):
        if window_idx >= len(cut_windows):
            window_idx = 0

        window = cut_windows[window_idx]
        window_idx += 1

        start = window.get("start")
        end = window.get("end")

        if start is None or end is None:
            print(f"  ⚠️  Segment {seg_idx}: window missing start/end, skipping")
            continue

        window_duration = end - start
        actual_duration = min(target_duration, window_duration)

        # Use middle portion of window if it's longer than needed
        if window_duration > actual_duration:
            offset = (window_duration - actual_duration) / 2
            cut_start = start + offset
        else:
            cut_start = start

        cut_end = cut_start + actual_duration

        output_clip = output_dir / f"{character_key}_verified_{event_id}_{seg_idx:02d}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(cut_start),
            "-t", str(actual_duration),
            "-i", str(source_path),
        ] + audio_map + [
            "-vf", (
                "crop=in_h:in_h:(in_w-in_h)/2:0,"
                "scale=1080:1080,"
                "setsar=1,fps=60"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(output_clip)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)

            if output_clip.exists() and output_clip.stat().st_size > 50_000:
                clip_paths.append(output_clip)

                clip_manifest.append({
                    "segment_index": seg_idx,
                    "clip_path": str(output_clip),
                    "event_id": event_id,
                    "source_id": event.get("source_id"),
                    "window_index": window_idx - 1,
                    "cut_start": round(cut_start, 2),
                    "cut_end": round(cut_end, 2),
                    "actual_duration": round(actual_duration, 2),
                    "semantic_status": window.get("semantic_status"),
                    "scene_suitability": window.get("scene_suitability", {})
                })

                suitability = window.get("scene_suitability", {})
                suit_tags = [k for k, v in suitability.items() if v]
                suit_str = f" [{', '.join(suit_tags)}]" if suit_tags else ""

                print(f"  ✅ Clip {seg_idx+1:02d}: {cut_start:.1f}s-{cut_end:.1f}s{suit_str}")
            else:
                print(f"  ⚠️  Clip {seg_idx+1} failed: output too small")

        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Clip {seg_idx+1} timed out")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Clip {seg_idx+1} FFmpeg error: {e}")

    if not clip_paths:
        raise RuntimeError(
            f"Failed to cut any clips from event {event_id}. "
            f"Source: {source_path.name}, Windows: {len(cut_windows)}"
        )

    print(f"\n✅ [VerifiedFetcher] Cut {len(clip_paths)} verified clips from event {event_id}")

    return {
        "clip_paths": clip_paths,
        "clip_manifest": clip_manifest,
        "event_id": event_id,
        "source_id": event.get("source_id"),
        "source_filename": source_path.name
    }


def fetch_verified_event_clips(
    event: Dict[str, Any],
    gdrive_folder_url: str,
    segment_durations: List[float],
    character_key: str,
    output_dir: Path,
    cache_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Main entry point: Resolve source, download, cut verified windows.

    Args:
        event: Selected verified event from VerifiedEventDatabase
        gdrive_folder_url: Google Drive folder URL containing sources
        segment_durations: Target durations for beat segments
        character_key: Character for clip naming
        output_dir: Output directory for clips
        cache_dir: Cache directory for downloaded sources

    Returns:
        Dict with clip_paths, clip_manifest, event_id, source_trace
    """
    if cache_dir is None:
        from config.settings import SCRATCH_DIR
        cache_dir = SCRATCH_DIR / "verified_sources_cache"

    # Validate event structure
    event_id = event.get("event_id")
    source_id = event.get("source_id")
    drive_file_id = event.get("drive_file_id")
    canonical_filename = event.get("canonical_filename")

    if not all([event_id, source_id, drive_file_id, canonical_filename]):
        raise ValueError(
            f"Event missing required fields. "
            f"event_id: {event_id}, source_id: {source_id}, "
            f"drive_file_id: {drive_file_id}, canonical_filename: {canonical_filename}"
        )

    # Resolve and download source
    source_path = resolve_and_download_source(
        source_id=source_id,
        drive_file_id=drive_file_id,
        canonical_filename=canonical_filename,
        gdrive_folder_url=gdrive_folder_url,
        cache_dir=cache_dir
    )

    # Cut verified clips
    result = cut_verified_event_clips(
        event=event,
        source_path=source_path,
        output_dir=output_dir,
        segment_durations=segment_durations,
        character_key=character_key
    )

    return result

