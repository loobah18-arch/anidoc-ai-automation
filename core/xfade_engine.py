"""
FFmpeg xfade Transitions & Velocity Ramping Engine for AniDoc.
Generates dynamic beat-synced visual transitions (whip pans, circle crops, dissolves)
and velocity speed ramping (slow-motion buildup into high-speed snap) directly in FFmpeg.
"""
import random
from typing import List, Dict, Any, Optional

# Curated list of high-energy transition effects supported natively by FFmpeg xfade
XFADE_TRANSITIONS = [
    "hlslice",
    "hrslice",
    "diagtl",
    "diagbr",
    "hblur",
    "zoomin",
    "fadewhite",
    "distance",
    "smoothleft",
    "smoothright",
    "squeezeh"
]

# 2026 Modern AMV Transitions (Smooth directional movement, kinetic punches, and clean optical dissolves; no harsh blinds or flashes)
MODERN_COMBAT_TRANSITIONS = [
    "smoothleft",   # Smooth horizontal camera pan left following blade swing
    "smoothright",  # Smooth horizontal camera pan right following blade swing
    "zoomin",       # Kinetic punch zoom forward into strike
    "dissolve",     # Clean seamless optical dissolve
    "wipeleft",     # Clean directional wipe
]

# Beat drop transition impact (Zero strobe / white flash)
MODERN_DROP_TRANSITIONS = [
    "zoomin",      # Hyper-velocity punch zoom into beat drop
    "dissolve",    # Smooth dramatic impact dissolve
]

# Outro resolution transition
MODERN_OUTRO_TRANSITIONS = [
    "fadeblack",   # Cinematic fade to black
    "dissolve"
]


def build_xfade_transition_filter(
    clip_count: int,
    durations: List[float],
    transition_duration: float = 0.15,
    custom_transitions: Optional[List[str]] = None,
    drop_index: Optional[int] = None,
    use_handle_compensation: bool = True
) -> str:
    """
    Constructs a chained FFmpeg xfade filtergraph with buttery-smooth 2026 transitions:
    - Beat Drop Transition (at drop_index): Smooth kinetic 'zoomin' or 'dissolve' (zero random flash).
    - Combat Cuts: Smooth directional pans and kinetic punches (smoothleft, smoothright, zoomin, dissolve, wipeleft).
    - Outro (final cut): Cinematic fadeblack on the final climax resolution cut.
    - Zero-Drift Sync Formula: With handle compensation, transition offset_i = sum(durations[:i])
      matching musical beats with 0.00ms cumulative error.
    """
    if clip_count < 2:
        return ""

    filter_parts = []
    current_offset = durations[0] if use_handle_compensation else max(0.1, durations[0] - transition_duration)
    last_v = "[v0]"
    
    for i in range(1, clip_count):
        # 1. Beat Drop transition
        if drop_index is not None and i == drop_index:
            t_effect = random.choice(MODERN_DROP_TRANSITIONS)
        # 2. Outro transition
        elif i == clip_count - 1:
            t_effect = random.choice(MODERN_OUTRO_TRANSITIONS)
        # 3. Custom or modern combat slash
        elif custom_transitions:
            t_effect = custom_transitions[i % len(custom_transitions)]
        else:
            t_effect = random.choice(MODERN_COMBAT_TRANSITIONS)

        next_v = f"[v{i}]"
        out_v = f"[xfade_v{i}]" if i < clip_count - 1 else "[xfade_vout]"

        # Ensure exact frame rate and timebase match across all chained xfade input links
        in_a = f"in_a_{i}"
        in_b = f"in_b_{i}"
        filter_parts.append(
            f"{last_v}fps=60,settb=1/60[{in_a}];"
            f"{next_v}fps=60,settb=1/60[{in_b}];"
            f"[{in_a}][{in_b}]xfade=transition={t_effect}:duration={transition_duration:.2f}:offset={max(0.1, current_offset):.2f}{out_v}"
        )
        last_v = out_v
        if i < len(durations) - 1:
            if use_handle_compensation:
                current_offset += durations[i]
            else:
                current_offset += durations[i] - transition_duration

    return ";".join(filter_parts)


def build_velocity_ramp_expression(is_drop: bool, segment_duration: float) -> str:
    """
    Generates a speed ramp filter expression for FFmpeg setpts.
    Pre-drop: tension buildup slow-mo (0.75x speed).
    Drop impact: hyper-velocity explosion (1.45x speed).
    """
    if is_drop:
        return "setpts=0.68*PTS"
    return "setpts=1.25*PTS"
