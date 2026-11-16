"""Find openings, endings, title cards and recaps: footage that repeats (nearly) frame for frame in another episode
of the same season. Fights never do, so anything that does is credits or recap and is kept out of every edit.

zones({ep: path}) -> {ep: [[start, end], ...]} in seconds. Needs at least two episodes of the same season.
"""
import subprocess
import numpy as np

FPS, W, H = 1, 32, 18


def thumbs(path):
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', path, '-vf', f'fps={FPS},scale={W}:{H}:flags=area,format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, W * H).astype(np.float32)
    sd = f.std(axis=1, keepdims=True)
    z = (f - f.mean(axis=1, keepdims=True)) / (sd + 1e-6)
    z[sd[:, 0] < 10] = 0                                              # black / flat frames match everything: ignore them
    return z / np.sqrt(W * H)


def _runs(mask, min_len, gap=3):
    out, st, miss = [], None, 0
    for i, m in enumerate(list(mask) + [False] * (gap + 1)):
        if m:
            st = i if st is None else st; miss = 0
        elif st is not None:
            miss += 1
            if miss > gap:
                end = i - miss + 1
                if end - st >= min_len:
                    out.append((st, end))
                st, miss = None, 0
    return out


def pair(a, b, thr=0.8, min_len=12):
    """frames of a and b that sit in a long run of near-identical frames (same offset)"""
    C = a @ b.T
    ma, mb = np.zeros(len(a), bool), np.zeros(len(b), bool)
    for d in range(-(len(b) - 1), len(a)):
        dg = np.diagonal(C, offset=-d) if d >= 0 else np.diagonal(C, offset=-d)
        i0, j0 = (d, 0) if d >= 0 else (0, -d)
        for s, e in _runs(dg > thr, min_len):
            ma[i0 + s:i0 + e] = True; mb[j0 + s:j0 + e] = True
    return ma, mb


def zones(paths, pad=6.0, min_zone=15):
    th = {e: thumbs(p) for e, p in paths.items()}
    marks = {e: np.zeros(len(t), bool) for e, t in th.items()}
    keys = list(th)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ma, mb = pair(th[keys[i]], th[keys[j]])
            marks[keys[i]] |= ma; marks[keys[j]] |= mb
    out = {}
    for e, m in marks.items():
        out[e] = [[max(0.0, s / FPS - pad), e_ / FPS + pad] for s, e_ in _runs(m, min_zone, gap=6)]
    return out


def hit(zs, a, b, margin=1.0):
    return any(a < z1 + margin and b > z0 - margin for z0, z1 in zs or [])
