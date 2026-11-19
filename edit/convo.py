"""Conversation-first Shorts, styled like AOT EDIT's "Reze's battle iq":
   1.5 s cold-open hook  ->  ~30-40 s of a real character conversation with burned-in captions
   (white, all-caps extra-bold, soft glow whose colour follows the speaker, word-by-word reveal)
   ->  ~20 s beat-synced AMV cut from the same episodes.   3:4 (1080x1440).

Steps
  1. pick anime + 3 episodes (newest / least used, like auto.py) from the Drive folder
  2. of the 3 episodes take the one with the biggest fight (motion + glowing power effects over 90 s)
     and transcribe the fight itself with faster-whisper (translated to English when needed)
  3. choose a 14-27 s stretch where characters talk WHILE the action is on screen, ending only once
     the speaker has finished (sentence end + pause); the anime's own music is removed (demucs vocals)
  4. split it into lines of <= 6 words, guess speakers from voice (pitch + timbre clustering)
  5. render the conversation shot by shot with a face-following 9:16 crop, captions burned in
  6. run auto.py for the AMV part (same episodes, conversation shots excluded), then join
"""
import json, os, random, re, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE); sys.path.insert(0, HERE)
from drive_index import library

W, H, FPS = 1080, int(os.environ.get("OUT_H", 1440)), 30          # 3:4 by default (1080x1440)
TOTAL = float(os.environ.get('TOTAL_SECONDS', 59))
CMIN, CMAX = float(os.environ.get('CONV_MIN', 14)), float(os.environ.get('CONV_MAX', 27))   # short talk, long edit
HOOK = 1.5
PICK = (os.environ.get('PICK') or 'auto').strip().lower()
SEED = int(os.environ.get('SEED', time.time())); rng = random.Random(SEED)
COLORS = ['#FF3B5C', '#3DFF7A', '#B266FF', '#33D6FF', '#FFC533']      # pink-red, green, purple, cyan, gold
FONT = os.environ.get('CAPTION_FONT', 'Montserrat ExtraBold')
os.makedirs('src', exist_ok=True); os.makedirs('work/convo', exist_ok=True); os.makedirs('../out', exist_ok=True)
EPISODES, LIB_SRC = library()
hist = json.load(open('history.json')) if os.path.exists('history.json') else {}
SRC = lambda code: 'src/' + code.replace(':', '__') + '.mp4'


def sh(cmd, binary=False):
    r = subprocess.run(cmd, capture_output=True, text=not binary)
    if r.returncode:
        raise RuntimeError(' '.join(map(str, cmd[:8])) + '\n' + (r.stderr[-1500:] if not binary else r.stderr[-1500:].decode(errors='ignore')))
    return r.stdout


def least_used(options, counts, k):
    opts = list(options); rng.shuffle(opts); opts.sort(key=lambda o: counts.get(o, 0)); return opts[:k]


def fetch(code):
    dst = SRC(code)
    if os.path.exists(dst) and os.path.getsize(dst) > 10_000_000:
        return dst
    for _ in range(3):
        subprocess.run([sys.executable, '-m', 'gdown', EPISODES[code]['drive_id'], '-O', dst, '-q'])
        if os.path.exists(dst) and os.path.getsize(dst) > 10_000_000:
            return dst
    raise SystemExit(f'download failed {code}')


