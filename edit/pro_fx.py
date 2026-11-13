"""
Pro AMV motion & transition FX for AniDoc (beat-synced, sync-safe).

Every effect lives INSIDE a shot, so shots can be joined with plain hard cuts and the
edit never drifts off the beat (no xfade overlap math). A "transition" is built from
the tail of shot A (out-FX) plus the head of shot B (in-FX), which is how CapCut /
AE edits fake whip pans and zoom transitions anyway.

In-FX (start of a shot):
  punch   - zoom punch-in that settles (1.0 + Z*exp(-k t))
  whip_in - slides in from the side with directional motion blur
  zoom_in - starts heavily zoomed + blurred, snaps back to 1.0 (pairs with zoom_out)
  flash   - white flash that decays over ~4 frames
  glitch  - RGB split + noise for 3 frames
  shake   - decaying camera shake (impact)
Out-FX (end of a shot):
  whip_out - slides out with motion blur (pairs with whip_in on the next shot)
  zoom_out - accelerating zoom + blur into the cut (pairs with zoom_in)
Body:
  drift   - slow 3-5% push-in for held / dialogue shots
  pulse   - small zoom pulse on every beat inside the shot
  speed   - playback speed (0.5 = slow motion)
"""
from typing import Dict, List, Optional

FPS = 30


def _sum(*terms: str) -> str:
    terms = [t for t in terms if t]
    return "+".join(terms) if terms else "0"


def build_shot_fx(
    duration: float,
    out_w: int,
    out_h: int,
    fx: Optional[List[str]] = None,
    beat: float = 0.4616,
    speed: float = 1.0,
    cover_input: bool = True,
    n_frames: Optional[int] = None,
) -> str:
    """Returns a comma-joined ffmpeg filter chain (no labels) that turns any source
    frame into an out_w x out_h shot with the requested FX. Duration is the shot's
    on-screen length; time t inside the chain starts at 0 for the shot."""
    fx = set(fx or [])
    d = max(0.05, duration)
    chain: List[str] = []

    if speed != 1.0:
        chain.append(f"setpts={1.0 / speed:.4f}*(PTS-STARTPTS)")
    else:
        chain.append("setpts=PTS-STARTPTS")
    chain.append(f"fps={FPS}")
    if cover_input:
        chain.append(f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},setsar=1")

    # ---- zoom factor z(t) ------------------------------------------------
    z_terms = ["1.06"]  # 6% headroom so shake / slides never show edges
    if "punch" in fx:
        z_terms.append("0.22*exp(-9*t)")
    if "zoom_in" in fx:
        z_terms.append("0.55*exp(-14*t)")
    if "drift" in fx:
        z_terms.append(f"0.05*t/{d:.3f}")
    if "pulse" in fx:
        z_terms.append(f"0.045*exp(-12*mod(t\\,{beat:.4f}))")
    if "whip_in" in fx:
        z_terms.append("if(lt(t\\,0.16)\\,0.5*pow(1-t/0.16\\,2)\\,0)")
    if "whip_out" in fx:
        z_terms.append(f"if(gt(t\\,{d - 0.16:.3f})\\,0.5*pow((t-{d - 0.16:.3f})/0.16\\,2)\\,0)")
    if "zoom_out" in fx:
        tail = 0.20
        z_terms.append(f"if(gt(t\\,{d - tail:.3f})\\,0.9*pow((t-{d - tail:.3f})/{tail:.3f}\\,2)\\,0)")
    z = _sum(*z_terms)
    chain.append(
        f"scale=w='trunc({out_w}*({z})/2)*2':h='trunc({out_h}*({z})/2)*2':eval=frame:flags=bilinear"
    )

    # ---- x/y offset (shake, whips) ----------------------------------------
    x_terms, y_terms = [], []
    if "shake" in fx:
        x_terms.append("26*sin(t*2*PI*14)*exp(-5*t)")
        y_terms.append("18*cos(t*2*PI*11)*exp(-5*t)")
    if "whip_in" in fx:
        # enters from the right: big offset -> 0 over 0.16s
        x_terms.append(f"if(lt(t\\,0.16)\\,{out_w*0.32:.0f}*pow(1-t/0.16\\,3)\\,0)")
    if "whip_out" in fx:
        tail = 0.16
        x_terms.append(f"if(gt(t\\,{d - tail:.3f})\\,-{out_w*0.32:.0f}*pow((t-{d - tail:.3f})/{tail:.3f}\\,3)\\,0)")
    x_off = _sum(*x_terms)
    y_off = _sum(*y_terms)
    # crop window centred, clamped inside the scaled frame; whip offsets go beyond the
    # frame, so we pad first to allow the slide to reveal a motion-blurred edge.
    if True:
        chain.append(
            f"crop={out_w}:{out_h}:x='max(0\\,min(iw-{out_w}\\,(iw-{out_w})/2+({x_off})))':"
            f"y='max(0\\,min(ih-{out_h}\\,(ih-{out_h})/2+({y_off})))'"
        )

    # ---- blur / colour hits (timeline-enabled, cheap) ---------------------
    if "whip_in" in fx:
        chain.append("dblur=angle=0:radius=60:enable='lt(t\\,0.14)'")
    if "whip_out" in fx:
        chain.append(f"dblur=angle=0:radius=60:enable='gt(t\\,{d - 0.14:.3f})'")
    if "zoom_in" in fx:
        chain.append("gblur=sigma=14:enable='lt(t\\,0.10)'")
    if "zoom_out" in fx:
        chain.append(f"gblur=sigma=14:enable='gt(t\\,{d - 0.10:.3f})'")
    if "glitch" in fx:
        chain.append("rgbashift=rh=-14:bh=14:gv=6:enable='lt(t\\,0.10)'")
        chain.append("noise=alls=40:allf=t:enable='lt(t\\,0.10)'")
    if "flash" in fx:
        chain.append("eq=brightness=0.75:enable='lt(t\\,0.034)'")
        chain.append("eq=brightness=0.45:enable='between(t\\,0.034\\,0.07)'")
        chain.append("eq=brightness=0.2:enable='between(t\\,0.07\\,0.13)'")
    if "shake" in fx:
        chain.append("rgbashift=rh=-6:bh=6:enable='lt(t\\,0.12)'")

    chain.append("tpad=stop_mode=clone:stop_duration=1")
    chain.append(f"trim=end_frame={n_frames or max(1, round(d * FPS))}")
    chain.append("setpts=PTS-STARTPTS")
    chain.append("setsar=1")
    chain.append("format=yuv420p")
    return ",".join(chain)


