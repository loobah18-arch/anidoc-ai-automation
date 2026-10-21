"""
FFmpeg xfade Transitions & Velocity Ramping Engine for AniDoc.
Generates dynamic beat-synced visual transitions (whip pans, circle crops, dissolves)
and velocity speed ramping (slow-motion buildup into high-speed snap) directly in FFmpeg.
"""
import random
from typing import List, Dict, Any, Optional

# Curated list of high-energy transition effects supported natively by FFmpeg xfade
XFADE_TRANSITIONS = [
    "wipeleft",
    "wiperight",
    "slideleft",
    "slideright",
    "circlecrop",
    "fadeblack",
    "smoothleft",
    "radial",
    "horzopen",
    "vertopen"
]


def build_xfade_transition_filter(
    clip_count: int,
    durations: List[float],
    transition_duration: float = 0.25,
    custom_transitions: Optional[List[str]] = None
) -> Tuple_or_Filter:
    """
    Constructs a chained FFmpeg xfade filtergraph for seamless scene transitions.
    Formula: offset_i = offset_{i-1} + dur_{i} - transition_duration
    """
    if clip_count < 2:
        return ""

    filter_parts = []
    current_offset = durations[0] - transition_duration
    last_v = "[v0]"
    
    for i in range(1, clip_count):
        t_effect = (
            custom_transitions[i % len(custom_transitions)]
            if custom_transitions
            else random.choice(XFADE_TRANSITIONS)
        )
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
    Drop impact: hyper-velocity explosion (1.35x speed).
    """
    if is_drop:
        return "setpts=0.74*PTS"
    return "setpts=1.20*PTS"
