"""
Intelligent 9:16 Reframing Engine for Anime Shorts (Phase 1).
Fills the 1080x1920 vertical canvas without black bars by dynamically tracking
characters, faces, and visual saliency with smooth ease-in/ease-out camera panning.
Automatically detects and strips baked-in letterbox bars from source footage.
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from config.settings import VIDEO_WIDTH, VIDEO_HEIGHT, BASE_DIR

MODELS_DIR = BASE_DIR / "assets" / "models"
_CACHED_CASCADES: Optional[List[Any]] = None


def _get_cascades() -> List[Any]:
    """
    Loads and caches face cascades (anime face cascade + human frontal face cascade).
    """
    global _CACHED_CASCADES
    if _CACHED_CASCADES is not None:
        return _CACHED_CASCADES

    cascades = []
    if not OPENCV_AVAILABLE or not hasattr(cv2, "CascadeClassifier"):
        _CACHED_CASCADES = cascades
        return cascades

    try:
        # 1. Anime face cascade (specifically trained for anime character eyes & faces)
        anime_xml = MODELS_DIR / "lbpcascade_animeface.xml"
        if anime_xml.exists():
            c = cv2.CascadeClassifier(str(anime_xml))
            if not c.empty():
                cascades.append(("anime", c))
    except Exception as e:
        print(f"⚠️ Notice loading anime face cascade: {e}")

    try:
        # 2. General frontal face cascade
        frontal_xml = MODELS_DIR / "haarcascade_frontalface_default.xml"
        if frontal_xml.exists():
            c = cv2.CascadeClassifier(str(frontal_xml))
            if not c.empty():
                cascades.append(("frontal", c))
        elif hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            sys_xml = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            if sys_xml.exists():
                c = cv2.CascadeClassifier(str(sys_xml))
                if not c.empty():
                    cascades.append(("frontal", c))
    except Exception as e:
        print(f"⚠️ Notice loading frontal face cascade: {e}")

    _CACHED_CASCADES = cascades
    return cascades


def detect_active_content_bounds(frame: np.ndarray, threshold: float = 12.0) -> Tuple[int, int, int, int]:
    """
    Detects the true active content area in a frame, stripping baked-in black letterbox bars.
    Returns (left, top, width, height).
    """
    if frame is None or frame.size == 0:
        return (0, 0, 1920, 1080)

    orig_h, orig_w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

    row_means = np.mean(gray, axis=1)
    col_means = np.mean(gray, axis=0)

    valid_rows = np.where(row_means > threshold)[0]
    valid_cols = np.where(col_means > threshold)[0]

    if len(valid_rows) > 0 and len(valid_cols) > 0:
        top = int(valid_rows[0])
        bot = int(valid_rows[-1])
        left = int(valid_cols[0])
        right = int(valid_cols[-1])
        # Ensure dimensions are even
        w = max(2, ((right - left + 1) // 2) * 2)
        h = max(2, ((bot - top + 1) // 2) * 2)
        return (left, top, w, h)

    return (0, 0, orig_w, orig_h)


def detect_subject_focus(frame: np.ndarray) -> Tuple[float, float, float]:
    """
    Detects the primary subject's normalized center coordinates (cx, cy) in a frame.
    Returns (cx_norm, cy_norm, confidence) where values are normalized to [0.0, 1.0].
    Prioritizes:
      1. Anime / character face detection
      2. Human face detection
      3. Visual saliency & edge/color energy center of mass
      4. Safe frame center (0.5, 0.5)
    """
    if not OPENCV_AVAILABLE or frame is None or frame.size == 0:
        return (0.5, 0.5, 0.0)

    orig_h, orig_w = frame.shape[:2]
    if orig_h == 0 or orig_w == 0:
        return (0.5, 0.5, 0.0)

    # Downscale for fast detection (max width 640)
    scale = 1.0
    if orig_w > 640:
        scale = 640.0 / orig_w
        proc_w = 640
        proc_h = int(round(orig_h * scale))
        proc_frame = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_LINEAR)
    else:
        proc_w = orig_w
        proc_h = orig_h
        proc_frame = frame

    gray = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)

    # 1. Face / Character Detection
    cascades = _get_cascades()
    detected_faces = []
    for c_type, cascade in cascades:
        img_input = gray_eq if c_type == "anime" else gray
        min_sz = (int(30 * scale), int(30 * scale))
        faces = cascade.detectMultiScale(img_input, scaleFactor=1.1, minNeighbors=3, minSize=min_sz)
        if len(faces) > 0:
            for (fx, fy, fw, fh) in faces:
                area = fw * fh
                detected_faces.append((area, fx, fy, fw, fh, 1.0 if c_type == "anime" else 0.85))

    if detected_faces:
        # Pick the most prominent / largest face
        detected_faces.sort(key=lambda item: item[0], reverse=True)
        _, fx, fy, fw, fh, conf = detected_faces[0]
        cx_norm = (fx + fw / 2.0) / float(proc_w)
        cy_norm = (fy + fh / 2.0) / float(proc_h)
        return (float(np.clip(cx_norm, 0.0, 1.0)), float(np.clip(cy_norm, 0.0, 1.0)), conf)

    # 2. Visual Saliency & Energy Center of Mass (Edge detail + color saturation)
    try:
        small_w = 320
        small_h = int(round(orig_h * (320.0 / orig_w)))
        small = cv2.resize(proc_frame, (small_w, small_h), interpolation=cv2.INTER_AREA)
        small_gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        small_hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        # High-contrast line art / edges
        laplacian = cv2.Laplacian(small_gray, cv2.CV_32F)
        edges = np.abs(laplacian)

        # Vivid color saturation (anime characters vs muted backgrounds)
        sat = small_hsv[:, :, 1].astype(np.float32)

        # Center-weighted Gaussian prior (slightly favors center to avoid edge letterbox artifacts)
        y_indices, x_indices = np.indices((small_h, small_w))
        center_x = small_w / 2.0
        center_y = small_h / 2.0
        sigma_x = small_w * 0.40
        sigma_y = small_h * 0.40
        gaussian_prior = np.exp(-0.5 * (((x_indices - center_x) / sigma_x) ** 2 + ((y_indices - center_y) / sigma_y) ** 2))

        energy_map = (edges * 0.60 + sat * 0.40) * gaussian_prior
        total_energy = np.sum(energy_map)

        if total_energy > 1e-4:
            col_weights = np.sum(energy_map, axis=0)
            row_weights = np.sum(energy_map, axis=1)

            cx = np.sum(np.arange(small_w) * col_weights) / (total_energy)
            cy = np.sum(np.arange(small_h) * row_weights) / (total_energy)

            cx_norm = cx / float(small_w)
            cy_norm = cy / float(small_h)
            return (float(np.clip(cx_norm, 0.0, 1.0)), float(np.clip(cy_norm, 0.0, 1.0)), 0.60)
    except Exception:
        pass

    # 3. Safe center fallback
    return (0.5, 0.5, 0.0)


def probe_clip_dimensions(clip_path: Union[str, Path]) -> Tuple[int, int]:
    """
    Probes video width and height using ffprobe.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(clip_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        data = json.loads(res.stdout)
        stream = data.get("streams", [{}])[0]
        w = int(stream.get("width", 1920))
        h = int(stream.get("height", 1080))
        return w, h
    except Exception:
        return 1920, 1080


def analyze_clip_framing(
    clip_path: Union[str, Path],
    duration: Optional[float] = None,
    num_samples: int = 5
) -> Dict[str, Any]:
    """
    Analyzes multiple frames across a video clip to track character movement
    and calculate start/end focus points for smooth 9:16 reframing.
    Automatically detects and strips baked-in letterbox bars.
    """
    clip_p = Path(clip_path)
    if not clip_p.exists():
        return {
            "in_w": 1920, "in_h": 1080,
            "act_x": 0, "act_y": 0, "act_w": 1920, "act_h": 1080,
            "cx_start": 0.5, "cx_end": 0.5,
            "cy_start": 0.5, "cy_end": 0.5,
            "is_dynamic": False
        }

    in_w = 0
    in_h = 0
    act_x, act_y, act_w, act_h = 0, 0, 0, 0
    samples: List[Tuple[float, float, float]] = []

    if OPENCV_AVAILABLE:
        try:
            cap = cv2.VideoCapture(str(clip_p))
            if cap.isOpened():
                in_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                in_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                if total_frames > 0 and in_w > 0 and in_h > 0:
                    frame_indices = [
                        int(total_frames * (i + 1) / (num_samples + 1))
                        for i in range(num_samples)
                    ]
                    for sample_idx, idx in enumerate(frame_indices):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            # Detect active bounds from the middle frame
                            if sample_idx == len(frame_indices) // 2:
                                act_x, act_y, act_w, act_h = detect_active_content_bounds(frame)
                            
                            # Analyze active area for subject focus
                            if act_w > 0 and act_h > 0 and (act_w < in_w or act_h < in_h):
                                sub_frame = frame[act_y:act_y + act_h, act_x:act_x + act_w]
                            else:
                                sub_frame = frame
                            
                            cx, cy, conf = detect_subject_focus(sub_frame)
                            samples.append((cx, cy, conf))
            cap.release()
        except Exception:
            pass

    if in_w <= 0 or in_h <= 0:
        in_w, in_h = probe_clip_dimensions(clip_p)

    if act_w <= 0 or act_h <= 0:
        act_x, act_y, act_w, act_h = 0, 0, in_w, in_h

    if not samples:
        return {
            "in_w": in_w, "in_h": in_h,
            "act_x": act_x, "act_y": act_y, "act_w": act_w, "act_h": act_h,
            "cx_start": 0.5, "cx_end": 0.5,
            "cy_start": 0.5, "cy_end": 0.5,
            "is_dynamic": False
        }

    # Extract x and y sample series
    cx_vals = [s[0] for s in samples]
    cy_vals = [s[1] for s in samples]

    half = max(1, len(samples) // 2)
    cx_start = float(np.mean(cx_vals[:half]))
    cx_end = float(np.mean(cx_vals[-half:]))
    cy_start = float(np.mean(cy_vals[:half]))
    cy_end = float(np.mean(cy_vals[-half:]))

    # Dynamic camera movement check
    is_dynamic = abs(cx_end - cx_start) >= 0.04
    if not is_dynamic:
        med_x = float(np.median(cx_vals))
        cx_start = med_x
        cx_end = med_x

    return {
        "in_w": in_w, "in_h": in_h,
        "act_x": act_x, "act_y": act_y, "act_w": act_w, "act_h": act_h,
        "cx_start": cx_start, "cx_end": cx_end,
        "cy_start": cy_start, "cy_end": cy_end,
        "is_dynamic": is_dynamic
    }


def build_smart_reframe_filter(
    clip_path: Optional[Union[str, Path]] = None,
    duration: float = 1.0,
    video_width: int = VIDEO_WIDTH,
    video_height: int = VIDEO_HEIGHT,
    framing_info: Optional[Dict[str, Any]] = None,
    camera_motion: str = "auto",
    narrative_role: Optional[str] = None
) -> str:
    """
    Builds the complete FFmpeg filter string for intelligent 9:16 reframing with
    subject-aware camera movement (Phase 1 & Phase 4).
    - Fills the 1080x1920 portrait canvas without black bars.
    - Strips any baked-in letterbox black bars from source footage.
    - Anchors camera motion to detected anime character faces/focal points.
    - Restrained motion: subtle push-ins, pull-outs, punch-ins, and horizontal/vertical tracking.
    """
    target_ar = video_width / float(video_height)  # 1080 / 1920 = 0.5625 (9:16)

    # 1. Analyze clip framing if not already provided
    if framing_info is None and clip_path is not None:
        try:
            framing_info = analyze_clip_framing(clip_path, duration=duration)
        except Exception:
            framing_info = None

    # Resolve automatic camera motion based on narrative role
    resolved_motion = camera_motion
    if resolved_motion == "auto":
        if narrative_role == "intro_buildup":
            resolved_motion = "push_in"
        elif narrative_role == "climax_finisher":
            resolved_motion = "push_in"
        elif narrative_role == "payoff_outro":
            resolved_motion = "pull_out"
        elif narrative_role in ("combat_strike", "combat_micro_rush"):
            resolved_motion = "punch_in"
        elif framing_info and framing_info.get("is_dynamic"):
            resolved_motion = "pan_track"
        else:
            resolved_motion = "static_steady"

    # 2. Specific analyzed framing
    if framing_info is not None and framing_info.get("in_w", 0) > 0 and framing_info.get("in_h", 0) > 0:
        in_w = framing_info["in_w"]
        in_h = framing_info["in_h"]
        act_x = framing_info.get("act_x", 0)
        act_y = framing_info.get("act_y", 0)
        act_w = framing_info.get("act_w", in_w)
        act_h = framing_info.get("act_h", in_h)

        input_ar = act_w / float(act_h)

        # Subject anchor focal point (normalized to pixel coords)
        cx = framing_info.get("cx_start", 0.5)
        cy = framing_info.get("cy_start", 0.5)
        anchor_x = int(round(act_x + cx * act_w))
        anchor_y = int(round(act_y + cy * act_h))

        # Case A: Active content is wider than 9:16 (widescreen / landscape)
        if input_ar >= target_ar:
            base_crop_h = act_h
            base_crop_w = int(round(act_h * target_ar / 2.0)) * 2
            base_crop_w = min(base_crop_w, act_w)
            max_scroll_x = act_w - base_crop_w

            if resolved_motion == "push_in" and duration > 0.4:
                # 1.00x -> 1.06x restrained subtle push-in anchored on subject
                w_expr = f"({base_crop_w}*(1.0-0.06*min(t/{duration:.3f}\\,1)))"
                h_expr = f"({base_crop_h}*(1.0-0.06*min(t/{duration:.3f}\\,1)))"
                x_expr = f"clip({anchor_x}-{w_expr}/2\\,{act_x}\\,{act_x+act_w}-{w_expr})"
                y_expr = f"clip({anchor_y}-{h_expr}/2\\,{act_y}\\,{act_y+act_h}-{h_expr})"
                crop_filter = f"crop=w='{w_expr}':h='{h_expr}':x='{x_expr}':y='{y_expr}'"
            elif resolved_motion == "pull_out" and duration > 0.4:
                # 1.06x -> 1.00x subtle pull-out anchored on subject
                w_expr = f"({base_crop_w}*(0.94+0.06*min(t/{duration:.3f}\\,1)))"
                h_expr = f"({base_crop_h}*(0.94+0.06*min(t/{duration:.3f}\\,1)))"
                x_expr = f"clip({anchor_x}-{w_expr}/2\\,{act_x}\\,{act_x+act_w}-{w_expr})"
                y_expr = f"clip({anchor_y}-{h_expr}/2\\,{act_y}\\,{act_y+act_h}-{h_expr})"
                crop_filter = f"crop=w='{w_expr}':h='{h_expr}':x='{x_expr}':y='{y_expr}'"
            elif resolved_motion == "punch_in" and duration > 0.3:
                # 1.08x -> 1.00x impact punch-in recovering over first 0.20s
                w_expr = f"({base_crop_w}*(0.93+0.07*min(t/0.20\\,1)))"
                h_expr = f"({base_crop_h}*(0.93+0.07*min(t/0.20\\,1)))"
                x_expr = f"clip({anchor_x}-{w_expr}/2\\,{act_x}\\,{act_x+act_w}-{w_expr})"
                y_expr = f"clip({anchor_y}-{h_expr}/2\\,{act_y}\\,{act_y+act_h}-{h_expr})"
                crop_filter = f"crop=w='{w_expr}':h='{h_expr}':x='{x_expr}':y='{y_expr}'"
            elif max_scroll_x <= 0:
                crop_filter = f"crop={base_crop_w}:{base_crop_h}:{act_x}:{act_y}"
            else:
                # Horizontal pan tracking subject
                ideal_x_start = act_x + (framing_info["cx_start"] * act_w - (base_crop_w / 2.0))
                ideal_x_end = act_x + (framing_info["cx_end"] * act_w - (base_crop_w / 2.0))
                x_start = int(round(np.clip(ideal_x_start, act_x, act_x + max_scroll_x)))
                x_end = int(round(np.clip(ideal_x_end, act_x, act_x + max_scroll_x)))

                if x_start == x_end or duration <= 0.20 or resolved_motion == "static_steady":
                    crop_x_expr = str(x_start)
                else:
                    crop_x_expr = f"'{x_start}+({x_end - x_start})*(0.5-0.5*cos(PI*min(t/{duration:.3f}\\,1)))'"
                crop_filter = f"crop={base_crop_w}:{base_crop_h}:{crop_x_expr}:{act_y}"

        # Case B: Active content is narrower than 9:16 (ultra-tall)
        else:
            base_crop_w = act_w
            base_crop_h = int(round(act_w / target_ar / 2.0)) * 2
            base_crop_h = min(base_crop_h, act_h)
            max_scroll_y = act_h - base_crop_h

            if max_scroll_y <= 0:
                crop_y_expr = str(act_y)
            else:
                ideal_y_start = act_y + (framing_info["cy_start"] * act_h - (base_crop_h / 2.0))
                ideal_y_end = act_y + (framing_info["cy_end"] * act_h - (base_crop_h / 2.0))
                y_start = int(round(np.clip(ideal_y_start, act_y, act_y + max_scroll_y)))
                y_end = int(round(np.clip(ideal_y_end, act_y, act_y + max_scroll_y)))

                if y_start == y_end or duration <= 0.20 or resolved_motion == "static_steady":
                    crop_y_expr = str(y_start)
                else:
                    crop_y_expr = f"'{y_start}+({y_end - y_start})*(0.5-0.5*cos(PI*min(t/{duration:.3f}\\,1)))'"
            crop_filter = f"crop={base_crop_w}:{base_crop_h}:{act_x}:{crop_y_expr}"

        return f"{crop_filter},scale={video_width}:{video_height}:flags=lanczos,setsar=1"

    # 3. Fallback: Safe Dynamic Center-Crop to 9:16 without black bars
    safe_crop = (
        "crop="
        "w='min(iw,trunc(ih*9/16/2)*2)':"
        "h='min(ih,trunc(iw*16/9/2)*2)':"
        "x='(iw-ow)/2':"
        "y='(ih-oh)/2'"
    )
    return f"{safe_crop},scale={video_width}:{video_height}:flags=lanczos,setsar=1"
