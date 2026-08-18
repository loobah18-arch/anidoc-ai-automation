"""
BeatSync-Engine Integration Bridge (Merserk/BeatSync-Engine)
=============================================================
Wraps BeatSync-Engine's 6-stage audio analysis pipeline as a drop-in
upgrade to our existing beat_detector.py.

Improvements over our original librosa-only detector:
  - Stage 1: HPSS (harmonic-percussive source separation) before beat tracking
             → prevents vocal melody & synth pads from polluting rhythm detection
  - Stage 2: Multi-band frequency analysis (kick 20-150Hz, snare 200-2.5kHz,
             hihat 5-16kHz) → enables per-instrument drop detection
  - Stage 3: Song section segmentation (intro/build/drop/outro) with
             agglomerative clustering on chroma+MFCC+onset features
  - Stage 4: Energy-wave cut density — cuts held for 4-8 beats in calm sections,
             1 beat per kick in drops → eliminates visual fatigue from over-cutting

Fallback: if vendor import fails (missing deps), falls back to existing beat_detector.
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False

# ── Vendor path injection ────────────────────────────────────────────────────
_VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor" / "BeatSync-Engine"
_VENDOR_SRC  = _VENDOR_DIR / "src"

def _add_vendor_paths():
    """Inject BeatSync-Engine source paths into sys.path."""
    for p in [str(_VENDOR_DIR), str(_VENDOR_SRC)]:
        if p not in sys.path:
            sys.path.insert(0, p)

_BEATSYNC_AVAILABLE = False
try:
    _add_vendor_paths()
    from src.auto_mode import analyze_beats_auto, AutoWaveConfig, CONFIG as _BS_CONFIG  # noqa
    _BEATSYNC_AVAILABLE = True
    print("✅ [BeatSync-Engine] 6-stage HPSS analyzer loaded successfully")
except Exception as _e:
    print(f"⚠️  [BeatSync-Engine] Vendor import failed ({_e}); using fallback beat detector")


# ── Public API ───────────────────────────────────────────────────────────────

class BeatSyncResult:
    """
    Rich beat-analysis result that the rest of our pipeline consumes.
    Mirrors BeatGrid interface from beat_detector.py for drop-in compatibility.
    """
    def __init__(
        self,
        beat_times: Any,
        selected_beats: Any,
        tempo: float,
        duration: float,
        drop_time: float,
        sections: List[Dict],
        energy_wave: Any,
        kick_strength: Any,
        section_cut_density: Dict[str, float],
    ):
        self.beat_times     = beat_times
        self.selected_beats = selected_beats
        self.tempo          = tempo
        self.duration       = duration
        self.drop_time      = drop_time
        self.sections       = sections               # [{type, start, end, cut_interval_beats}, ...]
        self.energy_wave    = energy_wave            # per-beat [0..1]
        self.kick_strength  = kick_strength          # per-beat [0..1]
        self.section_cut_density = section_cut_density  # {"intro": 0.3, "drop": 4.0} cuts/sec

    # ── BeatGrid-compatible interface ──────────────────────────────────────
    def get_cut_segments(self) -> List[Dict[str, Any]]:
        """
        Returns segment dicts compatible with our video_assembler.
        Uses section-aware cut density from BeatSync Stage 4 instead of
        uniform beat spacing.
        """
        cuts = sorted(set(self.selected_beats))
        if not cuts:
            return []

        segments = []
        drop_t   = self.drop_time

        for i, t in enumerate(cuts):
            end_t    = cuts[i + 1] if i + 1 < len(cuts) else self.duration
            duration = max(0.12, end_t - t)
            section  = self._section_for_time(t)
            is_drop  = t >= drop_t

            segments.append({
                "start":        t,
                "end":          end_t,
                "duration":     duration,
                "is_drop":      is_drop,
                "prev_is_drop": (i > 0 and cuts[i - 1] >= drop_t),
                "section_type": section.get("type", "body") if section else "body",
                "energy":       float(self.energy_wave[i]) if i < len(self.energy_wave) else 0.5,
                "kick":         float(self.kick_strength[i]) if i < len(self.kick_strength) else 0.5,
            })

        return segments

    def _section_for_time(self, t: float) -> Optional[Dict]:
        for sec in self.sections:
            if sec.get("start", 0) <= t < sec.get("end", self.duration):
                return sec
        return None


def analyze_audio_beatsync(
    audio_path: Path,
    target_duration: float = 38.0,
) -> "BeatSyncResult":
    """
    Main entry point — runs BeatSync-Engine's full 6-stage analysis on the
    phonk track and returns a BeatSyncResult ready for the video assembler.

    Falls back gracefully to our existing beat_detector if BeatSync unavailable.
    """
    if not _BEATSYNC_AVAILABLE or not _NUMPY_AVAILABLE:
        return _fallback_beatsync(audio_path, target_duration)

    try:
        import librosa
        print(f"🎵 [BeatSync-Engine] Running 6-stage HPSS analysis on: {Path(audio_path).name}")

        # BeatSync's top-level analyze_beats_auto does stages 1-4 (+ optional 5-6)
        selected_beats, beat_info = analyze_beats_auto(
            audio_file=str(audio_path),
            end_time=target_duration,
            use_gpu=False,               # Termux: no CUDA
            enable_video_analysis=False, # Stage 5 (Qwen3-VL) — not available on Termux
            enable_qwen_semantics=False,
        )

        beat_times = np.asarray(beat_info.get("times", selected_beats), dtype=float)
        tempo      = float(beat_info.get("tempo", 120.0))
        sections   = beat_info.get("sections", [])
        duration   = float(beat_info.get("audio_duration", target_duration))

        # Identify drop_time: start of the highest-energy section
        drop_time = _detect_drop_from_sections(sections, beat_info, duration)

        # Extract per-beat energy & kick arrays (from Stage 2 features)
        ep         = beat_info.get("energy_profile", {})
        rd         = beat_info.get("rhythm_data", {})
        energy_w   = np.asarray(ep.get("wave", np.ones(len(beat_times)) * 0.5), dtype=float)
        kick_str   = np.asarray(rd.get("kick_strength", np.ones(len(beat_times)) * 0.5), dtype=float)

        # Per-section cuts/sec density from Stage 4 selection info
        sel_info   = beat_info.get("selection_info", [])
        sec_density = {}
        for si in sel_info:
            sec  = si.get("section", {})
            stype = sec.get("type", "body")
            dur  = max(0.01, sec.get("duration", 1.0))
            cnt  = si.get("selected_count", 1)
            sec_density[stype] = round(cnt / dur, 3)

        result = BeatSyncResult(
            beat_times=beat_times,
            selected_beats=np.asarray(selected_beats, dtype=float),
            tempo=tempo,
            duration=duration,
            drop_time=drop_time,
            sections=sections,
            energy_wave=energy_w[:len(beat_times)],
            kick_strength=kick_str[:len(beat_times)],
            section_cut_density=sec_density,
        )

        print(
            f"✅ [BeatSync-Engine] BPM={tempo:.1f} | {len(selected_beats)} cuts | "
            f"Drop@{drop_time:.2f}s | Sections: {[s.get('type') for s in sections]}"
        )
        return result

    except Exception as e:
        print(f"⚠️  [BeatSync-Engine] Analysis error: {e}; falling back")
        return _fallback_beatsync(audio_path, target_duration)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _detect_drop_from_sections(sections: List[Dict], beat_info: Dict, duration: float) -> float:
    """
    Identifies the beat drop timestamp from BeatSync's section list.
    Prefers sections explicitly typed as 'drop', 'chorus', or highest-energy body.
    """
    if not sections:
        return duration * 0.25

    DROP_TYPES = {"drop", "chorus", "drop_1", "drop_2", "refrain", "hook"}
    for sec in sections:
        if sec.get("type", "").lower() in DROP_TYPES:
            return max(0.5, float(sec["start"]))

    # Fallback: section with highest average energy
    best = max(sections, key=lambda s: s.get("avg_energy", s.get("energy", 0)))
    return max(0.5, float(best.get("start", duration * 0.25)))


def _fallback_beatsync(audio_path: Path, target_duration: float) -> BeatSyncResult:
    """Simple librosa fallback when BeatSync-Engine vendor is unavailable."""
    try:
        if not _NUMPY_AVAILABLE:
            raise RuntimeError("numpy is not installed")
        import librosa
        y, sr = librosa.load(str(audio_path), sr=22050, duration=target_duration, mono=True)
        y = librosa.util.normalize(y)
        tempo_raw, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
        tempo = float(np.atleast_1d(tempo_raw)[0])
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        beat_times = beat_times[beat_times < target_duration]

        # Naive section split: first 25% intro, rest body+drop
        duration   = min(target_duration, float(len(y) / sr))
        drop_time  = duration * 0.25
        sections   = [
            {"type": "intro", "start": 0.0,       "end": drop_time,  "avg_energy": 0.3},
            {"type": "drop",  "start": drop_time,  "end": duration,   "avg_energy": 0.9},
        ]
        energy_wave   = np.linspace(0.3, 1.0, len(beat_times))
        kick_strength = np.ones(len(beat_times)) * 0.5

        return BeatSyncResult(
            beat_times=beat_times,
            selected_beats=beat_times,
            tempo=tempo,
            duration=duration,
            drop_time=drop_time,
            sections=sections,
            energy_wave=energy_wave,
            kick_strength=kick_strength,
            section_cut_density={"intro": 0.5, "drop": 2.0},
        )
    except Exception as ex:
        raise RuntimeError(f"BeatSync fallback also failed: {ex}")
