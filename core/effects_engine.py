"""
4K HDR Cinematic Effects Engine — Replicating Reference Edits:
  xtlw3zvKGAE : DoF shallow rack-focus intro | light flicker into drop | speed lines overlay
  8Fyb0LXw1BU : Smooth velocity curve 0.3x→1.5x | color-reactive bloom on cursed techniques
  9_VAGhAdne8 : Camera shake (translate burst) | RGB split chromatic aberration

Implemented techniques (all pure FFmpeg):
  1. Rack-Focus (Depth-of-Field Blur Transition) — intro pull to character face
  2. Advanced Velocity Curve — 0.30x intro dialogue → 1.50x drop snap
  3. Camera Shake (Impact Displacement) — ±12px translate burst on drop first frames
  4. Chromatic Aberration (RGB Split) — ±5px horizontal channel offset on beat drops
  5. Cursed Technique Bloom Glow — highlight overexposure glimmer on technique shots
  6. Light Flicker — sinusoidal brightness oscillation in last 2s before beat drop
  7. Impact Flash + Dark Dip — white burst followed by brief blackout (8Fyb0LXw1BU)
"""
from typing import List, Dict, Any
from config.settings import CC_PRESETS, VIDEO_WIDTH, VIDEO_HEIGHT, FPS


def get_segment_velocity_profile(seg: Dict[str, Any], seg_idx: int, total_segs: int) -> Dict[str, Any]:
    """
    Advanced velocity profiles mapped from frame-by-frame analysis of all 3 reference edits.

    Reference curves:
    - Intro (pre-drop):  0.30x ultra-slow atmospheric tension (holds on character face)
    - Drop snap (first): 1.50x explosive impact + full VFX stack
    - Power slo-mo:      0.45x dramatic technique release (dur > 0.8s)
    - Fast clash:        1.40x rapid rhythmic exchange
    - Climax outro:      0.50x devastating hold into black
    """
    is_drop = seg.get("is_drop", False)
    duration = seg.get("duration", 1.0)

    if not is_drop:
        # Phase 1: Pre-Drop Intro — 0.30x ultra-slow atmospheric
        return {
            "role": "intro_slowmo",
            "speed": 0.30,
            "scale_factor": 1.03,
            "add_bars": True,
            "add_rack_focus": True,
            "add_shake": False,
            "add_chr_aber": False,
            "add_bloom": False,
            "add_flash": False,
        }

    if seg_idx == total_segs - 1:
        return {
            "role": "climax_outro",
            "speed": 0.50,
            "scale_factor": 1.06,
            "add_bars": False,
            "add_rack_focus": False,
            "add_shake": False,
            "add_chr_aber": False,
            "add_bloom": True,
            "add_flash": False,
        }

    if seg_idx > 0 and not seg.get("prev_is_drop", True):
        return {
            "role": "drop_snap",
            "speed": 1.50,
            "scale_factor": 1.25,
            "add_bars": False,
            "add_rack_focus": False,
            "add_shake": True,
            "add_chr_aber": True,
            "add_bloom": False,
            "add_flash": True,
            "add_exposure_pulse": True,
        }

    if duration > 0.80:
        return {
            "role": "power_slowmo",
            "speed": 0.45,
            "scale_factor": 1.14,
            "add_bars": False,
            "add_rack_focus": False,
            "add_shake": False,
            "add_chr_aber": False,
            "add_bloom": True,
            "add_flash": False,
        }

    return {
        "role": "fast_strike",
        "speed": 1.40,
        "scale_factor": 1.10,
        "add_bars": False,
        "add_rack_focus": False,
        "add_shake": (seg_idx % 5 == 0),
        "add_chr_aber": False,
        "add_bloom": False,
        "add_flash": (seg_idx % 6 == 0),
    }


