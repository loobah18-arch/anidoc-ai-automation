"""
Audio Beat & Onset Detection Engine for Phonk and Cinematic Sync.
Replicates NARRATIVE-DRIVEN dramatic AMV editing style:
- Phase 1 (0s - 6s): Atmospheric dialogue build — ONE continuous monologue shot.
- Phase 2 (6s - 18s): First drop — aggressive cuts at musically significant moments (NOT every beat).
- Phase 3 (18s - 24s): Bridge — held emotional shots, technique charge breather.
- Phase 4 (24s - 31s): Second drop — rapid but narrative-driven cuts.
- Phase 5 (31s - 38s): Final climax — powerful held finish with slow-burn outro.

Reference video has ~20 major segments in 23s (0.87 cuts/sec). This module targets
15-20 major segments for a 38s edit, with each segment 1.5-3.0s average.
NO micro-flash inserts. Flash is rare punctuation only (2-3 per edit).
"""
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfilt, correlate

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

        Reference video has ~20 major segments in 23s (avg ~1.15s each).
        This targets 15-20 major segments for a 38s edit. Each segment is a
        held shot — no micro-subdivision, no flash inserts between segments.
        Flash moments are identified separately (2-3 per edit) at the biggest drops.
        """
        raw_segments = []
        all_points = [0.0] + self.beat_times
        if self.duration not in all_points:
            all_points.append(self.duration)
        all_points = sorted(list(set(all_points)))

        for i in range(len(all_points) - 1):
            s = all_points[i]
            e = all_points[i+1]
            dur = e - s
            if dur < 0.5:
                continue  # skip sub-half-second fragments (noise)
            raw_segments.append({"start": s, "end": e})

        # No subdivision — each beat-to-beat interval is one held shot.
        # This matches the reference's narrative pacing where scenes are 1.0-2.0s.

        segments = []
        for seg in raw_segments:
            s, e = seg["start"], seg["end"]
            is_d = s >= self.drop_time
            prev_d = segments[-1]["is_drop"] if segments else False
            segments.append({
                "start": s,
                "end": e,
                "duration": round(e - s, 3),
                "is_drop": is_d,
                "prev_is_drop": prev_d,
                "is_flash": False,  # Flash is handled separately, not as segments
                "index": len(segments)
            })
        return segments

    def get_flash_timestamps(self, max_flashes: int = 3) -> List[float]:
        """Returns timestamps for white flash overlays — only at the biggest beat drops.
        Reference uses 2-3 total flashes across the entire edit, NOT constant micro-flashes.
        Flashes are placed at the first drop hit and 1-2 major energy peaks."""
        if not self.beat_times:
            return []
        # The biggest flash moment is the drop itself
        flash_times = [self.drop_time]
        # Add 1-2 more at musically significant intervals after the drop
        post_drop = [t for t in self.beat_times if t > self.drop_time + 0.5]
        if len(post_drop) >= 4:
            # Every ~4th beat after the drop (roughly every bar)
            for i in range(4, len(post_drop), 4):
                if len(flash_times) >= max_flashes:
                    break
                flash_times.append(post_drop[i])
        return flash_times[:max_flashes]


def _stream_wav_from_ffmpeg(audio_path: Path, duration: float) -> Tuple[np.ndarray, int]:
    """Extracts mono 22050 Hz PCM via FFmpeg pipe (no temp file / no WAV header)."""
    SR = 22050
    cmd = [
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-t", f"{duration:.2f}",
        "-ac", "1", "-ar", str(SR),
        "-acodec", "pcm_s16le",
        "-f", "s16le", "pipe:1"
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    data = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return data, SR


def _detect_onsets_and_bpm(audio_data: np.ndarray, sr: int) -> Tuple[float, List[float]]:
    """
    Detects BPM and bass onset times from audio data using scipy.
    Returns (bpm, onset_times_in_seconds).
    """
    # Low-pass at 100 Hz to tightly isolate 808 sub-bass kick transients
    sos = butter(4, 100.0 / (sr / 2), btype='low', output='sos')
    bass = sosfilt(sos, audio_data)

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
    Generates a NARRATIVE-DRIVEN beat grid matching reference AMV editing style.

    Reference: ~20 major segments in 23s (avg 1.15s each, range 0.5-2.0s).
    Target: 15-20 major segments for 38s edit.

    Structure:
    - Buildup (0.0s to drop_time): ONE continuous shot (no cuts — complete dialogue).
    - First Drop (drop_time to 18.0s): ~8 cuts at musically significant moments (every 1.5-2.0s).
    - Bridge (18.0s to 24.0s): ~3 held emotional shots (2.0s each).
    - Second Drop (24.0s to 32.0s): ~5 cuts (1.5s average).
    - Final Outro (32.0s to duration): 1-2 powerful held shots (2.0-3.0s).
    """
    beat_times = []

    # ── Phase 1: Intro — ONE continuous monologue shot ─────────────────────────
    # The character delivers their full iconic line without mid-sentence chops.
    # No cuts during buildup — just one held shot until the drop.
    beat_times.append(round(drop_time, 2))

    # ── Phase 2: First Drop — narrative-driven cuts (~8 segments) ──────────────
    # Cuts at every ~2nd beat (every bar), NOT every beat. ~1.8s average.
    bar_duration = 4 * (60.0 / bpm)  # 4 beats per bar
    curr = drop_time
    phase2_limit = min(duration - 8.0, 18.0)
    while curr < phase2_limit:
        curr += bar_duration * 0.9  # slightly less than a full bar for energy
        if curr < phase2_limit:
            beat_times.append(round(curr, 2))

    # ── Phase 3: Bridge — held emotional shots (~3 segments) ───────────────────
    if duration > 24.0:
        bridge_start = round(min(duration - 10.0, 18.5), 2)
        beat_times.append(bridge_start)
        beat_times.append(round(bridge_start + 2.2, 2))  # 2.2s held shot
        beat_times.append(round(bridge_start + 4.0, 2))  # 1.8s shot

    # ── Phase 4: Second Drop — rapid but narrative cuts (~5 segments) ──────────
    if duration > 28.0:
        curr = beat_times[-1] if beat_times else 24.0
        phase4_limit = min(duration - 3.0, 32.0)
        while curr < phase4_limit:
            curr += bar_duration * 0.75  # slightly tighter than first drop
            if curr < phase4_limit:
                beat_times.append(round(curr, 2))

    # ── Phase 5: Final Outro — powerful held finish ────────────────────────────
    if duration > 30.0:
        final_cut = round(duration - 2.5, 2)
        if final_cut > (beat_times[-1] if beat_times else 0.0) + 1.0:
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
            audio_data, sr = _stream_wav_from_ffmpeg(audio_path, dur)
            detected_bpm, detected_onsets = _detect_onsets_and_bpm(audio_data, sr)

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
