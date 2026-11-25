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

    if "freeze" in fx:                                    # reference look: the last shot freezes on its final pose
        hold = min(0.6, d * 0.4)
        chain.append(f"trim=end_frame={max(1, round((d - hold) * FPS))}")
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


def build_ref_grade(warm: bool = False, close: bool = False) -> str:
    """Look of the reference Shorts (Yoriichi 'Muzan's Nightmare', Gojo 'Jalebi Baby'):
    crushed blacks, a teal-blue grade that flips to warm amber/red after the midpoint,
    soft glow/halation on highlights, light chromatic aberration, vignette, fine grain."""
    bal = ("colorbalance=rs=0.05:gs=-0.01:bs=-0.07:rm=0.07:gm=0.01:bm=-0.07:rh=0.08:gh=0.02:bh=-0.08" if warm else
           "colorbalance=rs=-0.07:gs=0.0:bs=0.09:rm=-0.05:gm=0.01:bm=0.06:rh=-0.02:gh=0.02:bh=0.05")
    ca = "rgbashift=rh=-4:bh=4:edge=smear,crop=iw-8:ih:4:0,scale=iw+8:ih," if close else ""   # no coloured edge line
    return (
        "eq=contrast=1.10:saturation=1.12:gamma=1.04:brightness=0.01," + bal + "," + ca +
        "split[rg0][rg1];[rg1]gblur=sigma=22,eq=brightness=-0.10:contrast=1.35[rgl];"
        "[rg0][rgl]blend=all_mode=screen:all_opacity=0.30,"
        "vignette=PI/5.5,noise=alls=5:allf=t,setsar=1,format=yuv420p"
    )


def build_cine_fx(fx, d: float, w: int, h: int, idx: int = 0) -> str:
    """Cine look (TumpyGFX 'Middle of the Night' AMV) per-shot extras applied before the grade:
    blur-in open, echo trails on fast hits, procedural rain, dutch tilt."""
    fx = set(fx or [])
    ch = []
    if "echo" in fx:
        ch.append("tmix=frames=3:weights='4 1.5 0.5'")
    if "blurin" in fx:
        ch.append("gblur=sigma=26:enable='lt(t\\,0.07)',gblur=sigma=11:enable='between(t\\,0.07\\,0.15)',"
                  "gblur=sigma=4:enable='between(t\\,0.15\\,0.23)'")
    if "rain" in fx:                                      # sparse noise -> long slanted streaks, screened on luma only
        ch.append(f"split[cr0][cr1];[cr1]lutyuv=y=128:u=128:v=128,noise=alls=100:allf=t,"
                  f"lutyuv=y='if(gt(val\\,236)\\,255\\,0)':u=128:v=128,dblur=angle=100:radius=40,"
                  f"lutyuv=y='clip((val-5)*7\\,0\\,255)':u=128:v=128,crop={w}:{int(h * 0.9)}:0:{h - int(h * 0.9)},"
                  f"scale={w}:{h}[crl];[cr0][crl]blend=c0_mode=screen:c0_opacity=0.42:c1_mode=normal:c1_opacity=1:"
                  f"c2_mode=normal:c2_opacity=1")
    if "tilt" in fx:
        a = 0.075 if idx % 2 else -0.075
        ch.append(f"rotate={a}:fillcolor=black,scale={int(w * 1.12) // 2 * 2}:-2,crop={w}:{h},setsar=1")
    return ",".join(ch) if ch else "null"


def build_cine_grade(section: str = "teal", close: bool = False) -> str:
    """Section grades: 'cold' desaturated blue for the calm build, 'teal' orange-teal split-tone for the drop,
    'warm' amber after the breath; glow on highlights, heavier vignette, fine grain."""
    if section == "cold":
        eq, bal = ("eq=contrast=1.08:saturation=0.82:gamma=1.03",
                   "colorbalance=rs=-0.08:gs=-0.01:bs=0.10:rm=-0.05:bm=0.07:rh=-0.03:bh=0.05")
    elif section == "warm":
        eq, bal = ("eq=contrast=1.13:saturation=1.12:gamma=1.05",
                   "colorbalance=rs=0.07:gs=0.0:bs=-0.08:rm=0.08:gm=0.02:bm=-0.08:rh=0.09:gh=0.03:bh=-0.09")
    else:
        eq, bal = ("eq=contrast=1.14:saturation=1.18:gamma=1.05",
                   "colorbalance=rs=-0.08:gs=0.01:bs=0.10:rm=0.02:bm=-0.02:rh=0.09:gh=0.02:bh=-0.09")
    ca = "rgbashift=rh=-4:bh=4:edge=smear,crop=iw-8:ih:4:0,scale=iw+8:ih," if close else ""
    return (eq + "," + bal + "," + ca +
            "split[cg0][cg1];[cg1]gblur=sigma=22,eq=brightness=-0.16:contrast=1.45[cgl];"
            "[cg0][cgl]blend=all_mode=screen:all_opacity=0.22,"
            "vignette=PI/5.4,noise=alls=6:allf=t,setsar=1,format=yuv420p")


def build_cine_post(fx, d: float, w: int, h: int) -> str:
    """After the grade: letterbox bars on calm holds, a cut to black before the drop."""
    fx = set(fx or [])
    ch = []
    if "letterbox" in fx:
        bh = int(h * 0.10)
        ch.append(f"drawbox=x=0:y=0:w=iw:h={bh}:color=black:t=fill,drawbox=x=0:y=ih-{bh}:w=iw:h={bh}:color=black:t=fill")
    if "blackout" in fx:
        fd = min(0.16, d * 0.2)
        ch.append(f"fade=t=out:st={max(0.0, d - fd):.3f}:d={fd:.3f}")
    return ",".join(ch) if ch else "null"


def ref_transition_pattern(n_shots: int, drop_index: int, flip_index: int) -> List[str]:
    """Reference transitions: zoom-blur and directional motion-blur whips between
    most shots, a flash on the drop and on the colour flip, plain punch-ins between."""
    kinds = []
    for b in range(1, n_shots):
        k = b - drop_index
        if b < drop_index:
            kinds.append("cut")
        elif b == drop_index or b == flip_index:
            kinds.append("flash")
        elif k % 3 == 1:
            kinds.append("zoom")
        elif k % 3 == 2:
            kinds.append("whip")
        else:
            kinds.append("punch")
    return kinds


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
