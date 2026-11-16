"""Quality gate, run after the Short is rendered and before the YouTube upload.

Checks
  character  : the topic character is on screen in most cuts of the edit (charvis image refs)    GATE_CHAR_MIN (0.5)
  loudness   : the narrator voice and the finished Short are inside their loudness targets (ffmpeg ebur128)
  captions   : every caption row stays inside the safe frame (ASS \\pos + rendered text width + margins)
  video      : the file exists and is a valid Short length
A check that cannot run (missing tool, no refs ...) is reported as "skipped" and does not fail the gate, so the
pipeline falls back to its old behaviour. Writes out/gate.json and `gate=pass|fail` to $GITHUB_OUTPUT. Always exits 0.
"""
import json, os, re, subprocess, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE); sys.path.insert(0, HERE)
OUT = os.path.abspath('../out')
CHAR_MIN = float(os.environ.get('GATE_CHAR_MIN', 0.5))
VOICE_I = (float(os.environ.get('GATE_VOICE_I_MIN', -15)), float(os.environ.get('GATE_VOICE_I_MAX', -9)))
SHORT_I = (float(os.environ.get('GATE_I_MIN', -18)), float(os.environ.get('GATE_I_MAX', -4)))
NARR_I = (float(os.environ.get('GATE_NARR_I_MIN', -17)), float(os.environ.get('GATE_NARR_I_MAX', -8)))
TP_MAX = float(os.environ.get('GATE_TP_MAX', 2.0))
SAFE_X = float(os.environ.get('GATE_SAFE_X', 0.04))        # fraction of the width kept clear at each side
SAFE_Y = (float(os.environ.get('GATE_SAFE_TOP', 0.12)), float(os.environ.get('GATE_SAFE_BOTTOM', 0.80)))   # Shorts UI covers the rest
checks, reasons = {}, []