def duration(p):
    return float(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


# ------------------------------------------------------------------ 1. choose
series_all = sorted({v['series'] for v in EPISODES.values()})
known = set(hist.get('known', []))
new_eps = sorted(k for k in EPISODES if k not in known) if 'known' in hist else []
match = [s for s in series_all if PICK != 'auto' and (s == PICK or s.startswith(PICK.replace(' ', '-')) or PICK.replace(' ', '-') in s)]
chars = json.load(open('characters.json'))
chars = {c: [e if ':' in e else f'jujutsu-kaisen:{e}' for e in v] for c, v in chars.items()}
used_eps = {(k if ':' in k else f'jujutsu-kaisen:{k}'): v for k, v in hist.get('episodes', {}).items()}
for c in hist.get('convos', []):
    used_eps[c['ep']] = used_eps.get(c['ep'], 0) + 2                  # conversation episodes rest longer
if PICK in chars:
    cand = [e for e in chars[PICK] if e in EPISODES]
else:
    series = match[0] if match else (EPISODES[new_eps[0]]['series'] if new_eps else least_used(series_all, hist.get('series', {}), 1)[0])
    cand = [k for k, v in EPISODES.items() if v['series'] == series]
fresh = [e for e in new_eps if e in cand][:3]
eps = fresh + least_used([e for e in cand if e not in fresh], used_eps, 3 - len(fresh))
SF, SW, SH_ = 4, 64, 36
def motion(src):
    raw = sh(['ffmpeg', '-nostdin', '-v', 'error', '-i', src, '-vf', f'fps={SF},scale={SW}:{SH_}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], binary=True)
    f = np.frombuffer(raw, np.uint8).reshape(-1, SH_, SW, 3).astype(np.float32)
    g = f.mean(axis=3)
    mot = np.concatenate([[0], np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))])
    sat = f.max(axis=3) - f.min(axis=3)                                 # glowing auras / power effects are bright and saturated
    glow = ((sat > 90) & (f.max(axis=3) > 170)).mean(axis=(1, 2)) * 40
    n = len(mot) // SF
    THUMBS[src] = g[:n * SF:SF].reshape(n, 9, 4, 16, 4).mean(axis=(2, 4)).reshape(n, -1)   # one 16x9 picture per second
    return np.array([mot[i * SF:(i + 1) * SF].mean() + glow[i * SF:(i + 1) * SF].mean() for i in range(n)])


# ------------------------------------------------------------------ 1b. opening / ending songs: never talk inside them
# (Gojo run 44242818226 took S2E03 231-259 s, inside the opening at 186-273 s). Known ranges come from history
# (auto.py's detection); new episodes are matched picture-by-picture against an episode with the same opening.
THUMBS = {}
SONG_PAD = 3.0


def op_group(code):                                                   # same rule as auto.py
    v = EPISODES[code]; se, ep = v['season'], v['ep']
    if v['series'] == 'jujutsu-kaisen' and se == 2:
        return (v['series'], se, 0 if ep <= 5 else 1)
    return (v['series'], se, (ep - 1) // 13)


def _norm_ranges(w):
    if not w:
        return []
    if not isinstance(w[0], (list, tuple)):
        w = [w]
    return [(float(a), float(b)) for a, b in w]


def _shared_runs(a, b):
    """stretches of episode a whose pictures also appear in episode b (opening, ending, recap)"""
    A, B = THUMBS.get(SRC(a)), THUMBS.get(SRC(b))
    if A is None or B is None:
        return []
    Bv = B[B.std(axis=1) > 10]                                       # flat / black seconds match anything
    if not len(Bv):
        return []
    hits = [t for t in np.where(A.std(axis=1) > 10)[0] if np.abs(Bv - A[t]).mean(axis=1).min() < 5]
    runs, grp = [], []
    for h in hits + [10 ** 9]:
        if grp and h - grp[-1] > 8:
            if len(grp) >= 12 and grp[-1] - grp[0] >= 20:
                runs.append([round(float(grp[0]) - 4.0, 1), round(float(grp[-1]) + 5.0, 1)])
            grp = []
        grp.append(h)
    return runs


def song_ranges(ep):
    """opening / ending ranges of an episode (seconds), from history or detected now and remembered"""
    known = _norm_ranges(hist.get('openings2', {}).get(ep))
    if known:
        return known
    peers = [o for o in eps if o != ep and SRC(o) in THUMBS and op_group(o) == op_group(ep)]
    if not peers:
        sib = sorted((o for o in EPISODES if o != ep and op_group(o) == op_group(ep)),
                     key=lambda o: abs(EPISODES[o]['ep'] - EPISODES[ep]['ep']))[:1]
        for o in sib:
            try:
                fetch(o); motion(SRC(o)); peers.append(o)
            except BaseException as ex:                               # a missing sibling must not kill the run
                print('opening reference failed', o, ex, flush=True)
    found = []
    for o in peers:
        found += _shared_runs(ep, o)
    found = sorted(found)
    merged = []
    for a, b in found:
        if merged and a <= merged[-1][1] + 5:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    if peers:
        print(ep, 'opening/ending (matched against', peers[0] + ')', merged, flush=True)
    if merged:
        try:                                                          # auto.py reads the same cache
            h_ = json.load(open('history.json'))
            h_.setdefault('openings2', {})[ep] = merged
            json.dump(h_, open('history.json', 'w'), indent=1)
            hist.setdefault('openings2', {})[ep] = merged
        except Exception as ex:
            print('could not cache opening', ex, flush=True)
    return [tuple(r) for r in merged]


def song_mask(ep, dur_):
    m = np.zeros(int(dur_) + 2, bool)
    for a, b in song_ranges(ep):
        m[max(0, int(a - SONG_PAD)):max(0, int(b + SONG_PAD) + 1)] = True
    return m

# ------------------------------------------------------------------ 2. pick the episode with the biggest fight, find it
FW = 90
best_all = None
motions = {}
for ep in eps:
    fetch(ep)
    motions[ep] = (duration(SRC(ep)), motion(SRC(ep)))
SONGS = {}
for ep in eps:
    d_, ps = motions[ep]
    SONGS[ep] = song_mask(ep, d_)
    lo_, hi_ = 150, int(d_) - 150                                        # skip openings and the ending/preview
    prev = [(c['s'], c['e']) for c in hist.get('convos', []) if c['ep'] == ep]
    for t in range(lo_, hi_ - FW, 5):
        if any(a_ - FW < t < b_ for a_, b_ in prev) or SONGS[ep][t:t + FW].mean() > 0.2:
            continue
        v = ps[t:t + FW].mean()
        if best_all is None or v > best_all[0]:
            best_all = (v, ep, t, ps, d_)
    print(f'{ep} peak fight {max(ps[lo_:hi_].tolist() or [0]):.1f}', flush=True)
_, conv_ep, fight, per_s, dur = best_all
eps = [conv_ep] + [e for e in eps if e != conv_ep]
src = SRC(conv_ep)
lo, hi = 150, int(dur) - 150
mref = np.percentile(per_s[lo:hi], 90) + 1e-6
# scan the whole episode for speech, then take the stretch where they talk the most WHILE fighting
from faster_whisper import WhisperModel
import soundfile as _sf
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(lo), '-t', str(hi - lo), '-i', src, '-vn', '-ac', '1', '-ar', '16000', 'work/convo/full.wav'])
_scan = WhisperModel('small', device='cpu', compute_type='int8')
_ss, _ = _scan.transcribe(_sf.read('work/convo/full.wav', dtype='float32')[0], beam_size=1, vad_filter=True)
speech = np.zeros(int(dur) + 1)
SONG = SONGS[conv_ep]
_ss = list(_ss)
_key = lambda t_: re.sub(r'[\W_]+', '', (t_ or '').lower())          # letters only (kana / kanji kept)
_seen = {}
for sg in _ss:
    if len(_key(sg.text)) >= 10:
        _seen[_key(sg.text)] = _seen.get(_key(sg.text), 0) + 1