def build_velocity_clip_filter(
    seg_idx: int,
    duration: float,
    speed: float = 1.0,
    scale_factor: float = 1.0,
    video_width: int = VIDEO_WIDTH,
    video_height: int = VIDEO_HEIGHT,
    fps: int = FPS,
    add_bars: bool = False,
    add_rack_focus: bool = False,
    add_shake: bool = False,
    add_chr_aber: bool = False,
    add_bloom: bool = False,
    add_impact_invert: bool = False,
    add_speed_lines: bool = False,
    add_whip_pan: bool = False,
    add_exposure_pulse: bool = False,
) -> str:
    """
    Builds the complete per-clip video filter chain implementing all cinematic techniques.

    Filter order:
      1. Edge crop (watermark strip)
      2. Scale + center crop to canvas
      3. Velocity speed ramp (setpts)
      4. Twixtor-style tblend motion blur (slow-mo only)
      5. Animated zoom punch (zoompan ease-down)
      6. Rack-Focus DoF blur (boxblur with time-based envelope) — intro
      7. Directional Whip Pan (rapid 2-frame directional motion translation on fast cuts)
      8. Camera Shake (geq translate burst) — drop impact
      9. Chromatic Aberration (geq R/B channel shift) — drop
     10. Bloom Glow (curves highlight lift + unsharp) — technique shots
     11. Impact Invert (1-frame negative color inversion on climax punch)
     12. Speed Lines (high-speed velocity streaks on fast slices)
     13. Cinematic letterbox bars — intro
     14. SAR + duration trim + PTS reset
    """
    pts_mult = 1.0 / max(0.15, speed)
    filters = []

    # 1. Watermark-free edge crop
    filters.append("crop=in_w-24:in_h-24:12:12")

    # 2. Scale + center crop
    filters.append(f"scale={video_width}:{video_height}:force_original_aspect_ratio=increase")
    filters.append(f"crop={video_width}:{video_height}")

    # 3. Velocity ramp
    filters.append(f"setpts={pts_mult:.4f}*PTS")

    # 4. Twixtor-style smooth frame blend interpolation on slow-mo (< 0.70x)
    if speed < 0.70:
        filters.append(
            f"minterpolate=fps={fps}:mi_mode=blend:scd=fdiff:scd_threshold=10.0"
        )

    # 5. Animated Dynamic Zoom (Slowmo Progressive Ease Zoom vs. Drop Impact Zoom Punch)
    if scale_factor > 1.05:
        punch_delta = scale_factor - 1.0
        if speed < 0.70:
            # Slowmo optical-flow buildup (QrzRe5DM0iQ inspiration): smooth progressive zoom-in over full clip duration
            total_f = max(1, int(duration * fps))
            zoom_expr = f"min({scale_factor:.3f},1.0+{punch_delta:.3f}*(in/{total_f}))"
        else:
            # Beat Drop impact zoom punch: instant snap on frame 0, smooth exponential ease-down
            punch_frames = 14 if fps >= 50 else 8
            zoom_expr = (
                f"if(lte(in,{punch_frames}),{scale_factor:.2f}-{punch_delta:.2f}*(1-pow(1-(in/{punch_frames}),2)),1.0)"
            )
        filters.append(
            f"zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s={video_width}x{video_height}:fps={fps}"
        )
    else:
        filters.append(f"fps={fps}")

    # 6. Rack-Focus DoF blur (xtlw3zvKGAE: shallow depth-of-field pull on character face)
    if add_rack_focus:
        dur_f = max(0.4, duration)
        filters.append(f"boxblur=luma_radius=2:luma_power=1:enable='between(t,0,{dur_f:.2f})'")

    # 6b. Directional Whip Pan (2-frame dynamic translation snap + directional motion blur)
    if add_whip_pan:
        whip_offset = 64
        filters.append(
            f"geq=lum='p(X+if(lte(N,1),{whip_offset}*(1-N),0),Y)':"
            f"cb='cb(X+if(lte(N,1),{whip_offset}*(1-N),0),Y)':"
            f"cr='cr(X+if(lte(N,1),{whip_offset}*(1-N),0),Y)'"
        )
        filters.append("boxblur=luma_radius=4:luma_power=1:enable='lte(n,1)'")

    # 7. Camera Shake (9_VAGhAdne8 & CapCut Auto-Velocity: multi-harmonic exponential decay shake)
    if add_shake:
        shake_frames = 10
        shake_amp = 16
        # Multi-harmonic exponential decay: explosive instant punch on frame 0, organic damping over 10 frames
        sx_expr = (
            f"if(lt(N,{shake_frames}),{shake_amp}*sin(N*2.2)*exp(-0.30*N),0)"
        )
        sy_expr = (
            f"if(lt(N,{shake_frames}),{shake_amp//2}*cos(N*3.1)*exp(-0.30*N),0)"
        )
        filters.append(
            f"geq=lum='p(X+({sx_expr}),Y+({sy_expr}))':cb='cb(X+({sx_expr}),Y+({sy_expr}))':cr='cr(X+({sx_expr}),Y+({sy_expr}))'"
        )

    # 8. Multi-Harmonic Chromatic Dispersion RGB Split (Boris FX Sapphire / 8Fyb0LXw1BU style)
    if add_chr_aber:
        split_frames = 10
        split_amp = 8
        # Multi-plane optical dispersion: instant explosive color refraction decaying with exponential damping
        split_x = f"if(lt(N,{split_frames}),{split_amp}*cos(N*1.8)*exp(-0.32*N),0)"
        split_y = f"if(lt(N,{split_frames}),{split_amp//2}*sin(N*2.4)*exp(-0.32*N),0)"
        filters.append(
            f"geq=lum='p(X+({split_x}),Y+({split_y}))':cb='cb(X,Y)':cr='cr(X-({split_x}),Y-({split_y}))'"
        )

    # 9. Cursed Technique Bloom Glow (8Fyb0LXw1BU: highlight overexposure + soft unsharp fringe)
    if add_bloom:
        filters.append("curves=all='0/0 0.5/0.55 0.75/0.90 1/1'")
        filters.append("unsharp=11:11:2.2:11:11:0.0")

    # 10. Impact Invert Frame (1-frame negative color inversion on climax strike)
    if add_impact_invert:
        filters.append("negate=enable='between(n,0,1)'")

    # 11. Speed Lines (velocity streaks on fast slices)
    if add_speed_lines:
        filters.append("drawgrid=w=100:h=100:t=2:c=white@0.10:enable='between(n,0,5)'")

    # 11b. Beat-Reactive Exposure & Saturation Pulse (2-frame high-shutter contrast/saturation burst on drop impacts)
    if add_exposure_pulse:
        filters.append("eq=contrast=1.22:brightness=0.05:saturation=1.36:enable='between(n,0,2)'")

    # 12. Cinematic letterbox bars — intro atmospheric framing
    if add_bars:
        bar_h = 90
        filters.append(f"drawbox=x=0:y=0:w=iw:h={bar_h}:color=black:t=fill")
        filters.append(f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=black:t=fill")

    # 13. SAR normalization + exact duration trim + PTS reset
    filters.append("setsar=1")
    filters.append(f"trim=duration={duration:.3f}")
    filters.append("setpts=PTS-STARTPTS")

    return ",".join(filters)


def build_cc_filter(
    preset_name: str = "marvel_hdr",
    with_flicker: bool = False,
    drop_time: float = 0.0,
    dynamic_mood_shift: bool = True
) -> str:
    """
    Builds the 4K HDR Color Grade filtergraph snippet.
    Dynamic Mood Shift:
      - Pre-drop (t < drop_time): Moody desaturation (0.72x) + subtle contrast pull for tense atmosphere
      - Drop & Climax (t >= drop_time): Hyper-vibrant color explosion (1.20x saturation) + punchy HDR contrast
    Adds xtlw3zvKGAE-style light flicker: sinusoidal brightness oscillation at 3Hz
    in the 2 seconds immediately before the beat drop.
    Adds fine film grain (noise) to eliminate flat digital gradients and provide texture.
    """
    cfg = CC_PRESETS.get(preset_name, CC_PRESETS["marvel_hdr"])

    if dynamic_mood_shift and drop_time > 0.8:
        # Pre-drop desaturated cinematic grade -> Drop neon color explosion
        sat_expr = (
            f"'if(lt(t,{drop_time:.2f}),{cfg['saturation']*0.72:.2f},{cfg['saturation']*1.28:.2f})'"
        )
        con_expr = (
            f"'if(lt(t,{drop_time:.2f}),{cfg['contrast']*0.94:.2f},{cfg['contrast']*1.06:.2f})'"
        )
        gam_expr = (
            f"'if(lt(t,{drop_time:.2f}),{cfg['gamma']*1.04:.2f},{cfg['gamma']*0.96:.2f})'"
        )
        eq_part = (
            f"eq=contrast={con_expr}:brightness={cfg['brightness']}"
            f":saturation={sat_expr}:gamma={gam_expr}:eval=frame"
        )
    else:
        eq_part = (
            f"eq=contrast={cfg['contrast']}:brightness={cfg['brightness']}"
            f":saturation={cfg['saturation']}:gamma={cfg['gamma']}"
        )

    unsharp_part = f"unsharp={cfg['unsharp']}"
    levels_part = "colorlevels=rimin=0.03:gimin=0.03:bimin=0.03:rimax=0.98:gimax=0.98:bimax=0.98"
    grain_part = "noise=alls=5:allf=t+u"

    # Light flicker & vignette breathing — xtlw3zvKGAE & 9_VAGhAdne8: tension oscillation before drop
    if with_flicker and drop_time > 2.0:
        flicker_start = drop_time - 2.0
        flicker_end = drop_time
        flicker_eq = (
            f",eq=brightness='if(between(t,{flicker_start:.2f},{flicker_end:.2f}),"
            f"sin(t*6.28*3)*0.08,0)':eval=frame"
        )
        base_vig = cfg['vignette']
        vignette_part = (
            f"vignette='if(between(t,{flicker_start:.2f},{flicker_end:.2f}),"
            f"{base_vig}+sin(t*6.28*2)*0.06,{base_vig})':eval=frame"
        )
    else:
        flicker_eq = ""
        vignette_part = f"vignette={cfg['vignette']}"

    return f"{eq_part},{levels_part},{unsharp_part},{vignette_part},{grain_part}{flicker_eq}"


def build_beat_flash_filters(
    beat_timestamps: List[float],
    flash_duration: float = 0.07,
    opacity: float = 0.80,
    include_dark_dip: bool = True
) -> List[str]:
    """
    Builds white impact flash + dark dip sequence (8Fyb0LXw1BU style).
    Flash fires on 808 drops; a brief dark dip follows 0.10s after for the
    'hit → blackout → scene' rhythm characteristic of all 3 reference edits.
    """
    flash_filters = []
    last_flash = -10.0
    for t in beat_timestamps:
        if t - last_flash >= 0.55:
            cond = f"between(t,{t:.2f},{t+flash_duration:.2f})"
            flash_filters.append(
                f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{opacity:.2f}:t=fill:enable='{cond}'"
            )
            if include_dark_dip:
                dip_start = t + flash_duration
                dip_end = dip_start + 0.05
                dip_cond = f"between(t,{dip_start:.2f},{dip_end:.2f})"
                flash_filters.append(
                    f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.60:t=fill:enable='{dip_cond}'"
                )
            last_flash = t
    return flash_filters