def jload(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


def ebur(path, ss=None, t=None):
    cmd = ['ffmpeg', '-nostdin', '-hide_banner']
    if ss is not None:
        cmd += ['-ss', f'{ss:.3f}']
    if t is not None:
        cmd += ['-t', f'{t:.3f}']
    cmd += ['-i', path, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-']
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    summ = err[err.rfind('Summary:'):]
    I = float(re.search(r'I:\s+(-?[\d.]+|-inf) LUFS', summ).group(1))
    tp = re.search(r'Peak:\s+(-?[\d.]+|-inf) dBFS', summ)
    return I, (float(tp.group(1)) if tp else None)


def duration(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                capture_output=True, text=True).stdout)


def run(name, fn):
    try:
        r = fn()
    except Exception as ex:
        traceback.print_exc()
        r = dict(status='skipped', why=f'{type(ex).__name__}: {ex}'[:300])
    checks[name] = r
    if r.get('status') == 'fail':
        reasons.append(f"{name}: {r.get('why', '')}")
    print(f'gate {name}: {json.dumps(r)}', flush=True)


meta = jload(os.path.join(OUT, 'meta.json'), {})
convo = jload('work/convo/convo.json', {})
plan = jload('work/edit_plan.json', {})
video = meta.get('file') or ''


def c_video():
    if not video or not os.path.exists(video):
        return dict(status='fail', why='no rendered video')
    d = duration(video)
    ok = 10 <= d <= 61
    return dict(status='pass' if ok else 'fail', duration=round(d, 2), why='' if ok else f'duration {d:.1f}s outside 10-61s')


def c_character():
    name = convo.get('topic_name') or meta.get('character_name')
    if not name:
        return dict(status='skipped', why='no topic character')
    import charvis
    series = (convo.get('ep') or meta.get('ep') or '').split(':')[0]
    cv = charvis.get(name, series)
    if cv is None or not cv.image_mode:
        return dict(status='skipped', why='character refs unavailable')
    SRC = lambda code: 'src/' + code.replace(':', '__') + '.mp4'
    items = []
    tempo = float(plan.get('tempo') or 120); P = 60.0 / tempo
    for c in plan.get('plan', []):
        if not os.path.exists(SRC(c['ep'])):
            continue
        d = (c['beats'][1] - c['beats'][0]) * P * c.get('speed', 1.0)
        items.append((SRC(c['ep']), c['start'] + d / 2))
    nar_items = []
    if convo.get('ep') and os.path.exists(SRC(convo['ep'])):           # the narrated part shows the topic character too
        s0, s1 = float(convo['s']), float(convo['e'])
        nar_items = [(SRC(convo['ep']), s0 + (s1 - s0) * f) for f in (0.15, 0.4, 0.65, 0.9)]
    if len(items) < 4:
        return dict(status='skipped', why='edit plan / source episodes missing')
    pres = cv.present(items + nar_items)
    cuts = [p for p in pres[:len(items)] if p is not None]
    narr = [p for p in pres[len(items):] if p is not None]
    share = sum(cuts) / max(1, len(cuts))
    ok = share >= CHAR_MIN
    return dict(status='pass' if ok else 'fail', character=name, cuts=len(cuts), on_screen=int(sum(cuts)), share=round(share, 3),
                narration_on_screen=f'{sum(narr)}/{len(narr)}', why='' if ok else f'{name} on screen in {share:.0%} of cuts (< {CHAR_MIN:.0%})')


def c_loudness():
    out = dict()
    bad = []
    if os.path.exists('work/convo/narr.wav'):
        vi, vtp = ebur('work/convo/narr.wav')
        out.update(voice_I=vi, voice_TP=vtp)
        if not VOICE_I[0] <= vi <= VOICE_I[1]:
            bad.append(f'narrator voice {vi} LUFS outside {VOICE_I}')
    if video and os.path.exists(video):
        si, stp = ebur(video)
        out.update(short_I=si, short_TP=stp)
        if not SHORT_I[0] <= si <= SHORT_I[1]:
            bad.append(f'Short {si} LUFS outside {SHORT_I}')
        if stp is not None and stp > TP_MAX:
            bad.append(f'Short true peak {stp} dBFS > {TP_MAX}')
        cl = float(convo.get('conv_len') or 0)
        if cl > 3:
            ni, _ = ebur(video, 0, cl)
            out.update(narration_section_I=ni)
            if not NARR_I[0] <= ni <= NARR_I[1]:
                bad.append(f'narrated section {ni} LUFS outside {NARR_I}')
    if not out:
        return dict(status='skipped', why='no audio to measure')
    out.update(status='fail' if bad else 'pass', why='; '.join(bad))
    return out


def c_captions():
    path = 'work/convo/captions.ass'
    if not os.path.exists(path):
        return dict(status='skipped', why='no captions')
    txt = open(path).read()
    W = int(re.search(r'PlayResX:\s*(\d+)', txt).group(1)); H = int(re.search(r'PlayResY:\s*(\d+)', txt).group(1))
    st = re.search(r'^Style:\s*Cap,([^,]+),(\d+(?:\.\d+)?),(?:[^,]*,){10}(-?\d+(?:\.\d+)?),', txt, re.M)
    font_name, size, spacing = st.group(1), float(st.group(2)), float(st.group(3))
    try:
        from PIL import ImageFont
        fp = subprocess.run(['fc-match', '-f', '%{file}', font_name], capture_output=True, text=True).stdout.strip()
        font = ImageFont.truetype(fp, int(size))
        width = lambda s: font.getlength(s) + spacing * max(0, len(s) - 1)
        how = os.path.basename(fp)
    except Exception:
        width = lambda s: len(s) * (0.66 * size + spacing)
        how = 'estimate'
    worst, bad, n = 0.0, [], 0
    for line in txt.splitlines():
        if not line.startswith('Dialogue: 1,'):
            continue                                                  # layer 1 = the visible text (layer 0 is the soft glow)
        body = line.split(',', 9)[9]
        pos = re.search(r'\\pos\((-?[\d.]+),(-?[\d.]+)\)', body)
        x, y = (float(pos.group(1)), float(pos.group(2))) if pos else (W / 2, H / 2)
        sc = [float(v) for v in re.findall(r'\\fscx(\d+(?:\.\d+)?)', body)] or [100.0]
        scale = sc[-1] / 100.0                                        # the settled size (the 106% pop lasts 90 ms)
        bord = float((re.findall(r'\\bord(\d+(?:\.\d+)?)', body) or [0])[-1])
        rows = [re.sub(r'\{[^}]*\}', '', r) for r in body.split('\\N')]
        w = max(width(r) for r in rows) * scale + 2 * bord
        h = len(rows) * size * 1.15 * scale
        left, right, top, bottom = x - w / 2, x + w / 2, y - h / 2, y + h / 2
        n += 1
        over = max(SAFE_X * W - left, right - (1 - SAFE_X) * W, SAFE_Y[0] * H - top, bottom - SAFE_Y[1] * H)
        if over > worst:
            worst = over
        if over > 0:
            bad.append(' / '.join(rows))
    if not n:
        return dict(status='skipped', why='no caption events')
    bad = list(dict.fromkeys(bad))
    return dict(status='fail' if bad else 'pass', events=n, measured_with=how, worst_overflow_px=round(max(0, worst), 1),
                why='' if not bad else f'{len(bad)} caption rows leave the safe frame, e.g. "{bad[0]}"')


def _shown():
    P = 60.0 / float(plan.get('tempo') or 120)
    out = []
    for k, x in enumerate(plan.get('plan') or []):
        d = (x['beats'][1] - x['beats'][0]) * P * float(x.get('speed') or 1)
        out.append((k, x['ep'], float(x['start']), float(x['start']) + d))
    if convo.get('ep') and convo.get('s') is not None:
        out.append(('narration', convo['ep'], float(convo['s']), float(convo['e'])))
    return out


def c_repeats():
    sh_ = _shown()
    if not sh_:
        return dict(status='skipped', why='no edit plan')
    bad = [(a[0], b[0]) for i, a in enumerate(sh_) for b in sh_[i + 1:]
           if a[1] == b[1] and min(a[3], b[3]) - max(a[2], b[2]) > 0.2]
    return dict(status='fail' if bad else 'pass', cuts=len(sh_), repeats=len(bad),
                why='' if not bad else f'{len(bad)} cuts show footage already used, e.g. cuts {bad[0]}')


def c_credits():
    zs = jload('work/credit_zones.json', None)
    if zs is None:
        return dict(status='skipped', why='no credit zone scan')
    bad = [k for k, ep, a, b in _shown() if any(a < z1 and b > z0 for z0, z1 in zs.get(ep, []))]
    return dict(status='fail' if bad else 'pass', zones=sum(len(v) for v in zs.values()),
                why='' if not bad else f'{len(bad)} cuts come from an opening/ending/recap, e.g. {bad[0]}')


run('video', c_video)
run('repeats', c_repeats)
run('credits', c_credits)
run('captions', c_captions)
run('loudness', c_loudness)
if os.environ.get('GATE_CHARACTER', '1') != '0':
    run('character', c_character)
ok = not reasons
res = dict(result='pass' if ok else 'fail', reasons=reasons, checks=checks, writer=meta.get('writer') or convo.get('writer'),
           character=meta.get('character_name'), song=meta.get('song'))
os.makedirs(OUT, exist_ok=True)
json.dump(res, open(os.path.join(OUT, 'gate.json'), 'w'), indent=1)
print('GATE', res['result'].upper(), '|', '; '.join(reasons) or 'all checks passed or skipped', flush=True)
if os.environ.get('GITHUB_OUTPUT'):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"gate={res['result']}\n")
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
        f.write(f"### Quality gate: {res['result'].upper()}\nwriter: {res['writer']} | character: {res['character']} | song: {res['song']}\n\n")
        for k, v in checks.items():
            f.write(f"- **{k}**: {v.get('status')} {v.get('why', '')}\n")
sys.exit(0)
