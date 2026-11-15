"""Narrated Shorts: a serious narrator over a fight scene, then the beat-synced edit.
   1.5 s cold-open hook -> ~15-25 s of fight footage with a narrator (scene / character facts / praise),
   burned-in captions in the same style -> long edit from the same fight scene.   3:4 (1080x1440).
   No anime audio is used at all: only the narrator and our song (copyright-safe).
   Narration text: Groq (GROQ_API_KEY secret) using the scene's translated dialogue as context;
   voice: edge-tts (free Microsoft neural voices).
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
PICK = (os.environ.get('CHARACTER') or os.environ.get('PICK') or 'auto').strip().lower()
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
# every Short is about ONE topic character: the narration names them and the edit only uses their fight episodes
LORE_ALL = json.load(open('lore.json'))
def lore_name(key, series):
    for nm, d in LORE_ALL.get(series, {}).items():
        if key in d['names'] or key == nm.lower():
            return nm
    return None
avail = {c: [e for e in v if e in EPISODES] for c, v in chars.items()}
avail = {c: v for c, v in avail.items() if v and lore_name(c, EPISODES[v[0]]['series'])}
if PICK in avail:
    TOPIC = PICK
else:                                                                 # auto / an anime name: rotate through that anime's characters
    series = match[0] if match else (EPISODES[new_eps[0]]['series'] if new_eps else least_used(series_all, hist.get('series', {}), 1)[0])
    pool_c = [c for c, v in avail.items() if EPISODES[v[0]]['series'] == series] or list(avail)
    TOPIC = least_used(pool_c, hist.get('narr_chars', {}), 1)[0]
cand = avail[TOPIC]
TOPIC_NAME = lore_name(TOPIC, EPISODES[cand[0]]['series'])
print('topic character', TOPIC, '->', TOPIC_NAME, '|', len(cand), 'mapped episodes', flush=True)
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
    return np.array([mot[i * SF:(i + 1) * SF].mean() + glow[i * SF:(i + 1) * SF].mean() for i in range(n)])

# ------------------------------------------------------------------ 2. pick the episode with the biggest fight, find it
FW = 90
best_all = None
for ep in eps:
    fetch(ep)
    d_ = duration(SRC(ep)); ps = motion(SRC(ep))
    lo_, hi_ = 150, int(d_) - 150                                        # skip openings and the ending/preview
    prev = [(c['s'], c['e']) for c in hist.get('convos', []) if c['ep'] == ep]
    for t in range(lo_, hi_ - FW, 5):
        if any(a_ - FW < t < b_ for a_, b_ in prev):
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
_fw = _sf.read('work/convo/full.wav', dtype='float32')[0]
loud = np.zeros(int(dur) + 1)                                         # per-second loudness: fights are loud (impacts, screams, score)
for k in range(len(_fw) // 16000):
    loud[lo + k] = np.sqrt(np.mean(_fw[k * 16000:(k + 1) * 16000] ** 2))
lref = np.percentile(loud[lo:hi], 90) + 1e-6
speech = np.zeros(int(dur) + 1)
for sg in _ss:
    if len((sg.text or '').split()) >= 3 and sg.avg_logprob > -1.0 and sg.no_speech_prob < 0.6:
        speech[int(lo + sg.start):int(lo + sg.end) + 1] = 1
SKIP = [float(x) for x in os.environ.get('CONVO_SKIP', '').split(',') if x]
prevc = [(c['s'], c['e']) for c in hist.get('convos', []) if c['ep'] == conv_ep]
bs, bt = -1, fight
for t in range(lo, hi - 40, 2):
    if any(a_ - 40 < t < b_ for a_, b_ in prevc) or any(abs(t - k) < 40 for k in SKIP):
        continue
    talk = speech[t:t + 24].mean()
    act = per_s[t:t + 24].mean() / mref
    lnd = loud[t:t + 24].mean() / lref
    sc = min(act, 1.3) * min(lnd, 1.3) + 0.5 * min(np.percentile(per_s[t:t + 24], 25) / mref, 1.0)   # sustained motion AND loud audio = a real fight
    if sc > bs:
        bs, bt = sc, t
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
# ------------------------------------------------------------------ 3. write the narration and voice it
import urllib.request, asyncio
series_name = EPISODES[conv_ep]['series'].replace('-', ' ').title()
context = ' '.join(w['w'] for w in words)[:1800]
LORE = json.load(open('lore.json')).get(EPISODES[conv_ep]['series'], {})
heard = {}
for nm, d in LORE.items():                                            # who is named in the scene's dialogue
    n = sum(len(re.findall(r'\b' + re.escape(a) + r'\b', context.lower())) for a in d['names'])
    if n: heard[nm] = n
if not heard:                                                         # names are rarely said inside 60 s: listen to ~5 min around the fight (dub or Japanese)
    w0, w1 = max(0, bt - 180), bt + 120
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(w0), '-t', str(w1 - w0), '-i', src, '-vn', '-ac', '1', '-ar', '16000', 'work/convo/wide.wav'])
    jtxt = ' '.join(sg.text for sg in WhisperModel('small', device='cpu', compute_type='int8').transcribe(
        _sf.read('work/convo/wide.wav', dtype='float32')[0], language=info.language if info.language in ('en', 'ja') else None, beam_size=1, vad_filter=True)[0])
    for nm, d in LORE.items():
        n = sum(jtxt.count(a) for a in d.get('ja', [])) + sum(len(re.findall(r'\b' + re.escape(a) + r'\b', jtxt.lower())) for a in d['names'])
        if n: heard[nm] = n
    print('names in wider audio:', heard, flush=True)
CHAR = TOPIC_NAME if TOPIC_NAME in LORE else (max(heard, key=heard.get) if heard else None)   # the topic character, never a guess
MODE = os.environ.get('NARRATION') or 'trailer'
FACTS = LORE[CHAR]['power'] if CHAR in LORE else ''
# technique / domain names the bars should drop (capitalised phrases in the lore, minus sentence starters)
TERMS = sorted({t.strip() for t in re.findall(r"(?<![.!?]\s)(?<!^)\b([A-Z][\w'-]+(?:\s(?:of\s)?[A-Z][\w'-]+)*)", FACTS)
                if t.split()[0] not in ('A', 'An', 'The', 'His', 'Her', 'Their', 'He', 'She', 'With', 'When', 'Born')} - {CHAR, CHAR.split()[0]} if CHAR else set())
first_name = CHAR.split()[0] if CHAR else 'the fighter'
ASK = (f"Write a hype poem about {CHAR} from {series_name}, voiced by a deep movie-trailer narrator, like spoken-word bars.\n"
       f"Facts you may use (and ONLY these, reworded): {FACTS}\n"
       "Rules:\n"
       "- 6 short lines, 5 to 9 words each. Lines 1 and 2 rhyme, lines 3 and 4 rhyme, lines 5 and 6 rhyme. Never end two lines on the same word, and never tack an extra rhyme word onto the end of a line.\n"
       f"- Name {first_name} in the first line.\n"
       "- Every single line must point at a real power, technique, battle or piece of lore from the facts above"
       + (f" (for example: {', '.join(sorted(TERMS)[:6])})" if TERMS else '') + ". No generic filler like 'rise up' or 'never give up'.\n"
       "- Do not invent names, numbers, techniques or events that are not in the facts.\n"
       "- Rhyme with plain, real English words that make sense (no forced or nonsense rhymes).\n"
       "- Style example for a different character (do not copy it): Six Eyes open, he sees it all, / Limitless space makes every fist stall,\n"
       "- One line per row, a comma or full stop at the end of each line, no title.")
prompt = (f"Anime: {series_name}. Scene: episode {conv_ep.split(':')[-1]}.\n"
          f"Dialogue heard in the scene (auto-translated, may contain errors): {context[:600] or '(no clear dialogue)'}\n\n"
          f"{ASK}\nNo emojis, no hashtags, no quotes, no stage directions. Reply with the six lines only.")

_STOP = set('the and with that this from into their they them have has had been were when which while will would can could only also more most than then over under after before about against there where what your his her its one two who whom same must each other just like very upon'.split())
LORE_WORDS = {w for w in re.findall(r"[a-z][a-z'-]{3,}", FACTS.lower()) if w not in _STOP} | {t.lower() for t in TERMS}

def _lines(raw):
    ls = [l.strip(' -\u2014') for l in re.split(r'\n', raw) if len(l.split()) >= 3]
    return ls[:6]

def _end(l):
    w = re.sub(r'[^a-z]', '', (l.split() or [''])[-1].lower())
    return w

def _rhyme_pair(a, b):
    if not a or not b or a == b:
        return False
    tail = lambda w: (re.search(r'[aeiouy]+[^aeiouy]*$', w).group(0) if re.search(r'[aeiouy]', w) else w)
    return a[-3:] == b[-3:] or tail(a) == tail(b) and len(tail(a)) >= 2 or a[-2:] == b[-2:]

def _score(raw):                                                      # higher is better; returns (score, lines)
    ls = _lines(raw)
    if len(ls) < 6:
        return -1, ls
    ends = [_end(l) for l in ls]
    rhymed = sum(_rhyme_pair(ends[i], ends[i + 1]) for i in (0, 2, 4))
    lore = sum(any(w in l.lower() for w in LORE_WORDS) for l in ls)     # lines that point at real powers / lore
    named = first_name.lower() in ' '.join(ls).lower()
    repeats = len(ends) - len(set(ends))
    words = sum(len(l.split()) for l in ls)
    sc = rhymed * 3 + lore + (3 if named else -6) - repeats * 2 - (4 if not 24 <= words <= 64 else 0)
    return sc, ls

best = (-99, [])
for i in range(5):
    try:
        ask = prompt + f"\n(Take {i + 1}: fresh wording, different rhymes.)"   # new text each try, so a cached reply is never reused
        raw_txt = re.sub(r'[*"#]|\(.*?\)', '', llm(ask).strip())
        sc, ls = _score(raw_txt)
        ok = len(ls) == 6 and sc >= 9 + 4                              # all 3 couplets rhyme, named, 4+ lore lines
        print('draft', 'ok' if ok else 'rejected', sc, '|', ' / '.join(ls), flush=True)
        if sc > best[0]:
            best = (sc, ls)
        if ok:
            break
    except Exception as ex:
        print('llm error', ex, getattr(ex, 'read', lambda: b'')()[:300], flush=True); time.sleep(20)
if best[0] >= 9:                                                      # at least two rhyming couplets, named, on-lore
    narration = ' '.join(l if l[-1] in '.,!?;' else l + ',' for l in best[1]).rstrip(',') + '.'
    narration = re.sub(r'\s+', ' ', narration)
else:                                                                 # last resort: safe lines that need no invented facts
    nm = CHAR.split()[0] if CHAR else 'the fighter'
    narration = f"This is {CHAR}. {FACTS}" if FACTS else f"This is {nm}, and this is the fight."
print('narration', MODE, CHAR, '|', narration, flush=True)

import edge_tts
VOICE_NAME = os.environ.get('VOICE', 'en-US-ChristopherNeural')   # deepest stock edge-tts male voice
async def _tts():
    com = edge_tts.Communicate(narration, VOICE_NAME, rate=os.environ.get('VOICE_RATE', '-4%'), pitch=os.environ.get('VOICE_PITCH', '-10Hz'), boundary='WordBoundary')
    bounds = []
    with open('work/convo/narr.mp3', 'wb') as f:
        async for ch in com.stream():
            if ch['type'] == 'audio':
                f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                bounds.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    return bounds
bounds = asyncio.run(_tts())
DEEP = float(os.environ.get('VOICE_DEEP', '0.88'))
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', 'work/convo/narr.mp3', '-af',
    f'aresample=48000,asetrate={int(48000 * DEEP)},aresample=48000,atempo={1 / DEEP:.5f},'   # pitch and formants down, same timing: a heavy trailer voice
    'highpass=f=45,bass=g=6:f=95:w=0.8,equalizer=f=3200:t=q:w=1.2:g=2,'                       # chest + presence
    'acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,'                        # dense, close-mic'd trailer read
    'aecho=0.8:0.55:55:0.10,loudnorm=I=-11:TP=-1.0,aresample=48000', '-ac', '2', 'work/convo/narr.wav'])

# natural pacing: squeeze any silence between words down so there are no long, awkward pauses
import soundfile as _sfv
MAX_GAP = float(os.environ.get('MAX_GAP', '0.28'))                   # longest pause kept between two words (s)
KEEP_GAP = float(os.environ.get('KEEP_GAP', '0.18'))                 # what a long pause is cut down to (s)
_a, _sr = _sfv.read('work/convo/narr.wav', dtype='float32')
cuts_ = []                                                            # (start, end) of audio to remove, in seconds
if bounds:
    if bounds[0][0] > 0.08:
        cuts_.append((0.0, bounds[0][0] - 0.04))                      # no dead air before the first word
    for (a0, b0, _), (a1, b1, _) in zip(bounds[:-1], bounds[1:]):
        if a1 - b0 > MAX_GAP:
            cuts_.append((b0 + KEEP_GAP * 0.5, a1 - KEEP_GAP * 0.5))
pieces, last, xf = [], 0, int(0.012 * _sr)
for c0_, c1_ in cuts_:
    i0, i1 = int(c0_ * _sr), int(c1_ * _sr)
    if i1 - i0 > 2 * xf:
        pieces.append((last, i0)); last = i1
pieces.append((last, len(_a)))
out_a = _a[pieces[0][0]:pieces[0][1]].copy()
for p0, p1 in pieces[1:]:
    nxt = _a[p0:p1].copy()
    if len(out_a) > xf and len(nxt) > xf:                            # 12 ms crossfade, no clicks
        r_ = np.linspace(0, 1, xf)[:, None] if _a.ndim == 2 else np.linspace(0, 1, xf)
        out_a[-xf:] = out_a[-xf:] * (1 - r_) + nxt[:xf] * r_
        nxt = nxt[xf:]
    out_a = np.concatenate([out_a, nxt])
_sfv.write('work/convo/narr.wav', out_a, _sr)
def _shift(t):                                                        # map an original time onto the tightened audio
    removed = sum(min(max(t - c0_, 0), c1_ - c0_) for c0_, c1_ in cuts_ if int(c1_ * _sr) - int(c0_ * _sr) > 2 * xf)
    return max(0.0, t - removed)
bounds = [(_shift(a), _shift(b), t) for a, b, t in bounds]
print(f'pacing: removed {sum(b - a for a, b in cuts_):.2f}s of pauses ({len(cuts_)} gaps)', flush=True)
LEAD = 0.05                                                           # the narrator speaks from the first frame
narr_len = duration('work/convo/narr.wav')
CONV = round((LEAD + narr_len + 0.35) * FPS) / FPS                  # short tail: the edit kicks in right after the last word
c0 = float(min(max(lo, fight), hi - CONV)); c0 = round(c0 * FPS) / FPS; c1 = c0 + CONV
toks = narration.split(); cw = []; ti = 0; sent = 0
for a, b, t in bounds:                                                # map spoken words back onto the text (keeps punctuation)
    w = toks[ti] if ti < len(toks) else t
    cw.append(dict(w=w, s=c0 + LEAD + a, e=c0 + LEAD + max(b, a + 0.12), seg=sent))
    if w[-1:] in '.?!':
        sent += 1
    ti += 1
words = cw
print(f'narrated {c0:.2f}-{c1:.2f}s ({CONV:.1f}s, {len(cw)} words)', flush=True)

# ------------------------------------------------------------------ 4. caption lines + speakers
CAP_SIZE = int(os.environ.get('CAPTION_SIZE', 68))                   # readable but never edge to edge
SAFE_X = int(os.environ.get('CAPTION_MARGIN', 80))                   # px kept clear at the left and right edges
LINE_CHARS = int(os.environ.get('CAPTION_LINE_CHARS', 14))           # wrap a caption line after ~14 characters
lines, cur = [], []
for k, w in enumerate(cw):
    if cur and (len(cur) >= 5 or sum(len(x['w']) + 1 for x in cur) + len(w['w']) > 2 * LINE_CHARS or w['s'] - cur[-1]['e'] > 0.6 or w['seg'] != cur[-1]['seg'] or
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
if False:                                                             # one voice: the narrator
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
Style: Cap,{FONT},{CAP_SIZE},&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H96000000,0,0,0,0,100,100,2,0,1,0,3,5,{SAFE_X},{SAFE_X},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""]
DIM = '&H00A0A0A0&'
CHAR_W = 0.66 * CAP_SIZE + 2                                          # ~width of one upper-case Montserrat ExtraBold glyph + spacing


def wrap_rows(toks):                                                  # greedy word wrap: each row <= LINE_CHARS characters
    rows, row = [], []
    for t in toks:
        if row and len(' '.join(row + [t])) > LINE_CHARS:
            rows.append(row); row = []
        row.append(t)
    if row:
        rows.append(row)
    return rows


def fit_scale(rows):                                                  # a single very long word: shrink it so it still fits inside the margins
    widest = max(len(' '.join(r)) for r in rows) * CHAR_W + 2 * 18   # + glow border on both sides
    room = W - 2 * SAFE_X
    return 100.0 if widest <= room else max(55.0, 100.0 * room / widest)

for li, ln in enumerate(lines):
    col = colour_of[spk[li]]
    t_end = min(ln[-1]['e'] + 0.35, lines[li + 1][0]['s'] if li + 1 < len(lines) else c1) - c0 + HOOK
    toks = [clean(w['w']) for w in ln]
    toks = [t for t in toks if t]
    if not toks:
        continue
    rows = wrap_rows(toks)
    breaks = set(); acc = 0
    for r_ in rows[:-1]:
        acc += len(r_); breaks.add(acc - 1)                          # index of the last word on each row
    fit = fit_scale(rows)
    for k in range(len(toks)):                                        # word-by-word: spoken white, the rest dim
        a = ln[min(k, len(ln) - 1)]['s'] - c0 + HOOK
        b = (ln[k + 1]['s'] - c0 + HOOK) if k + 1 < len(toks) and k + 1 < len(ln) else t_end
        if b <= a:
            continue
        parts = []
        for m, t in enumerate(toks):
            parts.append(('{\\1c&H00FFFFFF&}' if m <= k else '{\\1c' + DIM + '}') + t)
            if m in breaks and m != len(toks) - 1:
                parts.append('\\N')
            elif m != len(toks) - 1:
                parts.append(' ')
        txt = ''.join(parts).replace(' \\N', '\\N')
        pop = (f'{{\\fscx{fit * 1.06:.0f}\\fscy{fit * 1.06:.0f}\\t(0,90,\\fscx{fit:.0f}\\fscy{fit:.0f})}}' if k == 0
               else f'{{\\fscx{fit:.0f}\\fscy{fit:.0f}}}')
        glow = f'{{\\pos({W // 2},{int(H * 0.53)})\\bord18\\blur16\\3c{ass_col(col)}\\3a&H20&\\shad0\\1a&HFF&}}'
        main = f'{{\\pos({W // 2},{int(H * 0.53)})\\bord4\\blur3\\3c{ass_col(col)}\\shad3}}'
        ass.append(f'Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{glow}{pop}{txt}')
        ass.append(f'Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{main}{pop}{txt}')
open('work/convo/captions.ass', 'w').write('\n'.join(ass) + '\n')
json.dump(dict(ep=conv_ep, s=c0, e=c1, mode=MODE, character=CHAR, lines=[dict(t=' '.join(w['w'] for w in ln), speaker=int(spk[i]), colour=colour_of[spk[i]])
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

VOICE = 'work/convo/narr.wav'

# ------------------------------------------------------------------ 6. the AMV part (auto.py), then join
amv_len = max(14.0, TOTAL - CONV)                                   # no cold-open hook any more: the narrator opens the Short
# multi-fight edit: fights from SEVERAL of the topic character's episodes across the whole anime (no single-scene INCLUDE lock)
AMV_EPS = int(os.environ.get('AMV_EPS', 4))
amv_eps = [conv_ep] + [e for e in eps if e != conv_ep]               # already downloaded and scanned above
amv_eps += least_used([e for e in cand if e not in amv_eps], used_eps, max(0, AMV_EPS - len(amv_eps)))
amv_eps = amv_eps[:max(2, AMV_EPS)]
print('AMV episodes for', CHAR, ':', amv_eps, flush=True)
env = {k: v for k, v in os.environ.items() if k != 'INCLUDE'}
env.update(FORCE_EPS=','.join(amv_eps), START_BEAT='9', MAX_SECONDS=f'{amv_len:.2f}', W=str(W), H=str(H),
           EXCLUDE=f'{conv_ep}|{c0}|{c1}', OUT_NAME='_amv_part', PICK=TOPIC, BALANCE_EPS='1')
subprocess.run([sys.executable, 'auto.py'], env=env, check=True)
amv = '../out/_amv_part.mp4'
plan = json.load(open('work/edit_plan.json'))
P = 60.0 / plan['tempo']
hook_at = (17 - 9) * P                                                # the first drop inside the AMV part
name = re.sub(r'[^A-Za-z0-9]+', '_', EPISODES[conv_ep]['series'].title()) + '_narrated_' + plan['song']
# the same song plays quietly under the conversation and runs straight into the edit at full volume
BED_LUFS = float(os.environ.get('BED_LUFS', '-26'))                   # phonk under the narrator: fixed loudness, ducked further while he speaks
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
# the bed is the stretch of the song right BEFORE the edit's own start, so the phonk runs on without restarting
song_start = float(plan.get('song_start', 0.0))
bed_ss = song_start - CONV
if bed_ss >= 0:
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{bed_ss:.3f}', '-t', f'{CONV:.3f}', '-i', song_file, '-ac', '2', '-ar', '48000', 'work/convo/bed.wav'])
else:                                                                 # edit starts in the intro: borrow a later bar that sounds the same as the edit's
    import librosa as _lb                                             # first bar (phonk repeats in phrases), so the hand-off is seamless
    yy, sr = _lb.load(song_file, sr=22050, mono=True)
    P_ = 60.0 / plan['tempo']
    ch = _lb.feature.chroma_cqt(y=yy, sr=sr, hop_length=512); rms = _lb.feature.rms(y=yy, hop_length=512)[0]
    fr = lambda t: int(t * sr / 512)
    def look(t, d=4.0):
        v = ch[:, fr(t):fr(t + d)]; return v / (np.linalg.norm(v) + 1e-9) if v.shape[1] >= fr(d) - 1 else None
    ref = look(song_start); cands = []
    for k in range(4, 400, 4):                                        # whole bars after the edit start
        t = song_start + k * P_
        if t + 4 > len(yy) / sr: break
        v = look(t)
        if t < CONV or v is None or ref is None or v.shape != ref.shape: continue
        cands.append((float((v * ref).sum()), float(np.percentile(rms[fr(t - CONV):fr(t)], 20)), t))
    top = max((c[0] for c in cands), default=0)
    best = (0, max((c for c in cands if c[0] >= top - 0.05), key=lambda c: c[1])[2] if cands else None)
    print('bed borrowed from bar at', best[1], f'(similarity {top:.2f})', flush=True)
    t = best[1] if best[1] is not None else _busy_part(song_file, CONV) + CONV
    bed_ss = t - CONV
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{bed_ss:.3f}', '-t', f'{CONV:.3f}', '-i', song_file, '-ac', '2', '-ar', '48000', 'work/convo/bed.wav'])
print(f'song bed {bed_ss:.1f}s -> {song_start:.1f}s (edit starts there)', flush=True)
# ONE continuous phonk track from the first frame to the last: never restarted, never cut.
# It is ducked with a volume expression while the narrator speaks (NOT sidechaincompress, which ends with the
# shorter voice input and leaves the rest of the Short silent), then rises smoothly when the edit takes over.
amv_dur = duration(amv)
TOTAL_DUR = round((CONV + amv_dur) * FPS) / FPS
VOICE_END = LEAD + narr_len                                           # last narrated sample, on the Short's clock
DUCK = float(os.environ.get('DUCK_LEVEL', '0.20'))                    # BGM gain under the narrator
RISE = float(os.environ.get('DUCK_RISE', '0.6'))                      # seconds for the BGM to come back up
BGM_LUFS = float(os.environ.get('BGM_LUFS', '-12'))
bgm_ss = bed_ss
if bgm_ss + TOTAL_DUR > song_len:                                     # not enough song left: start whole bars earlier (beat grid kept)
    bars = int(np.ceil((bgm_ss + TOTAL_DUR - song_len) / (4 * P)))
    bgm_ss = max(0.0, bgm_ss - bars * 4 * P)
print(f'continuous bgm {bgm_ss:.2f}s -> {bgm_ss + TOTAL_DUR:.2f}s, ducked to {DUCK} until {VOICE_END:.2f}s, total {TOTAL_DUR:.2f}s', flush=True)
duck_expr = f"if(lt(t,{VOICE_END:.3f}),{DUCK},{DUCK}+({1 - DUCK:.3f})*min(1,(t-{VOICE_END:.3f})/{RISE}))"
fc = (
    f"[1:v]setpts=PTS-STARTPTS,fps={FPS},ass=work/convo/captions_shift.ass,trim=duration={CONV:.3f}[cv];"
    f"[0:v]setpts=PTS-STARTPTS,fps={FPS}[av];"
    f"[cv][av]concat=n=2:v=1:a=0[v];"
    f"[2:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-11:TP=-1.0:LRA=9,aresample=48000,"
    f"adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad=whole_dur={TOTAL_DUR:.3f}[vo];"
    f"[3:a]atrim=start={bgm_ss:.3f}:duration={TOTAL_DUR:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
    f"loudnorm=I={BGM_LUFS}:TP=-1.5:LRA=11,aresample=48000,apad=whole_dur={TOTAL_DUR:.3f},"
    f"volume=eval=frame:volume='{duck_expr}'[bg];"
    f"[vo][bg]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95,"
    f"afade=t=out:st={max(0.0, TOTAL_DUR - 1.2):.3f}:d=1.2,atrim=duration={TOTAL_DUR:.3f}[a]"
)
# captions were timed from the start of the short (hook included); the conversation clip starts at 0
txt = open('work/convo/captions.ass').read()
txt = re.sub(r'(\d+:\d\d:\d\d\.\d\d)', lambda m: ts(max(0, sum(float(x) * f for x, f in zip(m.group(1).split(':'), (3600, 60, 1))) - HOOK)), txt)
open('work/convo/captions_shift.ass', 'w').write(txt)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', amv, '-i', 'work/convo/video.mp4',
    '-i', VOICE,
    '-i', song_file,
    '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'../out/{name}.mp4'])
os.remove(amv)
print('wrote', f'out/{name}.mp4', flush=True)

out_dir = os.path.abspath('../out')
os.makedirs(out_dir, exist_ok=True)
video_file = os.path.join(out_dir, f'{name}.mp4')
series_key = conv_ep.split(':')[0]
series_title = series_key.replace('-', ' ').title()
tag_series = series_key.replace('-', '')
rng_m = random.Random()
first = CHAR.split()[0] if CHAR else series_title
if MODE == 'character' and CHAR and CHAR in LORE:
    meta_title = rng_m.choice([f'Who is {CHAR}? 🤯', f'{CHAR} explained in 20 seconds 🔥', f"{first}'s power is unreal 😳"])
    meta_desc = f"{CHAR}'s power, explained.\n\n{LORE[CHAR].get('power', '')}"
else:
    meta_title = rng_m.choice([f'{first} hits different 🥶', f'This {series_title} edit goes hard 🔥', f'{first} quote that hits hard 🥶'])
    meta_desc = ' '.join(' '.join(w['w'] for w in ln) for ln in lines) if lines else f"{series_title} anime edit"

meta_title = meta_title[:90] + ' #shorts'
tags = ['shorts', 'anime', 'animeedit', tag_series, 'phonk', 'amv']
meta_desc = f"{meta_desc}\n\n#{tag_series} #animeedit #anime #phonk #shorts"
meta = dict(file=video_file, style='narrated', ep=conv_ep, title=meta_title, description=meta_desc, tags=tags)
json.dump(meta, open(os.path.join(out_dir, 'meta.json'), 'w'), indent=1, ensure_ascii=False)

hist = json.load(open('history.json'))
hist.setdefault('narr_chars', {})[TOPIC] = hist.get('narr_chars', {}).get(TOPIC, 0) + 1
hist.setdefault('convos', []).append(dict(ep=conv_ep, s=c0, e=c1, character=TOPIC, file=f'{name}.mp4', time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
json.dump(hist, open('history.json', 'w'), indent=1)
