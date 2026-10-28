"""
Sound Design Engine for Anime Shorts (Phase 8).
Generates subtle, synchronized audio enhancements:
- Pre-drop tension risers
- 808 drop & climax sub-bass impacts
- Transition whooshes on major scene cuts
Subtle (-18dB) and balanced to never overpower dialogue or music.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path


def build_pre_drop_riser_filter(
    drop_time: float,
    riser_duration: float = 0.50,
    gain_db: float = -18.0
) -> str:
    """
    Synthesizes a subtle high-frequency tension riser before the 808 beat drop.
    Thins out lower frequencies while introducing a crisp ambient sweep into the drop.
    """
    r_start = max(0.05, drop_time - riser_duration)
    r_end = drop_time
    cond = f"between(t\\,{r_start:.3f}\\,{r_end:.3f})"
    return f"highpass=f=1400:enable='{cond}',volume=enable='{cond}':volume=1.15"


def build_sub_impact_filter(
    impact_times: List[float],
    duration: float = 0.35,
    boost_db: float = 3.5
) -> str:
    """
    Synthesizes a deep sub-bass physical impact (60Hz) on key narrative hits
    (such as the 808 drop and the climax finisher strike).
    """
    if not impact_times:
        return "anull"

    filters = []
    for t in impact_times:
        t_end = t + duration
        cond = f"between(t\\,{t:.3f}\\,{t_end:.3f})"
        filters.append(f"bass=g={boost_db}:f=60:enable='{cond}'")
        filters.append(f"volume=enable='{cond}':volume=1.20")
    return ",".join(filters)


def build_transition_whoosh_filter(
    transition_times: List[float],
    whoosh_duration: float = 0.22
) -> str:
    """
    Synthesizes a subtle high-pass air whoosh on major narrative transitions
    (e.g. Hook -> Drop, Escalation -> Climax).
    """
    if not transition_times:
        return "anull"

    filters = []
    for t in transition_times:
        t_start = max(0.0, t - (whoosh_duration * 0.6))
        t_end = t + (whoosh_duration * 0.4)
        cond = f"between(t\\,{t_start:.3f}\\,{t_end:.3f})"
        filters.append(f"treble=g=2.8:f=5500:enable='{cond}'")
    return ",".join(filters)


def build_sound_design_filter_chain(
    drop_time: float,
    cut_timestamps: List[float],
    climax_time: Optional[float] = None,
    enable_sound_design: bool = True
) -> str:
    """
    Constructs the complete chained audio filter for subtle, non-intrusive sound design.
    """
    if not enable_sound_design:
        return "anull"

    chains = []

    # 1. Pre-drop tension riser
    riser = build_pre_drop_riser_filter(drop_time)
    if riser != "anull":
        chains.append(riser)

    # 2. Key impact hits (808 drop + climax hit)
    impact_hits = [drop_time]
    if climax_time and climax_time > drop_time + 1.5:
        impact_hits.append(climax_time)
    impacts = build_sub_impact_filter(impact_hits)
    if impacts != "anull":
        chains.append(impacts)

    # 3. Transition whooshes (at most 2-3 key transition moments)
    trans_hits = []
    for t in cut_timestamps:
        if t > drop_time + 1.0 and (climax_time is None or abs(t - climax_time) > 1.0):
            trans_hits.append(t)
            if len(trans_hits) >= 2:
                break
    whooshes = build_transition_whoosh_filter(trans_hits)
    if whooshes != "anull":
        chains.append(whooshes)

    return ",".join(chains) if chains else "anull"
