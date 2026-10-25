"""
Intelligent Climax & Motion-Based Scene Selector (OpenCV).
Replaces random/naive slicing with computer vision scene analysis:
1. Optical Flow / Frame Difference (cv2.absdiff): Measures fast combat motion.
2. Highlight Saturation & Brightness (HSV): Captures vibrant fire, lightning, water dragon, neon cursed energy.
3. Timeline Climax Weighting: Multiplies scores in the 40%-90% duration mark by 1.35x to guarantee climax attacks.
4. Strict Black/Dark Rejection: Rejects any window with mean_luma < 28 or frame_diff < 2.0 (fade-to-black or static shot).
5. Intro Hook Enforcement: Ensures clip 00 has active movement and applies 1.0x -> 1.15x dynamic zoom.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np


class SceneScorer:
    """
    Fast, lightweight OpenCV-based scene excitement and climax scorer.
    Downscales frames to 320x180 for low-memory, high-speed analysis.
    """

    def __init__(self, video_path: Path):
        self.video_path = Path(video_path)
        self.duration = 0.0
        self.fps = 24.0
        self.total_frames = 0
        self.window_scores: List[Dict[str, Any]] = []

    def analyze(self, step_frames: int = 4, window_duration: float = 1.5) -> List[Dict[str, Any]]:
        """
        Scans video sampling every `step_frames` to build 1.5s window excitement scores.
        Stepping every 4 frames gives ~6 samples/sec at 24fps — fast and accurate.
        """
        if not self.video_path.exists():
            return []

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            return []

        self.fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.duration = self.total_frames / self.fps if self.total_frames > 0 else 0.0

        prev_gray: Optional[np.ndarray] = None
        frame_metrics: List[Dict[str, float]] = []

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step_frames == 0:
                t = frame_idx / self.fps
                # Downsample to 320x180 for fast processing
                small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_NEAREST)
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                mean_luma = float(cv2.mean(gray)[0])

                # 1. Optical flow / frame diff
                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    diff_mean = float(cv2.mean(diff)[0])
                else:
                    diff_mean = 0.0
                prev_gray = gray

                # 2. Highlight Saturation & Brightness (HSV)
                # Anime fire, lightning, neon attacks have high saturation (>90) and bright value (>150)
                hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
                s_channel = hsv[:, :, 1]
                v_channel = hsv[:, :, 2]
                highlight_count = int(np.count_nonzero((s_channel > 90) & (v_channel > 150)))
                highlight_ratio = (highlight_count / (320.0 * 180.0)) * 100.0

                frame_metrics.append({
                    "time": t,
                    "luma": mean_luma,
                    "diff": diff_mean,
                    "highlight": highlight_ratio
                })

            frame_idx += 1

        cap.release()

        if not frame_metrics:
            return []

        # 3. Aggregate into window_duration blocks (e.g. 1.5s windows)
        windows: List[Dict[str, Any]] = []
        step_time = window_duration * 0.5
        max_time = frame_metrics[-1]["time"]
        t_win = 0.0

        while t_win + window_duration <= max_time:
            samples = [
                m for m in frame_metrics
                if t_win <= m["time"] < t_win + window_duration
            ]
            if samples:
                avg_luma = float(np.mean([s["luma"] for s in samples]))
                min_luma = float(np.min([s["luma"] for s in samples]))
                avg_diff = float(np.mean([s["diff"] for s in samples]))
                avg_high = float(np.mean([s["highlight"] for s in samples]))

                # Strict Black/Dark Frame Rejection:
                # mean_luma < 28 (fade-to-black/dark void) or avg_diff < 2.0 (frozen/static frame)
                is_rejected = (min_luma < 28.0) or (avg_diff < 2.0)

                # Timeline Weighting: Multiply scores in 40%-90% mark by 1.35x
                climax_boost = 1.35 if (0.40 * self.duration <= t_win <= 0.90 * self.duration) else 1.0

                # Base excitement: motion diff (fast combat) + highlight saturation (fire/slashes) + ambient luma
                excitement = ((avg_diff * 2.5) + (avg_high * 1.8) + (avg_luma * 0.10)) * climax_boost
                if is_rejected:
                    excitement = -100.0

                windows.append({
                    "start": round(t_win, 2),
                    "end": round(t_win + window_duration, 2),
                    "score": round(excitement, 2),
                    "avg_luma": round(avg_luma, 1),
                    "min_luma": round(min_luma, 1),
                    "avg_diff": round(avg_diff, 2),
                    "avg_highlight": round(avg_high, 2),
                    "rejected": is_rejected,
                    "climax_boost": climax_boost > 1.0
                })

            t_win += step_time

        self.window_scores = windows
        return windows

    def get_ranked_scenes(
        self,
        n_clips: int = 15,
        clip_duration: float = 2.5,
        min_gap: float = 3.5,
        start_bound: float = 10.0,
        end_bound: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Picks top n_clips high-energy timestamps that are not rejected and separated by min_gap.
        Guarantees that the #1 climax window (highest weighted score) is captured.
        """
        if not self.window_scores:
            self.analyze()

        if not self.window_scores:
            return []

        effective_end = end_bound if end_bound is not None else (self.duration - clip_duration)
        valid_windows = [
            w for w in self.window_scores
            if not w["rejected"]
            and start_bound <= w["start"]
            and (w["start"] + clip_duration) <= effective_end
        ]

        # Sort by excitement score descending
        valid_windows.sort(key=lambda w: w["score"], reverse=True)

        chosen: List[Dict[str, Any]] = []
        for w in valid_windows:
            if len(chosen) >= n_clips * 2:
                break
            # Ensure separation from already chosen timestamps
            if not any(abs(w["start"] - c["start"]) < min_gap for c in chosen):
                chosen.append(w)

        # Fallback if too few valid windows
        if len(chosen) < n_clips:
            for w in self.window_scores:
                if len(chosen) >= n_clips:
                    break
                if w["min_luma"] >= 20.0 and not any(abs(w["start"] - c["start"]) < min_gap for c in chosen):
                    chosen.append(w)

        return chosen[:n_clips]

    def find_active_intro_hook(self, max_start: float = 45.0, min_diff: float = 3.0) -> Optional[Dict[str, Any]]:
        """
        Intro Hook Enforcement (0:00–0:03):
        Ensures the first clip starts on active movement, never a static/dark frame.
        """
        if not self.window_scores:
            self.analyze()

        candidates = [
            w for w in self.window_scores
            if not w["rejected"]
            and w["start"] <= max_start
            and w["avg_diff"] >= min_diff
            and w["avg_luma"] >= 35.0
        ]
        if candidates:
            # Pick the highest motion window in the opening range
            return max(candidates, key=lambda w: w["avg_diff"])
        return None
