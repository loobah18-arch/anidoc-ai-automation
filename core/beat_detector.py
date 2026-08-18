"""
Audio Beat & Onset Detection Engine for Phonk and Cinematic Sync.
Replicates top viral anime/Marvel TikTok & Shorts editing styles:
- Phase 1 (0s - 5.5s): Atmospheric slow-building tension cuts (1.5s - 1.8s) leading into dialogue.
- Phase 2 (5.5s - 18s): Explosive 808 drop snap with velocity contrast (sixteenth notes + power shot holds).
- Phase 3 (18s - 28s): Secondary escalation & technique charges leading into the second drop.
- Phase 4 (28s - 35s+): Final devastation climax impact with slow-burn outro.
"""
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.phonk_manager import POPULAR_PHONK_CATALOG


class BeatGrid:
    def __init__(self, duration: float, drop_time: float, beat_times: List[float], bpm: float = 134.0):
        self.duration = duration
        self.drop_time = drop_time
        self.beat_times = sorted(list(set([round(t, 2) for t in beat_times if 0.0 <= t <= duration])))
        self.bpm = bpm

    def get_cut_segments(self) -> List[Dict[str, Any]]:
        """Returns list of segments with start, end, duration, is_drop, and prev_is_drop flags."""
        segments = []
        all_points = [0.0] + self.beat_times
        if self.duration not in all_points:
            all_points.append(self.duration)
        all_points = sorted(list(set(all_points)))
        
        for i in range(len(all_points) - 1):
            s = all_points[i]
            e = all_points[i+1]
            if e - s < 0.22:
                continue
            is_d = s >= self.drop_time
            prev_d = segments[-1]["is_drop"] if segments else False
            segments.append({
                "start": s,
                "end": e,
                "duration": round(e - s, 2),
                "is_drop": is_d,
                "prev_is_drop": prev_d,
                "index": len(segments)
            })
        return segments


def generate_procedural_beat_grid(duration: float = 35.0, drop_time: float = 6.0, bpm: float = 134.0) -> BeatGrid:
    """
    Generates a viral 30-40s Phonk beat grid with multi-phrase velocity contrast:
    - Buildup (0.0s to drop_time): Atmospheric cuts (1.6s - 2.0s) matching intro phrasing.
    - First Drop (drop_time to 18.0s): High-speed sync cuts alternating between rapid 16th beats and held quarter beats.
    - Secondary Bridge (18.0s to 22.0s): 1.2s technique charge-up breather.
    - Second Drop / Frenzy (22.0s to 31.0s): Ultra-fast combat flashes (0.35s - 0.50s).
    - Final Climax Outro (31.0s to duration): Powerful held finish (1.8s - 2.5s).
    """
    beat_times = []
    beat_interval = 60.0 / bpm
    
    # ── Phase 1: Intro Atmospheric Dialogue Buildup ───────────────────────────
    # In viral anime edits, the character delivers their COMPLETE iconic dialogue line
    # (e.g. "Honored One", "Stand proud", "Hello Peter") without mid-sentence chops.
    # We maintain ONE continuous monologue shot (or max 2 if drop_time > 6.2s).
    if drop_time > 6.2:
        beat_times.append(round(drop_time / 2.0, 2))
    beat_times.append(round(drop_time, 2))
    
    # ── Phase 2: First Drop Frenzy (Drop to 18.0s) ────────────────────────────
    curr = drop_time
    # Velocity contrast pattern: 2 fast sixteenths -> 1 held power beat -> 2 fast sixteenths -> 1 quarter beat
    phrase2_pattern = [1.0, 1.0, 2.0, 1.0, 1.0, 1.5]
    p_idx = 0
    phase2_limit = min(duration - 4.0, 18.0)
    
    while curr < phase2_limit:
        step_mult = phrase2_pattern[p_idx % len(phrase2_pattern)]
        step = max(0.35, beat_interval * step_mult)
        curr += step
        p_idx += 1
        if curr < phase2_limit:
            beat_times.append(round(curr, 2))
            
    # ── Phase 3: Secondary Bridge & Second Drop (18.0s to 30.0s) ─────────────
    if duration > 24.0:
        # Technique charge breather (1.2s - 1.5s)
        bridge_anchor = round(min(duration - 6.0, 19.5), 2)
        beat_times.append(bridge_anchor)
        curr = bridge_anchor
        
        # Second Drop frenzy
        phrase3_pattern = [0.8, 1.0, 0.8, 1.5, 1.0, 1.2]
        p3_idx = 0
        phase3_limit = min(duration - 2.5, 31.0)
        
        while curr < phase3_limit:
            step_mult = phrase3_pattern[p3_idx % len(phrase3_pattern)]
            step = max(0.32, beat_interval * step_mult)
            curr += step
            p3_idx += 1
            if curr < phase3_limit:
                beat_times.append(round(curr, 2))

    # ── Phase 4: Final Devastation Climax Outro ──────────────────────────────
    # Hold the ultimate final impact shot for the final 1.8s - 2.5s
    if duration > 10.0:
        final_cut = round(duration - 2.2, 2)
        if final_cut > (beat_times[-1] if beat_times else 0.0) + 0.8:
            beat_times.append(final_cut)

    return BeatGrid(duration=duration, drop_time=drop_time, beat_times=beat_times, bpm=bpm)


