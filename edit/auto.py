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
SONG = (os.environ.get('SONG') or os.environ.get('BGM') or '').strip().lower()
SEED = int(os.environ.get('SEED', time.time()))
TEMPLATE_BEATS = 130            # length of the edit in beats (60 s at 130 BPM)
DROP_BEAT = 17                  # first drop, same as the Gojo AMV
START_BEAT = int(os.environ.get('START_BEAT', 0))     # convo shorts start the edit a few beats before the drop
MAX_SECONDS = float(os.environ.get('MAX_SECONDS', 60))
FORCE_EPS = [e for e in os.environ.get('FORCE_EPS', '').split(',') if e]
INCLUDE = os.environ.get('INCLUDE', '')                 # ep|s|e: only shots from this scene (same characters)
EXCLUDE = [x.rsplit('|', 2) for x in os.environ.get('EXCLUDE', '').split(';') if x]   # ep|s|e already used
OUT_NAME = os.environ.get('OUT_NAME', '')
# AMV_STYLE=drop (set by convo.py): the edit starts ON the drop (beat 17), one cut per beat, only the topic
# character's combat / awakening shots with impact >= the 85th percentile, Gojo v2 FX on every cut.
DROP_STYLE = os.environ.get('AMV_STYLE', '') == 'drop'
IMPACT_PCT = float(os.environ.get('IMPACT_PCT', 85))
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


PERF = hist.get('perf', {}) if isinstance(hist.get('perf'), dict) else {}
PERF_W = float(os.environ.get('PERF_WEIGHT', 1.5))                # how many "uses" a top performer is worth (learn.py)


def least_used(options, counts, k, perf=None):
    opts = list(options); rng.shuffle(opts)
    perf = perf or {}
    opts.sort(key=lambda o: counts.get(o, 0) - PERF_W * float(perf.get(o, 0) or 0))   # least used, nudged toward what viewers watched
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
if SONG and SONG != 'auto':
    match_song = [s for s in songs if s.lower() == SONG or SONG in s.lower() or s.lower().startswith(SONG)]
    song = match_song[0] if match_song else (least_used(songs, hist['songs'], 1, PERF.get('song'))[0])
else:
    song = least_used(songs, hist['songs'], 1, PERF.get('song'))[0]
    if PERF.get('song'):
        print('song pick weighted by past performance:', {k: round(v, 2) for k, v in PERF['song'].items()}, flush=True)
if FORCE_EPS:
    eps = list(FORCE_EPS); series = EPISODES[eps[0]]['series']; title = series
elif PICK in CHARS:                                                     # a character: its fight episodes
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


BLACK_MEAN, BLACK_P90 = 14.0, 30.0                                    # per frame, 0-255 luma at scan size
DARK_MEAN = float(os.environ.get('DARK_MEAN', 24)); DARK_P90 = float(os.environ.get('DARK_P90', 36))   # night fights sit at
                                                                     # ~19-34 / 40-60 and stay; corridor 10-21 / 18-33, title card 4 / 0 go
