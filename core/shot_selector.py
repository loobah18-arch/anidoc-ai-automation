"""
Smart Shot Selection and Variable Pacing Engine (Phase 2 & Phase 7).
Scores candidate anime footage for visual quality, action/motion, face visibility,
and composition, eliminating duplicate content and assigning shots to narrative acts
(Hook -> Build -> Escalation -> Climax -> Payoff) with dynamic variable pacing.
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from core.smart_reframe import detect_subject_focus, detect_active_content_bounds


def compute_frame_color_histogram(frame: np.ndarray) -> np.ndarray:
    """Computes a lightweight 24-bin HSV color histogram for shot deduplication."""
    if not OPENCV_AVAILABLE or frame is None or frame.size == 0:
        return np.zeros(24, dtype=np.float32)
    small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist_h = cv2.calcHist([hsv], [0], None, [12], [0, 180])
    hist_s = cv2.calcHist([hsv], [1], None, [8], [0, 256])
    hist_v = cv2.calcHist([hsv], [2], None, [4], [0, 256])
    hist = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])
    norm = np.linalg.norm(hist)
    return hist / (norm + 1e-6)


def score_candidate_shot(clip_path: Union[str, Path], num_samples: int = 4) -> Dict[str, Any]:
    """
    Evaluates a candidate video shot across:
    1. Visual Quality (Sharpness & clean exposure)
    2. Action / Motion Dynamics (Frame difference energy)
    3. Subject / Face Visibility (Anime face detection & saliency)
    4. Composition & Framing
    Returns comprehensive scoring metrics and color fingerprint.
    """
    clip_p = Path(clip_path)
    default_res = {
        "path": clip_p,
        "total_score": 60.0,
        "quality_score": 60.0,
        "action_score": 50.0,
        "subject_score": 50.0,
        "composition_score": 60.0,
        "fingerprint": np.zeros(24, dtype=np.float32),
        "duration": 2.0
    }

    if not clip_p.exists() or not OPENCV_AVAILABLE:
        return default_res

    cap = cv2.VideoCapture(str(clip_p))
    if not cap.isOpened():
        return default_res

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    duration = total_frames / fps if fps > 0 else 2.0

    if total_frames < 3:
        cap.release()
        return default_res

    frame_indices = [
        int(total_frames * (i + 1) / (num_samples + 1))
        for i in range(num_samples)
    ]

    frames = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret and frame is not None:
            frames.append(frame)
    cap.release()

    if not frames:
        return default_res

    # 1. Visual Quality: Sharpness (Laplacian var) and Exposure
    sharpness_scores = []
    exposure_scores = []
    for f in frames:
        gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        lap_var = cv2.Laplacian(gray, cv2.CV_32F).var()
        # Scale: variance >= 250 is very sharp (100 pts), < 20 is blurry (0 pts)
        s_score = float(np.clip((lap_var - 20) / 2.3, 0.0, 100.0))
        sharpness_scores.append(s_score)

        mean_val = float(np.mean(gray))
        # Ideal exposure mean is between 50 and 170
        if 50 <= mean_val <= 170:
            exp_score = 100.0
        elif mean_val < 50:
            exp_score = max(0.0, (mean_val / 50.0) * 100.0)
        else:
            exp_score = max(0.0, ((255 - mean_val) / 85.0) * 100.0)
        exposure_scores.append(exp_score)

    quality_score = float(np.mean(sharpness_scores) * 0.65 + np.mean(exposure_scores) * 0.35)

    # 2. Action / Motion Dynamics (Inter-frame difference)
    motion_scores = []
    for i in range(len(frames) - 1):
        g1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(frames[i+1], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(g1, g2)
        diff_mean = float(np.mean(diff))
        # Scale: diff >= 35 is intense combat motion (100 pts), < 5 is static (20 pts)
        m_score = float(np.clip(diff_mean * 2.8, 15.0, 100.0))
        motion_scores.append(m_score)
    action_score = float(np.mean(motion_scores)) if motion_scores else 50.0

    # 3. Subject Visibility & Composition
    subject_scores = []
    comp_scores = []
    for f in frames:
        cx, cy, conf = detect_subject_focus(f)
        # Face confidence = 1.0 (95-100 pts), saliency = 0.6 (70 pts), fallback = 0.0 (40 pts)
        subj_score = conf * 60.0 + 40.0
        subject_scores.append(subj_score)

        # Rule of thirds composition (focal point near 0.33, 0.50, or 0.67)
        dist_from_sweet_spot = min(abs(cx - 0.35), abs(cx - 0.50), abs(cx - 0.65))
        c_score = max(40.0, 100.0 - (dist_from_sweet_spot * 150.0))
        comp_scores.append(c_score)

    subject_score = float(np.mean(subject_scores))
    composition_score = float(np.mean(comp_scores))

    # Color Fingerprint (middle frame)
    mid_frame = frames[len(frames) // 2]
    fingerprint = compute_frame_color_histogram(mid_frame)

    # Total Score
    total_score = (
        quality_score * 0.25 +
        action_score * 0.35 +
        subject_score * 0.25 +
        composition_score * 0.15
    )

    return {
        "path": clip_p,
        "total_score": round(total_score, 1),
        "quality_score": round(quality_score, 1),
        "action_score": round(action_score, 1),
        "subject_score": round(subject_score, 1),
        "composition_score": round(composition_score, 1),
        "fingerprint": fingerprint,
        "duration": duration
    }


def compute_shot_similarity(fp1: np.ndarray, fp2: np.ndarray) -> float:
    """Computes cosine similarity between two shot color fingerprints."""
    if fp1 is None or fp2 is None or len(fp1) == 0 or len(fp2) == 0:
        return 0.0
    dot = np.dot(fp1, fp2)
    norm1 = np.linalg.norm(fp1)
    norm2 = np.linalg.norm(fp2)
    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0.0
    return float(dot / (norm1 * norm2))


def select_smart_shots(
    candidate_clips: List[Path],
    num_shots: int,
    is_drop_flags: Optional[List[bool]] = None
) -> List[Path]:
    """
    Selects the highest quality, most diverse anime shots for the video.
    Deduplicates visually repetitive shots and reserves top-scoring action
    shots for the beat drop and narrative climax.
    """
    if not candidate_clips:
        return []

    # Score all candidate clips
    scored_pool = [score_candidate_shot(p) for p in candidate_clips if p.exists() and p.stat().st_size > 10_000]
    if not scored_pool:
        return candidate_clips[:num_shots]

    # Filter out visually duplicate shots (similarity > 0.88 with an already selected shot)
    # Sort candidate pool by total score descending
    scored_pool.sort(key=lambda s: s["total_score"], reverse=True)

    unique_pool: List[Dict[str, Any]] = []
    for cand in scored_pool:
        is_dup = False
        for chosen in unique_pool:
            sim = compute_shot_similarity(cand["fingerprint"], chosen["fingerprint"])
            if sim > 0.88:
                is_dup = True
                break
        if not is_dup:
            unique_pool.append(cand)

    # If deduplication was too aggressive, re-add remaining shots
    if len(unique_pool) < num_shots:
        for cand in scored_pool:
            if cand not in unique_pool:
                unique_pool.append(cand)
            if len(unique_pool) >= num_shots:
                break

    # Structure into 5-Act Narrative Arc (Phase 7: Build the Climax):
    # Act 1: HOOK (immediate subject intrigue)
    # Act 2: BUILD (dialogue / atmosphere buildup toward drop)
    # Act 3: ESCALATION (accelerating combat clashes)
    # Act 4: CLIMAX (#1 highest-energy action strike / ultimate technique)
    # Act 5: PAYOFF (lingering character resolution / aftermath)
    sorted_by_subject = sorted(unique_pool, key=lambda s: s["subject_score"] + s["quality_score"], reverse=True)
    sorted_by_action = sorted(unique_pool, key=lambda s: s["action_score"] + s["total_score"], reverse=True)

    num_intro = sum(1 for f in (is_drop_flags or []) if not f)
    if num_intro == 0:
        num_intro = max(1, num_shots // 4)

    used_paths = set()

    # 1. Hook & Build shots (from high-subject pool)
    intro_selected: List[Path] = []
    for s in sorted_by_subject:
        if s["path"] not in used_paths:
            intro_selected.append(s["path"])
            used_paths.add(s["path"])
        if len(intro_selected) >= num_intro:
            break

    # 2. Climax finisher shot (#1 absolute highest action score in candidate pool)
    action_candidates = [s for s in sorted_by_action if s["path"] not in used_paths]
    if not action_candidates:
        action_candidates = sorted_by_action[:]
    climax_shot = action_candidates[0]["path"] if action_candidates else unique_pool[0]["path"]
    used_paths.add(climax_shot)

    # 3. Payoff resolution shot (high subject/quality aftermath)
    payoff_candidates = [s for s in sorted_by_subject if s["path"] not in used_paths]
    payoff_shot = payoff_candidates[0]["path"] if payoff_candidates else (action_candidates[-1]["path"] if action_candidates else climax_shot)
    used_paths.add(payoff_shot)

    # 4. Escalation combat shots
    combat_needed = max(0, num_shots - len(intro_selected) - 2)
    combat_selected: List[Path] = []
    for s in action_candidates:
        if s["path"] not in used_paths:
            combat_selected.append(s["path"])
            used_paths.add(s["path"])
        if len(combat_selected) >= combat_needed:
            break

    # Fill any remaining slots
    all_available = [s["path"] for s in unique_pool]
    while len(intro_selected) + len(combat_selected) + 2 < num_shots:
        for p in all_available:
            if p not in used_paths:
                combat_selected.append(p)
                used_paths.add(p)
                break
        else:
            combat_selected.append(all_available[len(combat_selected) % len(all_available)])

    # Assemble complete 5-act narrative sequence
    final_shots = intro_selected + combat_selected + [climax_shot, payoff_shot]
    return final_shots[:num_shots]


def calculate_variable_pacing(
    total_duration: float,
    drop_time: float,
    major_beat_times: List[float],
    min_cut_dur: float = 0.55,
    max_cut_dur: float = 2.40
) -> List[Dict[str, Any]]:
    """
    Constructs an intentional narrative pacing curve:
    - Act 1 (Hook & Intro, 0 -> drop_time): Calmer, narrative pacing (1.4s - 2.2s per shot)
    - Act 2 (Drop Impact, drop_time -> ~60% dur): Snappy rapid combat rush (0.6s - 1.1s)
    - Act 3 (Escalation, 60% -> 80% dur): Micro-burst rhythmic velocity cuts (0.55s - 0.85s)
    - Act 4 (Climax & Finisher, 80% -> 92% dur): #1 Impact peak hold (1.4s - 1.8s)
    - Act 5 (Payoff / Outro, 92% -> end): Lingering cinematic payoff hold (1.5s - 2.2s)
    Every cut aligns to real musical bass onsets.
    """
    sorted_beats = sorted(list(set([round(t, 2) for t in major_beat_times if 0.0 < t < total_duration])))

    # 1. Ensure beat drop is an exact cut timestamp
    drop_t = round(drop_time, 2)
    cut_points = [0.0]

    # Act 1: Intro pacing (calm, 1.4s - 2.2s intervals leading to drop)
    curr_t = 0.0
    while curr_t < drop_t - 0.70:
        # Find nearest beat between curr_t + 1.2s and curr_t + 2.2s
        candidates = [b for b in sorted_beats if curr_t + 1.1 <= b <= curr_t + 2.2 and b < drop_t - 0.5]
        if candidates:
            next_t = candidates[0]
        else:
            next_t = round(curr_t + 1.6, 2)
            if next_t >= drop_t - 0.5:
                break
        cut_points.append(next_t)
        curr_t = next_t

    # Add Drop cut
    cut_points.append(drop_t)
    curr_t = drop_t

    # Acts 2 & 3: High-Energy Combat Rush (faster, snappy 0.6s - 1.1s cuts)
    climax_start = round(total_duration * 0.78, 2)
    finisher_start = round(total_duration * 0.90, 2)

    while curr_t < climax_start - 0.60:
        # Target cut interval: 0.60s - 1.10s
        candidates = [b for b in sorted_beats if curr_t + 0.55 <= b <= curr_t + 1.15 and b < climax_start]
        if candidates:
            # Pick beat that creates rhythmic variety (alternating between shorter and medium)
            next_t = candidates[0]
        else:
            next_t = round(curr_t + 0.85, 2)
        cut_points.append(next_t)
        curr_t = next_t

    # Act 4: Climax Finisher (weighty hold on the ultimate technique impact)
    cut_points.append(climax_start)
    curr_t = climax_start

    # Climax hold: 1.4s - 2.0s hold on peak action
    candidates_climax = [b for b in sorted_beats if curr_t + 1.2 <= b <= total_duration - 1.2]
    if candidates_climax:
        next_t = min(candidates_climax, key=lambda b: abs(b - (curr_t + 1.6)))
        cut_points.append(next_t)
        curr_t = next_t

    # Act 5: Payoff / Outro (lingering resolution hold: 1.4s - 2.4s)
    if total_duration - curr_t > 2.8:
        candidates_outro = [b for b in sorted_beats if curr_t + 1.2 <= b <= total_duration - 1.0]
        if candidates_outro:
            next_t = min(candidates_outro, key=lambda b: abs(b - (curr_t + 1.6)))
            cut_points.append(next_t)
            curr_t = next_t
        else:
            cut_points.append(round(total_duration - 1.8, 2))

    cut_points.append(round(total_duration, 2))

    # Clean and build segments
    cut_points = sorted(list(set(cut_points)))
    segments = []
    for i in range(len(cut_points) - 1):
        s = cut_points[i]
        e = cut_points[i+1]
        dur = round(e - s, 3)
        if dur < 0.35 and len(segments) > 0:
            # Merge tiny slivers
            segments[-1]["end"] = e
            segments[-1]["duration"] = round(e - segments[-1]["start"], 3)
            continue

        is_d = s >= drop_t
        is_climax = (s >= climax_start and s < finisher_start)
        is_finisher = (s >= finisher_start)

        # Tag narrative role
        if not is_d:
            role = "intro_buildup"
        elif i == len(cut_points) - 2 and len(cut_points) >= 4:
            role = "payoff_outro"
        elif is_climax:
            role = "climax_finisher"
        elif is_finisher:
            role = "payoff_outro"
        elif dur <= 0.80:
            role = "combat_micro_rush"
        else:
            role = "combat_strike"

        segments.append({
            "start": s,
            "end": e,
            "duration": dur,
            "is_drop": is_d,
            "is_climax": is_climax,
            "is_finisher": is_finisher,
            "role": role,
            "index": len(segments)
        })

    return segments
