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
    sc = 0.3 * talk + 1.5 * min(act, 1.3)                         # narrator: action first, some talk for context
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
CHAR = max(heard, key=heard.get) if heard else None
MODE = os.environ.get('NARRATION') or ('character' if CHAR and rng.random() < 0.5 else 'rhyme')
if MODE == 'character' and not CHAR:
    MODE = 'rhyme'                                                    # never guess who is on screen
if MODE == 'character':
    ASK = (f"Introduce {CHAR} and explain their power to someone who has never watched the anime. "
           f"Use ONLY these facts, reworded: {LORE[CHAR]['power']} Do not add any other names, techniques, numbers or events.")
    WORDS = '34 to 46 words of narration'
else:
    who = f"{CHAR}, using their ideals, struggle and power ({LORE[CHAR]['power']})" if CHAR else 'the fighters in this scene and what is at stake'
    ASK = (f"Write a rhyming quote, like a dark motivational poem, about {who}. "
           "Four to six short lines in rhyming couplets (AABB), every line ending in a strong rhyme. Do not name any techniques, places or people other than "
           + (CHAR.split()[0] if CHAR else 'none') + ".")
    WORDS = '30 to 46 words'
prompt = (f"Anime: {series_name}, episode {conv_ep.split(':')[-1]}.\n"
          f"Dialogue heard in the scene (auto-translated, may contain errors): {context or '(no clear dialogue)'}\n\n"
          f"{ASK}\nWrite {WORDS} for a YouTube Short, serious, deep, cinematic tone. "
          "Never invent facts. Plain sentences, no emojis, "
          "no hashtags, no quotes, no stage directions, no titles. Reply with the text only.")

def llm(prompt):
    key = os.environ.get('GROQ_API_KEY')
    if key:
        req = urllib.request.Request('https://api.groq.com/openai/v1/chat/completions', method='POST',
            data=json.dumps(dict(model=os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile'), temperature=0.7,
                                 messages=[dict(role='user', content=prompt)])).encode(),
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'User-Agent': 'narrate/1.0'})
        return json.load(urllib.request.urlopen(req, timeout=60))['choices'][0]['message']['content']
    req = urllib.request.Request('https://text.pollinations.ai/openai', method='POST',     # free fallback, no key
        data=json.dumps(dict(model='openai', max_tokens=3000, reasoning_effort='low', messages=[dict(role='system', content='You write short narration and rhyming quotes about anime for YouTube Shorts.'), dict(role='user', content=prompt)])).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(req, timeout=90))['choices'][0]['message']['content']

for _ in range(3):
    try:
        narration = re.sub(r'\s+', ' ', re.sub(r'(?<![.,!?;:])[ \t]*\n+', '. ', re.sub(r'[*"#]|\(.*?\)', '', re.sub(r'[ \t]+\n', '\n', llm(prompt).strip())))).strip()
        if 20 <= len(narration.split()) <= 70 and (MODE != 'character' or CHAR.split()[0] in narration):
            break
    except Exception as ex:
        print('llm error', ex, getattr(ex, 'read', lambda: b'')()[:300], flush=True); time.sleep(50)
else:                                                                 # last resort: safe lines that need no invented facts
    nm = CHAR.split()[0] if CHAR else 'the fighter'
    narration = (f"This is {CHAR}. {LORE[CHAR]['power']}" if MODE == 'character' else rng.choice([
        f"They said to kneel, they said to fall. {nm} rose up and faced it all. Every scar became a vow, the weak one is the hunter now.",
        f"Pain is the teacher, blood is the test. {nm} gives everything, nothing less. When the world says stop, the heart says go, the strongest fire burns slow."]))
print('narration', MODE, CHAR, '|', narration, flush=True)