sung = []                                                             # lyrics: music notes, or a long line heard twice (a chorus)
for sg in _ss:
    if any(c in (sg.text or '') for c in '♪♫🎵') or _seen.get(_key(sg.text), 0) >= 2:
        sung.append((lo + sg.start, lo + sg.end))
for a_, b_ in sung:
    SONG[max(0, int(a_) - 2):int(b_) + 3] = True
for k_ in range(len(sung) - 2):                                       # three sung lines within 40 s: a song, block all of it
    if sung[k_ + 2][1] - sung[k_][0] <= 40:
        SONG[max(0, int(sung[k_][0]) - 2):int(sung[k_ + 2][1]) + 3] = True
if sung:
    print(f'singing / lyric segments in {conv_ep}: {len(sung)}', flush=True)
print(f'{conv_ep} song seconds excluded from the talk: {int(SONG.sum())}', flush=True)
for sg in _ss:
    if len((sg.text or '').split()) >= 3 and sg.avg_logprob > -1.0 and sg.no_speech_prob < 0.6:
        speech[int(lo + sg.start):int(lo + sg.end) + 1] = 1
speech[SONG[:len(speech)]] = 0
SKIP = [float(x) for x in os.environ.get('CONVO_SKIP', '').split(',') if x]
prevc = [(c['s'], c['e']) for c in hist.get('convos', []) if c['ep'] == conv_ep]
bs, bt = -1, fight
_cands = []
for t in range(lo, hi - 40, 2):
    if any(a_ - 40 < t < b_ for a_, b_ in prevc) or any(abs(t - k) < 40 for k in SKIP) or SONG[max(0, t - 2):t + 27].any():
        continue
    talk = speech[t:t + 24].mean()
    if talk < 0.45:
        continue
    act = per_s[t:t + 24].mean() / mref
    sc = 0.6 * talk + 1.5 * min(act, 1.3)
    _cands.append((sc, t))
    if sc > bs:
        bs, bt = sc, t
LORE_ALL = json.load(open('lore.json')) if os.path.exists('lore.json') else {}
_SKIP_SONG = lambda t_: bool(SONG[min(len(SONG) - 1, max(0, int(t_)))])
PICK_NAME = None                                                      # a character pick: their full name in lore.json
if PICK in chars:
    PICK_NAME = next((nm for nm, d in LORE_ALL.get(EPISODES[conv_ep]['series'], {}).items()
                      if PICK in [a.lower() for a in d.get('names', [])] or PICK == nm.lower()), None)
if PICK_NAME and _cands and os.environ.get('CONVO_IDENT_PICK', '1') == '1':
    # a character pick talks in a scene that is visibly about them: of the 5 best talk moments (30+ s apart) the best
    # one where identify() puts the character on top wins; none of them -> the best-scoring moment as before
    try:
        import charvis
        _top = []
        for sc_, t_ in sorted(_cands, reverse=True):
            if all(abs(t_ - u) >= 30 for _, u in _top):
                _top.append((sc_, t_))
            if len(_top) >= 5:
                break
        for sc_, t_ in _top:
            r_ = charvis.identify(src, t_, t_ + 24, EPISODES[conv_ep]['series'], lo, hi, skip=_SKIP_SONG,
                                  expected=(PICK_NAME,), target=PICK_NAME, log=lambda m: print('identify:', m, flush=True))
            print(f'talk candidate {t_}s (score {sc_:.2f}): {PICK_NAME} votes {r_.get("target_share", 0):.0%}, '
                  f'top {"yes" if r_.get("target_top") else "no"}', flush=True)
            if r_.get('target_top'):
                if t_ != bt:
                    print(f'talk moment {bt}s -> {t_}s: {PICK_NAME} is on screen there', flush=True)
                bs, bt = sc_, t_
                break
        else:
            print(f'no talk candidate shows {PICK_NAME} on top; keeping the best-scoring moment {bt}s', flush=True)
    except Exception as ex:
        print('talk candidate identification skipped:', ex, flush=True)
