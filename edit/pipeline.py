"""One Short per run: conversation Shorts only (drop-locked AMV edit from edit/convo.py, same as convo_short.yml).
   STYLE=convo (default, also 'auto'); STYLE=narrated must be asked for explicitly (old quote/rhyme style, off by default).
   Writes out/meta.json (file, style, title, description, tags) for the upload step."""
import json, os, random, re, subprocess, sys, glob, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
hist_path = os.path.join(HERE, 'history.json')
hist = json.load(open(hist_path)) if os.path.exists(hist_path) else {}
styles = hist.get('styles', [])
want = (os.environ.get('STYLE') or 'convo').strip().lower()
style = 'narrated' if want == 'narrated' else 'convo'      # convo only unless narrated is explicitly forced
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
    char, mode = info.get('character'), info.get('mode')
    lore = json.load(open(os.path.join(HERE, 'lore.json'))).get(series_key, {})
    first = char.split()[0] if char else series
    if mode == 'character' and char in lore:
        title = rng.choice([f'Who is {char}? 🤯', f'{char} explained in 20 seconds 🔥', f"{first}'s power is unreal 😳"])
        desc = f"{char}'s power, explained.\n\n{lore[char]['power']}"
    else:
        title = rng.choice([f'{first} hits different 🥶', f'This {series} edit goes hard 🔥', f'{first} quote that hits hard 🥶'])
        desc = ' '.join(lines)
else:
    char = info.get('character_name') or info.get('character')
    first = char.split()[0] if char else series
    title = rng.choice([f'{first} battle IQ is unreal 🔥', f'{first} fight goes crazy 😳', f'{first} goes all out 🥶'])
    desc = '\n'.join(lines[:6])
title = title[:90] + ' #shorts'
tags = ['shorts', 'anime', 'animeedit', tag_series, 'phonk', 'amv']
if info.get('character'):
    tags.append(re.sub(r'\W+', '', str(info['character']).lower()))
desc = f"{desc}\n\n#{tag_series} #animeedit #anime #phonk #shorts"

styles.append(dict(style=style, ep=ep, file=os.path.basename(video), time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
hist = json.load(open(hist_path)) if os.path.exists(hist_path) else {}   # the render may have updated it
hist['styles'] = styles[-200:]
json.dump(hist, open(hist_path, 'w'), indent=1)
meta = dict(file=video, style=style, ep=ep, title=title, description=desc, tags=tags)
json.dump(meta, open(os.path.join(ROOT, 'out', 'meta.json'), 'w'), indent=1, ensure_ascii=False)
print('meta', json.dumps(meta, ensure_ascii=False), flush=True)
