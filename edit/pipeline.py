"""One Short per run, alternating styles: conversation Short, then narrated Short, then conversation ...
   STYLE=auto (default) flips from the last style in history.json; STYLE=convo / narrated forces one.
   Writes out/meta.json (file, style, title, description, tags) for the upload step."""
import json, os, random, re, subprocess, sys, glob, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
hist_path = os.path.join(HERE, 'history.json')
hist = json.load(open(hist_path)) if os.path.exists(hist_path) else {}
styles = hist.get('styles', [])
want = (os.environ.get('STYLE') or 'auto').strip().lower()
if want in ('convo', 'narrated'):
    style = want
else:
    style = 'narrated' if (styles and styles[-1]['style'] == 'convo') else 'convo'
print('style this run:', style, '| last:', styles[-1]['style'] if styles else None, flush=True)

os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
before = set(glob.glob(os.path.join(ROOT, 'out', '*.mp4')))
script = 'convo.py' if style == 'convo' else 'narrate.py'
subprocess.run([sys.executable, os.path.join(HERE, script)], check=True, cwd=HERE)
new = sorted(set(glob.glob(os.path.join(ROOT, 'out', '*.mp4'))) - before, key=os.path.getmtime)
if not new:
    raise SystemExit('no Short was written')
video = new[-1]

info = json.load(open(os.path.join(HERE, 'work', 'convo', 'convo.json')))
ep = info.get('ep', '')
series_key = ep.split(':')[0]
series = series_key.replace('-', ' ').title()
tag_series = series_key.replace('-', '')
lines = [l['t'] for l in info.get('lines', [])]
rng = random.Random()

if style == 'narrated':
    first = re.split(r'(?<=[.!?])\s', ' '.join(lines))[0].strip()
    hook = first if len(first) <= 70 else ' '.join(first.split()[:9]) + '...'
    title = rng.choice([f'{hook} 🔥', f'The truth about this {series} fight 😳', f'This {series} moment is pure aura 🔥'])
    desc = ' '.join(lines)
else:
    best = max(lines, key=len) if lines else ''
    quote = best if len(best) <= 60 else ' '.join(best.split()[:8]) + '...'
    title = rng.choice([f'"{quote}" 🥶', f'{series} battle IQ is unreal 🔥', f'This {series} fight goes hard 😳'])
    desc = '\n'.join(lines[:6])
title = title[:90] + ' #shorts'
tags = ['shorts', 'anime', 'animeedit', tag_series, 'phonk', 'amv']
desc = f"{desc}\n\n#{tag_series} #animeedit #anime #phonk #shorts"

styles.append(dict(style=style, ep=ep, file=os.path.basename(video), time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
hist = json.load(open(hist_path)) if os.path.exists(hist_path) else {}   # the render may have updated it
hist['styles'] = styles[-200:]
json.dump(hist, open(hist_path, 'w'), indent=1)
meta = dict(file=video, style=style, ep=ep, title=title, description=desc, tags=tags)
json.dump(meta, open(os.path.join(ROOT, 'out', 'meta.json'), 'w'), indent=1, ensure_ascii=False)
print('meta', json.dumps(meta, ensure_ascii=False), flush=True)