fight = bt
win0, win1 = max(lo, bt - 12), min(hi, bt + 52)
print('conversation from', conv_ep, f'| talking fight at {bt}s (score {bs:.2f}), transcribing {win0}-{win1}s', flush=True)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(win0), '-t', str(win1 - win0), '-i', src, '-vn', '-ac', '1', '-ar', '16000', 'work/convo/win.wav'])

from faster_whisper import WhisperModel
model = WhisperModel(os.environ.get('WHISPER', 'small'), device='cpu', compute_type='int8')
import soundfile as _sf
audio16 = _sf.read('work/convo/win.wav', dtype='float32')[0]
segs, info = model.transcribe(audio16, beam_size=3, word_timestamps=True, vad_filter=True)
segs = list(segs)
task = 'transcribe'
if True:                                                              # anime is Japanese audio; detection is fooled by music                                             # Japanese audio: English captions
    task = 'translate'
    model = WhisperModel(os.environ.get('WHISPER_TRANSLATE', 'medium'), device='cpu', compute_type='int8')
    segs = list(model.transcribe(audio16, task='translate', language='ja', beam_size=3, word_timestamps=True, vad_filter=True)[0])
if len(segs) < 3:                                                     # misdetected (music) or VAD ate it: force Japanese -> English
    task = 'translate'
    segs = list(model.transcribe(audio16, task='translate', language='ja', beam_size=3, word_timestamps=True, vad_filter=False)[0])
    segs = [sg for sg in segs if getattr(sg, 'no_speech_prob', 0) < 0.6 and len((sg.text or '').split()) >= 2]
print('language', info.language, task, len(segs), 'segments', flush=True)
words = []
for sg in segs:
    text = (sg.text or '').strip()
    if not text:
        continue
    ws = [w for w in (sg.words or []) if w.word.strip()]
    if task == 'transcribe' and ws:                                   # real word timings; glue split tokens back together
        for w in ws:
            if words and not w.word.startswith(' ') and words[-1]['seg'] == id(sg):
                words[-1]['w'] += w.word.strip(); words[-1]['e'] = win0 + max(w.end, w.start + 0.05)
            else:
                words.append(dict(w=w.word.strip(), s=win0 + w.start, e=win0 + max(w.end, w.start + 0.12), seg=id(sg)))
    else:                                                             # translation: full sentence, timing spread over the line
        toks = text.split()
        a0, a1 = (ws[0].start, ws[-1].end) if ws else (sg.start, sg.end)
        a1 = max(a1, a0 + 0.3 * len(toks))
        wts = np.cumsum([0] + [len(t) + 2 for t in toks]); wts = wts / wts[-1]
        for k, t in enumerate(toks):
            words.append(dict(w=t, s=win0 + a0 + (a1 - a0) * wts[k], e=win0 + a0 + (a1 - a0) * wts[k + 1], seg=id(sg)))
words = [w for w in words if not SONG[min(len(SONG) - 1, int(w['s']))] and not SONG[min(len(SONG) - 1, int(w['e']))]]
if len(words) < 12:
    if len(SKIP) >= 4:
        raise SystemExit('not enough dialogue in the fight')
    print('too little dialogue there, trying the next fight moment', flush=True)
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])

# ------------------------------------------------------------------ 3. densest stretch of dialogue
starts = [i for i, w in enumerate(words) if i == 0 or words[i - 1]['w'][-1:] in '.?!' or w['s'] - words[i - 1]['e'] > 0.8]
best, pick = -1, None
for i in starts:
    for j in range(i + 6, len(words)):
        L = words[j]['e'] - words[i]['s']
        if L > CMAX:
            break
        # only end where the character has finished: sentence end AND a real pause (or nothing after)
        done = words[j]['w'][-1:] in '.?!' and (j == len(words) - 1 or words[j + 1]['s'] - words[j]['e'] > 0.7)
        if L < CMIN or not done:
            continue
        if SONG[max(0, int(words[i]['s'] - 0.35)):int(words[j]['e'] + 0.8) + 1].any():   # never across an opening/ending
            continue
        talk = sum(w['e'] - w['s'] for w in words[i:j + 1]) / L
        act = per_s[int(words[i]['s']):int(words[j]['e']) + 1].mean() / mref    # action on screen while they talk
        score = 1.0 * talk + 0.08 * (j - i) / L + 1.0 * min(act, 1.3)
        if score > best:
            best, pick = score, (i, j)
if pick is None:
    i = starts[0]
    ends = [k for k in range(len(words)) if words[k]['e'] - words[i]['s'] <= CMAX and words[k]['w'][-1:] in '.?!']
    j = max(ends) if ends else max(k for k in range(len(words)) if words[k]['e'] - words[i]['s'] <= CMAX)
    pick = (i, j)
cw = words[pick[0]:pick[1] + 1]
c0 = max(win0, cw[0]['s'] - 0.35); c1 = min(win1, cw[-1]['e'] + 0.8)
c0 = round(c0 * FPS) / FPS; c1 = round(c1 * FPS) / FPS
CONV = c1 - c0
if SONG[max(0, int(c0)):int(c1) + 1].any():                           # fallback stretch touched an opening/ending: next moment
    if len(SKIP) >= 4:
        raise SystemExit('every conversation candidate sits in an opening/ending song')
    print(f'conversation {c0:.1f}-{c1:.1f}s touches an opening/ending, trying the next fight moment', flush=True)
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
if CONV < CMIN * 0.6:                                                 # too thin to be a conversation: next fight moment
    if len(SKIP) >= 4:
        raise SystemExit('no real conversation found in the fights')
    print(f'conversation only {CONV:.1f}s, trying the next fight moment', flush=True)
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
print(f'conversation {c0:.2f}-{c1:.2f}s ({CONV:.1f}s, {len(cw)} words)', flush=True)