def pair_transitions(n_shots: int, kinds: List[str]) -> List[List[str]]:
    """Given the transition kind for each boundary (len n_shots-1: 'cut', 'whip',
    'zoom', 'flash', 'glitch'), returns the per-shot fx lists for out/in sides."""
    out = [[] for _ in range(n_shots)]
    for i, k in enumerate(kinds):
        a, b = i, i + 1
        if b >= n_shots:
            break
        if k == "whip":
            out[a].append("whip_out"); out[b].append("whip_in")
        elif k == "zoom":
            out[a].append("zoom_out"); out[b].append("zoom_in")
        elif k == "flash":
            out[b].append("flash"); out[b].append("punch")
        elif k == "glitch":
            out[b].append("glitch")
        elif k == "punch":
            out[b].append("punch")
    return out


def default_transition_pattern(n_shots: int, drop_index: int, beat_starts: Optional[List[int]] = None) -> List[str]:
    """A musical default: flash on the drop, zoom every 8th cut, whip every 4th,
    punch on the rest, an occasional glitch. Pre-drop boundaries are soft cuts."""
    kinds = []
    for b in range(1, n_shots):
        if b < drop_index:
            kinds.append("cut")
        elif b == drop_index:
            kinds.append("flash")
        else:
            k = b - drop_index
            if k % 8 == 0:
                kinds.append("zoom")
            elif k % 4 == 0:
                kinds.append("whip")
            elif k % 6 == 3:
                kinds.append("glitch")
            else:
                kinds.append("punch")
    return kinds


def build_battle_iq_grade() -> str:
    """Reference look (AOT EDIT style): crushed blacks, muted mids, teal-green
    shadows / warm highlights, soft bloom, heavy vignette, fine grain."""
    return (
        "eq=contrast=1.18:saturation=1.08:gamma=0.94:brightness=-0.02,"
        "colorbalance=rs=-0.06:gs=0.02:bs=0.07:rh=0.06:gh=0.01:bh=-0.06,"
        "split[gb0][gb1];[gb1]gblur=sigma=18,eq=brightness=-0.08:contrast=1.3[gbl];"
        "[gb0][gbl]blend=all_mode=screen:all_opacity=0.28,"
        "vignette=PI/4.2,format=yuv420p"
    )


def shot_frame_counts(durations: List[float], fps: int = FPS) -> List[int]:
    """Exact per-shot frame counts from cumulative boundaries, so hard-cut edits never
    drift off the beat grid through rounding."""
    out, acc, prev = [], 0.0, 0
    for d in durations:
        acc += d
        cur = round(acc * fps)
        out.append(max(1, cur - prev))
        prev = cur
    return out
