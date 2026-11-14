"""Automatic AMV builder: picks a song and episodes it hasn't used, finds the best fight shots
itself, reads the song's beats and cuts a new edit with the same rhythm and effects as the
hand-made Gojo AMV.  Writes edit plan files into ./work and the final mp4 into ../out.

Steps
  1. choose character, song, 3 episodes (least used first, from history.json)
  2. download episodes from Drive (pinned ids in episodes.json)
  3. scan each episode at low res: cut detection, motion, contrast -> shot list with scores
  4. drop shots repeated across episodes (openings / recaps) and shots used before
  5. beat-track the song, find the drop, choose the 60 s window so the drop lands on beat 17
  6. fill the Gojo AMV beat template (template.txt) with shots: calm wide/close shots before
     the drop, highest-impact shots on the drops, the rest in story order
  7. render each shot with pro_fx, join, add the song, update history.json
"""
import json, os, random, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pro_fx import build_shot_fx, pair_transitions, default_transition_pattern
from drive_index import library

W, H, FPS = int(os.environ.get('W', 1080)), int(os.environ.get('H', 1080)), 30   # 1:1 square
PICK = (os.environ.get('PICK') or os.environ.get('CHARACTER') or 'auto').strip().lower()
SONG = os.environ.get('SONG', '').strip()
SEED = int(os.environ.get('SEED', time.time()))
TEMPLATE_BEATS = 130            # length of the edit in beats (60 s at 130 BPM)
DROP_BEAT = 17                  # first drop, same as the Gojo AMV
SCAN_W, SCAN_H, SCAN_FPS = 64, 36, 12
rng = random.Random(SEED)
os.chdir(HERE)
os.makedirs('src', exist_ok=True); os.makedirs('work', exist_ok=True)
EPISODES, LIB_SRC = library()                                     # every episode currently in the Drive folder
CHARS = json.load(open('characters.json'))
HIST_PATH = 'history.json'
hist = json.load(open(HIST_PATH)) if os.path.exists(HIST_PATH) else {}
hist.setdefault('songs', {}); hist.setdefault('episodes', {}); hist.setdefault('shots', []); hist.setdefault('runs', [])
hist.setdefault('series', {})


def _k(code):                                                         # old JJK-only keys -> series:key
    return f'jujutsu-kaisen:{code}' if code[:1] == 'S' and ':' not in code else code


hist['episodes'] = {_k(k): v for k, v in hist['episodes'].items()}
hist['openings2'] = {_k(k): v for k, v in hist.get('openings2', {}).items()}
hist.pop('openings', None)
for u in hist['shots']:
    u['ep'] = _k(u['ep'])
for r in hist['runs']:
    if r.get('episodes'):
        r['episodes'] = [_k(e) for e in r['episodes']]
    r.setdefault('series', EPISODES.get(r['episodes'][0], {}).get('series', 'jujutsu-kaisen') if r.get('episodes') else '')
if not hist['series']:
    for r in hist['runs']:
        hist['series'][r['series']] = hist['series'].get(r['series'], 0) + 1
CHARS = {c: [_k(e) for e in v] for c, v in CHARS.items()}


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(' '.join(cmd[:6]) + '\n' + r.stderr[-1500:])
    return r.stdout


def least_used(options, counts, k):
    opts = list(options); rng.shuffle(opts)
    opts.sort(key=lambda o: counts.get(o, 0))
    return opts[:k]


# ---------------------------------------------------------------- 1. choices
series_all = sorted({v['series'] for v in EPISODES.values()})
first_listing = 'known' not in hist
known = set(hist.get('known', []))
new_eps = [] if first_listing else sorted(k for k in EPISODES if k not in known)
print(f'library ({LIB_SRC}):', ', '.join(f"{s} {sum(v['series'] == s for v in EPISODES.values())}" for s in series_all), flush=True)
if new_eps:
    print('new in Drive since last run:', new_eps, flush=True)