# ------------------------------------------------------------------ 4. caption lines + speakers
lines, cur = [], []
for k, w in enumerate(cw):
    if cur and (len(cur) >= 5 or sum(len(x['w']) for x in cur) >= 22 or w['s'] - cur[-1]['e'] > 0.6 or w['seg'] != cur[-1]['seg'] or
                (cur[-1]['w'][-1:] in '.?!,' and len(cur) >= 3)):
        lines.append(cur); cur = []
    cur.append(w)
if cur:
    lines.append(cur)

import librosa
y, sr = librosa.load('work/convo/win.wav', sr=16000)
feats = []
for ln in lines:
    a, b = int((ln[0]['s'] - win0) * sr), int((ln[-1]['e'] - win0) * sr)
    seg = y[a:max(b, a + 1600)]
    f0 = librosa.yin(seg, fmin=70, fmax=500, sr=sr) if len(seg) > 2048 else np.array([150.0])
    mf = librosa.feature.mfcc(y=seg, sr=sr, n_mfcc=13).mean(axis=1) if len(seg) > 2048 else np.zeros(13)
    feats.append(np.concatenate([[np.log(np.median(f0)) * 6], mf[1:8] / 20]))
feats = np.array(feats)
spk = [0] * len(lines)
if len(lines) >= 4:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    X = (feats - feats.mean(0)) / (feats.std(0) + 1e-6)
    best_k, best_s = 1, 0.08
    for k in (2, 3):
        if len(lines) > k + 1:
            lab = KMeans(k, n_init=10, random_state=0).fit_predict(X)
            s = silhouette_score(X, lab)
            if s > best_s:
                best_k, best_s, spk = k, s, list(lab)
    if best_k == 1:                                                   # no clear voices: change colour on each turn
        spk = [0] * len(lines); c = 0
        for i in range(1, len(lines)):
            if lines[i][0]['seg'] != lines[i - 1][0]['seg'] and lines[i][0]['s'] - lines[i - 1][-1]['e'] > 0.5:
                c = (c + 1) % 3
            spk[i] = c
order = list(dict.fromkeys(spk))                                     # first speaker gets pink, next green ...
pal = COLORS[:]; rng.shuffle(pal[2:])
colour_of = {s: pal[order.index(s) % len(pal)] for s in order}


def ass_col(hexc, a='00'):
    r, g_, b = hexc[1:3], hexc[3:5], hexc[5:7]
    return f'&H{a}{b}{g_}{r}&'


def clean(t):
    return re.sub(r'[^\w\'?!.,-]', '', t).upper()


def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'


ass = [f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},98,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H96000000,0,0,0,0,100,100,3,0,1,0,3,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""]
DIM = '&H00A0A0A0&'
for li, ln in enumerate(lines):
    col = colour_of[spk[li]]
    t_end = min(ln[-1]['e'] + 0.35, lines[li + 1][0]['s'] if li + 1 < len(lines) else c1) - c0 + HOOK
    toks = [clean(w['w']) for w in ln]
    toks = [t for t in toks if t]
    if not toks:
        continue
    split = len(toks) if len(toks) <= 3 or sum(map(len, toks)) <= 14 else (len(toks) + 1) // 2
    for k in range(len(toks)):                                        # word-by-word: spoken white, the rest dim
        a = ln[min(k, len(ln) - 1)]['s'] - c0 + HOOK
        b = (ln[k + 1]['s'] - c0 + HOOK) if k + 1 < len(toks) and k + 1 < len(ln) else t_end
        if b <= a:
            continue
        parts = []
        for m, t in enumerate(toks):
            parts.append(('{\\1c&H00FFFFFF&}' if m <= k else '{\\1c' + DIM + '}') + t)
            if m == split - 1 and m != len(toks) - 1:
                parts.append('\\N')
            elif m != len(toks) - 1:
                parts.append(' ')
        txt = ''.join(parts).replace(' \\N', '\\N')
        pop = '{\\fscx106\\fscy106\\t(0,90,\\fscx100\\fscy100)}' if k == 0 else ''
        glow = f'{{\\pos({W // 2},{int(H * 0.53)})\\bord18\\blur16\\3c{ass_col(col)}\\3a&H20&\\shad0\\1a&HFF&}}'
        main = f'{{\\pos({W // 2},{int(H * 0.53)})\\bord4\\blur3\\3c{ass_col(col)}\\shad3}}'
        ass.append(f'Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{glow}{pop}{txt}')
        ass.append(f'Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{main}{pop}{txt}')
