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
    Determines the musical velocity curve, slow-motion factor, zoom punch, and visual FX for a clip segment:
    - 'intro_slowmo': 0.65x slow motion for cinematic tension & dialogue (0.0s to Drop)
    - 'drop_snap': 1.30x explosive impact on the 808 kick + 1.18x punch zoom + white flash
    - 'power_slowmo': 0.50x dramatic slow motion during held strikes/energy releases (dur > 0.8s)
    - 'fast_strike': 1.25x aggressive clash on fast 16th beats (dur <= 0.5s)
    - 'bridge_slowmo': 0.55x technique charge breather
    - 'climax_outro': 0.60x devastating slow-mo hold into black fade
    """
    is_drop = seg.get("is_drop", False)
    duration = seg.get("duration", 1.0)
    
    if not is_drop:
        # Phase 1: Intro Atmospheric Slow-Mo & Dialogue
        return {
            "role": "intro_slowmo",
            "speed": 0.65,
            "scale_factor": 1.04,
            "add_bars": True,
            "add_flash": False
        }
        
    if seg_idx == total_segs - 1:
        # Final Climax Outro Finisher
        return {
            "role": "climax_outro",
            "speed": 0.60,
            "scale_factor": 1.06,
            "add_bars": False,
            "add_flash": False
        }
        
    # Check if this is the first drop trigger segment
    if seg_idx > 0 and not seg.get("prev_is_drop", True):
        return {
            "role": "drop_snap",
            "speed": 1.30,
            "scale_factor": 1.18,
            "add_bars": False,
            "add_flash": True
        }
        
    # Drop Frenzy Segments
    if duration > 0.80:
        # Held power attack swing / technique explosion in dramatic slow motion
        return {
            "role": "power_slowmo",
            "speed": 0.50,
            "scale_factor": 1.14,
            "add_bars": False,
            "add_flash": False
        }
    else:
        # Fast rhythmic clash
        return {
            "role": "fast_strike",
            "speed": 1.25,
            "scale_factor": 1.08,
            "add_bars": False,
            "add_flash": (seg_idx % 6 == 0)
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
    Builds the agency-grade per-clip video filter for 60FPS viral anime edits:
    1. Edge crop to remove potential broadcast watermarks.
    2. Aspect ratio fit & center crop for 1080x1080 1:1 square canvas.
    3. Twixtor-style speed ramp with frame-blending motion blur on slow-mo (speed < 0.8x).
    4. Continuous animated dynamic zoom punch (zooms in to 1.25x and eases down on impact).
    5. 60 FPS & SAR normalization.
    6. Exact duration trimming to lock zero-drift beat sync.
    """
    pts_mult = 1.0 / max(0.2, speed)
    filters = [
        # Watermark-free edge crop
        "crop=in_w-24:in_h-24:12:12",
        # Fit to 1:1 square canvas
        f"scale={video_width}:{video_height}:force_original_aspect_ratio=increase",
        f"crop={video_width}:{video_height}",
        # Velocity speed ramp
        f"setpts={pts_mult:.4f}*PTS",
    ]

    # Apply frame blending motion blur on slow-motion clips (Twixtor-style)
    if speed < 0.80:
        filters.append("tblend=all_mode=average")

    # Animated Dynamic Zoom Punch (Continuous ease-down from punch scale to 1.0x over first 14 frames @ 60fps)
    if scale_factor > 1.05:
        punch_delta = scale_factor - 1.0
        punch_frames = 14 if fps >= 50 else 8
        zoom_expr = f"if(lte(in,{punch_frames}),{scale_factor:.2f}-{punch_delta:.2f}*(in/{punch_frames}),1.0)"
        filters.append(
            f"zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={video_width}x{video_height}:fps={fps}"
        )
    else:
        filters.append(f"fps={fps}")

    filters.extend([
        "setsar=1",
        f"trim=duration={duration:.3f}",
        "setpts=PTS-STARTPTS"
    ])

    if add_bars:
        # Cinematic 2.39:1 letterbox bars on intro (100px top and bottom on 1080x1080)
        bar_h = 100
        filters.append(f"drawbox=x=0:y=0:w=iw:h={bar_h}:color=black:t=fill")
        filters.append(f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=black:t=fill")

    return ",".join(filters)


def build_cc_filter(preset_name: str = "marvel_hdr") -> str:
    """
    Builds the 4K HDR Color Grade filtergraph snippet.
    Includes contrast expansion, saturation boost, unsharp masking, and cinematic vignette.
    """
    cfg = CC_PRESETS.get(preset_name, CC_PRESETS["marvel_hdr"])
    eq_part = f"eq=contrast={cfg['contrast']}:brightness={cfg['brightness']}:saturation={cfg['saturation']}:gamma={cfg['gamma']}"
    unsharp_part = f"unsharp={cfg['unsharp']}"
    vignette_part = f"vignette={cfg['vignette']}"
    # Colorlevels expansion for crushed blacks and crisp highlight contrast
    levels_part = "colorlevels=rimin=0.03:gimin=0.03:bimin=0.03:rimax=0.98:gimax=0.98:bimax=0.98"
    # Film grain texture (matching viral reference edit look)
    grain_part = "noise=c0s=12:allf=t+u"
    return f"{eq_part},{levels_part},{unsharp_part},{vignette_part},{grain_part}"


def build_monochrome_cc_filter(preset_name: str = "jjk_void") -> str:
    """
    Builds a heavy-desaturation / near-monochrome grade with selective color pop.
    Matches the viral Gojo reference style: almost B&W with a hint of character color in shadows.
    """
    cfg = CC_PRESETS.get(preset_name, CC_PRESETS["jjk_void"])
    # Desaturate heavily (0.18 = 18% of original saturation)
    eq_part = f"eq=contrast={cfg['contrast'] + 0.12}:brightness={cfg['brightness'] - 0.01}:saturation=0.18:gamma={cfg['gamma'] - 0.04}"
    levels_part = "colorlevels=rimin=0.05:gimin=0.05:bimin=0.05:rimax=0.96:gimax=0.96:bimax=0.96"
    unsharp_part = f"unsharp={cfg['unsharp']}"
    vignette_part = f"vignette=PI/3.2"
    grain_part = "noise=c0s=18:allf=t+u"
    return f"{eq_part},{levels_part},{unsharp_part},{vignette_part},{grain_part}"


def build_beat_flash_filters(beat_timestamps: List[float], flash_duration: float = 0.09, opacity: float = 0.60) -> List[str]:
    """
    Builds energetic white screen burst flash overlays timed to heavy bass drops.
    Reference edit uses frequent strobe flashes at 0.35s minimum spacing.
    """
    flash_filters = []
    # Add flashes on downbeats (spaced by at least 0.35s to match viral reference edit strobe density)
    last_flash = -10.0
    for t in beat_timestamps:
        if t - last_flash >= 0.35:
            cond = f"between(t,{t:.2f},{t+flash_duration:.2f})"
            flash_filters.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{opacity}:t=fill:enable='{cond}'")
            last_flash = t
    return flash_filters