DARK_SHARE = float(os.environ.get('DARK_SHARE', 0.4))


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
    flat = gray.reshape(len(gray), -1)
    f_mean, f_p90 = flat.mean(axis=1), np.percentile(flat, 90, axis=1)
    black = (f_mean < BLACK_MEAN) & (f_p90 < BLACK_P90)               # truly black (fade to / from black)
    dark = (f_mean < DARK_MEAN) & (f_p90 < DARK_P90)                 # too dark to read (corridor, glint on black, title card)
    shots, sigs = [], []
    n_dark = 0
    for a, b in zip(cuts[:-1], cuts[1:]):
        s, e = a / SCAN_FPS, b / SCAN_FPS
        if b - a >= 3:
            sigs.append((s, gray[(a + b) // 2].reshape(9, 4, 16, 4).mean(axis=(1, 3)).ravel()))
        while a < b and black[a]:                                     # a fade: drop only the truly black frames, keep the shot
            a += 1
        while b > a and black[b - 1]:
            b -= 1
        a0, b0 = a, b                                                 # dark head / tail (title card, corridor) cut off too
        while a < b and dark[a]:
            a += 1
        while b > a and dark[b - 1]:
            b -= 1
        if b - a < 6:                                                 # nothing readable left
            a, b = a0, b0
        if b - a < 3:
            continue
        s, e = a / SCAN_FPS, b / SCAN_FPS
        if e - s < 0.45 or s < lo or e > hi:
            continue
        if dark[a:b].mean() > DARK_SHARE:                             # mostly dark: mean AND bright end both low
            n_dark += 1
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
    print(code, 'shots', len(shots), f'({n_dark} mostly-dark shots dropped)', flush=True)
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
allshots = [s for s in allshots if not any(s['ep'] == ep and s['e'] > float(a) - 2 and s['s'] < float(b) + 2 for ep, a, b in EXCLUDE)]
CREDITS = [x.rsplit('|', 2) for x in os.environ.get('CREDITS', '').split(';') if x]   # openings / endings / recaps: never used
allshots = [s for s in allshots if not any(s['ep'] == ep and s['e'] > float(a) - 1 and s['s'] < float(b) + 1 for ep, a, b in CREDITS)]
ep_all = list(allshots)
if INCLUDE:                                                           # widen around the scene only as far as needed
    iep, ia, ib = INCLUDE.rsplit('|', 2); ia, ib = float(ia), float(ib)
    for pad in range(0, 421, 30):
        scene = [s for s in allshots if s['ep'] == iep and s['s'] >= ia - pad and s['e'] <= ib + pad]
        if len(scene) >= 45:
            break
    print('scene shots', len(scene), 'within', pad, 's of', INCLUDE, flush=True)
    allshots = scene
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
if len(pool) < 90 or INCLUDE:                                                    # history too tight: allow reuse
    pool = [s for k, s in enumerate(allshots) if not dup[k]]
elif DROP_STYLE and os.environ.get('CHAR_SLUG'):                     # a character's fights are finite: earlier runs must not
    fresh_ids = {id(s) for s in pool}                                # eat them up (the pool shrank to 10 Gojo shots), so used
    pool = [s for k, s in enumerate(allshots) if not dup[k]]         # shots come back, ranked a little below fresh ones
    for s in pool:
        s['reused'] = id(s) not in fresh_ids
    print(f'drop style: {sum(s["reused"] for s in pool)} shots used by earlier runs allowed back (ranked below fresh ones)', flush=True)
print('pool', len(pool), 'of', len(allshots), flush=True)


def z(v):
    v = np.asarray(v, float); return (v - v.mean()) / (v.std() + 1e-6)


M, P_, C, S, B = (z([s[k] for s in pool]) for k in ('motion', 'peak', 'contrast', 'sat', 'bright'))
for i, s in enumerate(pool):
    s['impact'] = float(0.55 * M[i] + 0.35 * P_[i] + 0.25 * C[i] + 0.2 * S[i] + 0.15 * min(B[i], 1.0))
    s['calm'] = float(-0.6 * abs(M[i] + 0.3) + 0.4 * C[i] + 0.3 * S[i] + 0.3 * min(2.5, s['e'] - s['s']))
for s in pool:
    if s.get('reused'):
        s['impact'] -= 0.25
full_pool = list(pool)
if DROP_STYLE:                                                        # action only: every shot in the top 15% by impact
    gate = float(np.percentile([s['impact'] for s in pool], IMPACT_PCT))
    pool = [s for s in pool if s['impact'] >= gate]
    print(f'drop style: impact gate p{IMPACT_PCT:.0f} = {gate:.3f}, {len(pool)} of {len(full_pool)} shots pass', flush=True)

# ---------------------------------------------------------------- 4b. keep only shots where the topic character is on screen, fighting
CHAR_NAME = os.environ.get('CHAR_NAME', '')
_PROMPTS_ADDED = []


def _char_filter(pool):
    import charvis
    if DROP_STYLE and not _PROMPTS_ADDED:
        _PROMPTS_ADDED.append(1)                                                    # awakening counts as action; crowds / talking heads / idle do not
        charvis.ACTION += ['an anime character powering up with a glowing aura and crackling energy',
                           'an anime character awakening with glowing eyes and a burst of cursed energy',
                           'an anime character dashing through the air mid-attack with speed lines']
        charvis.CALM += ['a crowd of anime characters watching and reacting in shock',
                         'an anime close-up of a character talking with a still face',
                         'anime characters standing around in conversation']
    cv_ = charvis.get(CHAR_NAME, os.environ.get('CHAR_SERIES', ''))
    if cv_ is not None:
        cands = sorted(pool, key=lambda s: -s['impact'])[:int(os.environ.get('CHAR_CANDS', 420))]
        sc_ = cv_.score([(SRC(s['ep']), (s['s'] + s['e']) / 2) for s in cands])
        cands = [s for s, v in zip(cands, sc_) if v]
        for s, v in zip(cands, [v for v in sc_ if v]):
            s.update(char=v['char'], action=v['action'], rel=v.get('rel', 0.0))
        if len(cands) >= 20:
            Cz, Az = z([s['char'] for s in cands]), z([s['action'] for s in cands])
            for i, s in enumerate(cands):
                s['char_z'], s['act_z'] = float(Cz[i]), float(Az[i])
            per_ep = {}
            for s in cands:
                per_ep.setdefault(s['ep'], []).append(s['char_z'])
            rel_ep = {}
            for s in cands:
                rel_ep.setdefault(s['ep'], []).append(s.get('rel', 0) > -0.03)
            share = {e: float(np.mean(v)) for e, v in rel_ep.items()}
            print('character presence per episode (mean of top 10 z):',
                  {e: round(float(np.mean(sorted(v)[-10:])), 2) for e, v in per_ep.items()},
                  '| share of shots that look like them:', {e: round(v, 2) for e, v in share.items()}, flush=True)
            weak = [e for e, v in share.items() if v < 0.04 and max(share.values()) >= 0.12]   # character barely in this episode: drop it
            if weak and len(weak) < len(share):
                print('dropping episodes without the character:', weak, flush=True)
                cands = [s for s in cands if s['ep'] not in weak]
            n_need = int(os.environ.get('CHAR_MIN_SHOTS', 45))
            REL_MIN = float(os.environ.get('CHAR_REL_MIN', 0.04))     # identity is never relaxed: the shot must look more like
            ACT_MIN = float(os.environ.get('CHAR_ACT_MIN', 0.0))           # after the narration: fight shots only, never relaxed
            ident = [s for s in cands if s.get('rel', 0) >= REL_MIN and s['act_z'] >= ACT_MIN]     # the topic than like ANY other character (Nezuko vs Daki)
            print(f'identity check "{CHAR_NAME}": {len(ident)} of {len(cands)} shots clearly them in a fight (rel>={REL_MIN}, act_z>={ACT_MIN})', flush=True)
            if len(ident) < int(os.environ.get('CHAR_MIN_IDENT', 10)):
                raise SystemExit(f'character gate: only {len(ident)} shots clearly show {CHAR_NAME}; refusing to fill with look-alikes')
            for thr in (0.6, 0.35, 0.1, -0.15, -0.4):                   # strictest bar that still fills the edit (only the bar, never identity)
                keep = [s for s in ident if s['char_z'] >= thr and s['act_z'] >= -0.8]
                if len(keep) >= n_need:
                    break
            if DROP_STYLE:                                            # purity first: every clearly-them fight shot, nothing else
                keep, thr = list(ident), 'identity+action'
            for s in keep:                                            # action + character lift the drops and the fast cuts
                s['impact'] += 0.9 * s['char_z'] + 0.6 * s['act_z']
                s['calm'] += 0.8 * s['char_z']
            print(f'character filter "{CHAR_NAME}": kept {len(keep)} of {len(cands)} scored shots (bar z>={thr})', flush=True)
            pool = keep
    return pool


purity_pct = IMPACT_PCT if DROP_STYLE else None


def _curated_windows():
    """Hand-checked fight windows for this character (fight_windows.json), keyed by full episode code."""
    try:
        fw = json.load(open('fight_windows.json'))
    except Exception:
        return {}
    slug = os.environ.get('CHAR_SLUG', '').strip().lower()
    return {_k(e): [tuple(w) for w in v] for e, v in fw.get(slug, {}).items()} if slug else {}


def _cached_auto_windows():
    """fight windows detected automatically by earlier runs (fight_windows.json -> _auto -> slug -> episode)"""
    slug = os.environ.get('CHAR_SLUG', '').strip().lower()
    try:
        fw = json.load(open('fight_windows.json')).get('_auto', {}).get(slug, {}) if slug else {}
        return {_k(e): [tuple(w) for w in d['windows']] for e, d in fw.items() if d.get('windows')}
    except Exception:
        return {}


def _save_auto_windows(det, anchors):
    """remember detected windows so later runs reuse them; hand-checked entries are never touched"""
    slug = os.environ.get('CHAR_SLUG', '').strip().lower()
    if not slug or not det:
        return
    try:
        fw = json.load(open('fight_windows.json'))
        auto = fw.setdefault('_auto', {}).setdefault(slug, {})
        for e, w in det.items():
            auto[e] = dict(windows=[[round(a, 1), round(b, 1)] for a, b in w], source='auto', character=CHAR_NAME,
                           anchors=sum(1 for s in anchors if s['ep'] == e), detected=time.strftime('%Y-%m-%d', time.gmtime()))
        fw['_doc_auto'] = ('_auto: fight windows found automatically (_auto_fight_windows) for characters without hand-checked '
                           'windows, cached so later runs reuse them. Hand-checked entries stay at the top level.')
        json.dump(fw, open('fight_windows.json', 'w'), indent=1)
        print('drop style: cached auto fight windows for', slug, sorted(det), flush=True)
    except Exception as ex:
        print('could not cache auto fight windows:', ex, flush=True)


def _auto_fight_windows(full_pool, anchors, rel_of, act_of=None):
    """Any anime, any character: a fight is a sustained stretch of hot shots (heat = impact + 0.6 * CLIP action z for
    the shots charvis scored; hot = top 65% of the episode; hot shots no more than 6 s apart, 10 s+ long, 4+ shots).
    It is this character's fight when clear-identity shots sit inside it and, on balance, the stretch does not read as
    someone else. Tuned offline against the hand-checked Gojo windows (S1E07, S2E04, S2E09): recall 75.5% of curated
    seconds at 41.3% precision (the old 60th-percentile / 4 s rule: recall 11.5%, precision 21.7%)."""
    HOT_PCT = float(os.environ.get('FIGHT_HOT_PCT', 35))
    GAP = float(os.environ.get('FIGHT_GAP', 6.0))
    ACT_W = float(os.environ.get('FIGHT_ACT_W', 0.6))
    act_of = act_of or {}
    heat = lambda s: s['impact'] + ACT_W * act_of.get((s['ep'], s['s']), 0.0)
    win = {}
    for ep in sorted({s['ep'] for s in full_pool}):
        sh_ = sorted((s for s in full_pool if s['ep'] == ep), key=lambda s: s['s'])
        if len(sh_) < 8:
            continue
        hot_gate = float(np.percentile([heat(s) for s in sh_], HOT_PCT))
        segs, cur = [], None
        for s in sh_:
            if heat(s) < hot_gate:
                continue
            if cur and s['s'] - cur[1] <= GAP:
                cur[1] = s['e']; cur[2] += 1
            else:
                cur = [s['s'], s['e'], 1]; segs.append(cur)
        for a, b, k in segs:
            if b - a < 10.0 or k < 4:
                continue
            inside = lambda s: s['ep'] == ep and a - 0.5 <= s['s'] and s['e'] <= b + 0.5
            n_anchor = sum(1 for s in anchors if inside(s))
            rels = [r for s, r in rel_of if inside(s)]
            if n_anchor >= 2 or (n_anchor >= 1 and rels and float(np.mean(rels)) >= 0.0):
                win.setdefault(ep, []).append((a - 2.0, b + 2.0))
    return win


NONCOMBAT_MAX = -0.003                                                # charvis noncombat score above this: never a fight shot
                                                                      # (Gojo windows: title logo .13, Halloween crowd .05, mahjong .03,
                                                                      #  Joker cosplayer .007, opening shots .01; fight shots <= -0.02)


def _drop_char_pool(full_pool):
    """Character purity for the drop edit, for any anime and any character. Shots come ONLY from the character's
    fights: hand-checked windows (fight_windows.json) when the character has them, else fight stretches detected
    automatically. Inside a fight a shot still goes if it clearly shows someone else (opponent solo, other characters),
    reads as calm (talking, idle, crowd) or is too dark to read. Impact >= p85 first."""
    global purity_pct
    import charvis
    if not _PROMPTS_ADDED:
        _PROMPTS_ADDED.append(1)
        charvis.ACTION += ['an anime character powering up with a glowing aura and crackling energy',
                           'an anime character awakening with glowing eyes and a burst of cursed energy',
                           'an anime character dashing through the air mid-attack with speed lines']
        charvis.CALM += ['a crowd of anime characters watching and reacting in shock',
                         'an anime close-up of a character talking with a still face',
                         'anime characters standing around in conversation',
                         'anime students playing baseball on a sports field',
                         'a comedic chibi anime reaction with blushing cheeks']
    cv_ = charvis.get(CHAR_NAME, os.environ.get('CHAR_SERIES', ''))
    if cv_ is None:
        raise RuntimeError('charvis unavailable')
    imp = [s['impact'] for s in full_pool]
    curated = {e: w for e, w in _curated_windows().items() if any(s['ep'] == e for s in full_pool)}
    in_win = lambda s, win: any(a <= s['s'] and s['e'] <= b for a, b in win.get(s['ep'], []))
    lo_imp = float(np.percentile(imp, 55))
    cands = [s for s in full_pool if (in_win(s, curated) if curated else s['impact'] >= lo_imp)]
    res = cv_.score([(SRC(s['ep']), (s['s'] + s['e']) / 2) for s in cands])
    cands = [dict(s, rel=r['rel'], char=r['char'], action=r['action'], noncombat=r.get('noncombat', -1.0))
             for s, r in zip(cands, res) if r]
    Az = z([s['action'] for s in cands]); Cz = z([s['char'] for s in cands])
    for i, s in enumerate(cands):
        s['act_z'], s['char_z'] = float(Az[i]), float(Cz[i])
    REL_MIN = float(os.environ.get('CHAR_REL_MIN', 0.04))
    anchors = [s for s in cands if s['rel'] >= REL_MIN]
    if curated:
        win, how = curated, 'hand-checked'
    else:                                                             # auto windows found by an earlier run are reused
        cached = _cached_auto_windows()
        pool_eps = sorted({s['ep'] for s in full_pool})
        win = {e: cached[e] for e in pool_eps if cached.get(e)}
        todo = [e for e in pool_eps if e not in win]
        det = _auto_fight_windows([s for s in full_pool if s['ep'] in todo], anchors, [(s, s['rel']) for s in cands],
                                  {(s['ep'], s['s']): s['act_z'] for s in cands}) if todo else {}
        win.update(det)
        how = f"detected {sorted(det)}" + (f" + cached {sorted(e for e in win if e not in det)}" if len(win) > len(det) else '')
        _save_auto_windows(det, anchors)
        if not win:                                                   # nothing reads as a fight: stay close to the anchors
            for s in anchors:
                win.setdefault(s['ep'], []).append((s['s'] - 12, s['e'] + 12))
            how = 'anchor +-12 s (no fight stretch detected)'
    print(f'drop style: {len(anchors)} anchor shots clearly {CHAR_NAME}; {how} fight windows:',
          {e: [(round(a), round(b)) for a, b in v] for e, v in win.items()}, flush=True)
    BRIGHT_MIN = float(os.environ.get('DROP_BRIGHT_MIN', 32))
    NC_MAX = float(os.environ.get('DROP_NONCOMBAT_MAX', NONCOMBAT_MAX))
    AUTO_REL = float(os.environ.get('DROP_AUTO_REL_MIN', 0.02))
    noncombat = [s for s in cands if in_win(s, win) and s['noncombat'] > NC_MAX]   # crowd / costume / title card / empty sky,
    if noncombat:                                                     # even inside a hand-checked window
        print(f'drop style: {len(noncombat)} non-combat shots out of the fight windows (crowd, title card, scenery):',
              [(s_['ep'].split(':')[-1], round(s_['s'])) for s_ in noncombat[:12]], flush=True)
    if curated:                                                       # hand-checked fights: only drop a clear opponent solo / dark shot
        pure = [s for s in cands if in_win(s, win) and s['rel'] >= -0.05 and s['bright'] >= BRIGHT_MIN and s['noncombat'] <= NC_MAX]
    else:                                                             # detected fights: the character must clearly be the one on screen
        pure = [s for s in cands if in_win(s, win) and s['rel'] >= AUTO_REL and s['act_z'] >= -0.25 and s['bright'] >= BRIGHT_MIN
                and s['noncombat'] <= NC_MAX]
    print(f'drop style: {len(pure)} {CHAR_NAME} shots inside the fight windows', flush=True)
    need = int(os.environ.get('DROP_MIN_SHOTS', 60))
    for pct in (IMPACT_PCT, 75.0, 65.0, 50.0):
        gate = float(np.percentile([s['impact'] for s in cands] if curated else imp, pct))
        keep = [s for s in pure if s['impact'] >= gate]
        print(f'drop style: p{pct:.0f} gate {gate:.3f}: {len(keep)} pure {CHAR_NAME} combat shots', flush=True)
        if len(keep) >= need:
            break
    purity_pct = pct
    if len(keep) < 6:
        raise SystemExit(f'drop style: only {len(keep)} clean {CHAR_NAME} combat shots; refusing to fill with other characters')
    for s in keep:
        s['impact'] += 0.6 * max(0.0, s['char_z']) + 0.6 * s['act_z']
    return keep


if CHAR_NAME and DROP_STYLE:
    try:
        pool = _drop_char_pool(full_pool)
    except SystemExit:
        raise
    except Exception as ex:
        print('character filter failed, impact-gated motion picks only:', ex, flush=True)
    if purity_pct != IMPACT_PCT:
        print(f'WARNING drop style: impact gate relaxed to p{purity_pct:.0f} to find enough {CHAR_NAME} shots', flush=True)
elif CHAR_NAME:
    try:
        pool = _char_filter(pool)
    except Exception as ex:                                           # fail-safe: motion-only picks
        print('character filter failed, motion-only picks:', ex, flush=True)

if DROP_STYLE:                                                        # talking heads: a big still face is never a combat shot
    try:
        import cv2
        _casc = cv2.CascadeClassifier('lbpcascade_animeface.xml')
        mot_hi = float(np.percentile([s['motion'] for s in pool], 60)) if pool else 0
        kept = []
        for s in pool:
            raw = sh_bytes(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f"{(s['s'] + s['e']) / 2:.2f}", '-i', SRC(s['ep']),
                            '-frames:v', '1', '-vf', 'scale=480:270,format=gray', '-f', 'rawvideo', '-'])
            img = np.frombuffer(raw, np.uint8).reshape(270, 480)
            faces = _casc.detectMultiScale(img, 1.1, 4, minSize=(40, 40))
            big = max((w * h for x, y, w, h in faces), default=0) / (480 * 270)
            if big > 0.07 and s['motion'] < mot_hi:
                continue
            kept.append(s)
        print(f'drop style: talking-head check dropped {len(pool) - len(kept)} of {len(pool)}', flush=True)
        if len(kept) >= 6:
            pool = kept
    except Exception as ex:
        print('talking-head check skipped', ex, flush=True)

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
if DROP_STYLE:                                                        # only the part after the drop has to fit in the song
    need = DROP_BEAT * P + MAX_SECONDS


def level(t0, t1):
    m = (rt >= t0) & (rt < t1)
    return float(rms[m].mean()) if m.any() else 0.0


best, drop_t = -1e9, None
MIN_START = float(os.environ.get('MIN_SONG_START', 0))               # narration bed plays the song right before the edit
for b in beats:
    if b - (DROP_BEAT - START_BEAT) * P < MIN_START:
        continue
    if b - DROP_BEAT * P < 0 or b - DROP_BEAT * P + need > song_len:
        continue
    jump = level(b, b + 8 * P) - level(b - 8 * P, b)
    if jump > best:
        best, drop_t = jump, float(b)
if drop_t is None:
    drop_t = max(DROP_BEAT * P, MIN_START + (DROP_BEAT - START_BEAT) * P)
    if DROP_STYLE:                                                    # still land it on a real beat
        later = [float(b) for b in beats if b >= drop_t]
        drop_t = later[0] if later else drop_t
song_start = max(0.0, drop_t - (DROP_BEAT - START_BEAT) * P)
print(f'tempo {tempo:.1f} beat {P:.4f}s drop {drop_t:.2f}s start {song_start:.2f}s', flush=True)

# ---------------------------------------------------------------- 6. fill the template
tmpl = [tuple(map(int, l.split()[:2])) for l in open('template.txt')]
max_beats = START_BEAT + int(MAX_SECONDS / P)                         # keep every edit to its length, whatever the tempo
tmpl = [(a, min(b, max_beats)) for a, b in tmpl if START_BEAT <= a < max_beats]
if DROP_STYLE:                                                        # fast section: one cut on every beat from the drop
    tmpl = [(j, j + 1) for j in range(max(START_BEAT, DROP_BEAT), max_beats)]
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
    for s in ([] if DROP_STYLE else sorted(pool, key=lambda s: -s['calm'])[:90]):
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
if os.environ.get('BALANCE_EPS') == '1' and len({s['ep'] for s in pool}) > 1:   # multi-fight edit: spread the cuts over every episode
    by_ep = {}
    for s in sorted((s for s in pool if id(s) not in taken), key=lambda s: -s['impact']):
        by_ep.setdefault(s['ep'], []).append(s)
    top, qs = [], list(by_ep.values())
    while len(top) < k and any(qs):
        for q in qs:
            if q and len(top) < k:
                top.append(q.pop(0))
    print('balanced cuts per episode:', {e: sum(t['ep'] == e for t in top) for e in by_ep}, flush=True)
top.sort(key=lambda s: (s['ep'], s['s']))                            # story order through the fights
for i, s in zip(rest, top):
    assign[i] = s; taken.add(id(s))
if len(assign) < n:                                                   # small pool: never show the same footage twice
    print(f'pool short ({len(assign)}/{n}), filling without repeats', flush=True)
    sd = lambda i: (tmpl[i][1] - tmpl[i][0]) * P

    def shown(s, d):
        L = s['e'] - s['s']
        return (s['s'] + (L - d) / 2, s['s'] + (L + d) / 2) if L >= d else (s['s'], s['e'])
    on = {}
    for i, s in assign.items():
        on.setdefault(s['ep'], []).append(shown(s, sd(i)))
    free = lambda ep, a, b: all(b <= x - 0.3 or a >= y + 0.3 for x, y in on.get(ep, []))

    def unused_piece(s, d):                                           # a part of a long shot nobody has seen yet
        t = s['s']
        while t + d <= s['e'] + 1e-6:
            if free(s['ep'], t, t + d):
                return dict(s, s=round(t, 3), e=round(t + d, 3), orig=s.get('orig', s['s']))
            t += 0.25
        return None
    near = sorted((s for s in ep_all if id(s) not in taken and all(id(s) != id(p) for p in pool)),
                  key=lambda s: abs((s['s'] + s['e']) / 2 - (float(INCLUDE.rsplit('|', 2)[1]) if INCLUDE else s['s'])))
    for i in [x for x in range(n) if x not in assign]:
        d = sd(i); got = None
        for s in sorted(pool, key=lambda s: -s['impact']):            # 1. same fight, an unseen part of a long shot
            got = unused_piece(s, d)
            if got:
                break
        if got is None and not CHAR_NAME and not DROP_STYLE:                             # 2. the nearest unused shot (never with a topic: it may be someone else)
            for s in near:
                if id(s) not in taken and s['e'] - s['s'] >= min(d * 0.6, 2.0) and free(s['ep'], s['s'], s['e']):
                    got = s; taken.add(id(s))
                    _lo = min((p['impact'] for p in pool), default=0.0)
                    for k_, v_ in (('impact', _lo), ('calm', 0.0)):
                        got.setdefault(k_, v_)
                    break
        if got is not None:
            assign[i] = got; on.setdefault(got['ep'], []).append(shown(got, d))
    miss = [x for x in range(n) if x not in assign]
    if miss and DROP_STYLE:                                           # 3. drop edit: hold the pace, never a long static cut
        # 1 cut per beat for as long as the shots allow, then half-time (2 beats per cut) so no cut ever runs past
        # ~1 s; with very few shots the holds spread evenly over the whole edit instead
        shots_ = [assign[i] for i in sorted(assign)]
        m = len(shots_)
        b0, b1 = tmpl[0][0], tmpl[-1][1]
        total = b1 - b0
        if 2 * m >= total:
            lens = [1] * (2 * m - total) + [2] * (total - m)
        else:
            q, r_ = divmod(total, m)
            lens = [q + (1 if j < r_ else 0) for j in range(m)]
        new_t, t0 = [], b0
        for L in lens:
            new_t.append((t0, t0 + L)); t0 += L
        print(f'drop style: {m} shots for {total} beats -> {lens.count(1)} single-beat cuts, then holds of '
              f'{max(lens)} beats (no merge into long cuts)', flush=True)
        tmpl = new_t; assign = {i: s for i, s in enumerate(shots_)}; n = len(tmpl)
        second_drop = next((i for i, (a, b) in enumerate(tmpl) if a == 113), None)
        miss = []
    if miss:                                                          # 3. still short: let the previous cut run longer instead
        print('merging', len(miss), 'beats into the cut before them', flush=True)
        keep = [i for i in range(n) if i in assign]
        new_t, new_a = [], {}
        for i in range(n):
            if i in assign:
                new_t.append(list(tmpl[i])); new_a[len(new_t) - 1] = assign[i]
            elif new_t:
                new_t[-1][1] = tmpl[i][1]
        tmpl = [tuple(x) for x in new_t]; assign = new_a; n = len(tmpl)
        second_drop = next((i for i, (a, b) in enumerate(tmpl) if a == 113), None)
if len(assign) < n:
    sys.exit(f'not enough shots ({len(assign)}/{n})')
if DROP_STYLE and n > 3:                                              # pieces of one long shot never sit within 4 cuts of each other
    near_ = lambda x, y: x['ep'] == y['ep'] and x['s'] < y['e'] + 6 and y['s'] < x['e'] + 6   # (reads as a frozen hold / a repeat)
    SPACE = int(os.environ.get('DROP_REPEAT_SPACE', 4))
    clash = lambda shot, pos, skip: any(near_(shot, assign[x]) for x in range(pos - SPACE, pos + SPACE + 1)
                                        if 0 <= x < n and x != pos and x not in skip)
    for i in range(2, n):
        if any(near_(assign[i], assign[x]) for x in range(max(0, i - SPACE), i)):
            for j in list(range(i + 1, n)) + list(range(1, i - 1)):
                if not clash(assign[j], i, {i, j}) and not clash(assign[i], j, {i, j}):
                    assign[i], assign[j] = assign[j], assign[i]; break
    rep = sum(1 for i in range(1, n) if any(near_(assign[i], assign[x]) for x in range(max(0, i - SPACE), i)))
    print(f'drop style: {len({(s_["ep"], s_.get("orig", s_["s"])) for s_ in assign.values()})} distinct shots for {n} cuts, '
          f'{rep} cuts still within {SPACE} of a piece of the same shot', flush=True)
if DROP_STYLE and n > 2:                                              # end on the finisher, not on whatever came last
    fin = max(range(1, n), key=lambda i: assign[i]['impact'])
    assign[fin], assign[n - 1] = assign[n - 1], assign[fin]
impact_cut = np.percentile([s['impact'] for s in pool], 85)

# ---------------------------------------------------------------- 7. render
fr = lambda j: round((j - START_BEAT) * P * FPS)
drop_i = next(i for i, (a, b) in enumerate(tmpl) if a == DROP_BEAT)
kinds = default_transition_pattern(n, drop_i)
if second_drop:
    kinds[second_drop - 1] = 'flash'
fxl = pair_transitions(n, kinds)
if DROP_STYLE:                                                        # the drop: 3-stage flash + punch-in on the very first cut
    for f_ in ('flash', 'punch'):
        if f_ not in fxl[drop_i]:
            fxl[drop_i].append(f_)
    heavy_cut = float(np.percentile([assign[i].get('peak', 0) for i in range(n)], 65))   # heavy hits: top third by peak motion
os.makedirs('segfx', exist_ok=True)
jobs, plan = [], []
for k_, (a, b) in enumerate(tmpl):
    s = assign[k_]
    nf = fr(b) - fr(a); dur = nf / FPS
    fx = list(fxl[k_])
    if DROP_STYLE:                                                    # pulse on every beat, shake + RGB split on the heavy hits
        fx.append('pulse')
        if k_ == drop_i or s.get('peak', 0) >= heavy_cut:
            fx.append('shake')
    elif a < DROP_BEAT or 109 <= a < 113:
        fx.append('drift')
    elif b - a >= 2:
        fx.append('pulse')
    if not DROP_STYLE and s['impact'] >= impact_cut and a >= DROP_BEAT:
        fx.append('shake')
    L = s['e'] - s['s']; spd = 1.0
    if L >= dur:
        st = s['s'] + (L - dur) / 2
    else:
        st = s['s']; spd = max(0.5, L / dur)
    vf = build_shot_fx(dur, W, H, fx, beat=P, speed=spd)
    vf += ',eq=contrast=1.12:saturation=1.18:gamma=0.97,vignette=PI/5'
    if k_ == n - 1:
        fd = min(0.6, dur * 0.5); vf += f',fade=out:st={max(0.0, dur - fd):.2f}:d={fd:.2f}'
    plan.append(dict(beats=[a, b], ep=s['ep'], start=round(st, 3), fx=fx, speed=round(spd, 3)))
    jobs.append(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{st:.3f}', '-i', SRC(s['ep']), '-an',
                 '-vf', vf, '-frames:v', str(nf), '-r', str(FPS), '-fps_mode', 'cfr',
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', f'segfx/{k_:03d}.mp4'])
json.dump(dict(pick=PICK, anime=series, song=song, episodes=eps, tempo=tempo, song_start=song_start, drop_t=drop_t,
               style='drop' if DROP_STYLE else 'template', impact_pct=purity_pct, character=CHAR_NAME, plan=plan),
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
name = OUT_NAME or (re.sub(r'[^A-Za-z0-9]+', '_', title.title()) + f'_AMV_{song}')
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