open('work/convo/captions.ass', 'w').write('\n'.join(ass) + '\n')
json.dump(dict(ep=conv_ep, s=c0, e=c1, lines=[dict(t=' '.join(w['w'] for w in ln), speaker=int(spk[i]), colour=colour_of[spk[i]])
                                               for i, ln in enumerate(lines)]), open('work/convo/convo.json', 'w'), indent=1)
print('captions', len(lines), 'lines,', len(set(spk)), 'speaker colours', flush=True)

# ------------------------------------------------------------------ 5. face-following 9:16 crop, shot by shot
raw = sh(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{c0:.3f}', '-t', f'{CONV:.3f}', '-i', src, '-vf',
          'fps=12,scale=64:36,format=gray', '-f', 'rawvideo', '-'], binary=True)
gg = np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.float32)
d = np.abs(np.diff(gg, axis=0)).mean(axis=(1, 2))
cuts = [0.0] + [(i + 1) / 12 for i in range(len(d)) if d[i] > max(18, 4 * np.median(d[max(0, i - 12):i + 12]))] + [CONV]
cuts = sorted(set(round(c * FPS) / FPS for c in cuts))
cuts = [c for k, c in enumerate(cuts) if k == 0 or c - cuts[k - 1] >= 0.3 or c == CONV]
iw, ih = map(int, sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', src]).strip().split(','))
try:
    import cv2
    casc = cv2.CascadeClassifier('lbpcascade_animeface.xml')
except Exception:
    casc = None
crop_w = ih * W / H                                                    # 9:16 window in source pixels
prev_x = 0.5
xs = []
for a, b in zip(cuts[:-1], cuts[1:]):
    cx = []
    for f in (0.3, 0.7):
        if casc is None:
            break
        t = c0 + a + (b - a) * f
        fr = np.frombuffer(sh(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1', '-vf',
                               'scale=640:360,format=gray', '-f', 'rawvideo', '-'], binary=True), np.uint8).reshape(360, 640)
        faces = casc.detectMultiScale(fr, 1.1, 3, minSize=(28, 28))
        if len(faces):
            x, y_, w, h = max(faces, key=lambda f_: f_[2] * f_[3])
            cx.append((x + w / 2) / 640)
    x = float(np.mean(cx)) if cx else 0.5
    xs.append(x)
os.makedirs('work/convo/seg', exist_ok=True)
lst = []
for k, ((a, b), x) in enumerate(zip(zip(cuts[:-1], cuts[1:]), xs)):
    nf = round(b * FPS) - round(a * FPS)
    if nf <= 0:
        continue
    left = min(max(x * iw - crop_w / 2, 0), iw - crop_w)
    vf = (f'crop={int(crop_w) // 2 * 2}:{ih}:{int(left)}:0,scale={W}:{H}:flags=lanczos,setsar=1,'
          f'eq=contrast=1.06:saturation=1.12,fps={FPS}')
    out = f'work/convo/seg/{k:03d}.mp4'
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{c0 + a:.3f}', '-i', src, '-an', '-vf', vf, '-frames:v', str(nf),
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', out])
    lst.append(out)
open('work/convo/seg/list.txt', 'w').write(''.join(f"file '{os.path.basename(p)}'\n" for p in lst))
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'work/convo/seg/list.txt', '-c', 'copy', 'work/convo/video.mp4'])

# ------------------------------------------------------------------ 5b. voices only: strip the anime's own music (copyright)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{c0:.3f}', '-t', f'{CONV:.3f}', '-i', src, '-vn', '-ac', '2', '-ar', '44100', 'work/convo/talk.wav'])
subprocess.run([sys.executable, '-m', 'demucs', '--two-stems=vocals', '-n', 'htdemucs', '-o', 'work/convo/sep', 'work/convo/talk.wav'], check=True)
VOICE = 'work/convo/sep/htdemucs/talk/vocals.wav'
print('voices separated from the anime music', flush=True)

# ------------------------------------------------------------------ 5c. identify the main character speaking in this scene
series_key = EPISODES[conv_ep]['series']
series_title = series_key.replace('-', ' ').title()
series_lore = LORE_ALL.get(series_key, {})


def lore_name(key, series):
    for nm, d in LORE_ALL.get(series, {}).items():
        if key in [a.lower() for a in d.get('names', [])] or key == nm.lower():
            return nm
    return None


def char_slug(nm, series):
    if not nm:
        return None
    d = LORE_ALL.get(series, {}).get(nm, {})
    for n in d.get('names', []):
        if n in chars:
            return n
    for part in nm.lower().split():
        if part in chars:
            return part
    clean = re.sub(r'\W+', '_', nm.lower()).strip('_')
    if clean in chars:
        return clean
    return clean


topic_name = None
topic_slug = None

# 1. If explicit PICK matches a character slug
if PICK in chars:
    topic_slug = PICK
    topic_name = lore_name(topic_slug, series_key) or topic_slug.title()

