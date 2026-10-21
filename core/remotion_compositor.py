"""
Remotion Compositor for AniDoc 4K Anime Shorts.
Bridges the Python edit engine with Remotion's React-based kinetic typography engine.
Renders transparent motion graphic overlays in GitHub Actions and composites them with FFmpeg.
"""
import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
REMOTION_DIR = BASE_DIR / "studio" / "remotion"


def render_remotion_kinetic_overlay(
    quote_text: str,
    character_name: str,
    accent_color: str = "#FF3333",
    duration_sec: float = 18.0,
    fps: int = 24,
    output_overlay_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Renders transparent kinetic captions using Remotion CLI.
    Requires Node.js and npx remotion (available in GitHub Actions CI).
    """
    if not shutil.which("npx"):
        print("ℹ️ [Remotion] npx not found in environment (skipping Remotion render).")
        return None

    if not output_overlay_path:
        output_overlay_path = BASE_DIR / "scratch" / "remotion_overlay.webm"
    output_overlay_path.parent.mkdir(parents=True, exist_ok=True)

    props = {
        "quoteText": quote_text,
        "characterName": character_name,
        "accentColor": accent_color
    }
    props_file = REMOTION_DIR / "props.json"
    with open(props_file, "w") as f:
        json.dump(props, f)

    frames = int(duration_sec * fps)
    cmd = [
        "npx", "remotion", "render",
        str(REMOTION_DIR / "src" / "Root.tsx"),
        "KineticCaptions",
        str(output_overlay_path),
        f"--props={props_file}",
        f"--frames=0-{frames}",
        "--codec=prores",
        "--pixel-format=yuva444p10le"
    ]
    try:
        print(f"🎨 [Remotion] Rendering kinetic typography overlay ({frames} frames)...")
        res = subprocess.run(cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True, timeout=120)
        if res.returncode == 0 and output_overlay_path.exists():
            print(f"✅ [Remotion] Overlay rendered successfully: {output_overlay_path.name}")
            return output_overlay_path
        else:
            print(f"⚠️ [Remotion] Render failed, stderr: {res.stderr[:300]}")
    except Exception as e:
        print(f"⚠️ [Remotion] Execution error: {e}")

    return None
