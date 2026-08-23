import subprocess, numpy as np, json, os, sys

EPS = "~/storage/downloads/AniDoc-Footage"
OUT = os.path.expanduser("~/.cache/opencode/tmp/smart_clips")
os.makedirs(OUT, exist_ok=True)
W, H = 96, 54

def motion_profile(ep, t0, dur=12.0, fps=6):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", ep,
           "-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (W * H)
    if n < 10: return None
    f = np.frombuffer(raw[: n * W * H], dtype=np.uint8).reshape(n, H, W).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    if f.mean() < 8: return None
    return d

GC=[0]
def extract(ep_file, tag, windows, count):
    ep = os.path.expanduser(f"{EPS}/{ep_file}")
    made = 0
    for i, t in enumerate(windows):
        if made >= count: break
        d = motion_profile(ep, t)
        if d is None: continue
        fps = 6
        best_span, best_v = 0, -1
        for s in range(0, len(d) - int(3.3 * fps)):
            v = d[s : s + int(3.3 * fps)].sum()
            if v > best_v:
                best_v, best_span = v, s
        start = round(t + best_span / fps, 2)
        out = f"{OUT}/{tag}_{GC[0]}.mp4"; GC[0]+=1
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", "3.25",
                            "-i", ep, "-an", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "18", "-threads", "2", "-pix_fmt", "yuv420p", out])
        if r.returncode == 0 and os.path.getsize(out) > 50000:
            print(f"{tag}_{GC[0]-1}: {ep_file} @{start}s score={best_v:.1f}")
            made += 1

jobs = json.load(open(sys.argv[1]))
for job in jobs:
    extract(job["ep"], job["tag"], job["windows"], job["count"])
