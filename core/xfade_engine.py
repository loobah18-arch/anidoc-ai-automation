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

# 2026 Modern AMV Transitions (Katana slashes, directional whips, kinetic zoom punches)
MODERN_COMBAT_TRANSITIONS = [
    "hlslice",     # Horizontal katana slash cut
    "hrslice",     # Reverse horizontal slash cut
    "diagtl",      # Diagonal top-left katana slash
    "diagbr",      # Diagonal bottom-right katana slash
    "hblur",       # High-speed horizontal motion-blur whip
    "zoomin",      # Kinetic punch zoom forward into strike
    "smoothleft",  # Directional whip pan left following blade swing
    "smoothright", # Directional whip pan right following blade swing
    "squeezeh",    # Fast horizontal compression snap
    "distance"     # 3D spatial push warp
]

# Beat drop transition impact
MODERN_DROP_TRANSITIONS = [
    "fadewhite",   # Signature 2026 white exposure burst on 808 drop
    "zoomin",      # Hyper-velocity punch zoom
    "distance"     # Spatial impact push
]

# Outro resolution transition
MODERN_OUTRO_TRANSITIONS = [
    "fadeblack",   # Cinematic fade to black
    "dissolve"
]


def build_xfade_transition_filter(
    clip_count: int,
    durations: List[float],
    transition_duration: float = 0.12,
    custom_transitions: Optional[List[str]] = None,
    drop_index: Optional[int] = None
) -> str:
    """
    Constructs a chained FFmpeg xfade filtergraph with 2026 Modern AMV transitions:
    - Beat Drop Transition (at drop_index): High-impact 'fadewhite' or 'zoomin' flash.
    - Combat Cuts: Ultra-snappy 0.12s katana slashes (hlslice, diagtl, diagbr, hblur, zoomin).
    - Outro (final cut): Cinematic fadeblack on the final climax resolution cut.
    - Formula: offset_i = offset_{i-1} + dur_{i} - transition_duration
    """
    if clip_count < 2:
        return ""

    filter_parts = []
    current_offset = durations[0] - transition_duration
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
        
        filter_parts.append(
            f"{last_v}{next_v}xfade=transition={t_effect}:duration={transition_duration:.2f}:offset={max(0.1, current_offset):.2f}{out_v}"
        )
        last_v = out_v
        if i < len(durations) - 1:
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
