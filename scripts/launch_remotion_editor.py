#!/usr/bin/env python3
"""
Launcher for AniDoc Remotion Visual Video Editor.
Starts the Vite dev server for local visual editing at http://127.0.0.1:5173/editor.html.
"""
import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EDITOR_DIR = BASE_DIR / "studio" / "remotion_editor"

def launch_editor():
    if not EDITOR_DIR.exists():
        print(f"[ERROR] Remotion editor directory not found at {EDITOR_DIR}")
        sys.exit(1)

    print("🚀 Launching AniDoc Remotion Visual Video Editor...")
    print("📍 URL: http://127.0.0.1:5173/editor.html")
    print("Press Ctrl+C to stop.")

    bin_vite = EDITOR_DIR / "node_modules" / ".bin" / "vite"
    cmd = [str(bin_vite), "--host", "127.0.0.1", "--port", "5173"]

    try:
        subprocess.run(cmd, cwd=str(EDITOR_DIR), check=True)
    except KeyboardInterrupt:
        print("\n👋 Remotion Visual Video Editor stopped.")

if __name__ == "__main__":
    launch_editor()
