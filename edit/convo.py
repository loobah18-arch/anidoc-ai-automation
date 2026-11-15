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
HOOK = 0.0
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
    if talk < 0.45:
        continue
    act = per_s[t:t + 24].mean() / mref
    sc = 0.6 * talk + 1.5 * min(act, 1.3)
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


# ------------------------------------------------------------------ 4b. English voiceover (edge-tts Christopher voice)
import edge_tts, asyncio
VOICE_NAME = os.environ.get('VOICE', 'en-US-ChristopherNeural')
VOICE_RATE = os.environ.get('VOICE_RATE', '+2%')
PITCH_LIST = ['+0Hz', '-6Hz', '+5Hz', '-3Hz', '+3Hz']

os.makedirs('work/convo/tts', exist_ok=True)
async def _synth_lines():
    line_bounds = []
    for li, ln in enumerate(lines):
        txt = ' '.join(w['w'] for w in ln).strip()
        txt_clean = re.sub(r'[*"#]|\(.*?\)', '', txt)
        txt_clean = re.sub(r'\.\s+', ', ', txt_clean.rstrip('.'))
        spk_pitch = PITCH_LIST[spk[li] % len(PITCH_LIST)]
        com = edge_tts.Communicate(txt_clean, VOICE_NAME, rate=VOICE_RATE, pitch=spk_pitch, boundary='WordBoundary')
        bounds = []
        out_mp3 = f'work/convo/tts/{li:02d}.mp3'
        with open(out_mp3, 'wb') as f:
            async for ch in com.stream():
                if ch['type'] == 'audio':
                    f.write(ch['data'])
                elif ch['type'] == 'WordBoundary':
                    bounds.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
        line_bounds.append((out_mp3, bounds))
    return line_bounds

tts_results = asyncio.run(_synth_lines())

# Map word boundaries back onto lines to sync captions with the English speech
for li, (mp3_path, bnds) in enumerate(tts_results):
    ln = lines[li]
    line_s = max(0.0, ln[0]['s'] - c0)
    if bnds:
        for bi, (ba, bb, bt) in enumerate(bnds):
            if bi < len(ln):
                ln[bi]['s'] = c0 + line_s + ba
                ln[bi]['e'] = c0 + line_s + max(bb, ba + 0.12)
        ln[-1]['e'] = max(ln[-1]['e'], c0 + line_s + bnds[-1][1] + 0.1)

# Mix the dialogue audio files into one single stereo track
mix_inputs = []
mix_filters = []
for li, (mp3_path, _) in enumerate(tts_results):
    line_s = max(0.0, lines[li][0]['s'] - c0)
    delay_ms = int(line_s * 1000)
    mix_inputs.extend(['-i', mp3_path])
    mix_filters.append(f'[{li}:a]adelay={delay_ms}|{delay_ms}[a{li}];')

n_lines = len(tts_results)
pads = ''.join(f'[a{i}]' for i in range(n_lines))
mix_fc = ''.join(mix_filters) + (f'{pads}amix=inputs={n_lines}:normalize=0,' if n_lines > 1 else '[a0]') + f'apad=whole_dur={CONV:.3f},aresample=48000,aformat=channel_layouts=stereo,highpass=f=75,lowpass=f=12000,bass=g=3:f=110,loudnorm=I=-11:TP=-1.0:LRA=7[out]'
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y'] + mix_inputs + ['-filter_complex', mix_fc, '-map', '[out]', 'work/convo/talk.wav'])
VOICE = 'work/convo/talk.wav'
print(f'synthesized {n_lines} lines of English dialogue with {VOICE_NAME}', flush=True)


def get_wrap_breaks(toks, max_chars=14, max_words=3):
    breaks = set()
    cur_len = 0
    cur_words = 0
    for i, t in enumerate(toks[:-1]):
        cur_words += 1
        cur_len += len(t)
        next_w_len = len(toks[i + 1])
        if cur_len + 1 + next_w_len > max_chars or cur_words >= max_words:
            breaks.add(i)
            cur_len = 0
            cur_words = 0
        else:
            cur_len += 1
    return breaks