# 2. who the scene is about: charvis.identify() - a frame every 0.75 s, each votes for its best character
#    (name / look / stills, z-scored against frames every 25 s of the same episode). Always run and logged, so a
#    character pick shows whether the talk really features them.
IDENT = {}
try:
    import charvis
    IDENT = charvis.identify(src, c0, c1, series_key, lo, hi, skip=_SKIP_SONG, expected=(PICK_NAME,) if PICK_NAME else (),
                             target=PICK_NAME, series_title=series_title, log=lambda m: print('identify:', m, flush=True))
    print(f'identify votes for the talk {c0:.1f}-{c1:.1f}s: {IDENT.get("votes")} of {IDENT.get("frames")} frames '
          f'-> {IDENT.get("name") or "unsure"}' + (f' ({PICK_NAME} share {IDENT.get("target_share")})' if PICK_NAME else ''), flush=True)
    if not topic_name and IDENT.get('name'):
        topic_name = IDENT['name']
        topic_slug = char_slug(topic_name, series_key)
        print('conversation character from identify():', topic_name, flush=True)
except Exception as ex:
    print('identify() skipped:', ex, flush=True)

# 3. names said in the subtitles / transcript (lore.json, else the cast the research step found)
if not topic_name:
    context_txt = ' '.join(w['w'] for w in cw).lower()
    heard = {}
    _names = {nm: d.get('names', []) for nm, d in series_lore.items()}
    if not _names:
        try:
            import research
            research.get_series(series_key, EPISODES)
            _names = research.character_names(series_key)
        except Exception as ex:
            print('research names skipped:', ex, flush=True)
    for nm, al in _names.items():
        n = sum(len(re.findall(r'\b' + re.escape(a.lower()) + r'\b', context_txt)) for a in al)
        if n: heard[nm] = n
    if heard:
        topic_name = max(heard, key=heard.get)
        topic_slug = char_slug(topic_name, series_key)
        print('conversation character from the transcript:', heard, flush=True)

# 4. a main character of the series (research_cache.json): the one identify() voted for most, else the main whose
#    researched fights include this episode
if not topic_name:
    try:
        _rc = json.load(open('research_cache.json')).get(series_key, {}).get('characters', {})
        mains = [nm for nm, d in _rc.items() if (d.get('role') or '').lower() == 'main']
        _v = IDENT.get('votes') or {}
        voted = [nm for nm in mains if _v.get(nm)]
        if voted:
            topic_name = max(voted, key=lambda nm: _v[nm])
        else:
            here = [(max([r.get('score', 0) for r in _rc[nm].get('ranked', []) if r.get('ep') == conv_ep] or [0]), nm) for nm in mains]
            here = [x for x in here if x[0] > 0]
            if here:
                topic_name = max(here)[1]
        if topic_name:
            topic_slug = char_slug(topic_name, series_key)
            print('conversation character from the researched main cast:', topic_name, flush=True)
    except Exception as ex:
        print('research main characters skipped:', ex, flush=True)

# 5. last resort: the old 4-frame best reference match
if not topic_name:
    try:
        import charvis
        bk = charvis.bank(series_key)
        times = [c0 + (c1 - c0) * fr for fr in (0.2, 0.4, 0.6, 0.8)]
        ims = [charvis.frame(src, t) for t in times]
        ims = [im for im in ims if im is not None]
        if ims and bk.whole:
            E = charvis.embed_images(ims)
            scores = {n: float((bk.whole[n] @ E.T).max()) for n in bk.whole}
            for im in ims:
                fc = charvis.faces(im)
                if fc:
                    F = charvis.embed_images(fc)
                    for n in bk.face:
                        scores[n] = max(scores.get(n, 0), float((bk.face[n] @ F.T).max()))
            if scores:
                top_char = max(scores, key=scores.get)
                if scores[top_char] >= 0.20:
                    topic_name = top_char
                    topic_slug = char_slug(topic_name, series_key)
                    print('conversation character from the 4-frame reference match:', topic_name, flush=True)
    except Exception as ex:
        print('charvis conversation identification skipped:', ex, flush=True)

print(f'conversation character identified: {topic_name} ({topic_slug})', flush=True)

# Update convo.json with identified character
try:
    cinfo = json.load(open('work/convo/convo.json'))
    cinfo.update(character=topic_slug, character_name=topic_name)
    json.dump(cinfo, open('work/convo/convo.json', 'w'), indent=1)
except Exception:
    pass

# Fetch up to 3 distinct fight episodes for this character from characters.json
fight_eps = [e for e in chars.get(topic_slug, []) if e in EPISODES] if topic_slug else []
try:                                                                  # hand-checked fight windows first, when this character has them
    _fw = json.load(open('fight_windows.json')).get(topic_slug or '', {})
    _fw = [e if ':' in e else f'jujutsu-kaisen:{e}' for e in _fw]
except Exception as ex:
    print('fight_windows.json skipped:', ex, flush=True)
    _fw = []
_researched = []
try:                                                                  # self-research: the episodes where this character fights
    import research
    _researched, _rinfo = research.fight_episodes(series_key, topic_name, topic_slug, EPISODES)
    if _researched:
        _top = _researched[:6]                                       # strongest researched fights, the ones the character map confirms first
        _researched = [e for e in _top if e in fight_eps] + [e for e in _top if e not in fight_eps] + _researched[6:]
        print('research: fight episodes for', topic_name or topic_slug, '->', _researched[:6], flush=True)
except Exception as ex:
    print('research skipped:', ex, flush=True)
