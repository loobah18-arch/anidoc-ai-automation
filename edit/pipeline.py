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
lines = [l['t'] for l in info.get('lines', [])]
rng = random.Random()


def strip_anime_names(text: str) -> str:
    patterns = [
        r"demon\s*slayer[:\s]*kimetsu\s*no\s*yaiba",
        r"demon\s*slayer",
        r"kimetsu\s*no\s*yaiba",
        r"jujutsu\s*kaisen",
        r"\bjjk\b",
        r"#demonslayer\w*",
        r"#jujutsukaisen\w*",
        r"#jjk\b",
    ]
    if series_key:
        clean = re.escape(series_key.replace('-', ' ').strip())
        joined = re.escape(series_key.replace('-', '').strip())
        patterns.extend([rf"\b{clean}\b", rf"\b{joined}\b", rf"#{joined}\b"])
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"#(?=\s|$)", "", cleaned)
    return re.sub(r"[ \t]+", " ", cleaned).strip()


if style == 'narrated':
    char, mode = info.get('character'), info.get('mode')
    lore = json.load(open(os.path.join(HERE, 'lore.json'))).get(series_key, {})
    first = char.split()[0] if (char and char.lower() not in series_key.replace('-', ' ').lower()) else None
    if mode == 'character' and char in lore:
        t_opts = [f'Who is {char}? 🤯', f'{char} explained in 20 seconds 🔥']
        if first:
            t_opts.append(f"{first}'s power is unreal 😳")
        title = rng.choice(t_opts)
        desc = f"{char}'s power, explained.\n\n{lore[char]['power']}"
    else:
        t_opts = ['This edit goes hard 🔥', 'This fight hits different 🥶', 'This quote hits hard 🥶']
        if first:
            t_opts.append(f'{first} hits different 🥶')
        title = rng.choice(t_opts)
        desc = ' '.join(lines)
else:
    char = info.get('title_name') if 'title_name' in info else (info.get('character_name') or info.get('character'))
    is_guess = info.get('topic_guess', False)
    if char and not is_guess and char.lower() not in series_key.replace('-', ' ').lower():
        first = char.split()[0]
        title = rng.choice([f'{first} battle IQ is unreal 🔥', f'{first} fight goes crazy 😳', f'{first} goes all out 🥶'])
    else:
        title = rng.choice([
            'This battle IQ is unreal 🔥',
            'This fight goes crazy 😳',
            'He goes all out 🥶',
            'This scene hits different 🥶',
            'The aura is unreal 🥶',
            'Pure cinema 🥶🔥',
        ])
    desc = '\n'.join(lines[:6])

title = strip_anime_names(title)
if not title or title.lower() == '#shorts':
    title = 'This fight goes crazy 😳'
title = title[:90] + ' #shorts'

tags = ['shorts', 'anime', 'animeedit', 'phonk', 'amv']
if info.get('character'):
    c_clean = re.sub(r'\W+', '', str(info['character']).lower())
    if c_clean and c_clean not in ('demonslayer', 'demonslayerkimetsunoyaiba', 'jujutsukaisen', 'jjk', series_key.replace('-', '')):
        tags.append(c_clean)

desc = strip_anime_names(desc)
desc = f"{desc}\n\n#animeedit #anime #phonk #shorts"

styles.append(dict(style=style, ep=ep, file=os.path.basename(video), time=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())))
hist = json.load(open(hist_path)) if os.path.exists(hist_path) else {}   # the render may have updated it
hist['styles'] = styles[-200:]
json.dump(hist, open(hist_path, 'w'), indent=1)
meta = dict(file=video, style=style, ep=ep, title=title, description=desc, tags=tags)
json.dump(meta, open(os.path.join(ROOT, 'out', 'meta.json'), 'w'), indent=1, ensure_ascii=False)
print('meta', json.dumps(meta, ensure_ascii=False), flush=True)