ass = [f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},68,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H96000000,0,0,0,0,100,100,1,0,1,3.5,2,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""]
DIM = '&H00A0A0A0&'
for li, ln in enumerate(lines):
    col = colour_of[spk[li]]
    t_end = min(ln[-1]['e'] + 0.35, lines[li + 1][0]['s'] if li + 1 < len(lines) else c1) - c0
    toks = [clean(w['w']) for w in ln]
    toks = [t for t in toks if t]
    if not toks:
        continue
    brks = get_wrap_breaks(toks, max_chars=14, max_words=3)
    for k in range(len(toks)):                                        # word-by-word: spoken white, the rest dim
        a = ln[min(k, len(ln) - 1)]['s'] - c0
        b = (ln[k + 1]['s'] - c0) if k + 1 < len(toks) and k + 1 < len(ln) else t_end
        if b <= a:
            continue
        parts = []
        for m, t in enumerate(toks):
            parts.append(('{\\1c&H00FFFFFF&}' if m <= k else '{\\1c' + DIM + '}') + t)
            if m in brks:
                parts.append('\\N')
            elif m != len(toks) - 1:
                parts.append(' ')
        txt = ''.join(parts).replace(' \\N', '\\N')
        pop = '{\\fscx106\\fscy106\\t(0,90,\\fscx100\\fscy100)}' if k == 0 else ''
        glow = f'{{\\pos({W // 2},{int(H * 0.54)})\\bord12\\blur10\\3c{ass_col(col)}\\3a&H25&\\shad0\\1a&HFF&}}'
        main = f'{{\\pos({W // 2},{int(H * 0.54)})\\bord3.5\\blur2\\3c{ass_col(col)}\\shad2}}'
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

# ------------------------------------------------------------------ 6. the AMV part (auto.py), then join
amv_len = max(14.0, TOTAL - CONV)
env = dict(os.environ, FORCE_EPS=conv_ep, INCLUDE=f'{conv_ep}|{c0 - 150:.1f}|{c1 + 150:.1f}', START_BEAT='9', MAX_SECONDS=f'{amv_len:.2f}', W=str(W), H=str(H),
           EXCLUDE=f'{conv_ep}|{c0}|{c1}', OUT_NAME='_amv_part', PICK=PICK, START_OFFSET=f'{CONV:.2f}')
subprocess.run([sys.executable, 'auto.py'], env=env, check=True)
amv = '../out/_amv_part.mp4'
plan = json.load(open('work/edit_plan.json'))
song_file = f"music/{plan['song']}.mp3"
song_len = duration(song_file)
song_start = float(plan.get('song_start', 0.0))
# One continuous phonk audio stream throughout the whole Short (zero restarting):
bgm_start = max(0.0, song_start - CONV)
if bgm_start + TOTAL > song_len:
    bgm_start = max(0.0, song_len - TOTAL)
print(f'continuous song {bgm_start:.2f}s -> {bgm_start + TOTAL:.2f}s (AMV edit hits at t={CONV:.2f}s, song_start={song_start:.2f}s)', flush=True)

name = re.sub(r'[^A-Za-z0-9]+', '_', EPISODES[conv_ep]['series'].title()) + '_convo_' + plan['song']

fc = (
    f"[1:v]setpts=PTS-STARTPTS,fps={FPS},ass=work/convo/captions.ass[cv];"
    f"[0:v]setpts=PTS-STARTPTS,fps={FPS}[av];"
    f"[cv][av]concat=n=2:v=1:a=0[v];"
    f"[3:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
    f"volume=eval=frame:volume='if(lt(t, {CONV:.3f}), 0.20, 1.0)'[bgm_curved];"
    f"[2:a]asetpts=PTS-STARTPTS,apad=whole_dur={CONV:.3f},"
    f"aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-11:TP=-1.0:LRA=7,asplit=2[v_sc][v_mix];"
    f"[bgm_curved][v_sc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=300:makeup=1[ducked_bgm];"
    f"[ducked_bgm][v_mix]amix=inputs=2:duration=first:dropout_transition=0,"
    f"afade=t=out:st={TOTAL - 1.2:.2f}:d=1.2[a]"
)
sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', amv, '-i', 'work/convo/video.mp4',
    '-i', VOICE,
    '-ss', f'{bgm_start:.3f}', '-t', f'{TOTAL:.3f}', '-i', song_file,
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
lines_text = [w['w'] for w in cw] if 'cw' in locals() and cw else []
quote = ' '.join(lines_text[:8]) if lines_text else series_title
if len(quote) > 60:
    quote = quote[:57] + '...'
meta_title = rng_m.choice([f'"{quote}" 🥶', f'{series_title} battle IQ is unreal 🔥', f'This {series_title} fight goes hard 😳'])
meta_desc = '\n'.join(' '.join(w['w'] for w in ln) for ln in lines) if 'lines' in locals() and lines else (' '.join(lines_text) or f"{series_title} anime fight")
meta_title = meta_title[:90] + ' #shorts'
tags = ['shorts', 'anime', 'animeedit', tag_series, 'phonk', 'amv']
meta_desc = f"{meta_desc}\n\n#{tag_series} #animeedit #anime #phonk #shorts"
meta = dict(file=video_file, style='convo', ep=conv_ep, title=meta_title, description=meta_desc, tags=tags)
json.dump(meta, open(os.path.join(out_dir, 'meta.json'), 'w'), indent=1, ensure_ascii=False)

hist = json.load(open('history.json'))
hist.setdefault('convos', []).append(dict(ep=conv_ep, s=c0, e=c1, file=f'{name}.mp4', time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
json.dump(hist, open('history.json', 'w'), indent=1)
