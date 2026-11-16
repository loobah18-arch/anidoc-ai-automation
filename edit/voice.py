"""Expressive narrator voice: edge-tts read phrase by phrase, each phrase with its own pace, pitch and
loudness, so the read rises and falls like a person telling a story instead of one flat take.

speak(text) -> (wav_path, bounds)   bounds = [(start_s, end_s, word), ...] on the joined audio
"""
import asyncio, os, random, re, subprocess, time

import numpy as np
import soundfile as sf

VOICE = os.environ.get('VOICE', 'en-US-BrianNeural')               # calm, low, dry narrator (Nanami-style), user-picked
BASE_RATE = int(os.environ.get('VOICE_RATE', '-10%').rstrip('%'))
BASE_PITCH = int(os.environ.get('VOICE_PITCH', '-8Hz').rstrip('Hz'))
SR = 24000
STRONG = re.compile(r'\b(never|only|every|all|no one|nothing|dead|death|die|kill|blood|end|last|strongest|alone|fear|curse[ds]?|king|god|freeze|finished|lose|fall|rise)\b', re.I)


def _phrases(text):
    """Split at sentence ends, then long sentences at commas / dashes, keeping the punctuation."""
    out = []
    for s in re.split(r'(?<=[.!?])\s+', text.strip()):
        parts = re.split(r'(?<=[,;:—–])\s+', s) if len(s.split()) > 9 else [s]
        buf = ''
        for p in parts:                                              # don't leave 1-2 word scraps on their own
            buf = f'{buf} {p}'.strip()
            if len(buf.split()) >= 3:
                out.append(buf); buf = ''
        if buf:
            if out: out[-1] += ' ' + buf
            else: out.append(buf)
    return [p for p in out if p.strip()]


def _style(i, n, p, rng):
    """Pace / pitch / loudness / pause after, by where the phrase sits and what it says."""
    rate, pitch, vol, pause = BASE_RATE, BASE_PITCH, 0, 0.16
    end = p.rstrip()[-1:]
    if i == 0:                                   # the hook: unhurried, low, sure of itself
        rate -= 4; pitch -= 2; pause = 0.26
    if end == '?':                               # a real question lifts
        pitch += 6; pause = 0.30
    elif end == '!':                             # an exclamation pushes forward and gets louder
        rate += 6; pitch += 3; vol += 8; pause = 0.22
    elif end == ',':                             # mid-thought: keep moving, small breath
        rate += 3; pause = 0.10
    elif end == '.':
        pause = 0.24
    if STRONG.search(p) and end != '?':          # loaded words: lean in, slower and heavier
        rate -= 3; pitch -= 2; vol += 4
    if i == n - 1:                               # the last line lands: slowest and lowest of the read
        rate -= 6; pitch -= 4; vol += 2; pause = 0.0
    elif i == n - 2:
        pause = max(pause, 0.32)                 # a beat before the closer
    rate += rng.randint(-2, 2); pitch += rng.randint(-2, 2)   # no two phrases read the same
    return f'{rate:+d}%', f'{pitch:+d}Hz', f'{vol:+d}%', pause


async def _one(text, rate, pitch, vol, path):
    com = edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch, volume=vol, boundary='WordBoundary')
    bounds = []
    with open(path, 'wb') as f:
        async for ch in com.stream():
            if ch['type'] == 'audio':
                f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                bounds.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    return bounds


def _say(text, rate, pitch, vol, path):
    for i in range(7):                                               # the service drops requests now and then: retry the same read, flatten only as a last resort
        try:
            return asyncio.run(_one(text, rate, pitch if i < 5 else '+0Hz', vol, path))
        except Exception as e:
            print('tts retry', i, e, flush=True); time.sleep(1.5 * (i + 1))
    raise SystemExit('tts failed')


def _trim(y, thr=0.006):
    """Cut edge-tts's own lead-in / tail silence so we control every pause."""
    idx = np.where(np.abs(y) > thr)[0]
    if not len(idx):
        return y, 0
    a = max(0, idx[0] - int(0.02 * SR)); b = min(len(y), idx[-1] + int(0.06 * SR))
    return y[a:b], a / SR


ORPHEUS_VOICE = os.environ.get('ORPHEUS_VOICE', 'troy')            # Groq Orpheus: human, emotional read; edge-tts is the fallback
_SOFT = re.compile(r'\b(alone|tears?|lost|mother|brother|sister|silence|quiet|dead|death|grave|last|never again|gone)\b', re.I)


def _orpheus(text, i, n, path):
    import json as _j, urllib.request as _u
    key = os.environ.get('GROQ_API_KEY')
    if not key:
        return False
    tag = '[dramatic]' if i == 0 or STRONG.search(text) else ''
    if i == n - 1 or (_SOFT.search(text) and i > 0):
        tag = '[whisper]' if i == n - 1 else tag or ''
    body = _j.dumps(dict(model='canopylabs/orpheus-v1-english', voice=ORPHEUS_VOICE, response_format='wav',
                         input=f'{tag} {text}'.strip()[:200])).encode()
    for k in range(4):
        try:
            r = _u.Request('https://api.groq.com/openai/v1/audio/speech', body,
                           {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
            data = _u.urlopen(r, timeout=60).read()
            if data[:4] == b'RIFF':
                open(path, 'wb').write(data); print(f'voice orpheus/{ORPHEUS_VOICE} {tag or "-"}  {text}', flush=True); return True
        except Exception as e:
            print('orpheus retry', k, e, flush=True); time.sleep(2 * (k + 1))
    return False


def _even_bounds(text, dur):
    ws = text.split(); tot = sum(len(w) + 1 for w in ws) or 1; t, out = 0.0, []
    for w in ws:
        d = dur * (len(w) + 1) / tot; out.append((t, t + d * 0.92, w)); t += d
    return out


def speak(text, out='work/convo/narr_raw.wav', seed=None):
    rng = random.Random(seed)
    use_orpheus = os.environ.get('TTS', 'orpheus') == 'orpheus' and bool(os.environ.get('GROQ_API_KEY'))
    phrases = _phrases(text)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    audio, bounds, t = [], [], 0.0
    for i, p in enumerate(phrases):
        rate, pitch, vol, pause = _style(i, len(phrases), p, rng)
        mp3 = f'{out}.{i}.mp3'
        if use_orpheus and _orpheus(p, i, len(phrases), mp3):
            b = None
        else:
            use_orpheus = False                                      # one voice per Short: never mix engines mid-read
            b = _say(p, rate, pitch, vol, mp3)
        y = np.frombuffer(subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', mp3, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                                         capture_output=True, check=True).stdout, np.int16).astype(np.float32) / 32768
        y, cut = _trim(y)
        if b is None:
            b = [(a + cut, e + cut, w) for a, e, w in _even_bounds(p, len(y) / SR)]
        bounds += [(float(max(0.0, t + a - cut)), float(t + e - cut), w) for a, e, w in b]
        audio += [y, np.zeros(int(pause * SR), np.float32)]
        t += len(y) / SR + pause
        os.remove(mp3)
        print(f'voice  {rate:>5} {pitch:>6} {vol:>5}  {p}', flush=True)
    sf.write(out, np.concatenate(audio), SR)
    return out, bounds


import edge_tts  # noqa: E402  (after the helpers so a missing package fails with a clear trace)
