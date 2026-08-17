"""
4K HDR Color Correction, Velocity Ramping, Beat Flashes & Dynamic Zoom Impact Engine.
Replicates top viral anime/Marvel TikTok & Shorts editing styles:
- Dynamic 4-tier velocity zoom punches (1.16x downbeat impact, 1.12x secondary hit, 1.08x fast cut, 1.04x cinematic slow push).
- Fast 0.07s optical white flashes on 808 bass drops.
- High-contrast 4K HDR Color Grading with deep blacks and vibrant neon highlights.
"""
from typing import List, Dict, Any
from config.settings import CC_PRESETS, VIDEO_WIDTH, VIDEO_HEIGHT

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
    return f"{eq_part},{levels_part},{unsharp_part},{vignette_part}"


def build_beat_flash_filters(beat_timestamps: List[float], flash_duration: float = 0.07, opacity: float = 0.50) -> List[str]:
    """
    Builds fast momentary white screen burst flash overlays timed to heavy bass drops.
    """
    flash_filters = []
    # Add flashes on downbeats (spaced by at least 0.5s to prevent strobe overload)
    last_flash = -10.0
    for t in beat_timestamps:
        if t - last_flash >= 0.65:
            cond = f"between(t,{t:.2f},{t+flash_duration:.2f})"
            flash_filters.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{opacity}:t=fill:enable='{cond}'")
            last_flash = t
    return flash_filters


def build_velocity_zoom_filter(is_drop: bool, seg_idx: int) -> str:
    """
    Applies viral CapCut / After Effects style dynamic zoom punches while preserving 1080x1080:
    - On downbeat drops (seg_idx % 4 == 0): aggressive 1.16x punch-in zoom.
    - On fast 16th cuts (seg_idx % 4 == 1): snappy 1.08x punch.
    - On secondary hits (seg_idx % 4 == 2): energetic 1.13x zoom.
    - On held power shots (seg_idx % 4 == 3): cinematic 1.04x slow push.
    """
    if is_drop:
        pattern = seg_idx % 4
        if pattern == 0:
            scale_factor = 1.16
        elif pattern == 1:
            scale_factor = 1.08
        elif pattern == 2:
            scale_factor = 1.13
        else:
            scale_factor = 1.05
        return f"scale={int(VIDEO_WIDTH * scale_factor)}:{int(VIDEO_HEIGHT * scale_factor)},crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
    else:
        return f"scale={int(VIDEO_WIDTH * 1.04)}:{int(VIDEO_HEIGHT * 1.04)},crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