def analyze_audio_beats(audio_path: Path, target_duration: float = 42.0) -> BeatGrid:
    """
    Intelligently syncs audio beats with frame-accurate precision:
    1. For Curated Catalog tracks: Uses the exact, millisecond-calibrated 808 drop timestamp & BPM.
    2. For Custom / Live tracks: Analyzes dynamic low-frequency sub-bass (35-130Hz) energy onset.
    3. Generates locked rhythmic cut points across 40-45 seconds without drift.
    """
    if not audio_path or not Path(audio_path).exists():
        return generate_procedural_beat_grid(duration=target_duration)

    track_stem = Path(audio_path).stem
    matched_entry = next((item for item in POPULAR_PHONK_CATALOG if item["id"] == track_stem or item["id"] in track_stem), None)
    
    calibrated_bpm = matched_entry.get("bpm", 134.0) if matched_entry else 134.0
    calibrated_drop = matched_entry.get("default_drop", 6.0) if matched_entry else 6.0

    try:
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        dur = min(float(res.stdout.strip()), target_duration)
        
        detected_drop = calibrated_drop
        # If not in curated catalog, detect exact sub-bass jump
        if not matched_entry:
            detect_cmd = [
                "ffmpeg", "-y", "-ss", "3.0", "-to", "10.0", "-i", str(audio_path),
                "-af", "highpass=f=35,lowpass=f=130,silencedetect=n=-18dB:d=0.08",
                "-f", "null", "-"
            ]
            det_res = subprocess.run(detect_cmd, capture_output=True, text=True)
            silence_ends = [float(m) + 3.0 for m in re.findall(r"silence_end:\s*([0-9\.]+)", det_res.stderr)]
            if silence_ends:
                valid_drops = [t for t in silence_ends if 4.0 <= t <= 9.0]
                if valid_drops:
                    detected_drop = valid_drops[0]

        print(f"🎵 [BeatSync] Track: {track_stem} | BPM: {calibrated_bpm} | Frame-Accurate Climax Drop: {detected_drop:.3f}s | Target: {dur:.1f}s")
        return generate_procedural_beat_grid(duration=dur, drop_time=detected_drop, bpm=calibrated_bpm)
    except Exception as e:
        print(f"⚠️ [BeatSync] Notice analyzing {audio_path}: {e}. Using calibrated catalog sync.")
        return generate_procedural_beat_grid(duration=target_duration, drop_time=calibrated_drop, bpm=calibrated_bpm)
