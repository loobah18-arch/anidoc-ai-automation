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
TOTAL = float(os.environ.get('TOTAL_SECONDS', 42))                   # sweet spot: ~20 s talk with full context + ~22 s edit (was 59)
MAXGAP = float(os.environ.get('CONV_MAXGAP', 6))                   # most screen time a cut inside the talk may skip
CMIN, CMAX = float(os.environ.get('CONV_MIN', 16)), float(os.environ.get('CONV_MAX', 26))   # talk carries the whole story; edit can be short
HOOK = float(os.environ.get('CONVO_HOOK', 0))                      # no cold open: the talk starts the Short at 0 s (set 1.5 for the old phonk hook)
PICK = (os.environ.get('PICK') or 'auto').strip().lower()
SEED = int(os.environ.get('SEED', time.time())); rng = random.Random(SEED)
os.environ['SEED'] = str(SEED)                                       # a re-run (next talk moment / episode) sees the same episodes
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
    # the talk must come from an episode the pick really fights in: chars.json put Sukuna in JJK S2E14 (Toji / Mei Mei vs
    # Dagon), and two Sukuna Shorts got that talk. Research's fight scores (>= 5) narrow it when they exist
    try:
        _rcp = json.load(open('research_cache.json'))
        _good = {}
        for _sv in _rcp.values():
            for _nm, _d in ((_sv.get('characters') or {}).items() if isinstance(_sv, dict) else []):
                if isinstance(_d, dict) and _nm.split() and PICK in (_nm.lower().split()[0], _nm.lower().split()[-1]):
                    for r in _d.get('ranked', []):
                        if r.get('ep') in EPISODES and r.get('score', 0) >= 5:
                            _good[r['ep']] = max(_good.get(r['ep'], 0), r['score'])
        if len(_good) >= 3:
            print(f'talk episodes for {PICK} from research fight scores: {sorted(_good, key=lambda e: -_good[e])}', flush=True)
            cand = sorted(_good, key=lambda e: -_good[e])
    except Exception as ex:
        print('research narrowing skipped:', ex, flush=True)
else:
    series = match[0] if match else (EPISODES[new_eps[0]]['series'] if new_eps else least_used(series_all, hist.get('series', {}), 1)[0])
    cand = [k for k, v in EPISODES.items() if v['series'] == series]
# characters of the last 4 Shorts rest: their episodes count as heavily used, and episodes a re-run rejected are skipped
RECENT_TOPICS = [c.get('topic') for c in hist.get('convos', [])[-4:] if c.get('topic')]
AVOID = [e for e in os.environ.get('CONVO_AVOID_EPS', '').split(',') if e]
if PICK == 'auto':
    try:
        _rc0 = json.load(open('research_cache.json'))
    except Exception:
        _rc0 = {}
    for _t in set(RECENT_TOPICS):
        _eps_t = set(chars.get(_t, []))
        for _sv in _rc0.values():
            if not isinstance(_sv, dict):                             # the cache also holds plain keys (a version, a date)
                continue
            for _nm, _d in (_sv.get('characters') or {}).items():
                if isinstance(_d, dict) and _nm.split() and (_nm.lower().split()[-1] == _t or _nm.lower().split()[0] == _t):
                    _eps_t |= {r.get('ep') for r in _d.get('ranked', []) if r.get('score', 0) >= 2}
        for _e in _eps_t:
            if _e:
                used_eps[_e] = used_eps.get(_e, 0) + 4
    if RECENT_TOPICS:
        print('resting characters of the last Shorts:', RECENT_TOPICS, flush=True)
    if len([e for e in cand if e not in AVOID]) >= 3:
        cand = [e for e in cand if e not in AVOID]
_TRIED = AVOID + [e for e in os.environ.get('CONVO_EP_EXCLUDE', '').split(',') if e]   # episodes a retry already ruled out:
if any(e not in _TRIED for e in cand):                                # leave them out for picks too, so the next 3 are new ones
    cand = [e for e in cand if e not in _TRIED]                       # (tanjiro run 45148880061 cycled S1E14/S1E18/S1E04 and failed)
fresh = [e for e in new_eps if e in cand][:3]
eps = fresh + least_used([e for e in cand if e not in fresh], used_eps, 3 - len(fresh))
PIN = os.environ.get('CONVO_EP', '').strip()                        # pinned talk episode, e.g. S2E16 or jujutsu-kaisen:S2E16
if PIN:
    _pm = [e for e in EPISODES if e == PIN or (e.endswith(':' + PIN) and e.split(':')[0] == (eps[0].split(':')[0] if eps else e.split(':')[0]))]
    if not _pm:
        raise SystemExit(f'CONVO_EP {PIN} is not an episode in the index')
    PIN = _pm[0]
    eps = [PIN] + [e for e in eps if e != PIN][:2]
    print('talk episode pinned:', PIN, flush=True)
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
EP_EXCLUDE = [e for e in os.environ.get('CONVO_EP_EXCLUDE', '').split(',') if e]   # talk episodes that did not show the pick
for ep in eps:
    d_, ps = motions[ep]
    if (PIN and ep != PIN) or (not PIN and ep in EP_EXCLUDE + AVOID and any(e not in EP_EXCLUDE + AVOID for e in eps)):   # rengoku run 45141125056 looped on S2E05
        SONGS[ep] = song_mask(ep, d_)
        continue
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
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(lo), '-t', str(hi - lo), '-i', src, '-vn', '-af', 'aresample=async=1:first_pts=0', '-ac', '1', '-ar', '16000', 'work/convo/full.wav'])
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
def _nwords(t_):                                                       # words, with CJK text (no spaces) counted ~2 chars a word
    t_ = t_ or ''
    cjk = len(re.findall(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', t_))
    return len(re.sub(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', ' ', t_).split()) + cjk // 2
for sg in _ss:
    if _nwords(sg.text) >= 3 and sg.avg_logprob > -1.0 and sg.no_speech_prob < 0.6:
        speech[int(lo + sg.start):int(lo + sg.end) + 1] = 1
speech[SONG[:len(speech)]] = 0
SKIP = [float(x) for x in os.environ.get('CONVO_SKIP', '').split(',') if x]


def next_episode(why):
    """this episode has no usable talk: try another episode (at most 3) instead of failing the whole run"""
    if PIN:
        raise SystemExit(f'{why} in the pinned episode {conv_ep}')
    if len(AVOID) < 3:
        print(f'{why} in {conv_ep}: trying another episode', flush=True)
        os.environ['CONVO_AVOID_EPS'] = ','.join(AVOID + [conv_ep])
        os.environ.pop('CONVO_SKIP', None)
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
    raise SystemExit(why)

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
if not _cands and SKIP:                                               # every talk moment here was tried (it kept retrying 950s)
    next_episode('no talk moment left')
# WEAK TALK GUARD: run 45629584475 had no talk candidate at all (score -1.00) and used the fight peak anyway. No candidate,
# or only weak ones (little talk, little action), moves on to another episode instead of making a weak Short.
TALK_MIN = float(os.environ.get('CONVO_MIN_SCORE', 0.95))
if not _cands:
    next_episode('no moment with real talk during a fight')
_strong = [c_ for c_ in _cands if c_[0] >= TALK_MIN]
print(f'talk candidates: {len(_cands)}, {len(_strong)} at score >= {TALK_MIN} (best {bs:.2f})', flush=True)
if not _strong:
    next_episode(f'only weak talk moments (best score {bs:.2f} < {TALK_MIN})')
_cands = _strong
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
                  f'clearly them {"yes" if r_.get("target_clear") else "no"}', flush=True)
            if r_.get('target_clear'):
                if t_ != bt:
                    print(f'talk moment {bt}s -> {t_}s: {PICK_NAME} is on screen there', flush=True)
                bs, bt = sc_, t_
                break
        else:
            left = [e for e in eps if e != conv_ep and e not in EP_EXCLUDE]
            if left and not PIN and len(EP_EXCLUDE) < 2:                          # try the talk in another of the picked episodes
                print(f'no talk candidate in {conv_ep} is clearly {PICK_NAME}; trying the next episode {left}', flush=True)
                os.environ['CONVO_EP_EXCLUDE'] = ','.join(EP_EXCLUDE + [conv_ep]); os.environ.pop('CONVO_SKIP', None)
                os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
            print(f'no talk candidate is clearly {PICK_NAME}; keeping the best-scoring moment {bt}s', flush=True)
    except Exception as ex:
        print('talk candidate identification skipped:', ex, flush=True)
fight = bt
win0, win1 = max(lo, bt - 12), min(hi, bt + int(os.environ.get('CONVO_WIN_AFTER', 72)))   # wide enough for the payoff to finish
print('conversation from', conv_ep, f'| talking fight at {bt}s (score {bs:.2f}), transcribing {win0}-{win1}s', flush=True)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(win0), '-t', str(win1 - win0), '-i', src, '-vn', '-af', 'aresample=async=1:first_pts=0', '-ac', '1', '-ar', '16000', 'work/convo/win.wav'])

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
words, SEGS = [], []
for sg in segs:
    text = (sg.text or '').strip()
    if not text:
        continue
    ws = [w for w in (sg.words or []) if w.word.strip()]
    SEGS.append(dict(s=win0 + (ws[0].start if ws else sg.start), e=win0 + (ws[-1].end if ws else sg.end), t=text, id=id(sg)))
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
        next_episode('not enough dialogue in the fight')
    print('too little dialogue there, trying the next fight moment', flush=True)
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])