songs = sorted(f[:-4] for f in os.listdir('music') if f.endswith('.mp3'))
song = SONG if SONG in songs else least_used(songs, hist['songs'], 1)[0]
if PICK in CHARS:                                                     # a character: its fight episodes
    title = PICK
    eps = least_used([e for e in CHARS[PICK] if e in EPISODES], hist['episodes'], 3)
    series = EPISODES[eps[0]]['series']
else:
    match = [s for s in series_all if PICK != 'auto' and (s == PICK or s.startswith(PICK) or PICK in s)]
    if match:
        series = match[0]
    elif new_eps:                                                     # something new was added: use it first
        series = EPISODES[new_eps[0]]['series']
    else:                                                             # rotate between the anime in the folder
        series = least_used(series_all, hist['series'], 1)[0]
    title = series
    pool_eps = [k for k, v in EPISODES.items() if v['series'] == series]
    fresh = [e for e in new_eps if e in pool_eps][:3]
    eps = fresh + least_used([e for e in pool_eps if e not in fresh], hist['episodes'], 3 - len(fresh))
if not eps:
    sys.exit(f'no episodes for {PICK}')
eps.sort()
print('pick', PICK, '| anime', series, '| song', song, '| episodes', eps, '| seed', SEED, flush=True)
SRC = lambda code: 'src/' + code.replace(':', '__') + '.mp4'


# ---------------------------------------------------------------- 2. download
def fetch(code):
    dst = SRC(code)
    if os.path.exists(dst) and os.path.getsize(dst) > 10_000_000:
        return dst
    for _ in range(3):
        r = subprocess.run([sys.executable, '-m', 'gdown', EPISODES[code]['drive_id'], '-O', dst, '-q'])
        if r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 10_000_000:
            return dst
    raise SystemExit(f'download failed {code}')


with ThreadPoolExecutor(3) as ex:
    list(ex.map(fetch, eps))


