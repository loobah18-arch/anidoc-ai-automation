"""
Ultimate-AMV Dead-Frame & Action Density Detector (ElishaPervez/Ultimate-AMV)
=============================================================================
Fast lightweight motion-delta analyzer based on Ultimate-AMV's dead-frame engine.

In anime, animation is often drawn on "twos" or "threes" (stills held across 2-3 frames),
and dialogue scenes frequently feature static holds. 

This detector:
  1. Decodes video clips via FFmpeg at 160px grayscale into raw numpy frames (~1ms/frame).
  2. Computes mean absolute pixel difference between consecutive frames.
  3. Detects static/dead frames (scores < threshold) to prune idle pauses.
  4. Computes an overall "Action Density" score [0.0 - 1.0] so the pipeline prioritizes
     explosive sakuga and high-motion combat moments over talking heads.
"""
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False


MEASURE_WIDTH = 160
MIN_THRESHOLD = 0.001
THRESHOLD_SPAN = 0.029
DEFAULT_SENSITIVITY = 18.0


def _get_removal_threshold(sensitivity: float = DEFAULT_SENSITIVITY) -> float:
    dial = max(0.0, min(100.0, float(sensitivity)))
    return MIN_THRESHOLD + (dial / 100.0) * THRESHOLD_SPAN


def measure_clip_motion(
    video_path: Path,
    max_duration: float = 10.0,
    sample_fps: int = 15,
) -> Dict[str, Any]:
    """
    Decodes video at 160px grayscale and returns frame-by-frame motion delta scores.
    Scores range from 0.0 (identical duplicate frame) to 1.0 (black-to-white flash).
    """
    if not _NUMPY_AVAILABLE or not Path(video_path).exists():
        return {"action_score": 0.60, "deadframe_ratio": 0.0, "scores": []}

    try:
        # Probe dimensions
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,r_frame_rate",
            "-of", "csv=p=0:s=x",
            str(video_path)
        ]
        probe_out = subprocess.check_output(probe_cmd, text=True, timeout=5).strip()
        parts = probe_out.split("x")
        orig_w = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 1920
        orig_h = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1080
    except Exception:
        orig_w, orig_h = 1920, 1080

    target_w = MEASURE_WIDTH
    target_h = int(round(target_w * orig_h / max(1, orig_w) / 2.0)) * 2
    target_h = max(2, target_h)
    frame_bytes = target_w * target_h

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-t", str(max_duration),
        "-i", str(video_path),
        "-map", "0:v:0",
        "-r", str(sample_fps),
        "-vf", f"scale={target_w}:{target_h},format=gray",
        "-f", "rawvideo",
        "-pix_fmt", "gray",
        "pipe:1"
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        scores = []
        previous = None

        while True:
            raw_frame = proc.stdout.read(frame_bytes)
            if not raw_frame or len(raw_frame) < frame_bytes:
                break
            frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape(target_h, target_w).astype(np.int16)
            if previous is None:
                scores.append(1.0)  # Opening frame is novel
            else:
                diff = float(np.mean(np.abs(frame - previous))) / 255.0
                scores.append(diff)
            previous = frame

        proc.stdout.close()
        proc.wait(timeout=5)

        if not scores:
            return {"action_score": 0.50, "deadframe_ratio": 0.0, "scores": []}

        # Calculate metrics
        thresh = _get_removal_threshold(DEFAULT_SENSITIVITY)
        scores_arr = np.asarray(scores, dtype=float)
        dead_count = np.sum(scores_arr[1:] < thresh)
        dead_ratio = float(dead_count / max(1, len(scores_arr) - 1))

        # Action density is weighted mean motion omitting duplicate holds
        motion_scores = scores_arr[1:]
        non_dead = motion_scores[motion_scores >= thresh]
        avg_motion = float(np.mean(non_dead)) if len(non_dead) > 0 else 0.01

        # Normalized action score [0.0 - 1.0] (0.05 is decent action, 0.15+ is intense sakuga)
        action_score = float(np.clip(avg_motion / 0.12, 0.0, 1.0) * (1.0 - dead_ratio * 0.5))

        return {
            "action_score": round(action_score, 3),
            "deadframe_ratio": round(dead_ratio, 3),
            "mean_motion": round(avg_motion, 4),
            "scores": scores,
        }

    except Exception as e:
        return {"action_score": 0.50, "deadframe_ratio": 0.0, "scores": []}


def filter_action_packed_clips(
    clip_paths: List[Path],
    min_action_score: float = 0.25,
) -> List[Path]:
    """
    Ranks and filters a list of candidate video clips, filtering out
    static holds and low-motion clips.
    """
    if len(clip_paths) <= 2:
        return clip_paths

    scored = []
    for p in clip_paths:
        res = measure_clip_motion(p, max_duration=4.0)
        scored.append((p, res.get("action_score", 0.50)))

    # Sort descending by action score
    scored.sort(key=lambda item: item[1], reverse=True)
    filtered = [p for p, sc in scored if sc >= min_action_score]

    # If filtering removed too many clips, return top performers
    if len(filtered) < max(2, len(clip_paths) // 2):
        return [p for p, _ in scored]

    return filtered
