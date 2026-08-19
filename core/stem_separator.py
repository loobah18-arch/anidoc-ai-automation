"""
Ultimate-AMV Audio Stem Separator (ElishaPervez/Ultimate-AMV)
=============================================================
Integrates the `audio-separator` library (used by Ultimate-AMV's
AudioSeparator component) to split a phonk BGM track into:
  - Instrumental stem  → used for beat detection (cleaner, no false triggers from vocals)
  - Vocal/SFX stem     → available for dialogue drop overlays

Why this matters:
  Running librosa beat_track() on a mixed phonk track with dense vocals and
  synthesizer pads causes false transient triggers that create mis-timed cuts.
  Separating to a clean instrumental stem before beat detection produces
  significantly more accurate BPM and beat grid results.

Usage in pipeline:
  1. split_phonk_stems(audio_path) → (instrumental_path, vocals_path)
  2. Pass instrumental_path to analyze_audio_beatsync() instead of the mixed track
  3. At assembly time, mix phonk BGM (original, louder) + clip audio

Falls back transparently to the original mixed file if audio-separator
is not installed or model download fails.
"""
import os
import shutil
from pathlib import Path
from typing import Tuple, Optional

_SEPARATOR_AVAILABLE = False
try:
    from audio_separator.separator import Separator as _Separator
    _SEPARATOR_AVAILABLE = True
    print("✅ [Ultimate-AMV] audio-separator loaded — stem split active")
except ImportError:
    print("⚠️  [Ultimate-AMV] audio-separator not installed; using mixed track (run: pip install audio-separator[cpu])")


# ── Model Configuration ──────────────────────────────────────────────────────
# MDX-Net Inst_HQ_3 — same model used by Ultimate-AMV for AMV/phonk music
_DEFAULT_MODEL = "UVR-MDX-NET-Inst_HQ_3.onnx"
_MODEL_DIR     = Path.home() / ".cache" / "audio-separator" / "models"


def split_phonk_stems(
    audio_path: Path,
    output_dir: Optional[Path] = None,
    model: str = _DEFAULT_MODEL,
    force_redo: bool = False,
) -> Tuple[Path, Path]:
    """
    Splits a phonk BGM file into (instrumental, vocals) stems using the
    UVR-MDX-NET-Inst_HQ_3 model (same as Ultimate-AMV's AudioSeparator).

    Args:
        audio_path:  Path to the original phonk .mp3 / .wav / .aac file
        output_dir:  Where to save stems (defaults to audio_path.parent/stems/)
        model:       Model filename — MDX-Net HQ3 gives best phonk separation
        force_redo:  Re-separate even if cached stems exist

    Returns:
        (instrumental_path, vocals_path) — both are .wav files
        Falls back to (audio_path, audio_path) if separation fails.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    stem_dir = output_dir or (audio_path.parent / "stems")
    stem_dir.mkdir(parents=True, exist_ok=True)

    stem_base       = audio_path.stem
    inst_path_wav   = stem_dir / f"{stem_base}_(Instrumental).wav"
    vocals_path_wav = stem_dir / f"{stem_base}_(Vocals).wav"

    # Return cached stems if they exist and force_redo=False
    if not force_redo and inst_path_wav.exists() and vocals_path_wav.exists():
        print(f"🎵 [StemSeparator] Using cached stems for: {audio_path.name}")
        return inst_path_wav, vocals_path_wav

    if not _SEPARATOR_AVAILABLE:
        print("⚠️  [StemSeparator] audio-separator not available — using mixed track")
        return audio_path, audio_path

    try:
        print(f"🔀 [Ultimate-AMV StemSep] Separating stems: {audio_path.name} → {model}")
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)

        separator = _Separator(
            output_dir=str(stem_dir),
            output_format="WAV",
            model_file_dir=str(_MODEL_DIR),
            log_level=30,  # WARNING only
        )
        separator.load_model(model_filename=model)
        output_files = separator.separate(str(audio_path))

        # audio-separator names outputs as: "stem_(Instrumental).wav" etc.
        instrumental = None
        vocals       = None
        for f in output_files:
            fp = Path(f)
            if "Instrumental" in fp.name or "instrumental" in fp.name:
                instrumental = fp
            elif "Vocals" in fp.name or "vocals" in fp.name or "Other" in fp.name:
                vocals = fp

        if not instrumental:
            # If naming is unexpected, pick by size (instrumental is usually larger)
            stems = [Path(f) for f in output_files if Path(f).exists()]
            stems.sort(key=lambda p: p.stat().st_size, reverse=True)
            instrumental = stems[0] if stems else audio_path
            vocals       = stems[1] if len(stems) > 1 else audio_path

        print(f"✅ [StemSeparator] Instrumental: {instrumental.name} | Vocals: {vocals.name if vocals else 'N/A'}")
        return instrumental, vocals or audio_path

    except Exception as e:
        print(f"⚠️  [StemSeparator] Separation failed ({e}); using original mixed track")
        return audio_path, audio_path


def get_best_beat_source(audio_path: Path, scratch_dir: Path) -> Path:
    """
    Returns the optimal audio path for beat detection:
    - Tries to get the clean instrumental stem via split_phonk_stems()
    - Falls back to the original mixed track

    This is the function called by the video assembler before beat analysis.
    """
    if not _SEPARATOR_AVAILABLE:
        return audio_path

    try:
        inst_path, _ = split_phonk_stems(
            audio_path=audio_path,
            output_dir=scratch_dir / "stems",
        )
        return inst_path
    except Exception as e:
        print(f"⚠️  [StemSeparator] get_best_beat_source error: {e}")
        return audio_path