# ------------------------------------------------------------------ 3. densest stretch of dialogue
PICK_T = []                                                           # a character pick: times of frames that vote for them
if PICK_NAME and os.environ.get('CONVO_IDENT_PICK', '1') == '1':
    try:
        import charvis
        _rw = charvis.identify(src, win0, win1, EPISODES[conv_ep]['series'], lo, hi, skip=_SKIP_SONG, expected=(PICK_NAME,),
                               target=PICK_NAME, log=lambda m: print('identify:', m, flush=True))
        PICK_T = [t_ for t_, n_ in _rw.get('per_frame', []) if n_ == PICK_NAME]
        _all_t = [t_ for t_, _ in _rw.get('per_frame', [])]
    except Exception as ex:
        print('pick frames skipped:', ex, flush=True)


def pick_frac(a, b):                                                  # share of the stretch's sampled frames that are the pick
    if not PICK_T:
        return 0.0
    n_all = sum(a <= t_ <= b for t_ in _all_t)
    return sum(a <= t_ <= b for t_ in PICK_T) / max(1, n_all)


# ------------------------------------------------------------------ 3. hook -> build -> payoff (cut only at whisper-segment edges)
# translated word times are spread evenly inside a segment, so the only honest cut points are segment edges. The talk is
# 1-4 stretches of whole segments: a HOOK line that grabs, BUILD lines, and a PAYOFF line that finishes the thought.
SEGS = [g for g in SEGS if not SONG[max(0, int(g['s'] - 0.35)):int(g['e'] + 0.8) + 1].any()]
# whisper hallucinations: a line repeated word for word (it loops a line over music: "No good! My teeth won't go through!"
# came back as a 13 s segment over the opening), or a long segment with almost no words in it
_seen_t, _keep = set(), []
for g in SEGS:
    _norm = re.sub(r'[^a-z0-9 ]', '', g['t'].lower()).strip()
    _dur = g['e'] - g['s']
    _nw = len(g['t'].split())
    if _norm and _norm in _seen_t:
        print(f"dropping repeated line {g['s']:.1f}-{g['e']:.1f}s: {g['t']}", flush=True)
        continue
    if _dur > 4.0 and _nw / _dur < 1.0:
        print(f"dropping sparse line {g['s']:.1f}-{g['e']:.1f}s ({_nw} words in {_dur:.1f}s): {g['t']}", flush=True)
        continue
    _seen_t.add(_norm)
    _keep.append(g)
SEGS = _keep
for k_, g in enumerate(SEGS):
    g['k'] = k_
SEND = lambda t_: re.sub(r'["\'\u201d\u2019)\]\s]+$', '', t_ or '')[-1:] in '.!?'
EDGE = 1.0                                                            # the window edge is not a pause: the line may go on


def pause_after(k):
    return (SEGS[k + 1]['s'] - SEGS[k]['e']) if k + 1 < len(SEGS) else (win1 - EDGE - SEGS[k]['e'])


def runs_of(sel):
    sel = sorted(set(sel)); out = []
    for k in sel:
        if out and k == out[-1][1] + 1:
            out[-1][1] = k
        else:
            out.append([k, k])
    return out


def pieces_of(sel):
    """[(src_start, length)] for the runs of selected segments, frame-rounded; the last one keeps up to 0.8 s of pause"""
    rs = runs_of(sel); out = []
    for n_, (f, l) in enumerate(rs):
        a = SEGS[f]['s'] - 0.12
        if f > 0:
            a = max(a, SEGS[f - 1]['e'] + 0.03)
        a = max(a, win0)
        pz = pause_after(l)
        tail = min(0.8, max(0.15, pz - 0.1)) if n_ == len(rs) - 1 else min(0.3, max(0.05, pz - 0.08))
        b = SEGS[l]['e'] + tail
        if l + 1 < len(SEGS):
            b = min(b, SEGS[l + 1]['s'] - 0.03)
        b = min(b, win1)
        a = round(a * FPS) / FPS; L = max(1, round((b - a) * FPS)) / FPS
        out.append((a, L))
    return out


def check(sel):
    """None when the pick is usable, else why not"""
    if not sel or any(not isinstance(k, int) or k < 0 or k >= len(SEGS) for k in sel):
        return 'line numbers out of range'
    if any(b <= a for a, b in zip(sel, sel[1:])):
        return 'lines not in order'
    rs = runs_of(sel)
    if not 1 <= len(rs) <= 3:
        return f'{len(rs)} stretches (1-3 allowed)'
    ps = pieces_of(sel); tot = sum(L for _, L in ps)
    for (a0, L0), (a1, _) in zip(ps, ps[1:]):                        # one scene: a cut may skip a few lines, never jump scenes
        if a1 - (a0 + L0) > MAXGAP:
            return f'{a1 - (a0 + L0):.1f}s skipped between stretches (one scene only, at most {MAXGAP:.0f}s skipped)'
    if not CMIN <= tot <= CMAX:
        return f'{tot:.1f}s long ({CMIN:.0f}-{CMAX:.0f}s allowed)'
    if any(SONG[max(0, int(a)):int(a + L) + 1].any() for a, L in ps):
        return 'touches an opening/ending song'
    if not SEND(SEGS[sel[-1]]['t']):
        return 'payoff does not end a sentence'
    if pause_after(sel[-1]) < 0.5:
        return f'only {pause_after(sel[-1]):.2f}s pause after the payoff'
    return None


def _load_groq():                                                     # narrate.py::_groq, without running narrate.py
    import ast, urllib.request
    tree = ast.parse(open('narrate.py').read())
    fn = next(n_ for n_ in tree.body if isinstance(n_, ast.FunctionDef) and n_.name == '_groq')
    ns = dict(json=json, os=os, re=re, urllib=urllib)
    exec(compile(ast.Module([fn], []), 'narrate.py', 'exec'), ns)
    return ns['_groq']


