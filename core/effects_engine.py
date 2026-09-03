"""
4K HDR Color Correction, Velocity Ramping, Beat Flashes & Dynamic Zoom Impact Engine.
Replicates top viral anime/Marvel TikTok & Shorts editing styles:
- Dynamic Twixtor-style slow-motion curves (0.50x - 0.65x) on power strikes, dialogue intro, and technique charges.
- Explosive snap impact speedups (1.25x - 1.30x) on 808 bass drops and rapid clashes.
- Dynamic 4-tier velocity zoom punches (1.18x downbeat impact, 1.14x power hit, 1.08x fast strike, 1.04x cinematic slow push).
- Fast 0.07s optical white flashes on 808 bass drops.
- High-contrast 4K HDR Color Grading with deep blacks and vibrant highlights.
"""
from typing import List, Dict, Any
from config.settings import CC_PRESETS, VIDEO_WIDTH, VIDEO_HEIGHT, FPS


def get_segment_velocity_profile(seg: Dict[str, Any], seg_idx: int, total_segs: int) -> Dict[str, Any]:
    """
    Determines the visual profile for a clip segment.

    Reference video uses NO velocity ramps — straight hard cuts are the standard.
    Motion comes from source footage, not speed manipulation.
    Only two exceptions: slight intro slow-mo and held outro.

    Returns speed=1.0 for all drop segments (no speed ramping).
    """
    is_drop = seg.get("is_drop", False)
    duration = seg.get("duration", 1.0)

    if not is_drop:
        # Phase 1: Intro — slight slow-mo for cinematic weight (reference does hold intro shots)
        return {
            "role": "intro_slowmo",
            "speed": 0.85,
            "scale_factor": 1.02,
            "add_bars": True,
            "add_flash": False
        }

    if seg_idx == total_segs - 1:
        # Final Outro — held shot, slight slow-mo for dramatic weight
        return {
            "role": "climax_outro",
            "speed": 0.80,
            "scale_factor": 1.03,
            "add_bars": False,
            "add_flash": False
        }

    # ALL drop segments: straight cuts, no velocity ramping, no zoom punch
    return {
        "role": "straight_cut",
        "speed": 1.0,
        "scale_factor": 1.0,
        "add_bars": False,
        "add_flash": False
    }