# ---------------------------------------------------------------- 3. scan episodes
def duration(p):
    return float(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


def scan(code):
    p = SRC(code)
    raw = sh_bytes(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-vf',
                    f'fps={SCAN_FPS},scale={SCAN_W}:{SCAN_H}:flags=area,format=rgb24', '-f', 'rawvideo', '-'])
    fr = np.frombuffer(raw, np.uint8).reshape(-1, SCAN_H, SCAN_W, 3).astype(np.float32)
    gray = fr.mean(axis=3)
    sat = fr.max(axis=3) - fr.min(axis=3)
    diff = np.abs(np.diff(gray, axis=0)).mean(axis=(1, 2))          # frame-to-frame change
    diff = np.concatenate([[0], diff])
    # cut = change far above the local level
    med = np.median(np.lib.stride_tricks.sliding_window_view(np.pad(diff, 12, mode='edge'), 25), axis=1)[:len(diff)]
    cuts = [0] + [i for i in range(1, len(diff)) if diff[i] > max(18, 4 * med[i])] + [len(diff)]
    dur = len(diff) / SCAN_FPS
    lo, hi = 25.0, dur - 140.0                                        # skip cold-open title + ED/preview
    shots, sigs = [], []
    for a, b in zip(cuts[:-1], cuts[1:]):
        s, e = a / SCAN_FPS, b / SCAN_FPS
        if b - a >= 3:
            sigs.append((s, gray[(a + b) // 2].reshape(9, 4, 16, 4).mean(axis=(1, 3)).ravel()))
        if e - s < 0.45 or s < lo or e > hi:
            continue
        seg = slice(a + 1, b)
        inner = diff[seg] if b - a > 2 else diff[a:b]
        g = gray[a:b]
        bright, contrast = float(g.mean()), float(g.std(axis=(1, 2)).mean())
        if bright < 18 or contrast < 12:                              # black / flat frames
            continue
        mid = gray[(a + b) // 2]
        thumb = mid.reshape(9, 4, 16, 4).mean(axis=(1, 3))
        shots.append(dict(ep=code, s=round(s + 0.04, 3), e=round(e - 0.04, 3),
                          motion=float(np.mean(inner)), peak=float(np.percentile(inner, 90)),
                          contrast=contrast, sat=float(sat[a:b].mean()), bright=bright,
                          thumb=thumb.round(1).tolist()))
    print(code, 'shots', len(shots), flush=True)
    return code, shots, sigs


def sh_bytes(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:].decode(errors='ignore'))
    return r.stdout


# opening song: each opening is shared by a run of episodes, so a sibling episode shows where it is
def op_group(code):
    v = EPISODES[code]; se, ep = v['season'], v['ep']
    if v['series'] == 'jujutsu-kaisen' and se == 2:
        part = 0 if ep <= 5 else 1
    else:
        part = (ep - 1) // 13                                        # a new opening roughly every cour
    return (v['series'], se, part)


hist.setdefault('openings2', {})
refs = []
for e in eps:
    if e in hist['openings2'] or any(op_group(o) == op_group(e) and o != e for o in eps + refs):
        continue
    sib = sorted((o for o in EPISODES if op_group(o) == op_group(e) and o not in eps),
                 key=lambda o: abs(EPISODES[o]['ep'] - EPISODES[e]['ep']))
    if sib:
        refs.append(sib[0])
if refs:
    print('reference episodes for opening detection', refs, flush=True)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(fetch, refs))
with ThreadPoolExecutor(3) as ex:
    scans = list(ex.map(scan, eps + refs))
allshots = sum((sh_ for c, sh_, _ in scans if c in eps), [])
sigs = {c: sg for c, _, sg in scans}
for c in eps:
    if c in hist['openings2']:
        continue
    hits = []
    for t, v in sigs[c]:
        for o, sg in sigs.items():
            if o == c or op_group(o) != op_group(c):
                continue
            if sg and min(np.abs(v - w).mean() for _, w in sg) < 5:
                hits.append(t); break
    win = []                                                          # every run of matching shots (opening, ending, recap)
    hits.sort(); grp = []
    for h in hits + [1e9]:
        if grp and h - grp[-1] > 20:
            if len(grp) >= 5:
                win.append([round(grp[0] - 4, 1), round(grp[-1] + 5, 1)])
            grp = []
        grp.append(h)
    hist['openings2'][c] = win
    print(c, 'opening', win, flush=True)
for s in allshots:
    w = hist['openings2'].get(s['ep']) or []
    if w and not isinstance(w[0], list):
        w = [w]
    s['op'] = any(a <= s['s'] <= b for a, b in w)

# ---------------------------------------------------------------- 4. filter repeats
thumbs = np.array([s['thumb'] for s in allshots]).reshape(len(allshots), -1)
dup = np.array([s['op'] for s in allshots])
for i in range(len(allshots)):
    d = np.abs(thumbs - thumbs[i]).mean(axis=1)
    other = np.array([s['ep'] != allshots[i]['ep'] for s in allshots])
    if np.any((d < 6) & other):
        dup[i] = True                                                 # same shot in another episode: recap
used = {(u['ep'], round(u['s'])) for u in hist['shots']}
pool = [s for k, s in enumerate(allshots)
        if not dup[k] and not any((s['ep'], round(s['s']) + o) in used for o in (-2, -1, 0, 1, 2))]
if len(pool) < 90:                                                    # history too tight: allow reuse
    pool = [s for k, s in enumerate(allshots) if not dup[k]]
print('pool', len(pool), 'of', len(allshots), flush=True)


def z(v):
    v = np.asarray(v, float); return (v - v.mean()) / (v.std() + 1e-6)


M, P_, C, S, B = (z([s[k] for s in pool]) for k in ('motion', 'peak', 'contrast', 'sat', 'bright'))
for i, s in enumerate(pool):
    s['impact'] = float(0.55 * M[i] + 0.35 * P_[i] + 0.25 * C[i] + 0.2 * S[i] + 0.15 * min(B[i], 1.0))
    s['calm'] = float(-0.6 * abs(M[i] + 0.3) + 0.4 * C[i] + 0.3 * S[i] + 0.3 * min(2.5, s['e'] - s['s']))

# ---------------------------------------------------------------- 5. music
song_path = f'music/{song}.mp3'
import librosa
y, sr = librosa.load(song_path, sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
tempo = float(np.atleast_1d(tempo)[0])
while tempo < 100: tempo *= 2
while tempo > 180: tempo /= 2
P = 60.0 / tempo
rms = librosa.feature.rms(y=y, hop_length=512)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
song_len = len(y) / sr
need = TEMPLATE_BEATS * P


def level(t0, t1):
    m = (rt >= t0) & (rt < t1)
    return float(rms[m].mean()) if m.any() else 0.0


best, drop_t = -1e9, None
for b in beats:
    if b - DROP_BEAT * P < 0 or b - DROP_BEAT * P + need > song_len:
        continue
    jump = level(b, b + 8 * P) - level(b - 8 * P, b)
    if jump > best:
        best, drop_t = jump, float(b)
if drop_t is None:
    drop_t = DROP_BEAT * P
song_start = max(0.0, drop_t - DROP_BEAT * P)
print(f'tempo {tempo:.1f} beat {P:.4f}s drop {drop_t:.2f}s start {song_start:.2f}s', flush=True)

# ---------------------------------------------------------------- 6. fill the template
tmpl = [tuple(map(int, l.split()[:2])) for l in open('template.txt')]
max_beats = int(60.0 / P)                                             # keep every edit to 60 s, whatever the tempo
tmpl = [(a, min(b, max_beats)) for a, b in tmpl if a < max_beats]
n = len(tmpl)
second_drop = next((i for i, (a, b) in enumerate(tmpl) if a == 113), None)
pre = [i for i, (a, b) in enumerate(tmpl) if a < DROP_BEAT]
build2 = [i for i, (a, b) in enumerate(tmpl) if 109 <= a < 113]
taken, assign = set(), {}


def take(idx_list, key, min_len):
    cands = sorted((s for s in pool if id(s) not in taken), key=lambda s: -s[key])
    for i in idx_list:
        dur = (tmpl[i][1] - tmpl[i][0]) * P
        for s in cands:
            if id(s) in taken:
                continue
            if s['e'] - s['s'] >= min(dur * min_len, 3.0):
                assign[i] = s; taken.add(id(s)); break


# build-ups want faces: grab a frame from the best calm candidates and look for an anime face
try:
    import cv2
    casc = cv2.CascadeClassifier('lbpcascade_animeface.xml')
    for s in sorted(pool, key=lambda s: -s['calm'])[:90]:
        t = (s['s'] + s['e']) / 2
        raw = sh_bytes(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.2f}', '-i', SRC(s['ep']), '-frames:v', '1',
                        '-vf', 'scale=480:270,format=gray', '-f', 'rawvideo', '-'])
        img = np.frombuffer(raw, np.uint8).reshape(270, 480)
        faces = casc.detectMultiScale(img, 1.1, 4, minSize=(40, 40))
        big = max((w * h for x, y, w, h in faces), default=0) / (480 * 270)
        s['calm'] += 2.5 if big > 0.04 else (1.2 if big > 0 else -0.5)
except Exception as ex:
    print('face check skipped', ex, flush=True)
take(pre + build2, 'calm', 0.8)                                      # build-ups: steady, readable shots
heroes = [next(i for i, (a, b) in enumerate(tmpl) if a == DROP_BEAT)]
if second_drop is not None:
    heroes.append(second_drop)
take(heroes, 'impact', 0.5)                                          # the two drops: hardest hits
rest = [i for i in range(n) if i not in assign]
k = len(rest)
top = sorted((s for s in pool if id(s) not in taken), key=lambda s: -s['impact'])[:k]
top.sort(key=lambda s: (s['ep'], s['s']))                            # story order through the fights
for i, s in zip(rest, top):
    assign[i] = s; taken.add(id(s))
if len(assign) < n:
    sys.exit(f'not enough shots ({len(assign)}/{n})')
impact_cut = np.percentile([s['impact'] for s in pool], 85)

# ---------------------------------------------------------------- 7. render
fr = lambda j: round(j * P * FPS)
drop_i = next(i for i, (a, b) in enumerate(tmpl) if a == DROP_BEAT)
kinds = default_transition_pattern(n, drop_i)
if second_drop:
    kinds[second_drop - 1] = 'flash'
fxl = pair_transitions(n, kinds)
os.makedirs('segfx', exist_ok=True)
jobs, plan = [], []
for k_, (a, b) in enumerate(tmpl):
    s = assign[k_]
    nf = fr(b) - fr(a); dur = nf / FPS
    fx = list(fxl[k_])
    if a < DROP_BEAT or 109 <= a < 113:
        fx.append('drift')
    elif b - a >= 2:
        fx.append('pulse')
    if s['impact'] >= impact_cut and a >= DROP_BEAT:
        fx.append('shake')
    L = s['e'] - s['s']; spd = 1.0
    if L >= dur:
        st = s['s'] + (L - dur) / 2
    else:
        st = s['s']; spd = max(0.5, L / dur)
    vf = build_shot_fx(dur, W, H, fx, beat=P, speed=spd)
    vf += ',eq=contrast=1.12:saturation=1.18:gamma=0.97,vignette=PI/5'
    if k_ == n - 1:
        vf += f',fade=out:st={dur - 0.6:.2f}:d=0.6'
    plan.append(dict(beats=[a, b], ep=s['ep'], start=round(st, 3), fx=fx, speed=round(spd, 3)))
    jobs.append(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{st:.3f}', '-i', SRC(s['ep']), '-an',
                 '-vf', vf, '-frames:v', str(nf), '-r', str(FPS), '-fps_mode', 'cfr',
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', f'segfx/{k_:03d}.mp4'])
json.dump(dict(pick=PICK, anime=series, song=song, episodes=eps, tempo=tempo, song_start=song_start, plan=plan),
          open('work/edit_plan.json', 'w'), indent=1)


def run(c):
    for _ in range(2):
        r = subprocess.run(c, capture_output=True, text=True)
        if r.returncode == 0:
            return
    raise RuntimeError(c[-1] + r.stderr[-800:])


with ThreadPoolExecutor(os.cpu_count() or 2) as ex:
    list(ex.map(run, jobs))
open('segfx/list.txt', 'w').write(''.join(f"file '{i:03d}.mp4'\n" for i in range(n)))
os.makedirs('../out', exist_ok=True)
name = re.sub(r'[^A-Za-z0-9]+', '_', title.title()) + f'_AMV_{song}'
total = fr(tmpl[-1][1]) / FPS
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'segfx/list.txt', '-c', 'copy', 'work/video.mp4'])
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', 'work/video.mp4', '-ss', f'{song_start:.3f}', '-i', song_path,
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
    '-af', f'afade=t=out:st={total - 1.2:.2f}:d=1.2', '-shortest', '-movflags', '+faststart', f'../out/{name}.mp4'])
print('wrote', f'out/{name}.mp4', flush=True)

# ---------------------------------------------------------------- history
hist['songs'][song] = hist['songs'].get(song, 0) + 1
for e in eps:
    hist['episodes'][e] = hist['episodes'].get(e, 0) + 1
hist['series'][series] = hist['series'].get(series, 0) + 1
hist['known'] = sorted(set(hist.get('known', [])) | set(EPISODES))
hist['shots'] += [dict(ep=p['ep'], s=p['start']) for p in plan]
hist['shots'] = hist['shots'][-3000:]
hist['runs'].append(dict(time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), pick=PICK, series=series, song=song, episodes=eps, file=f'{name}.mp4'))
json.dump(hist, open(HIST_PATH, 'w'), indent=1)
