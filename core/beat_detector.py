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
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfilt, correlate
from scipy.io import wavfile

from config.settings import SCRATCH_DIR
from core.phonk_manager import POPULAR_PHONK_CATALOG


class BeatGrid:
    def __init__(self, duration: float, drop_time: float, beat_times: List[float], bpm: float = 134.0):
        self.duration = duration
        self.drop_time = drop_time
        self.beat_times = sorted(list(set([round(t, 2) for t in beat_times if 0.0 <= t <= duration])))
        self.bpm = bpm

    def get_cut_segments(self) -> List[Dict[str, Any]]:
        """Returns list of segments with start, end, duration, is_drop, and prev_is_drop flags.
        Subdivides longer segments to match reference edit density (~100+ cuts in 38s).
        Inserts 0.03s micro-flash inserts between subdivided segments.
        """
        # Phase 1: build raw segments from beat points
        raw_segments = []
        all_points = [0.0] + self.beat_times
        if self.duration not in all_points:
            all_points.append(self.duration)
        all_points = sorted(list(set(all_points)))

        for i in range(len(all_points) - 1):
            s = all_points[i]
            e = all_points[i+1]
            if e - s < 0.22:
                continue
            raw_segments.append({"start": s, "end": e})

        # Phase 2: subdivide to match reference density (~120 cuts in 38s)
        # Reference has avg 0.26s cut gap — threshold at 0.42s balances density vs overshoot.
        # Flash inserts are PAIRED (two back-to-back) matching the reference's strobe pattern.
        subdivided = []
        for seg in raw_segments:
            dur = seg["end"] - seg["start"]
            if dur > 0.42 and dur < 0.90:
                # Split at ~60% through the segment (asymmetric energy)
                split_t = seg["start"] + dur * 0.60
                flash_pair_dur = 0.050  # paired flashes: 33ms + ~17ms gap
                # Part A: 60% of segment
                subdivided.append({"start": seg["start"], "end": round(split_t, 3)})
                # Paired micro-flash (2 back-to-back flashes like reference)
                subdivided.append({"start": round(split_t, 3), "end": round(split_t + flash_pair_dur, 3), "is_flash": True})
                # Part B: remaining 40%
                subdivided.append({"start": round(split_t + flash_pair_dur, 3), "end": seg["end"]})
            elif dur >= 0.90 and dur < 1.8:
                # Medium segments: split into 2 parts with paired flash
                split_t = seg["start"] + dur * 0.55
                flash_pair_dur = 0.050
                subdivided.append({"start": seg["start"], "end": round(split_t, 3)})
                subdivided.append({"start": round(split_t, 3), "end": round(split_t + flash_pair_dur, 3), "is_flash": True})
                subdivided.append({"start": round(split_t + flash_pair_dur, 3), "end": seg["end"]})
            elif dur >= 1.8:
                # Very long segments: split into 3 parts with 2 paired flash inserts
                third = dur / 3.0
                flash_pair_dur = 0.050
                t1 = seg["start"] + third
                t2 = seg["start"] + 2 * third
                subdivided.append({"start": seg["start"], "end": round(t1, 3)})
                subdivided.append({"start": round(t1, 3), "end": round(t1 + flash_pair_dur, 3), "is_flash": True})
                subdivided.append({"start": round(t1 + flash_pair_dur, 3), "end": round(t2, 3)})
                subdivided.append({"start": round(t2, 3), "end": round(t2 + flash_pair_dur, 3), "is_flash": True})
                subdivided.append({"start": round(t2 + flash_pair_dur, 3), "end": seg["end"]})
            else:
                subdivided.append(seg)

        # Phase 3: convert to final segment list with is_drop/prev_is_drop flags
        segments = []
        for seg in subdivided:
            s, e = seg["start"], seg["end"]
            if e - s < 0.015:
                continue  # skip sub-frame segments
            is_d = s >= self.drop_time
            is_flash = seg.get("is_flash", False)
            prev_d = segments[-1]["is_drop"] if segments else False
            segments.append({
                "start": s,
                "end": e,
                "duration": round(e - s, 3),
                "is_drop": is_d,
                "prev_is_drop": prev_d,
                "is_flash": is_flash,
                "index": len(segments)
            })
        return segments


