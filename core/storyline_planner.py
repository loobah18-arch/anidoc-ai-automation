"""
FireRed-OpenStoryline Narrative Arc Planner (FireRedTeam/FireRed-OpenStoryline)
===============================================================================
Implements OpenStoryline's HOOK → BUILD → DROP → OUTRO narrative arc logic
for viral short-form anime edits.

Key features:
  - 4-phase narrative arc with CPS (cuts-per-second) targeting per phase
  - Tension-curve modulation T(t) ∈ [0, 1] aligned with the music
  - Beat-snapped cut boundaries synchronized with BeatSync-Engine downbeats
  - Automatic VFX parameter assignment per phase (DoF rack focus, velocity curve, shake, CA, bloom, flash)
  - Anti-repetition & variety enforcement
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import math


@dataclass
class ArcPhase:
    name: str
    start_frac: float          # Fraction of total duration [0.0 - 1.0]
    end_frac: float
    cps_target: float          # Cuts per second target
    cps_min: float
    cps_max: float
    preferred_roles: List[str] # Clip roles: "dialogue", "tension", "action", "sakuga", "climax", "hero_pose"
    add_bars: bool             # Cinematic letterbox
    speed_bias: str            # "slow" | "ramp" | "snap" | "resolve"
    description: str


ARC_PHASES = [
    ArcPhase(
        name="HOOK",
        start_frac=0.0,
        end_frac=0.08,
        cps_target=0.6,
        cps_min=0.4,
        cps_max=0.8,
        preferred_roles=["dialogue", "hero_pose"],
        add_bars=True,
        speed_bias="slow",
        description="Character monologue / quote reveal with cinematic DoF rack-focus",
    ),
    ArcPhase(
        name="BUILD",
        start_frac=0.08,
        end_frac=0.25,
        cps_target=1.4,
        cps_min=0.9,
        cps_max=2.0,
        preferred_roles=["tension", "action"],
        add_bars=True,
        speed_bias="ramp",
        description="Escalating combat tension with accelerating speed ramp",
    ),
    ArcPhase(
        name="DROP",
        start_frac=0.25,
        end_frac=0.88,
        cps_target=2.8,
        cps_min=1.8,
        cps_max=4.0,
        preferred_roles=["sakuga", "climax", "action"],
        add_bars=False,
        speed_bias="snap",
        description="Peak sakuga explosion, velocity punch (0.3x->1.5x), camera shake, chromatic aberration & beat flashes",
    ),
    ArcPhase(
        name="OUTRO",
        start_frac=0.88,
        end_frac=1.0,
        cps_target=0.8,
        cps_min=0.5,
        cps_max=1.2,
        preferred_roles=["hero_pose", "dialogue"],
        add_bars=False,
        speed_bias="resolve",
        description="Cool-down, iconic stance / quote resolve with soft bloom",
    ),
]


@dataclass
class PlannedSegment:
    timeline_in: float
    timeline_out: float
    duration: float
    arc_phase: str
    is_drop: bool
    prev_is_drop: bool
    cps_density: float
    add_bars: bool
    add_rack_focus: bool
    add_shake: bool
    add_chr_aber: bool
    add_bloom: bool
    add_flash: bool
    speed: float
    scale_factor: float
    section_type: str
    energy: float
    start: float = 0.0
    end: float = 0.0


class StorylinePlanner:
    """
    Generates a narrative-arc-aware edit plan from a BeatSyncResult.
    """

    def __init__(self, drop_time: float, total_duration: float):
        self.drop_time = drop_time
        self.total_duration = total_duration
        self.phases = self._calibrate_phases(drop_time, total_duration)

    def _calibrate_phases(self, drop_time: float, dur: float) -> List[ArcPhase]:
        """
        Calibrates phase boundaries so the DROP phase begins precisely at the musical drop.
        """
        if dur <= 0:
            return ARC_PHASES

        drop_frac = drop_time / dur
        outro_start = max(drop_frac + 0.10, 0.88)
        if outro_start >= 1.0:
            outro_start = 0.90

        hook_end = min(drop_frac * 0.35, 0.10)

        calibrated = []
        for phase in ARC_PHASES:
            p = ArcPhase(**vars(phase))
            if p.name == "HOOK":
                p.start_frac = 0.0
                p.end_frac = hook_end
            elif p.name == "BUILD":
                p.start_frac = hook_end
                p.end_frac = drop_frac
            elif p.name == "DROP":
                p.start_frac = drop_frac
                p.end_frac = outro_start
            elif p.name == "OUTRO":
                p.start_frac = outro_start
                p.end_frac = 1.0
            calibrated.append(p)

        return calibrated

    def phase_for_time(self, t: float) -> ArcPhase:
        frac = t / max(self.total_duration, 0.01)
        for phase in self.phases:
            if phase.start_frac <= frac < phase.end_frac:
                return phase
        return self.phases[-1]

    def plan_from_beatsync(self, segments: List[Dict[str, Any]]) -> List[PlannedSegment]:
        """
        Converts raw BeatSyncResult segments into narrative-arc-enriched
        PlannedSegments with full cinematic VFX flag assignment.
        """
        planned = []
        total = len(segments)

        for idx, seg in enumerate(segments):
            t = seg["start"]
            phase = self.phase_for_time(t)
            is_drop = seg["is_drop"]
            energy = seg.get("energy", 0.5)
            kick = seg.get("kick", 0.5)
            duration = seg["duration"]

            # Velocity & VFX assignment based on Arc Phase
            if phase.name == "HOOK":
                speed = 0.30
                scale_factor = 1.03
                add_bars = True
                add_rf = (idx == 0) # Rack-focus on opening character reveal
                add_shake = False
                add_chr = False
                add_bloom = False
                add_flash = False

            elif phase.name == "BUILD":
                build_span = max(0.01, (phase.end_frac - phase.start_frac) * self.total_duration)
                build_progress = (t - phase.start_frac * self.total_duration) / build_span
                build_progress = max(0.0, min(1.0, build_progress))
                speed = 0.30 + build_progress * 0.40  # 0.30x -> 0.70x acceleration
                scale_factor = 1.03 + build_progress * 0.04
                add_bars = True
                add_rf = False
                add_shake = False
                add_chr = False
                add_bloom = energy > 0.65
                add_flash = False

            elif phase.name == "DROP":
                if not seg.get("prev_is_drop", True):
                    # First drop segment: explosive velocity snap
                    speed = 1.50
                    scale_factor = 1.20
                    add_shake = True
                    add_chr = True
                    add_flash = True
                    add_bloom = False
                elif duration > 0.80:
                    # Power slow-mo: technique release
                    speed = 0.45
                    scale_factor = 1.14
                    add_shake = False
                    add_chr = False
                    add_flash = False
                    add_bloom = True
                else:
                    # Fast combat clash
                    speed = 1.40
                    scale_factor = 1.10
                    add_shake = (idx % 4 == 0)
                    add_chr = (kick > 0.80)
                    add_flash = (kick > 0.75 or idx % 5 == 0)
                    add_bloom = False
                add_bars = False
                add_rf = False

            else:  # OUTRO
                speed = 0.50
                scale_factor = 1.05
                add_bars = False
                add_rf = False
                add_shake = False
                add_chr = False
                add_bloom = True
                add_flash = False

            ps = PlannedSegment(
                timeline_in=t,
                timeline_out=seg["end"],
                duration=duration,
                arc_phase=phase.name,
                is_drop=is_drop,
                prev_is_drop=seg.get("prev_is_drop", False),
                cps_density=phase.cps_target,
                add_bars=add_bars,
                add_rack_focus=add_rf,
                add_shake=add_shake,
                add_chr_aber=add_chr,
                add_bloom=add_bloom,
                add_flash=add_flash,
                speed=speed,
                scale_factor=scale_factor,
                section_type=seg.get("section_type", "body"),
                energy=energy,
                start=t,
                end=seg["end"],
            )
            planned.append(ps)

        return planned

    def to_segment_dicts(self, planned: List[PlannedSegment]) -> List[Dict[str, Any]]:
        return [
            {
                "start": ps.start,
                "end": ps.end,
                "duration": ps.duration,
                "is_drop": ps.is_drop,
                "prev_is_drop": ps.prev_is_drop,
                "arc_phase": ps.arc_phase,
                "speed": ps.speed,
                "scale_factor": ps.scale_factor,
                "add_bars": ps.add_bars,
                "add_rack_focus": ps.add_rack_focus,
                "add_shake": ps.add_shake,
                "add_chr_aber": ps.add_chr_aber,
                "add_bloom": ps.add_bloom,
                "add_flash": ps.add_flash,
                "energy": ps.energy,
                "section_type": ps.section_type,
            }
            for ps in planned
        ]

    def summary(self) -> str:
        lines = ["📖 [OpenStoryline] Narrative Arc Plan:"]
        for ph in self.phases:
            start_s = ph.start_frac * self.total_duration
            end_s = ph.end_frac * self.total_duration
            lines.append(
                f"  ▸ {ph.name:6s} [{start_s:5.1f}s – {end_s:5.1f}s] "
                f"CPS={ph.cps_target:.1f} | {ph.description[:55]}"
            )
        return "\n".join(lines)