def build_velocity_clip_filter(
    seg_idx: int,
    duration: float,
    speed: float = 1.0,
    scale_factor: float = 1.0,
    video_width: int = VIDEO_WIDTH,
    video_height: int = VIDEO_HEIGHT,
    fps: int = FPS,
    add_bars: bool = False
) -> str:
    """
    Builds the per-clip video filter chain for portrait 9:16 anime edits.
    Reference style: straight hard cuts, no velocity ramps, no zoom punches.
    Motion comes from source footage, not speed manipulation.

    Only exceptions: slight slow-mo on intro/outro (speed 0.80-0.85x) with
    light frame blending. All drop segments use speed=1.0.
    """
    filters = [
        # Scale to 9:16 portrait canvas
        f"scale={video_width}:{video_height}:force_original_aspect_ratio=increase",
        f"crop={video_width}:{video_height}",
        f"fps={fps}",
        "setsar=1",
    ]

    # Only apply speed ramp for intro/outro slow-mo (not for drop segments)
    if speed < 0.95:
        pts_mult = 1.0 / max(0.2, speed)
        filters.append(f"setpts={pts_mult:.4f}*PTS")
        # Light frame blending for slow-mo smoothness
        if speed < 0.82:
            filters.append("tblend=all_mode=average")

    # Subtle zoom for intro (1.02x, barely noticeable but adds weight)
    if scale_factor > 1.01 and scale_factor <= 1.05:
        punch_delta = scale_factor - 1.0
        punch_frames = 20
        zoom_expr = f"if(lte(in,{punch_frames}),{scale_factor:.3f}-{punch_delta:.3f}*(in/{punch_frames}),1.0)"
        filters.append(
            f"zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={video_width}x{video_height}:fps={fps}"
        )

    filters.extend([
        f"trim=duration={duration:.3f}",
        "setpts=PTS-STARTPTS"
    ])

    if add_bars:
        # Cinematic letterbox bars — 12.5% of frame height (matching reference ~80px on 640h)
        bar_h = max(60, int(video_height * 0.125))
        filters.append(f"drawbox=x=0:y=0:w=iw:h={bar_h}:color=black:t=fill")
        filters.append(f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=black:t=fill")

    return ",".join(filters)


def build_cc_filter(preset_name: str = "cool_blue") -> str:
    """
    Builds the dark, moody color grade filtergraph snippet.
    Targets mean luma ~25-40 (reference style) — very dark with muted saturation.

    Now supports colorbalance field for dual-tone blue/red alternation.
    """
    cfg = CC_PRESETS.get(preset_name, CC_PRESETS["cool_blue"])
    eq_part = f"eq=contrast={cfg['contrast']}:brightness={cfg['brightness']}:saturation={cfg['saturation']}:gamma={cfg['gamma']}"
    unsharp_part = f"unsharp={cfg['unsharp']}"
    vignette_part = f"vignette={cfg['vignette']}"
    # Crushed blacks + clipped highlights for high-contrast moody look
    levels_part = "colorlevels=rimin=0.05:gimin=0.05:bimin=0.05:rimax=0.96:gimax=0.96:bimax=0.96"
    # Lighter grain (c0s=12) — visible but not heavy
    grain_part = "noise=c0s=12:allf=t+u"

    parts = [eq_part, levels_part]
    if cfg.get("colorbalance"):
        parts.append(f"colorbalance={cfg['colorbalance']}")
    parts.extend([unsharp_part, vignette_part, grain_part])
    return ",".join(parts)


def build_monochrome_cc_filter(preset_name: str = "mono_bw") -> str:
    """
    Builds extreme monochromatic treatments matching the reference's 3 modes:
    - 'mono_blue': Cold blue desaturation (character moments)
    - 'mono_white': High-key washed-out pale (dreamlike transitions)
    - 'mono_bw': High-contrast B&W (manga-panel power moments)

    Each mode uses the full CC_PRESETS config for that monochrome variant.
    """
    cfg = CC_PRESETS.get(preset_name, CC_PRESETS["mono_bw"])

    eq_part = f"eq=contrast={cfg['contrast']}:brightness={cfg['brightness']}:saturation={cfg['saturation']}:gamma={cfg['gamma']}"
    levels_part = "colorlevels=rimin=0.05:gimin=0.05:bimin=0.05:rimax=0.96:gimax=0.96:bimax=0.96"
    unsharp_part = f"unsharp={cfg['unsharp']}"
    vignette_part = f"vignette={cfg['vignette']}"
    grain_part = "noise=c0s=14:allf=t+u"

    parts = [eq_part, levels_part]
    if cfg.get("colorbalance"):
        parts.append(f"colorbalance={cfg['colorbalance']}")
    parts.extend([unsharp_part, vignette_part, grain_part])
    return ",".join(parts)


def build_beat_flash_filters(beat_timestamps: List[float], flash_duration: float = 0.12, opacity: float = 0.70) -> List[str]:
    """
    Builds white flash overlays — ONLY at the 2-3 biggest drop moments.
    Reference edit has 2-3 total flashes across the entire video.
    Uses the FIRST and LAST few beat timestamps as the major energy peaks.
    """
    if not beat_timestamps:
        return []

    flash_filters = []
    # Pick only2-3 timestamps: the first drop moment, one mid-point, one near the end
    n = len(beat_timestamps)
    if n <= 3:
        flash_times = beat_timestamps
    else:
        flash_times = [
            beat_timestamps[0],                    # First drop hit
            beat_timestamps[n // 2],               # Mid-energy peak
            beat_timestamps[min(n - 2, n * 3 // 4)]  # Late climax
        ]

    for t in flash_times:
        cond = f"between(t,{t:.2f},{t + flash_duration:.2f})"
        flash_filters.append(
            f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{opacity}:t=fill:enable='{cond}'"
        )
    return flash_filters