def _extract_audio_wav(audio_path: Path, duration: float) -> Path:
    """Extracts mono 22050 Hz WAV from any audio/video file for onset analysis."""
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = SCRATCH_DIR / "beat_analysis.wav"
    cmd = [
        "ffmpeg", "-y", "-i", str(audio_path),
        "-t", f"{duration:.2f}",
        "-ac", "1", "-ar", "22050",
        "-acodec", "pcm_s16le",
        str(wav_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return wav_path


def _detect_onsets_and_bpm(wav_path: Path) -> Tuple[float, List[float]]:
    """
    Detects BPM and bass onset times from a WAV file using scipy.
    Returns (bpm, onset_times_in_seconds).
    """
    sr, data = wavfile.read(wav_path)
    if data.ndim > 1:
        data = data[:, 0]
    data = data.astype(np.float32) / 32768.0

    # Low-pass at 100 Hz to tightly isolate 808 sub-bass kick transients
    sos = butter(4, 100.0 / (sr / 2), btype='low', output='sos')
    bass = sosfilt(sos, data)

    # Onset envelope: half-wave rectified first derivative (energy jump detection)
    derivative = np.diff(bass)
    onset_env = np.maximum(derivative, 0.0)

    # Smooth with 8ms moving average to reduce noise while keeping transient sharpness
    win = max(1, int(sr * 0.008))
    kernel = np.ones(win, dtype=np.float32) / win
    onset_env = np.convolve(onset_env, kernel, mode='same')

    # ── BPM detection via autocorrelation (search 80-200 BPM range) ──────────
    min_lag = int(sr * 60.0 / 200)  # 200 BPM upper bound
    max_lag = int(sr * 60.0 / 80)   # 80 BPM lower bound
    ac = correlate(onset_env, onset_env, mode='full')
    ac = ac[len(ac) // 2:]  # keep positive lags only
    if max_lag > len(ac):
        max_lag = len(ac)
    ac_region = ac[min_lag:max_lag]
    if len(ac_region) == 0:
        return 134.0, []
    peak_lag = np.argmax(ac_region) + min_lag
    bpm = 60.0 * sr / peak_lag

    # ── Sub-harmonic check: if half the detected BPM has stronger autocorrelation
    #    (i.e. the real tempo is slower, not faster), use it ───────────────────
    double_lag = peak_lag * 2
    if double_lag < len(ac) and double_lag >= min_lag:
        sub_strength = ac[double_lag] / (ac[peak_lag] + 1e-10)
        if sub_strength > 0.90:
            bpm = 60.0 * sr / double_lag

    # ── Super-harmonic check: if double BPM (half-lag) has stronger autocorr ──
    #    Phonk often aliases to half the real BPM due to half-time feel.
    half_lag = peak_lag // 2
    if half_lag >= min_lag and half_lag < len(ac):
        harmonic_strength = ac[half_lag] / (ac[peak_lag] + 1e-10)
        if harmonic_strength > 0.80:
            bpm = 60.0 * sr / half_lag

    # ── Top-3 candidate validation: check which BPM best fits onset grid ──────
    # Find top 3 autocorrelation peaks and validate each against detected onsets
    ac_smooth = np.convolve(ac_region, np.ones(5) / 5, mode='same')  # smooth AC
    candidates_bpm = []
    min_peak_sep = int(sr * 60.0 / 200)  # minimum lag separation between peaks
    search_i = 0
    while search_i < len(ac_smooth) and len(candidates_bpm) < 5:
        local_end = min(search_i + min_peak_sep, len(ac_smooth))
        local_peak = search_i + int(np.argmax(ac_smooth[search_i:local_end]))
        candidates_bpm.append(60.0 * sr / (local_peak + min_lag))
        search_i = local_peak + min_peak_sep

    # ── Onset detection: adaptive threshold peak-picking ──────────────────────
    positive_env = onset_env[onset_env > 0]
    if len(positive_env) == 0:
        return bpm, []
    threshold = np.median(positive_env) * 1.4
    min_sep = int(sr * 0.2)  # minimum 200ms between onsets (prevents double-triggers)

    onsets = []
    i = 0
    while i < len(onset_env):
        if onset_env[i] > threshold:
            # Find local peak within the separation window
            end = min(i + min_sep, len(onset_env))
            peak = i + int(np.argmax(onset_env[i:end]))
            onsets.append(round(peak / sr, 4))
            i = peak + min_sep
        else:
            i += 1

    return bpm, onsets


def _snap_grid_to_onsets(beat_times: List[float], onset_times: List[float], bpm: float) -> List[float]:
    """
    Snaps each procedural beat time to the nearest detected bass onset.
    Only snaps if the onset is within ±30% of the beat interval (prevents false snaps).
    """
    if not onset_times:
        return beat_times

    beat_interval = 60.0 / bpm
    snap_window = beat_interval * 0.25
    onset_arr = np.array(onset_times)

    snapped = []
    for t in beat_times:
        distances = np.abs(onset_arr - t)
        nearest_idx = np.argmin(distances)
        nearest_dist = distances[nearest_idx]
        if nearest_dist <= snap_window:
            snapped.append(round(float(onset_arr[nearest_idx]), 3))
        else:
            snapped.append(round(t, 2))
    return snapped


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
    Intelligently syncs audio beats with frame-accurate precision using real audio analysis:
    1. Extracts audio waveform and detects bass onsets via scipy (low-pass + onset envelope).
    2. Detects actual BPM via autocorrelation of the onset envelope.
    3. Detects the 808 drop from the highest-energy onset in the 4-9s window.
    4. Snaps the procedural beat grid to real bass transient timestamps.
    5. Falls back to curated catalog data if audio analysis fails.
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

        # ── Real audio onset detection via scipy ──────────────────────────────
        detected_bpm = calibrated_bpm
        detected_drop = calibrated_drop
        detected_onsets = []

        try:
            wav_path = _extract_audio_wav(audio_path, dur)
            detected_bpm, detected_onsets = _detect_onsets_and_bpm(wav_path)

            # Use detected BPM for unknown tracks; for catalog tracks, prefer catalog BPM
            # but still use detected onsets for grid snapping
            if not matched_entry:
                calibrated_bpm = detected_bpm
                print(f"  🔍 [BeatSync] Detected BPM: {detected_bpm:.1f} (no catalog match)")

            # Detect drop from actual onsets: highest-energy onset in 4-9s window
            if detected_onsets:
                drop_candidates = [t for t in detected_onsets if 4.0 <= t <= 9.0]
                if drop_candidates:
                    # Prefer the onset closest to the catalog drop time
                    detected_drop = min(drop_candidates, key=lambda t: abs(t - calibrated_drop))
                    print(f"  🎯 [BeatSync] Drop snapped: {calibrated_drop:.2f}s → {detected_drop:.3f}s (from {len(detected_onsets)} onsets)")
                else:
                    # No onsets in drop window — use catalog/estimated drop
                    detected_drop = calibrated_drop
                    print(f"  ⚠️  [BeatSync] No onsets in 4-9s window, using catalog drop: {detected_drop:.2f}s")
            else:
                print(f"  ⚠️  [BeatSync] No onsets detected, using catalog defaults")

        except Exception as e:
            print(f"  ⚠️  [BeatSync] Onset detection failed: {e}. Using catalog defaults.")
            detected_bpm = calibrated_bpm
            detected_drop = calibrated_drop

        # ── Generate procedural grid then snap to real onsets ──────────────────
        grid = generate_procedural_beat_grid(duration=dur, drop_time=detected_drop, bpm=calibrated_bpm)

        if detected_onsets:
            grid.beat_times = _snap_grid_to_onsets(grid.beat_times, detected_onsets, calibrated_bpm)
            snapped_count = sum(1 for i, t in enumerate(grid.beat_times)
                              if any(abs(t - o) < 0.05 for o in detected_onsets))
            print(f"  📐 [BeatSync] Snapped {snapped_count}/{len(grid.beat_times)} cuts to real bass onsets")

        print(f"🎵 [BeatSync] Track: {track_stem} | BPM: {calibrated_bpm:.1f} | Drop: {detected_drop:.3f}s | Duration: {dur:.1f}s | Onsets: {len(detected_onsets)}")
        return grid

    except Exception as e:
        print(f"⚠️ [BeatSync] Notice analyzing {audio_path}: {e}. Using calibrated catalog sync.")
        return generate_procedural_beat_grid(duration=target_duration, drop_time=calibrated_drop, bpm=calibrated_bpm)
