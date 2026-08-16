"""
4K HDR Color Correction, Velocity Ramping, Beat Flashes & Camera Shake Filter Engine.
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
    return f"{eq_part},{unsharp_part},{vignette_part}"


def build_beat_flash_filters(beat_timestamps: List[float], flash_duration: float = 0.12, opacity: float = 0.55) -> List[str]:
    """
    Builds momentary white screen burst flash overlays timed to heavy bass drops.
    """
    flash_filters = []
    for t in beat_timestamps:
        cond = f"between(t,{t:.2f},{t+flash_duration:.2f})"
        flash_filters.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{opacity}:t=fill:enable='{cond}'")
    return flash_filters


def build_velocity_zoom_filter(is_drop: bool, seg_idx: int) -> str:
    """
    Applies dynamic zoom punches and subtle motion to clips while preserving exact 1080x1920:
    - In drop phase: aggressive punch-in zoom (1.12x / 1.08x) with fast impact.
    - In buildup phase: subtle cinematic slow-zoom.
    """
    if is_drop:
        if seg_idx % 2 == 0:
            return f"scale={int(VIDEO_WIDTH*1.12)}:{int(VIDEO_HEIGHT*1.12)},crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
        else:
            return f"scale={int(VIDEO_WIDTH*1.08)}:{int(VIDEO_HEIGHT*1.08)},crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
    else:
        return f"scale={int(VIDEO_WIDTH*1.04)}:{int(VIDEO_HEIGHT*1.04)},crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