def groq_pick():
    if not SEGS or not os.environ.get('GROQ_API_KEY', '').strip():
        return None, 'no GROQ_API_KEY' if SEGS else 'no segments'
    lines_ = '\n'.join(f"{g['k']}. [{g['s'] - win0:.1f}-{g['e'] - win0:.1f}s, {g['e'] - g['s']:.1f}s] {g['t']}" for g in SEGS)
    prompt = (f"Numbered subtitle lines (English translation) from an anime scene of {EPISODES[conv_ep]['series'].replace('-', ' ')}"
              + (f", focused on {PICK_NAME}" if PICK_NAME else '') + ":\n" + lines_ + "\n\n"
              f"Cut a {CMIN:.0f}-{CMAX:.0f} second talk clip for a YouTube Short using the TRIPLE HOOK "
              "(context -> lean -> contrarian snapback):\n"
              "- hook (CONTEXT): the first line makes it instantly clear who is talking and what is at stake, AND grabs "
              "at once (a threat, a bold claim, a challenge, a question, an emotional cry). Never open on filler, a name call "
              "alone, or a line that needs earlier context\n"
              "- STORY: someone who has never seen this anime must understand from these lines alone who is facing whom, "
              "what is happening and why it matters. Include the setup lines that explain it; never skip a line the payoff "
              "depends on. Prefer one unbroken stretch; cut lines out only when they are filler\n"
              "- build (LEAN): lines that make the viewer lean in: tension rises, one side looks sure to win, a shocking "
              "claim, proof of power, or a pain point. Prefer consecutive lines so the scene flows\n"
              "- payoff (SNAPBACK): the last line flips the direction the build leaned toward: a counter, a reveal, a "
              "defiant answer, an unexpected twist (but / no / you're wrong / I won't). It is a complete, strong statement "
              "that ends with . ! or ? and is followed by a pause. If no line truly flips it, take the strongest closing line\n"
              "Rules: line numbers in increasing order; the chosen lines form at most 3 separate stretches of consecutive "
              f"numbers, all from ONE scene: never jump to an unrelated scene, and never skip more than {MAXGAP:.0f} s between "
              f"stretches; the summed durations of the chosen lines are {CMIN:.0f}-{CMAX:.0f} s.\n"
              'Answer with JSON only: {"hook": <number>, "build": [<numbers>], "payoff": <number>, "reason": "<short>"}')
    prompt += ("\nAdd up the durations in brackets before answering; most picks need about "
               f"{max(2, int(len(SEGS) * (CMIN + CMAX) / 2 / max(1.0, sum(g['e'] - g['s'] + 0.4 for g in SEGS))))} lines.")
    sel, why, groq = None, 'groq not asked', _load_groq()
    for attempt in range(2):
        try:
            out, mdl = groq(prompt, temperature=0.2, system='You are a precise video editor of anime Shorts. You answer with JSON only.')
            js = json.loads(re.search(r'\{.*\}', out, re.S).group(0))
            if js.get('hook') is None or js.get('payoff') is None:
                raise ValueError(f'no hook/payoff line in {js}')
            sel = [int(js['hook'])] + [int(x) for x in (js.get('build') or []) if x is not None] + [int(js['payoff'])]
            sel = list(dict.fromkeys(sel))
            print(f'groq ({mdl}) pick {attempt + 1}: {js}', flush=True)
        except Exception as ex:
            sel, why = None, f'groq failed: {ex}'
            continue
        why = check(sel)
        if why is None:
            return sel, None
        fix = list(sel)                                               # too long: drop build lines after the hook, keep hook + payoff
        while len(fix) > 2 and check(fix) and sum(L for _, L in pieces_of(fix)) > CMAX:
            fix.pop(1)
        if check(fix) is None:
            print(f'groq pick trimmed to fit ({why}): {fix}', flush=True)
            return fix, None
        fix = list(sel)                                               # too short: add the lines just before it (more context)
        while fix[0] > 0 and sum(L for _, L in pieces_of(fix)) < CMIN \
                and sum(L for _, L in pieces_of([fix[0] - 1] + fix)) <= CMAX:
            fix.insert(0, fix[0] - 1)
        if check(fix) is None:
            print(f'groq pick extended back for context ({why}): {fix}', flush=True)
            return fix, None
        prompt += f"\n\nYour previous answer {json.dumps(js)} was rejected: {why}. Answer again, following every rule."
    return sel, why


HOOKY = re.compile(r"\?|!|\byou\b|\byour\b|\bi'll\b|\bi will\b|\bcan't\b|\bcannot\b", re.I)
SNAP = re.compile(r"\bbut\b|\bno\b|\bnot\b|\bnever\b|\bwrong\b|\bactually\b|\binstead\b|\bwon't\b|\bstill\b|\byet\b", re.I)   # contrarian snapback words


def heuristic_pick():
    best_ = None
    for h in range(len(SEGS)):
        if not HOOKY.search(SEGS[h]['t']):
            continue
        for p in range(h, len(SEGS)):
            t_ = SEGS[p]['t'].rstrip()
            if not SEND(t_) or t_.endswith('?') or pause_after(p) < 0.5:
                continue
            sel = list(range(h, p + 1))
            while len(sel) > 2 and sum(L for _, L in pieces_of(sel)) > CMAX:   # too long: drop build lines from the front
                sel.pop(1)
            if check(sel):
                continue
            a_, b_ = SEGS[h]['s'], SEGS[p]['e']
            act = per_s[int(a_):int(b_) + 1].mean() / mref
            dens = sum(SEGS[k]['e'] - SEGS[k]['s'] for k in sel) / sum(L for _, L in pieces_of(sel))
            sc = 1.0 * dens + 1.0 * min(act, 1.3) + 1.5 * pick_frac(a_, b_) + 0.3 * len(HOOKY.findall(SEGS[h]['t'])) + 0.4 * min(2, len(SNAP.findall(SEGS[p]['t']))) - 0.5 * (len(runs_of(sel)) - 1)   # cuts lose context: prefer one unbroken stretch
            if best_ is None or sc > best_[0]:
                best_ = (sc, sel)
    return best_[1] if best_ else None


def stretch_pick():
    """the old single stretch of words, snapped to segment edges and ended on a sentence end + pause, never the window edge"""
    starts = [i for i, w in enumerate(words) if i == 0 or words[i - 1]['w'][-1:] in '.?!' or w['s'] - words[i - 1]['e'] > 0.8]
    best, pick = -1, None
    for i in starts:
        for j in range(i + 6, len(words)):
            L = words[j]['e'] - words[i]['s']
            if L > CMAX:
                break
            done = words[j]['w'][-1:] in '.?!' and (j == len(words) - 1 and win1 - words[j]['e'] > EDGE + 0.5 or
                                                    j < len(words) - 1 and words[j + 1]['s'] - words[j]['e'] > 0.7)
            if L < CMIN or not done:
                continue
            if SONG[max(0, int(words[i]['s'] - 0.35)):int(words[j]['e'] + 0.8) + 1].any():
                continue
            talk = sum(w['e'] - w['s'] for w in words[i:j + 1]) / L
            act = per_s[int(words[i]['s']):int(words[j]['e']) + 1].mean() / mref
            score = 1.0 * talk + 0.08 * (j - i) / L + 1.0 * min(act, 1.3) + 1.5 * pick_frac(words[i]['s'], words[j]['e'])
            if score > best:
                best, pick = score, (i, j)
    if pick is None:
        i = starts[0]
        ends = [k for k in range(len(words)) if words[k]['e'] - words[i]['s'] <= CMAX and words[k]['w'][-1:] in '.?!']
        j = max(ends) if ends else max(k for k in range(len(words)) if words[k]['e'] - words[i]['s'] <= CMAX)
        pick = (i, j)
    k0 = next((g['k'] for g in SEGS if g['id'] == words[pick[0]]['seg']), 0)
    k1 = next((g['k'] for g in SEGS if g['id'] == words[pick[1]]['seg']), len(SEGS) - 1)
    k1 = max(k1, k0)
    while k1 < len(SEGS) - 1 and not (SEND(SEGS[k1]['t']) and pause_after(k1) >= 0.5) and \
            SEGS[k1 + 1]['e'] - SEGS[k0]['s'] <= CMAX + 6:                  # extend to the next sentence end + pause
        k1 += 1
    return list(range(k0, k1 + 1))


