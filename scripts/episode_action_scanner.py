import subprocess, numpy as np, sys, json

# Scan an episode at 2fps, 96x54 grayscale; rank 12s windows by motion energy.
ep, out_json = sys.argv[1], sys.argv[2]
W, H, FPS = 96, 54, 2
cmd = ["ffmpeg", "-v", "error", "-i", ep, "-vf", f"fps={FPS},scale={W}:{H}",
       "-f", "rawvideo", "-pix_fmt", "gray", "-"]
raw = subprocess.run(cmd, capture_output=True).stdout
n = len(raw) // (W * H)
frames = np.frombuffer(raw[: n * W * H], dtype=np.uint8).reshape(n, H, W).astype(np.float32)
diff = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))          # per-frame motion
lum = frames.mean(axis=(1, 2))                                     # black-frame guard

win = 12 * FPS
best = []
for start in range(0, n - win, 6 * FPS):                           # 50% overlap
    d = diff[start : start + win]
    l = lum[start : start + win]
    if l.min() < 8:                                                # skip black/fade windows
        continue
    score = float(np.percentile(d, 90) * 0.6 + d.mean() * 0.4)     # peaks + sustained action
    best.append((score, start / FPS))
best.sort(reverse=True)
picked, used = [], []
for s, t in best:
    if any(abs(t - u) < 20 for u in used):
        continue
    picked.append({"t": round(t, 1), "score": round(s, 3)})
    used.append(t)
    if len(picked) >= 6:
        break
json.dump(picked, open(out_json, "w"), indent=1)
print(ep.split("/")[-1], "->", [p["t"] for p in picked])
