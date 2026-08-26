"""
Ultimate-AMV Audio Stem Separator (ElishaPervez/Ultimate-AMV)
=============================================================
Integrates Ultimate-AMV's stem separation approach to split phonk BGM tracks into:
  - Instrumental stem  → clean drums/bass for accurate beat & drop detection
  - Vocal/SFX stem     → speech/dialogue overlays

Why this matters:
  Running beat detection on mixed tracks with dense vocal chops causes false
  transients and mis-timed cuts. Separating the clean instrumental stem
  produces razor-sharp BPM and beat grid synchronization.

Fallback:
  If audio-separator (MDX-Net / UVR) is not installed, applies high-quality DSP
  vocal suppression (mid-side phase cancellation + parametric notch) via FFmpeg.
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional

_SEPARATOR_AVAILABLE = False
try:
    from audio_separator.separator import Separator as _Separator
    _SEPARATOR_AVAILABLE = True
    print("✅ [Ultimate-AMV] audio-separator (MDX-Net) active")
except ImportError:
    print("ℹ️  [Ultimate-AMV] audio-separator not installed; using DSP vocal suppression fallback")


_DEFAULT_MODEL = "UVR-MDX-NET-Inst_HQ_3.onnx"
_MODEL_DIR = Path.home() / ".cache" / "audio-separator" / "models"


def split_phonk_stems(
    audio_path: Path,
    output_dir: Path,
    model_name: str = _DEFAULT_MODEL,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Splits an audio file into (instrumental_path, vocals_path).
    Returns (instrumental_path, vocals_path) or (audio_path, None) on fallback.
    """
    audio_path = Path(audio_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not audio_path.exists():
        return None, None

    # Option 1: AI Model Separation (audio-separator)
    if _SEPARATOR_AVAILABLE:
        try:
            print(f"🎛️ [Ultimate-AMV] Running MDX-Net stem separation on: {audio_path.name}")
            _MODEL_DIR.mkdir(parents=True, exist_ok=True)
            sep = _Separator(
                model_file_dir=str(_MODEL_DIR),
                output_dir=str(output_dir),
                output_format="WAV",
                log_level=30,
            )
            sep.load_model(model_filename=model_name)
            output_files = sep.separate(str(audio_path))

            inst_path = None
            voc_path = None
            for fname in output_files:
                p = output_dir / fname
                lower = fname.lower()
                if "instrumental" in lower or "inst" in lower:
                    inst_path = p
                elif "vocals" in lower or "voc" in lower:
                    voc_path = p

            if inst_path and inst_path.exists():
                print(f"✅ [Ultimate-AMV] Separated: {inst_path.name}")
                return inst_path, voc_path
        except Exception as ex:
            print(f"⚠️  [Ultimate-AMV] AI stem separation failed ({ex}); using DSP filter")

    # Option 2: DSP Vocal Attenuation Filter via FFmpeg
    # Center-channel mid-side cancellation + bandstop filter on human speech range (300Hz-3400Hz)
    dsp_inst_path = output_dir / f"inst_dsp_{audio_path.stem}.wav"
    if dsp_inst_path.exists():
        return dsp_inst_path, None

    try:
        dsp_filter = (
            "stereotools=mutem=1,"  # Mute mid channel to eliminate centered vocals
            "equalizer=f=1000:t=q:w=1.5:g=-12," # Attenuate residual vocal resonance
            "equalizer=f=60:t=q:w=1.0:g=4"      # Boost kick/sub-bass for beat tracking
        )
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(audio_path),
            "-af", dsp_filter,
            "-ar", "22050",
            "-ac", "1",
            str(dsp_inst_path)
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=10)
        if res.returncode == 0 and dsp_inst_path.exists() and dsp_inst_path.stat().st_size > 1000:
            print(f"✅ [Ultimate-AMV] Generated DSP rhythm stem: {dsp_inst_path.name}")
            return dsp_inst_path, None
    except Exception:
        pass

    return audio_path, None


def get_best_beat_source(audio_path: Path, output_dir: Path) -> Path:
    """
    Returns the cleanest audio path for beat detection (preferring instrumental stem).
    """
    inst, _ = split_phonk_stems(audio_path, output_dir)
    return inst if inst and inst.exists() else audio_path