SEL, how = None, None
if SEGS:
    sel_, why = groq_pick()
    if sel_ and why is None:
        SEL, how = sel_, 'groq'
    else:
        print('groq hook/build/payoff rejected:', why, flush=True)
        sel_ = heuristic_pick()
        if sel_:
            SEL, how = sel_, 'heuristic'
        else:
            print('heuristic hook/payoff found nothing valid; single stretch fallback', flush=True)
            SEL, how = stretch_pick(), 'stretch'
if not SEL:
    raise SystemExit('no talk segments')
PIECES = pieces_of(SEL)
OFFS = list(np.cumsum([0.0] + [L for _, L in PIECES])[:-1])
_sel_ids = {SEGS[k]['id'] for k in SEL}
cw = [w for w in words if w['seg'] in _sel_ids]
c0 = PIECES[0][0]; c1 = PIECES[-1][0] + PIECES[-1][1]               # the overall span (history, the edit's EXCLUDE)
CONV = round(sum(L for _, L in PIECES) * FPS) / FPS


def _piece(t):                                                         # the piece holding source time t (nearest one)
    return min(range(len(PIECES)), key=lambda n_: max(PIECES[n_][0] - t, t - PIECES[n_][0] - PIECES[n_][1], 0.0))


def to_out(t):
    """source time -> time inside the stitched talk"""
    n_ = _piece(t); a, L = PIECES[n_]
    return OFFS[n_] + min(max(t - a, 0.0), L)


def piece_end_out(t):                                                 # end of the stitched piece holding source time t
    n_ = _piece(t)
    return OFFS[n_] + PIECES[n_][1]


_lbl = {SEL[0]: 'HOOK', SEL[-1]: 'PAYOFF'}
for k in SEL:
    g = SEGS[k]
    print(f"talk {_lbl.get(k, 'BUILD')}: {g['s']:.2f}-{g['e']:.2f}s -> {to_out(g['s']):.2f}s in the Short | {g['t']}", flush=True)
if SONG[max(0, int(c0)):int(c1) + 1].any() and any(SONG[max(0, int(a)):int(a + L) + 1].any() for a, L in PIECES):
    if len(SKIP) >= 4:
        raise SystemExit('every conversation candidate sits in an opening/ending song')
    print(f'conversation {c0:.1f}-{c1:.1f}s touches an opening/ending, trying the next fight moment', flush=True)
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
_wps = len(cw) / max(0.1, CONV)
if CONV > CMAX + 2 or _wps < 0.7:                                     # a fallback that is mostly music/fight noise is no talk
    print(f'talk rejected: {CONV:.1f}s with {len(cw)} words ({_wps:.2f}/s)', flush=True)
    CONV = 0.0
if CONV < CMIN * 0.6:                                                 # too thin to be a conversation: next fight moment
    if len(SKIP) >= 4:
        next_episode('no real conversation found in the fights')
    print(f'conversation only {CONV:.1f}s, trying the next fight moment', flush=True)
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])


def dead_air(y_, sr_, a_, b_, min_len=0.8):
    """runs of true digital silence (a broken audio stretch in the source; real anime audio is never exactly 0)"""
    i0, i1 = max(0, int(a_ * sr_)), min(len(y_), int(b_ * sr_))
    hop = int(0.05 * sr_); runs, run0 = [], None
    for i in range(i0, i1, hop):
        quiet = float(np.abs(y_[i:i + hop]).max()) < 2e-4 if i + hop <= len(y_) else True
        if quiet and run0 is None:
            run0 = i
        elif not quiet and run0 is not None:
            if (i - run0) / sr_ >= min_len:
                runs.append((run0 / sr_, i / sr_))
            run0 = None
    if run0 is not None and (i1 - run0) / sr_ >= min_len:
        runs.append((run0 / sr_, i1 / sr_))
    return runs


_dead = sum([dead_air(audio16, 16000, a - win0, a - win0 + L) for a, L in PIECES], [])
if _dead:
    print(f'talk audio has dead air {[(round(x + win0, 1), round(y + win0, 1)) for x, y in _dead]} '
          f'(broken audio in the source): trying the next fight moment', flush=True)
    if len(SKIP) >= 4:
        raise SystemExit('every conversation candidate has broken audio')
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
print(f'conversation ({how}) {len(PIECES)} piece(s) ' + ', '.join(f'{a:.2f}-{a + L:.2f}s' for a, L in PIECES) +
      f' = {CONV:.2f}s, {len(cw)} words; span {c0:.2f}-{c1:.2f}s', flush=True)

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
    t_end = min(to_out(ln[-1]['e']) + 0.35, to_out(lines[li + 1][0]['s']) if li + 1 < len(lines) else CONV,
                piece_end_out(ln[0]['s'])) + HOOK
    toks = [clean(w['w']) for w in ln]
    toks = [t for t in toks if t]
    if not toks:
        continue
    # rows by width, not word count: at 98 px a caps row fits ~16 characters across the 1080 frame
    # ("HE KNOWS UROKODAKI?" ran off both edges). Two rows at most; a row still too wide shrinks the font.
    ROWC = int(os.environ.get('CAP_ROW_CHARS', 16))
    _w = lambda r: sum(len(t) for t in r) + max(0, len(r) - 1)
    if _w(toks) <= ROWC or len(toks) == 1:
        rows_ = [toks]
    else:
        rows_ = min(([toks[:i], toks[i:]] for i in range(1, len(toks))), key=lambda rr: max(_w(rr[0]), _w(rr[1])))
    widest = max(_w(r) for r in rows_)
    fs_tag = f'\\fs{max(56, int(98 * ROWC / widest))}' if widest > ROWC else ''
    ends = set()
    n_ = 0
    for r in rows_[:-1]:
        n_ += len(r); ends.add(n_ - 1)
    for k in range(len(toks)):                                        # word-by-word: spoken white, the rest dim
        a = to_out(ln[min(k, len(ln) - 1)]['s']) + HOOK
        b = (to_out(ln[k + 1]['s']) + HOOK) if k + 1 < len(toks) and k + 1 < len(ln) else t_end
        if b <= a:
            continue
        parts = []
        for m, t in enumerate(toks):
            parts.append(('{\\1c&H00FFFFFF&}' if m <= k else '{\\1c' + DIM + '}') + t)
            if m in ends:
                parts.append('\\N')
            elif m != len(toks) - 1:
                parts.append(' ')
        txt = ''.join(parts).replace(' \\N', '\\N')
        pop = '{\\fscx106\\fscy106\\t(0,90,\\fscx100\\fscy100)}' if k == 0 else ''
        glow = f'{{\\pos({W // 2},{int(H * 0.53)}){fs_tag}\\bord18\\blur16\\3c{ass_col(col)}\\3a&H20&\\shad0\\1a&HFF&}}'
        main = f'{{\\pos({W // 2},{int(H * 0.53)}){fs_tag}\\bord4\\blur3\\3c{ass_col(col)}\\shad3}}'
        ass.append(f'Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{glow}{pop}{txt}')
        ass.append(f'Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{main}{pop}{txt}')
open('work/convo/captions.ass', 'w').write('\n'.join(ass) + '\n')
json.dump(dict(ep=conv_ep, s=c0, e=c1, pieces=[[round(a_, 3), round(L_, 3)] for a_, L_ in PIECES], pick=how,
               hook=dict(t=SEGS[SEL[0]]['t'], s=round(SEGS[SEL[0]]['s'], 2), e=round(SEGS[SEL[0]]['e'], 2)),
               build=[dict(t=SEGS[k]['t'], s=round(SEGS[k]['s'], 2), e=round(SEGS[k]['e'], 2)) for k in SEL[1:-1]],
               payoff=dict(t=SEGS[SEL[-1]]['t'], s=round(SEGS[SEL[-1]]['s'], 2), e=round(SEGS[SEL[-1]]['e'], 2)), lines=[dict(t=' '.join(w['w'] for w in ln), speaker=int(spk[i]), colour=colour_of[spk[i]])
                                               for i, ln in enumerate(lines)]), open('work/convo/convo.json', 'w'), indent=1)
