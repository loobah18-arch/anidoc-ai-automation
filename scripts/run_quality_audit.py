#!/usr/bin/env python3
"""
Local Quality Audit Engine:
Compares rendered 4K edits against priority reference edits (@Chakra_boy & Satoru Gojo 4K).
Calculates cut pacing, dynamic contrast, saturation, luminance, and frame energy metrics.
"""
import os
import sys
import json
import glob
import subprocess
from pathlib import Path

AUDIT_DIR = Path("audit")
RENDERED_DIR = AUDIT_DIR / "rendered"
REF_DIR = AUDIT_DIR / "reference"
FRAMES_DIR = AUDIT_DIR / "frames"

PRIORITY_REF_URL = "https://youtube.com/shorts/R6NJ1ItHzdY"
SECONDARY_REF_URL = "https://youtube.com/shorts/QrzRe5DM0iQ"

def probe_video(path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=width,height,r_frame_rate,bit_rate",
        "-of", "json", path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(res.stdout)
    except Exception:
        return {}

def count_scene_cuts(path: str) -> int:
    cmd = [
        "ffmpeg", "-i", path,
        "-filter_complex", "select='gt(scene,0.55)',metadata=print",
        "-f", "null", "-"
    ]
    return sum(1 for line in subprocess.run(cmd, capture_output=True, text=True).stderr.splitlines() if "pts_time" in line)

def compute_signal_stats(path: str, max_frames: int = 150) -> dict:
    cmd = [
        "ffmpeg", "-i", path,
        "-vf", "signalstats,metadata=print",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    yavg = sat = count = 0
    for line in res.stderr.splitlines():
        if "lavfi.signalstats.YAVG=" in line:
            try:
                yavg += float(line.split("lavfi.signalstats.YAVG=")[1].strip())
                count += 1
            except Exception:
                pass
        elif "lavfi.signalstats.SATAVG=" in line:
            try:
                sat += float(line.split("lavfi.signalstats.SATAVG=")[1].strip())
            except Exception:
                pass
        if count >= max_frames:
            break
    n = max(count, 1)
    return {
        "yavg": round(yavg / n, 1),
        "saturation": round(sat / n, 1),
        "samples": count
    }

def main():
    AUDIT_DIR.mkdir(exist_ok=True)
    RENDERED_DIR.mkdir(exist_ok=True)
    REF_DIR.mkdir(exist_ok=True)
    FRAMES_DIR.mkdir(exist_ok=True)

    # 1. Locate local rendered edit
    rendered_files = list(Path("output").glob("*.mp4")) + list(RENDERED_DIR.glob("*.mp4"))
    if not rendered_files and Path("test_assembled_edit.mp4").exists():
        rendered_files = [Path("test_assembled_edit.mp4")]
    
    if not rendered_files:
        print("⚠️ No rendered video found in output/. Rendering a fresh test edit first...")
        subprocess.run([sys.executable, "main.py", "--character", "gojo", "--duration", "22.0"])
        rendered_files = list(Path("output").glob("*.mp4"))

    rendered_path = str(rendered_files[0])
    print(f"🎬 Auditing Rendered Video: {rendered_path}")

    # 2. Download priority reference video if missing
    priority_ref = REF_DIR / "priority_ref.mp4"
    if not priority_ref.exists():
        print(f"📥 Downloading Priority Reference Video (@Chakra_boy)...")
        cmd = [
            "yt-dlp", "-f", "bv*[height<=1080]+ba/b",
            "--merge-output-format", "mp4",
            "-o", str(priority_ref),
            PRIORITY_REF_URL
        ]
        subprocess.run(cmd, capture_output=True)

    # 3. Analyze Rendered vs Reference
    report = {"rendered": {}, "reference": {}, "gap_analysis": {}}

    r_info = probe_video(rendered_path)
    if r_info.get("format"):
        dur = float(r_info["format"]["duration"])
        cuts = count_scene_cuts(rendered_path)
        stats = compute_signal_stats(rendered_path)
        report["rendered"] = {
            "file": os.path.basename(rendered_path),
            "duration_sec": round(dur, 2),
            "scene_cuts": cuts,
            "cuts_per_sec": round(cuts / max(dur, 1.0), 2),
            **stats
        }

    if priority_ref.exists():
        ref_info = probe_video(str(priority_ref))
        if ref_info.get("format"):
            dur = float(ref_info["format"]["duration"])
            cuts = count_scene_cuts(str(priority_ref))
            stats = compute_signal_stats(str(priority_ref))
            report["reference"] = {
                "file": "priority_ref.mp4",
                "duration_sec": round(dur, 2),
                "scene_cuts": cuts,
                "cuts_per_sec": round(cuts / max(dur, 1.0), 2),
                **stats
            }

            # Gap Analysis
            r_cuts = report["rendered"].get("cuts_per_sec", 0)
            ref_cuts = report["reference"].get("cuts_per_sec", 0)
            r_sat = report["rendered"].get("saturation", 0)
            ref_sat = report["reference"].get("saturation", 0)
            report["gap_analysis"] = {
                "cut_pacing_diff_per_sec": round(r_cuts - ref_cuts, 2),
                "saturation_diff": round(r_sat - ref_sat, 1),
                "quality_match_score": max(0, min(100, round(
                    100 - (abs(r_cuts - ref_cuts) * 15 + abs(r_sat - ref_sat) * 1.5)
                )))
            }

    out_file = AUDIT_DIR / "eval_report.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n📊 Quality Audit Report:")
    print(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    main()
