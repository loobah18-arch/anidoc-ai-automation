"""Self-checking character map.

Scans each Drive episode ONCE with the character filter (charvis.scan_episode), caches who appears where in
edit/char_map.json, and corrects edit/characters.json:
  - drops an episode from a character's list when the character barely appears in it (e.g. a wrong S3E05 entry),
  - adds an episode when one character clearly dominates it and it is not listed yet.
Incremental: episodes already in char_map.json are never scanned again; each run scans the episodes this run
already downloaded plus at most MAP_EXTRA new downloads, within MAP_MAX_SCANS / MAP_BUDGET seconds.
Fail-safe: any error leaves characters.json untouched and exits 0.
"""
import json, os, subprocess, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE); sys.path.insert(0, HERE)
MAP_PATH, CHARS_PATH = 'char_map.json', 'characters.json'
MAX_SCANS = int(os.environ.get('MAP_MAX_SCANS', 3))
EXTRA = int(os.environ.get('MAP_EXTRA', 1))
BUDGET = float(os.environ.get('MAP_BUDGET', 900))
STEP = float(os.environ.get('MAP_STEP', 5))
DROP_SHARE = float(os.environ.get('MAP_DROP_SHARE', 0.04))      # below this share of frames the character "barely appears"
CONFIDENT = float(os.environ.get('MAP_CONFIDENT', 0.12))        # the character must reach this share in one of its episodes
ADD_SHARE = float(os.environ.get('MAP_ADD_SHARE', 0.25))
MIN_KEEP = 2
SRC = lambda code: 'src/' + code.replace(':', '__') + '.mp4'
T0 = time.time()


def norm(e):
    return e if ':' in e else f'jujutsu-kaisen:{e}'


def lore_name(key, lore, series):
    for nm, d in lore.get(series, {}).items():
        if key in d.get('names', []) or key == nm.lower():
            return nm
    return None


def write_chars(chars, orig_keys):
    """same layout as the hand-written file: one character per line, JJK episodes without the series prefix"""
    rows = []
    for k in orig_keys:
        eps = [e.split(':', 1)[1] if e.startswith('jujutsu-kaisen:') else e for e in chars[k]]
        rows.append(f' {json.dumps(k)}: {json.dumps(eps)}')
    open(CHARS_PATH, 'w').write('{\n' + ',\n'.join(rows) + '\n}\n')


def correct(chars_raw, cmap, lore):
    chars = {k: [norm(e) for e in v] for k, v in chars_raw.items()}
    eps_map = cmap.get('episodes', {})
    changes = []
    for k, listed in chars.items():
        series = listed[0].split(':')[0] if listed else None
        nm = lore_name(k, lore, series) if series else None
        if not nm:
            continue
        sh = {e: eps_map[e]['chars'][nm]['share'] for e in listed if e in eps_map and nm in eps_map[e].get('chars', {})}
        if not sh or max(sh.values()) < CONFIDENT:                    # refs can't recognise them reliably yet: leave the list alone
            continue
        best = max(sh.values())
        weak = sorted((e for e, v in sh.items() if v < min(0.06, max(DROP_SHARE, 0.2 * best))), key=lambda e: sh[e])
        keep = list(listed)
        for e in weak:
            if len(keep) <= MIN_KEEP:
                break
            keep.remove(e)
            changes.append(dict(char=k, ep=e, action='drop', share=sh[e], best=round(best, 3)))
        for e, d in eps_map.items():                                  # episodes where this character clearly leads
            if e in keep or not e.startswith(series + ':') or nm not in d.get('chars', {}):
                continue
            ranked = sorted(d['chars'].items(), key=lambda kv: -kv[1]['share'])
            if ranked[0][0] == nm and ranked[0][1]['share'] >= ADD_SHARE and ranked[0][1]['share'] >= 1.5 * ranked[1][1]['share']:
                keep.append(e)
                changes.append(dict(char=k, ep=e, action='add', share=ranked[0][1]['share']))
        chars[k] = sorted(keep, key=lambda e: (e.split(':')[0], e))
    return chars, changes