print('captions', len(lines), 'lines,', len(set(spk)), 'speaker colours', flush=True)

# ------------------------------------------------------------------ 5. face-following 9:16 crop, shot by shot, piece by piece
def scene_cuts(a, L):
    """shot changes (seconds from a) inside src a..a+L"""
    raw = sh(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{a:.3f}', '-t', f'{L:.3f}', '-i', src, '-vf',
              'fps=12,scale=64:36,format=gray', '-f', 'rawvideo', '-'], binary=True)
    gg = np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.float32)
    d = np.abs(np.diff(gg, axis=0)).mean(axis=(1, 2)) if len(gg) > 1 else np.zeros(0)
    cuts = [0.0] + [(i + 1) / 12 for i in range(len(d)) if d[i] > max(18, 4 * np.median(d[max(0, i - 12):i + 12]))] + [L]
    cuts = sorted(set(min(L, round(c * FPS) / FPS) for c in cuts))
    return [c for k, c in enumerate(cuts) if k == 0 or c - cuts[k - 1] >= 0.3 or c == L]


iw, ih = map(int, sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', src]).strip().split(','))
try:
    import cv2
    casc = cv2.CascadeClassifier('lbpcascade_animeface.xml')
except Exception:
    casc = None
crop_w = ih * W / H                                                    # 9:16 window in source pixels


def face_x(t0_, t1_):
    """crop centre (0..1) from the biggest anime face in the shot, None when no face"""
    cx = []
    for f in (0.3, 0.7):
        if casc is None:
            break
        t = t0_ + (t1_ - t0_) * f
        fr = np.frombuffer(sh(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1', '-vf',
                               'scale=640:360,format=gray', '-f', 'rawvideo', '-'], binary=True), np.uint8).reshape(360, 640)
        faces = casc.detectMultiScale(fr, 1.1, 3, minSize=(28, 28))
        if len(faces):
            x, y_, w, h = max(faces, key=lambda f_: f_[2] * f_[3])
            cx.append((x + w / 2) / 640)
    return float(np.mean(cx)) if cx else None


# no talk picture holds longer than ~6 s: long shots get a cutaway (a reaction / other shot of the same scene, outside the
# talk itself) every ~4 s; with no such shot, a punch-in on the same footage reads as the cut
MAXHOLD = float(os.environ.get('TALK_MAX_SHOT', 6.0))
_busy = [(a - 0.3, a + L + 0.3) for a, L in PIECES]
_wc = scene_cuts(win0, win1 - win0)
BROLL = []
for x_, y_ in zip(_wc[:-1], _wc[1:]):
    a_, b_ = win0 + x_, win0 + y_
    if b_ - a_ >= 1.2 and not any(a_ < u1 and b_ > u0 for u0, u1 in _busy) and not SONG[max(0, int(a_)):int(b_) + 1].any():
        BROLL.append([a_, b_, None])
for br in BROLL:
    br[2] = face_x(br[0], br[1])


def cutaway(t_src, dur):
    """the nearest unused scene shot that fits dur (faces first); removed from BROLL"""
    fit = [br for br in BROLL if br[1] - br[0] >= dur]
    if not fit:
        return None
    br = min(fit, key=lambda b: (b[2] is None, abs((b[0] + b[1]) / 2 - t_src)))
    BROLL.remove(br)
    return dict(ss=(br[0] + br[1]) / 2 - dur / 2, x=br[2] if br[2] is not None else 0.5, zoom=1.0, kind='cutaway')


SHOTS = []                                                            # dict(f0, f1 (frames of the Short), ss (src), x, zoom, kind)
n_cut, n_punch = 0, 0
for (a, L), o in zip(PIECES, OFFS):
    cuts = scene_cuts(a, L)
    for x0, x1 in zip(cuts[:-1], cuts[1:]):
        f0, f1 = round((o + x0) * FPS), round((o + x1) * FPS)
        if f1 <= f0:
            continue
        fx_ = face_x(a + x0, a + x1)
        xm = fx_ if fx_ is not None else 0.5
        t = f0
        while (f1 - t) / FPS > MAXHOLD:                              # hold 4 s, cut away for up to 2 s, come back
            k1 = t + round(4.0 * FPS)
            cl = round(min(2.0, (f1 - k1) / FPS - 1.0) * FPS)
            SHOTS.append(dict(f0=t, f1=k1, ss=a + x0 + (t - f0) / FPS, x=xm, zoom=1.0, kind='talk'))
            ca = cutaway(a + x0 + (k1 - f0) / FPS, cl / FPS)
            if ca is None:                                            # same footage (lips stay in sync), punched in
                ca = dict(ss=a + x0 + (k1 - f0) / FPS, x=min(0.8, max(0.2, xm + (0.12 if xm < 0.5 else -0.12))), zoom=1.3, kind='punch')
                n_punch += 1
            else:
                n_cut += 1
            SHOTS.append(dict(ca, f0=k1, f1=k1 + cl))
            t = k1 + cl
        SHOTS.append(dict(f0=t, f1=f1, ss=a + x0 + (t - f0) / FPS, x=xm, zoom=1.0, kind='talk'))
_holds = [(s_['f1'] - s_['f0']) / FPS for s_ in SHOTS]
print(f'talk picture: {len(SHOTS)} shots, longest {max(_holds):.1f}s, {n_cut} cutaways, {n_punch} punch-ins '
      f'(max hold {MAXHOLD:.0f}s)', flush=True)
os.makedirs('work/convo/seg', exist_ok=True)
lst = []
for k, s_ in enumerate(SHOTS):
    nf = s_['f1'] - s_['f0']
    cw_, ch_ = crop_w / s_['zoom'], ih / s_['zoom']
    left = min(max(s_['x'] * iw - cw_ / 2, 0), iw - cw_)
    top = (ih - ch_) * 0.35
    vf = (f'crop={int(cw_) // 2 * 2}:{int(ch_) // 2 * 2}:{int(left)}:{int(top)},scale={W}:{H}:flags=lanczos,setsar=1,'
          f'eq=contrast=1.06:saturation=1.12,fps={FPS}')
    out = f'work/convo/seg/{k:03d}.mp4'
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f"{s_['ss']:.3f}", '-i', src, '-an', '-vf', vf, '-frames:v', str(nf),
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', out])
    lst.append(out)
open('work/convo/seg/list.txt', 'w').write(''.join(f"file '{os.path.basename(p)}'\n" for p in lst))
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'work/convo/seg/list.txt', '-c', 'copy', 'work/convo/video.mp4'])

# ------------------------------------------------------------------ 5b. voices only: strip the anime's own music (copyright)
# each piece is cut with ~60 ms of extra tail (all but the last) and the pieces are joined with that much acrossfade, so the
# stitched talk is exactly CONV long and lines up with the picture; no hard joins, no clicks
XF = 0.06
for n_, (a, L) in enumerate(PIECES):
    ext = L + (XF if n_ < len(PIECES) - 1 else 0.0)
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-t', f'{ext:.3f}', '-i', src, '-vn', '-af', 'aresample=async=1:first_pts=0', '-ac', '2', '-ar', '44100',
        f'work/convo/talk_{n_}.wav'])
if len(PIECES) == 1:
    os.replace('work/convo/talk_0.wav', 'work/convo/talk.wav')