fight_eps = list(dict.fromkeys([e for e in _fw if e in EPISODES] + _researched + fight_eps))
amv_eps = list(dict.fromkeys([conv_ep] + fight_eps[:3])) if fight_eps else [conv_ep]
print('fight episodes for the edit:', amv_eps, flush=True)
for ep_code in amv_eps:
    try:
        fetch(ep_code)
    except Exception as ex:
        print(f'fetch failed for fight ep {ep_code}:', ex, flush=True)

# ------------------------------------------------------------------ 6. the AMV part (auto.py), then join
amv_len = max(14.0, TOTAL - HOOK - CONV)
env = dict(os.environ,
           FORCE_EPS=','.join(amv_eps),
           INCLUDE='',
           START_BEAT='17', MAX_SECONDS=f'{amv_len:.2f}', W=str(W), H=str(H),
           AMV_STYLE='drop',                                        # the edit opens ON the drop (beat 17), one cut per beat
           MIN_SONG_START=f'{CONV + 0.6:.2f}',                      # room before the drop for the song bed under the talk
           EXCLUDE=f'{conv_ep}|{c0}|{c1}', OUT_NAME='_amv_part', PICK=PICK,
           CHAR_NAME=topic_name or '',
           CHAR_SLUG=topic_slug or '',
           CHAR_SERIES=series_title,
           CHAR_ACT_MIN='0.0',
           CHAR_REL_MIN='0.04',
           CHAR_MIN_IDENT='6',
           CHAR_MIN_SHOTS='20')
subprocess.run([sys.executable, 'auto.py'], env=env, check=True)
amv = '../out/_amv_part.mp4'
plan = json.load(open('work/edit_plan.json'))
P = 60.0 / plan['tempo']
amv_dur = duration(amv)
hook_at = min(max(0.0, amv_dur - HOOK - 0.7), 16 * P)                 # cold open from mid-fight, so the drop itself stays fresh
name = re.sub(r'[^A-Za-z0-9]+', '_', EPISODES[conv_ep]['series'].title()) + '_convo_' + plan['song']
# the same song plays quietly under the conversation and runs straight into the edit at full volume
BED_VOL = float(os.environ.get('BED_VOL', '0.22'))
song_file = f"music/{plan['song']}.mp3"
song_len = duration(song_file)
def _busy_part(path, length):                                        # the steadiest loud stretch of the song (no silent intro/outro/break)
    import librosa as _lb
    yy, ss = _lb.load(path, sr=11025, mono=True)
    hop = ss // 2
    r = _lb.feature.rms(y=yy, frame_length=hop * 2, hop_length=hop)[0]
    n = max(1, int(length * 2))
    if len(r) <= n:
        return 0.0
    score = [np.percentile(r[i:i + n], 15) for i in range(0, len(r) - n)]
    return float(np.argmax(score)) / 2
drop_at = float(plan.get('drop_t', plan['song_start']))
bed_ss = drop_at - CONV                                              # the bed is the lead-in, so the talk ends exactly on the drop
if bed_ss < 0:
    bed_ss = _busy_part(song_file, CONV + 0.5)                       # song too short before its drop: old behaviour
    print('song has no room before the drop, bed from its busiest part', flush=True)
print(f'song bed from {bed_ss:.1f}s', flush=True)
fc = (
    f"[0:v]trim={hook_at:.3f}:{hook_at + HOOK:.3f},setpts=PTS-STARTPTS,fps={FPS}[hv];"
    f"[0:a]atrim={hook_at:.3f}:{hook_at + HOOK:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={HOOK - 0.25}:d=0.25,volume=0.8[ha];"
    f"[1:v]setpts=PTS-STARTPTS,fps={FPS},ass=work/convo/captions_shift.ass[cv];"
    f"[2:a]asetpts=PTS-STARTPTS,loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo[dl];"
    f"[3:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={BED_VOL},afade=t=in:d=0.4[bd];"
    f"[dl][bd]amix=inputs=2:duration=first:normalize=0[ca];"
    f"[0:v]setpts=PTS-STARTPTS,fps={FPS}[av];[0:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[aa];"
    f"[hv][ha][cv][ca][av][aa]concat=n=3:v=1:a=1[v][a]"
)
# captions were timed from the start of the short (hook included); the conversation clip starts at 0
txt = open('work/convo/captions.ass').read()
txt = re.sub(r'(\d+:\d\d:\d\d\.\d\d)', lambda m: ts(max(0, sum(float(x) * f for x, f in zip(m.group(1).split(':'), (3600, 60, 1))) - HOOK)), txt)
open('work/convo/captions_shift.ass', 'w').write(txt)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', amv, '-i', 'work/convo/video.mp4',
    '-i', VOICE,
    '-ss', f'{bed_ss:.3f}', '-t', f'{CONV + 0.5:.3f}', '-i', song_file,
    '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'../out/{name}.mp4'])
os.remove(amv)
print('wrote', f'out/{name}.mp4', flush=True)

hist = json.load(open('history.json'))
hist.setdefault('convos', []).append(dict(ep=conv_ep, s=c0, e=c1, file=f'{name}.mp4', time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
json.dump(hist, open('history.json', 'w'), indent=1)