import edge_tts
VOICE_NAME = os.environ.get('VOICE', 'en-US-ChristopherNeural')
async def _tts():
    com = edge_tts.Communicate(narration, VOICE_NAME, rate=os.environ.get('VOICE_RATE', '-10%'), pitch=os.environ.get('VOICE_PITCH', '-12Hz'), boundary='WordBoundary')
    bounds = []
    with open('work/convo/narr.mp3', 'wb') as f:
        async for ch in com.stream():
            if ch['type'] == 'audio':
                f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                bounds.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    return bounds
bounds = asyncio.run(_tts())
DEEP = float(os.environ.get('VOICE_DEEP', '0.86'))
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', 'work/convo/narr.mp3', '-af',
    f'aresample=48000,asetrate={int(48000 * DEEP)},aresample=48000,atempo={1 / DEEP:.5f},'   # pitch and formants down, same timing: a heavy trailer voice
    'bass=g=4:f=110,aecho=0.8:0.6:45:0.12,loudnorm=I=-11:TP=-1.0,aresample=48000', '-ac', '2', 'work/convo/narr.wav'])
LEAD = 0.05                                                           # the narrator speaks from the first frame
narr_len = duration('work/convo/narr.wav')
CONV = round((LEAD + narr_len + 0.7) * FPS) / FPS
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
env = dict(os.environ, FORCE_EPS=conv_ep, INCLUDE=f'{conv_ep}|{c0 - 150:.1f}|{c1 + 150:.1f}', START_BEAT='9', MAX_SECONDS=f'{amv_len:.2f}', W=str(W), H=str(H),
           EXCLUDE=f'{conv_ep}|{c0}|{c1}', OUT_NAME='_amv_part', PICK=PICK)
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
else:                                                                 # edit starts early in the song: lead in with its loudest part, then the run-up
    head = -bed_ss; busy = _busy_part(song_file, head + 0.5)
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{busy:.3f}', '-t', f'{head + 0.4:.3f}', '-i', song_file, '-ss', '0', '-t', f'{song_start:.3f}', '-i', song_file,
        '-filter_complex', '[0:a][1:a]acrossfade=d=0.4:c1=tri:c2=tri,aresample=48000[a]', '-map', '[a]', '-ac', '2', 'work/convo/bed.wav'])
print(f'song bed {bed_ss:.1f}s -> {song_start:.1f}s (edit starts there)', flush=True)
fc = (
    f"[1:v]setpts=PTS-STARTPTS,fps={FPS},ass=work/convo/captions_shift.ass[cv];"
    f"[2:a]asetpts=PTS-STARTPTS,adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad=whole_dur={CONV:.3f},aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-11:TP=-1.0:LRA=9,aresample=48000,asplit=2[dl][sc];"
    f"[3:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,loudnorm=I={BED_LUFS}:TP=-9:LRA=7,aresample=48000[bdr];"
    f"[bdr][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350:makeup=1[bd];"
    f"[dl][bd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[ca];"
    f"[0:v]setpts=PTS-STARTPTS,fps={FPS}[av];[0:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[aa];"
    f"[cv][ca][av][aa]concat=n=2:v=1:a=1[v][a]"
)
# captions were timed from the start of the short (hook included); the conversation clip starts at 0
txt = open('work/convo/captions.ass').read()
txt = re.sub(r'(\d+:\d\d:\d\d\.\d\d)', lambda m: ts(max(0, sum(float(x) * f for x, f in zip(m.group(1).split(':'), (3600, 60, 1))) - HOOK)), txt)
open('work/convo/captions_shift.ass', 'w').write(txt)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', amv, '-i', 'work/convo/video.mp4',
    '-i', VOICE,
    '-i', 'work/convo/bed.wav',
    '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'../out/{name}.mp4'])
os.remove(amv)
print('wrote', f'out/{name}.mp4', flush=True)

hist = json.load(open('history.json'))
hist.setdefault('convos', []).append(dict(ep=conv_ep, s=c0, e=c1, file=f'{name}.mp4', time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
json.dump(hist, open('history.json', 'w'), indent=1)