else:
    ins = sum([['-i', f'work/convo/talk_{n_}.wav'] for n_ in range(len(PIECES))], [])
    g_, prev_ = [], '[0:a]'
    for n_ in range(1, len(PIECES)):
        lab = f'[x{n_}]' if n_ < len(PIECES) - 1 else '[out]'
        g_.append(f'{prev_}[{n_}:a]acrossfade=d={XF}:c1=qsin:c2=qsin{lab}'); prev_ = lab
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(g_), '-map', '[out]', '-t', f'{CONV:.3f}',
        'work/convo/talk.wav'])
print(f'talk audio: {len(PIECES)} piece(s) stitched, {duration("work/convo/talk.wav"):.3f}s (picture {CONV:.3f}s)', flush=True)
_ty, _tsr = _sf.read('work/convo/talk.wav', dtype='float32')
_ty = _ty.mean(axis=1) if _ty.ndim > 1 else _ty
_tdead = dead_air(_ty, _tsr, 0, CONV)
if _tdead or len(_ty) / _tsr < CONV - 0.3:
    print(f'stitched talk audio broken (dead air {_tdead}, {len(_ty) / _tsr:.2f}s of {CONV:.2f}s): trying the next fight moment', flush=True)
    if len(SKIP) >= 4:
        raise SystemExit('every conversation candidate has broken audio')
    os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
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
TOPIC_GUESS = False                                                   # True when the character is only a guess (no pick, no clear frames, not said)

# 1. If explicit PICK matches a character slug
if PICK in chars:
    topic_slug = PICK
    topic_name = lore_name(topic_slug, series_key) or topic_slug.title()

# 2. who the scene is about: charvis.identify() - a frame every 0.75 s, each votes for its best character
#    (name / look / stills, z-scored against frames every 25 s of the same episode). Always run and logged, so a
#    character pick shows whether the talk really features them.
IDENT = {}


def _not_in_episode(nm):
    """True when research knows this character's episodes and this one is not among them, and nobody says the name in
    the talk: identify() picked Rengoku for Sabito in S1E03, so the edit became Rengoku's fights"""
    try:
        d_ = json.load(open('research_cache.json')).get(series_key, {}).get('characters', {}).get(nm)
    except Exception:
        return False
    if not isinstance(d_, dict) or not d_.get('ranked'):
        return False
    # a fight of theirs must be IN this episode (score >= 8): identify() voted Sukuna 57% on Dagon's beach talk in
    # JJK S2E15, where research only gave Sukuna 5.5 (he fights Jogo in S2E16), so the edit became Sukuna's fights
    if any(r.get('ep') == conv_ep and r.get('score', 0) >= float(os.environ.get('CONV_TRUST_SCORE', 8)) for r in d_['ranked']):
        return False
    said = ' '.join(w['w'] for w in cw).lower()
    if any(p_ and len(p_) >= 3 and re.search(r'\b' + re.escape(p_.lower()) + r'\b', said) for p_ in nm.split()):
        return False
    print(f'identify() says {nm}, but research has no fight of theirs in {conv_ep} and nobody says the name: not trusted', flush=True)
    return True


try:
    import charvis
    _parts = [charvis.identify(src, a_, a_ + L_, series_key, lo, hi, skip=_SKIP_SONG, expected=(PICK_NAME,) if PICK_NAME else (),
                               target=PICK_NAME, series_title=series_title, log=lambda m: print('identify:', m, flush=True))
              for a_, L_ in PIECES]
    _parts = [r_ for r_ in _parts if r_.get('votes')]
    if len(_parts) == 1:
        IDENT = _parts[0]
    elif _parts:                                                      # votes of every piece together, same 30% / 1.6x rule
        _v = {}
        for r_ in _parts:
            for nm_, c_ in r_['votes'].items():
                _v[nm_] = _v.get(nm_, 0) + c_
        _fr = sum(r_.get('frames', 0) for r_ in _parts)
        _o = sorted(_v, key=lambda nm_: -_v[nm_])
        _top_v, _run_v = _v[_o[0]], (_v[_o[1]] if len(_o) > 1 else 0)
        IDENT = dict(votes=dict(sorted(_v.items(), key=lambda kv: -kv[1])), frames=_fr, share=round(_top_v / max(1, _fr), 3),
                     margin=round(_top_v / max(1.0, _run_v), 2), runner=_o[1] if len(_o) > 1 else None,
                     name=_o[0] if _top_v / max(1, _fr) >= 0.30 and _top_v / max(1.0, _run_v) >= 1.6 else None,
                     per_frame=sum([r_.get('per_frame', []) for r_ in _parts], []))
        if PICK_NAME:
            _tv = sum(c_ for nm_, c_ in _v.items() if nm_.lower() == PICK_NAME.lower())
            IDENT['target_share'] = round(_tv / max(1, _fr), 3)
    print(f'identify votes for the talk {c0:.1f}-{c1:.1f}s: {IDENT.get("votes")} of {IDENT.get("frames")} frames '
          f'-> {IDENT.get("name") or "unsure"}' + (f' ({PICK_NAME} share {IDENT.get("target_share")})' if PICK_NAME else ''), flush=True)
    if PICK_NAME and IDENT.get('name') != PICK_NAME and IDENT.get('target_share', 0) < 0.25 \
            and os.environ.get('CONVO_IDENT_PICK', '1') == '1':
        # a Sukuna pick got Toji vs Dagon (Sukuna 18%): the talk itself must show the pick, or say their name
        _said = ' '.join(w['w'] for w in cw).lower()
        if not any(p_ and len(p_) >= 3 and re.search(r'\b' + re.escape(p_.lower()) + r'\b', _said) for p_ in PICK_NAME.split()):
            _left = [e for e in eps if e != conv_ep and e not in EP_EXCLUDE]
            if _left and not PIN and len(EP_EXCLUDE) < 3:
                print(f'the talk shows {IDENT.get("name")}, not {PICK_NAME} ({IDENT.get("target_share", 0):.0%}): trying another episode', flush=True)
                os.environ['CONVO_EP_EXCLUDE'] = ','.join(EP_EXCLUDE + [conv_ep]); os.environ.pop('CONVO_SKIP', None)
                os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
            if PIN and len(SKIP) < 4:                                   # pinned episode (run 45132798514 got Jogo): next talk moment there
                print(f'the talk shows {IDENT.get("name")}, not {PICK_NAME}: trying the next talk moment in {conv_ep}', flush=True)
                os.environ['CONVO_SKIP'] = ','.join(map(str, SKIP + [bt]))
                os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
    if not topic_name and IDENT.get('name') and not _not_in_episode(IDENT['name']):
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
        _fr = max(1, IDENT.get('frames') or sum(_v.values()) or 1)
        _recent = [c.get('topic') for c in hist.get('convos', [])[-4:] if c.get('topic')]   # last 4 Shorts' characters rest
        _ep_score = lambda nm: max([r.get('score', 0) for r in _rc[nm].get('ranked', []) if r.get('ep') == conv_ep] or [0])
        # a weak identify() vote only counts when it is a real share of the frames AND research says the character is in
        # this episode (fixes "Rengoku wins with 9/22 frames in S1E11", an episode he is not in)
        voted = [nm for nm in mains if _v.get(nm, 0) / _fr >= 0.20 and _ep_score(nm) >= 2.0
                 and char_slug(nm, series_key) not in _recent]
        if voted:
            topic_name = max(voted, key=lambda nm: _v[nm])
        else:
            here = [(_ep_score(nm), nm) for nm in mains if char_slug(nm, series_key) not in _recent]
            here = [x for x in here if x[0] > 0]
            if here:
                topic_name = max(here)[1]
                TOPIC_GUESS = True                                     # just the main with the best score for this episode
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
        times = [a_ + L_ * fr for a_, L_ in PIECES for fr in ((0.2, 0.4, 0.6, 0.8) if len(PIECES) == 1 else (0.3, 0.7))][:6]
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
                    TOPIC_GUESS = True
                    print('conversation character from the 4-frame reference match:', topic_name, flush=True)
    except Exception as ex:
        print('charvis conversation identification skipped:', ex, flush=True)

