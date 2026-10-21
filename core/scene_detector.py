"""
PySceneDetect Integration for AniDoc 4K Anime Edits.
Uses content-aware visual thresholding to slice anime fights on exact keyframe scene transitions,
preventing awkward mid-combat cuts.
"""
import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from scenedetect import detect, ContentDetector, AdaptiveDetector
    SCENEDETECT_AVAILABLE = True
except ImportError:
    SCENEDETECT_AVAILABLE = False


def detect_scene_cut_timestamps(
    video_path: Path,
    min_scene_len_sec: float = 1.0,
    max_scene_len_sec: float = 4.0,
    threshold: float = 27.0
) -> List[Tuple[float, float]]:
    """
    Detects natural scene cuts in an anime video file using PySceneDetect.
    Falls back to FFmpeg scene score analysis if scenedetect package is not installed.
    Returns a list of (start_sec, end_sec) tuples.
    """
    if not video_path.exists():
        return []

    scenes = []

    if SCENEDETECT_AVAILABLE:
        try:
            print(f"🎬 [PySceneDetect] Running ContentDetector on '{video_path.name}' (threshold={threshold})...")
            scene_list = detect(str(video_path), ContentDetector(threshold=threshold, min_scene_len=int(min_scene_len_sec * 24)))
            for start_tc, end_tc in scene_list:
                s = start_tc.get_seconds()
                e = end_tc.get_seconds()
                dur = e - s
                if dur >= min_scene_len_sec:
                    # If a detected scene is too long, cap it
                    if dur > max_scene_len_sec:
                        e = s + max_scene_len_sec
                    scenes.append((round(s, 2), round(e, 2)))
            if scenes:
                print(f"✅ [PySceneDetect] Detected {len(scenes)} natural scene cuts in '{video_path.name}'.")
                return scenes
        except Exception as err:
            print(f"⚠️ [PySceneDetect] Failed to run scenedetect: {err}, falling back to FFmpeg...")

    # Fallback: FFmpeg showinfo scene detection
    return detect_scenes_via_ffmpeg(video_path, min_scene_len_sec, max_scene_len_sec)


def detect_scenes_via_ffmpeg(
    video_path: Path,
    min_scene_len_sec: float = 1.0,
    max_scene_len_sec: float = 4.0
) -> List[Tuple[float, float]]:
    """
    Fallback scene cut detection using FFmpeg select='gt(scene,0.3)'.
    """
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-filter_complex", "select='gt(scene,0.3)',showinfo",
        "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        cut_pts = []
        for line in proc.stderr.splitlines():
            if "pts_time:" in line:
                for part in line.split():
                    if part.startswith("pts_time:"):
                        try:
                            cut_pts.append(float(part.split(":")[1]))
                        except ValueError:
                            pass
        
        # Build segment pairs
        scenes = []
        last_t = 0.0
        for t in cut_pts:
            if t - last_t >= min_scene_len_sec:
                end_t = min(t, last_t + max_scene_len_sec)
                scenes.append((round(last_t, 2), round(end_t, 2)))
                last_t = t
        if scenes:
            return scenes
    except Exception as e:
        print(f"⚠️ [SceneDetector] FFmpeg fallback error: {e}")

    # Default procedural 2.5s slices
    return [(i * 2.5, (i + 1) * 2.5) for i in range(10)]