def main():
    import charvis
    from drive_index import library
    EPISODES, _ = library()
    lore = json.load(open('lore.json'))
    chars_raw = json.load(open(CHARS_PATH))
    orig_keys = list(chars_raw)
    cmap = json.load(open(MAP_PATH)) if os.path.exists(MAP_PATH) else {}
    cmap.setdefault('episodes', {}); cmap.setdefault('corrections', [])
    listed = {norm(e) for v in chars_raw.values() for e in v}
    todo_local = [e for e in EPISODES if e not in cmap['episodes'] and os.path.exists(SRC(e)) and os.path.getsize(SRC(e)) > 10_000_000]
    # most-listed (most likely to be wrong for someone) unscanned episodes first
    count = {e: sum(norm(x) == e for v in chars_raw.values() for x in v) for e in listed}
    todo_new = sorted((e for e in EPISODES if e not in cmap['episodes'] and e not in todo_local and e in listed),
                      key=lambda e: (-count.get(e, 0), e))[:EXTRA]
    todo = (todo_local + todo_new)[:MAX_SCANS]
    print(f'char map: {len(cmap["episodes"])} episodes cached, scanning {todo} this run '
          f'({len([e for e in EPISODES if e not in cmap["episodes"]])} still unscanned)', flush=True)
    banks, scanned, downloaded = {}, [], []
    for e in todo:
        if time.time() - T0 > BUDGET:
            print('char map: time budget reached, rest next run', flush=True); break
        series = EPISODES[e]['series']
        try:
            if not os.path.exists(SRC(e)):
                subprocess.run([sys.executable, '-m', 'gdown', EPISODES[e]['drive_id'], '-O', SRC(e), '-q'], timeout=600)
                if not (os.path.exists(SRC(e)) and os.path.getsize(SRC(e)) > 10_000_000):
                    print('char map: download failed', e, flush=True); continue
                downloaded.append(e)
            if series not in banks:
                banks[series] = charvis.Bank(series)
            r = charvis.scan_episode(SRC(e), series, step=STEP, bk=banks[series])
            if r is None:
                print('char map: not enough references to scan', e, flush=True); continue
            r['scanned'] = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())
            cmap['episodes'][e] = r
            scanned.append(e)
            top = sorted(r['chars'].items(), key=lambda kv: -kv[1]['share'])[:5]
            print(f'char map {e}:', ', '.join(f'{n} {v["share"]:.2f}' for n, v in top), flush=True)
        except Exception as ex:
            print('char map: scan failed', e, ex, flush=True)
        finally:
            if e in downloaded and os.path.exists(SRC(e)):
                os.remove(SRC(e))                                         # extra downloads only for the scan
    chars, changes = correct(chars_raw, cmap, lore)
    if changes:
        for c in changes:
            c['time'] = time.strftime('%Y-%m-%d', time.gmtime())
            print(f'characters.json: {c["action"]} {c["ep"]} for {c["char"]} (share {c["share"]})', flush=True)
        cmap['corrections'] = (cmap['corrections'] + changes)[-300:]
        write_chars(chars, orig_keys)
    ref_stats = {s: b.stats() for s, b in banks.items()}
    cmap['stats'] = dict(episodes_cached=len(cmap['episodes']), episodes_total=len(EPISODES),
                         updated=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), refs=ref_stats or cmap.get('stats', {}).get('refs', {}))
    json.dump(cmap, open(MAP_PATH, 'w'), indent=1)
    summary = dict(scanned=scanned, corrections=changes, cached=len(cmap['episodes']), total=len(EPISODES), refs=ref_stats,
                   seconds=round(time.time() - T0))
    os.makedirs('work', exist_ok=True)
    json.dump(summary, open('work/charmap_summary.json', 'w'), indent=1)
    print('char map summary', json.dumps(summary), flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write(f"### Character map\nscanned {scanned or 'nothing new'} | cached {len(cmap['episodes'])}/{len(EPISODES)} episodes | "
                    f"corrections: {', '.join(c['action'] + ' ' + c['ep'] + ' (' + c['char'] + ')' for c in changes) or 'none'}\n"
                    f"refs: {json.dumps(ref_stats)}\n")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        print('char map skipped (characters.json unchanged)', flush=True)
    sys.exit(0)