print(f'conversation character identified: {topic_name} ({topic_slug})', flush=True)
if PICK == 'auto' and topic_slug and not TOPIC_GUESS and topic_slug in RECENT_TOPICS and len(AVOID) < 3 \
        and os.environ.get('REPEAT_GUARD', '1') != '0':                # same character as a recent Short: another episode
    print(f'{topic_slug} was in one of the last {len(RECENT_TOPICS)} Shorts, re-picking without {conv_ep}', flush=True)
    os.environ['CONVO_AVOID_EPS'] = ','.join(AVOID + [conv_ep])
    os.environ.pop('CONVO_SKIP', None)
    os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])

# ------------------------------------------------------------------ 5b. the question shown at the top during the talk only
QUESTION_ON = os.environ.get('QUESTION', '1') != '0'


def _clean_q(q):
    q = re.sub(r'[\r\n"\u201c\u201d*#{}\\]+', ' ', q or '').strip()
    q = re.sub(r'\s+', ' ', q)
    q = re.sub(r'^(question|q)\s*[:\-]\s*', '', q, flags=re.I)
    if not q or len(q.split()) > 9 or len(q) > 60:
        return None
    return q if q.endswith('?') else q.rstrip('.!') + '?'


def _ep_score_of(nm):
    try:
        rc = json.load(open('research_cache.json')).get(series_key, {}).get('characters', {})
        return max([r.get('score', 0) for r in rc.get(nm, {}).get('ranked', []) if r.get('ep') == conv_ep] or [0])
    except Exception:
        return 0


def _on_screen():
    """Who the question may name. identify() is noisy (it saw Enmu and Rengoku in Swordsmith Village), so a name counts only
    when it is said in the talk, or identify() saw it in 30%+ of the frames, or 15%+ AND research puts it in this episode."""
    talk_l = ' '.join(SEGS[k]['t'] for k in SEL).lower()
    heard = []
    for nm, als in _known_names().items():
        if any(len(a_) >= 3 and re.search(r'\b' + re.escape(a_.lower()) + r'\b', talk_l) for a_ in als if a_):
            heard.append(nm)
    _v, _fr = IDENT.get('votes') or {}, max(1, IDENT.get('frames') or 1)
    seen = [nm for nm, c in _v.items() if (c / _fr >= 0.30 and not _not_in_episode(nm)) or (c / _fr >= 0.15 and _ep_score_of(nm) >= 2.0)]
    names = []
    for nm in ([topic_name] if topic_name and (topic_name in heard or topic_name in seen or not (heard or seen or TOPIC_GUESS)) else []) + heard + seen:
        if nm and nm not in names:
            names.append(nm)
    return names[:3]


def _known_names():
    """Every name/alias of the series cast, so a question naming someone off screen can be caught."""
    out = {}
    for nm, d in (series_lore or {}).items():
        out[nm] = [nm] + list(d.get('names', []))
    try:
        for nm in json.load(open('research_cache.json')).get(series_key, {}).get('characters', {}):
            out.setdefault(nm, [nm])
    except Exception:
        pass
    try:
        import research
        for nm, al in (research.character_names(series_key) or {}).items():
            out.setdefault(nm, [nm]); out[nm] += list(al)
    except Exception:
        pass
    for nm in (IDENT.get('votes') or {}):
        out.setdefault(nm, [nm])
    return out


def _off_screen_name(q, here):
    ql = q.lower()
    here_l = {h.lower() for h in here}
    here_words = {w for h in here for w in h.lower().split()}
    for nm, als in _known_names().items():
        if nm.lower() in here_l:
            continue
        for a in als + nm.split():
            a = (a or '').lower().strip()
            if len(a) < 3 or a in here_words:
                continue
            if re.search(r'\b' + re.escape(a) + r'\b', ql):
                return nm
    return None


def make_question():
    if not QUESTION_ON:
        return None
    if os.environ.get('QUESTION_TEXT', '').strip():
        return _clean_q(os.environ['QUESTION_TEXT'])
    here = _on_screen()
    _ws = lambda n_: set(re.findall(r'\w+', n_.lower()))
    here = [n_ for n_ in here if not any(o_ != n_ and _ws(n_) < _ws(o_) for o_ in here)]   # 'Sukuna' and 'Ryomen Sukuna'
    here = list(dict.fromkeys(here))                                  # are one person (run 45153670807 asked 'Sukuna or Ryomen Sukuna?')
    first = here[0].split()[0] if here else ''
    talk = ' '.join(SEGS[k]['t'] for k in SEL)
    print('on screen for the question:', here, flush=True)
    who_txt = ', '.join(here) if here else (topic_name or 'unknown')
    try:
        groq = _load_groq()
        for attempt in range(2):
            out, mdl = groq(
                f"Anime: {EPISODES[conv_ep]['series'].replace('-', ' ')}. Characters ON SCREEN in this clip: {who_txt}.\n"
                f"What they say in the clip (auto-translated): {talk}\n\n"
                "Write ONE short question (4 to 8 words) shown as big text at the top of the video while they talk. "
                "It must make a viewer stop scrolling and want to argue in the comments. "
                "ONLY name characters from the on-screen list above; never bring in anyone else from the series. "
                "Best kinds: a power debate between two on-screen characters ('Who wins: A or B?'), a hard 'why' about "
                "what happens here ('Why didn't A finish it?'), or a bold opinion to defend ('Was A wrong here?'). "
                "If only one character is listed, use a why or opinion question, not a versus. Avoid soft feelings "
                "questions. Use the names fans use. Do not spoil the ending, no emojis, no hashtags, no quotes. "
                "Reply with the question only.",
                temperature=0.9 if attempt == 0 else 0.5,
                system='You write scroll-stopping on-screen questions for anime YouTube Shorts.')
            q = _clean_q(out.strip().splitlines()[0] if out.strip() else '')
            if not q:
                print('question from groq unusable:', out[:120], flush=True)
                continue
            bad = _off_screen_name(q, here)
            if bad:
                print(f'question rejected, names {bad} who is not on screen: {q}', flush=True)
                continue
            print(f'question ({mdl}): {q}', flush=True)
            return q
    except Exception as ex:
        print('question groq skipped:', ex, flush=True)
    who = first or 'he'
    if not first:
        return rng.choice(['Who wins this fight?', 'Who survives this?', 'Can anyone stop this?'])
    pool = [f'Did {who} just go too far?', f'Was {who} right here?', f'Would you survive {who}?',
            f'Is {who} stronger than you think?', 'Who wins this fight?']
    if len(here) >= 2:
        pool.append(f"Who wins: {here[0].split()[0]} or {here[1].split()[0]}?")
    return rng.choice(pool)


QUESTION_TXT = make_question()
print('top question:', QUESTION_TXT, flush=True)

# Update convo.json with identified character
try:
    cinfo = json.load(open('work/convo/convo.json'))
    cinfo.update(character=topic_slug, character_name=topic_name, question=QUESTION_TXT,
                 topic_guess=bool(TOPIC_GUESS), title_name=(None if TOPIC_GUESS else topic_name))   # a guess never goes in the title
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
# rank by the researched fight score; an episode under ~40% of the best score (or under 5) is not a fight source while
# enough stronger ones exist - not even the talk episode. More episodes so the impact gate is met before it relaxes.
MAX_FIGHT = int(os.environ.get('CONVO_FIGHT_EPS', 5))
_sc = {e: float(v) for e, v in ((_rinfo or {}).get('scores') or {}).items() if e in EPISODES} if _researched else {}
if _sc:
    _floor = max(5.0, 0.4 * max(_sc.values()))
    _strong = sorted((e for e in _sc if _sc[e] >= _floor), key=lambda e: -_sc[e])
    _hand = [e for e in _fw if e in EPISODES]
    _extra = [e for e in fight_eps if e not in _sc and e not in _hand]          # character map only, never scored low
    if len(set(_hand + _strong)) >= 3:
        amv_eps = list(dict.fromkeys(_hand + _strong + _extra))[:MAX_FIGHT]
        _weak = [e for e in list(dict.fromkeys([conv_ep] + fight_eps)) if e not in amv_eps and e in _sc and _sc[e] < _floor]
        print(f'fight episodes by research score (floor {_floor:.2f}): ' + ', '.join(f'{e.split(":")[-1]} {_sc[e]}' for e in _strong)
              + (f' | dropped weak: ' + ', '.join(f'{e.split(":")[-1]} {_sc[e]}' for e in _weak) if _weak else ''), flush=True)
    else:
        amv_eps = list(dict.fromkeys([conv_ep] + fight_eps))[:MAX_FIGHT]
else:
    amv_eps = list(dict.fromkeys([conv_ep] + fight_eps))[:MAX_FIGHT] if fight_eps else [conv_ep]
if TOPIC_GUESS and os.environ.get('EDIT_FROM_TALK', '1') != '0':
    # the character is only a guess (the Urogi talk was labelled Muichiro, so the edit showed his fights): build the edit
    # from the talk's own fight instead - its episode and the ones right around it - with no character filter
    _m = re.match(r'(.*S\d+E)(\d+)$', conv_ep)
    _near = [conv_ep]
    if _m:
        _n = int(_m.group(2))
        for d_ in (1, -1, 2, -2):
            _c = f'{_m.group(1)}{_n + d_:0{len(_m.group(2))}d}'
            if _c in EPISODES:
                _near.append(_c)
    amv_eps = _near[:3]
    print(f'character "{topic_name}" is only a guess: the edit comes from the talk\'s own fight {amv_eps}', flush=True)
# SAME FIGHT (default; EDIT_SAME_FIGHT=0 turns it off): the edit shows the fight the talk belongs to, never the
# character's other fights or neighbouring episodes (run 45629584475 mixed S3E02/03/04). Any anime: the talk's episode,
# inside a known fight window holding the talk, else grown around the talk only as far as needed; no character filter.
SAME_FIGHT = os.environ.get('EDIT_SAME_FIGHT', '1') != '0'
fight_a, fight_b = c0, c1
if SAME_FIGHT:
    try:
        _fwj = json.load(open('fight_windows.json'))
        _srcs = [_fwj.get(topic_slug or '', {})] + [{e_: (d_.get('windows') or []) for e_, d_ in v_.items() if isinstance(d_, dict)}
                                                   for k_, v_ in (_fwj.get('_auto') or {}).items()
                                                   if k_ in (topic_slug, '_fight') and isinstance(v_, dict)]
        _wins = [tuple(w_) for src_ in _srcs for e_, ws_ in src_.items() if isinstance(ws_, list)
                 if (e_ if ':' in e_ else f'jujutsu-kaisen:{e_}') == conv_ep for w_ in ws_]
        _near = [w_ for w_ in _wins if w_[0] - 30 <= c1 and w_[1] + 30 >= c0]
        if _near:
            fight_a, fight_b = min([c0] + [w_[0] for w_ in _near]), max([c1] + [w_[1] for w_ in _near])
    except Exception as ex:
        print('fight window lookup skipped:', ex, flush=True)
    amv_eps = [conv_ep]
    print(f'same fight: the edit comes from {conv_ep} {fight_a:.0f}-{fight_b:.0f}s (the talk is {c0:.0f}-{c1:.0f}s)', flush=True)
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
           INCLUDE=f'{conv_ep}|{fight_a:.1f}|{fight_b:.1f}' if SAME_FIGHT else '',
           INCLUDE_NEED=os.environ.get('SAME_FIGHT_SHOTS', '36'), INCLUDE_MAXPAD=os.environ.get('SAME_FIGHT_MAXPAD', '60'),   # run 45773246175: 180 s of padding pulled in Gojo, Panda, Maki scenes
           START_BEAT='17', MAX_SECONDS=f'{amv_len:.2f}', W=str(W), H=str(H),
           AMV_STYLE='drop',                                        # the edit opens ON the drop (beat 17), one cut per beat
           MIN_SONG_START=f'{CONV + 0.6:.2f}',                      # room before the drop for the song bed under the talk
           EXCLUDE=f'{conv_ep}|{c0}|{c1}', OUT_NAME='_amv_part', PICK=PICK,
           CHAR_NAME='' if (TOPIC_GUESS or SAME_FIGHT) else (topic_name or ''),
           CHAR_SLUG='' if (TOPIC_GUESS or SAME_FIGHT) else (topic_slug or ''),
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
_hook = (
    f"[0:v]trim={hook_at:.3f}:{hook_at + HOOK:.3f},setpts=PTS-STARTPTS,fps={FPS}[hv];"
    f"[0:a]atrim={hook_at:.3f}:{hook_at + HOOK:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={HOOK - 0.25}:d=0.25,volume=0.8[ha];"
) if HOOK > 0 else ''
fc = (
    _hook +
    f"[1:v]setpts=PTS-STARTPTS,fps={FPS},ass=work/convo/captions_shift.ass[cv];"
    f"[2:a]asetpts=PTS-STARTPTS,loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo[dl];"
    f"[3:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={BED_VOL},afade=t=in:d=1.0[bd];"
    f"[dl][bd]amix=inputs=2:duration=first:normalize=0[ca];"
    f"[0:v]setpts=PTS-STARTPTS,fps={FPS}[av];[0:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[aa];"
    + (f"[hv][ha][cv][ca][av][aa]concat=n=3:v=1:a=1[v][a]" if HOOK > 0 else f"[cv][ca][av][aa]concat=n=2:v=1:a=1[v][a]")
)
# captions were timed from the start of the short (hook included); the conversation clip starts at 0
txt = open('work/convo/captions.ass').read()
txt = re.sub(r'(\d+:\d\d:\d\d\.\d\d)', lambda m: ts(max(0, sum(float(x) * f for x, f in zip(m.group(1).split(':'), (3600, 60, 1))) - HOOK)), txt)
if QUESTION_TXT:                                                     # top question: talk part only, never on the edit
    _qw = QUESTION_TXT.upper().split(); _qrows, _cur = [], ''
    for w_ in _qw:
        if _cur and len(_cur) + 1 + len(w_) > int(os.environ.get('QUESTION_WRAP', 18)):
            _qrows.append(_cur); _cur = w_
        else:
            _cur = (_cur + ' ' + w_).strip()
    _qrows.append(_cur)
    _qfs = int(os.environ.get('QUESTION_SIZE', 72))
    _qy = int(H * float(os.environ.get('QUESTION_Y', 0.06)))
    _q = '\\N'.join(_qrows)
    txt = txt.rstrip('\n') + '\n' + (
        f"Dialogue: 2,{ts(0)},{ts(CONV)},Cap,,0,0,0,,{{\\an8\\pos({W // 2},{_qy})\\fs{_qfs}\\bord7\\3c&H00000000&\\shad4"
        f"\\4a&H60&\\1c&H00FFFFFF&\\fad(150,0)}}{_q}\n")
open('work/convo/captions_shift.ass', 'w').write(txt)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', amv, '-i', 'work/convo/video.mp4',
    '-i', VOICE,
    '-ss', f'{bed_ss:.3f}', '-t', f'{CONV + 0.5:.3f}', '-i', song_file,
    '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'../out/{name}.mp4'])
os.remove(amv)
print('wrote', f'out/{name}.mp4', flush=True)

hist = json.load(open('history.json'))
hist.setdefault('convos', []).append(dict(ep=conv_ep, s=c0, e=c1, topic=topic_slug, question=QUESTION_TXT, file=f'{name}.mp4', time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
json.dump(hist, open('history.json', 'w'), indent=1)
