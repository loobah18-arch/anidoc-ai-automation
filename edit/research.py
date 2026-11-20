"""Self-research: which episodes hold a character's fights, for any anime in the Drive folder.

For a series slug from drive_index (e.g. `jujutsu-kaisen`, `demon-slayer-kimetsu-no-yaiba`, or any new anime):
  1. Jikan API v4 (MyAnimeList, no key; AniList GraphQL as a fallback): the TV seasons (mal ids, episode counts),
     the main + supporting cast, episode titles and synopses.
  2. The anime's Fandom wiki through the MediaWiki API: every battle page (who fights, which anime episodes) and
     every "Episode N" page (season / episode number, summary + plot text).
  3. Each episode is scored per character: wiki battles the character fights in, plot / synopsis sentences that
     name the character together with fight words, fight words + the name in the title.  -> ranked fight episodes.
  4. Results are cached in edit/research_cache.json (series -> characters -> ranked episodes, with sources), so a
     series is researched once and only again when new episodes appear in the Drive folder.

Everything is fail-safe: any network or parse problem returns [] and the caller keeps its old behaviour.
CLI:  python3 edit/research.py <series-slug> [character]
"""
import html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(HERE, 'research_cache.json')
UA = {'User-Agent': 'anidoc-ai-automation/1.0 (github actions research; contact via repo)'}
JIKAN = 'https://api.jikan.moe/v4'
BUDGET = float(os.environ.get('RESEARCH_BUDGET', 240))          # seconds for one series, all sources together
MIN_SCORE = float(os.environ.get('RESEARCH_MIN_SCORE', 2.0))
KNOWN_WIKI = {'jujutsu-kaisen': 'jujutsu-kaisen.fandom.com', 'demon-slayer-kimetsu-no-yaiba': 'kimetsu-no-yaiba.fandom.com'}
FIGHT = re.compile(r"\b(fight\w*|battl\w*|vs\.?|versus|clash\w*|duel\w*|domain expansion|attack\w*|defeat\w*|kill\w*|slay\w*|"
                   r"slash\w*|strik\w*|punch\w*|kick\w*|blow|blows|technique\w*|breathing|form|blood demon art|cursed energy|"
                   r"black flash|hollow purple|unlimited void|infinity|beheads?|decapitat\w*|wound\w*|injur\w*|overwhelm\w*|"
                   r"combat|assault\w*|confront\w*|showdown|rematch|counter\w*|unleash\w*|ambush\w*|cuts?|sword\w*|blade)\b", re.I)
T0 = [time.time()]
_last_jikan = [0.0]
_jikan_down = [0]                                                     # consecutive connection failures: stop asking after 3


def log(*a):
    print('research:', *a, flush=True)


def _left():
    return BUDGET - (time.time() - T0[0])


def _get(url, data=None, headers=None, timeout=25):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method='POST' if data else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _json(url, **kw):
    return json.loads(_get(url, **kw).decode('utf-8', 'ignore'))


# ------------------------------------------------------------------ Jikan (MyAnimeList)
def jikan(path, tries=4):
    """GET with ~3 req/s pacing and back-off on 429 / 5xx. Returns None on failure."""
    for k in range(tries):
        if _left() < 5 or _jikan_down[0] >= 3:
            return None
        wait = 0.4 - (time.time() - _last_jikan[0])
        if wait > 0:
            time.sleep(wait)
        _last_jikan[0] = time.time()
        try:
            r = _json(JIKAN + path, timeout=12)
            _jikan_down[0] = 0
            return r
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                return None
            if ex.code >= 500:
                _jikan_down[0] += 1
            time.sleep(1.5 * (k + 1) if ex.code in (429, 500, 502, 503, 504) else 0.5)
        except Exception:
            _jikan_down[0] += 1
            time.sleep(1.0 * (k + 1))
    if _jikan_down[0] >= 3:
        log('Jikan unreachable, skipping it this run')
    return None


def _norm(t):
    return re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()


def _titles(a):
    ts = [a.get('title'), a.get('title_english')] + list(a.get('title_synonyms') or [])
    ts += [t.get('title') for t in a.get('titles') or [] if isinstance(t, dict)]
    return [t for t in ts if t]


def jikan_series(series, drive_seasons):
    """TV seasons in air order -> [dict(mal_id, title, episodes, aired)]"""
    q = series.replace('-', ' ')
    words = q.split()
    for query in dict.fromkeys([q, ' '.join(words[-3:]), ' '.join(words[:2])]):
        res = jikan('/anime?' + urllib.parse.urlencode(dict(q=query, limit=25, order_by='start_date', sort='asc')))
        if not res or not res.get('data'):
            continue
        cand = [a for a in res['data'] if a.get('type') in ('TV', 'ONA') and (a.get('episodes') or 0) >= 3]
        if not cand:
            continue
        key = set(_norm(query).split())
        def match(a):
            return max((len(key & set(_norm(t).split())) / max(1, len(key)) for t in _titles(a)), default=0)
        best = max(match(a) for a in cand)
        if best < 0.5:
            continue
        cand = [a for a in cand if match(a) >= best - 0.25]
        cand.sort(key=lambda a: (a.get('aired') or {}).get('from') or '9999')
        out = [dict(mal_id=a['mal_id'], title=a.get('title'), title_english=a.get('title_english'), episodes=a.get('episodes'),
                    aired=((a.get('aired') or {}).get('from') or '')[:10]) for a in cand]
        return out[:max(drive_seasons + 1, 1)]
    return []


def jikan_cast(mal_ids):
    cast = {}
    for mid in mal_ids:
        res = jikan(f'/anime/{mid}/characters')
        for c in (res or {}).get('data', []):
            nm = (c.get('character') or {}).get('name') or ''
            if ',' in nm:                                                 # "Gojo, Satoru" -> "Satoru Gojo"
                last, first = [x.strip() for x in nm.split(',', 1)]
                nm = f'{first} {last}'
            if nm and c.get('role') in ('Main', 'Supporting'):
                d = cast.setdefault(nm, dict(role=c['role'], favorites=0))
                d['favorites'] = max(d['favorites'], c.get('favorites') or 0)
                if c['role'] == 'Main':
                    d['role'] = 'Main'
    return cast


def jikan_episodes(season_list):
    """-> {(season, ep): dict(title, synopsis)}"""
    out = {}
    for si, s in enumerate(season_list, 1):
        page = 1
        while page < 6 and _left() > 20:
            res = jikan(f'/anime/{s["mal_id"]}/episodes?page={page}')
            if not res:
                break
            for e in res.get('data', []):
                out[(si, int(e['mal_id']))] = dict(title=e.get('title') or '', synopsis='')
            if not (res.get('pagination') or {}).get('has_next_page'):
                break
            page += 1
        for n in sorted(k[1] for k in out if k[0] == si):
            if _left() < 30:
                break
            res = jikan(f'/anime/{s["mal_id"]}/episodes/{n}', tries=2)
            syn = ((res or {}).get('data') or {}).get('synopsis') or ''
            out[(si, n)]['synopsis'] = syn
    return out


def anilist_cast(series):
    q = '''query($s:String){Media(search:$s,type:ANIME){id idMal title{romaji english}
           characters(sort:[ROLE,FAVOURITES_DESC],perPage:50){edges{role node{name{full alternative}}}}}}'''
    try:
        r = _json('https://graphql.anilist.co', data=json.dumps(dict(query=q, variables=dict(s=series.replace('-', ' ')))).encode(),
                  headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
    except Exception as ex:
        log('anilist failed', ex)
        return {}, {}
    m = (r.get('data') or {}).get('Media') or {}
    cast = {}
    for e in ((m.get('characters') or {}).get('edges') or []):
        nm = ((e.get('node') or {}).get('name') or {}).get('full')
        if nm and e.get('role') in ('MAIN', 'SUPPORTING'):
            cast[nm] = dict(role=e['role'].title(), favorites=0, alt=[a for a in (e['node']['name'].get('alternative') or []) if a])
    return cast, dict(anilist_id=m.get('id'), mal_id=m.get('idMal'), titles=list((m.get('title') or {}).values()))


# ------------------------------------------------------------------ Fandom wiki (MediaWiki API)
def _api(host):
    return f'https://{host}/api.php?'


def wiki_q(host, **p):
    p.setdefault('format', 'json'); p.setdefault('formatversion', '2')
    return _json(_api(host) + urllib.parse.urlencode(p), timeout=25)


def find_wiki(series, titles=()):
    if series in KNOWN_WIKI:
        return KNOWN_WIKI[series]
    names = [series] + [re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-') for t in titles if t]
    guesses = []
    for n in names:
        toks = [t for t in n.split('-') if t]
        guesses += [n, n.replace('-', '')]
        for k in range(len(toks) - 1, 0, -1):                          # prefixes and suffixes: "kimetsu-no-yaiba"
            guesses += ['-'.join(toks[:k]), '-'.join(toks[-k:]), ''.join(toks[:k]), ''.join(toks[-k:])]
    for g in dict.fromkeys(x for x in guesses if len(x) >= 4):
        if _left() < 10:
            break
        try:
            d = wiki_q(f'{g}.fandom.com', action='query', meta='siteinfo')
            host = urllib.parse.urlparse(d['query']['general']['base']).netloc
            hits = wiki_q(host, action='query', list='search', srsearch='episode', srlimit=5)
            if hits.get('query', {}).get('search'):
                log('wiki found', host)
                return host
        except Exception:
            continue
    return None


def _clean(wt):
    t = re.sub(r'<ref[^>]*/>|<ref.*?</ref>', ' ', wt, flags=re.S)
    t = re.sub(r'\[\[(?:File|Image):[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]', ' ', t)
    for _ in range(3):
        t = re.sub(r'\{\{[^{}]*\}\}', ' ', t)
    t = re.sub(r'\[\[([^\]|]*\|)?([^\]]*)\]\]', r'\2', t)
    t = re.sub(r"'{2,}|<[^>]+>|^=+.*?=+\s*$", ' ', t, flags=re.M)
    return html.unescape(re.sub(r'[ \t]+', ' ', t))


def _contents(host, titles):
    out = {}
    for i in range(0, len(titles), 40):
        if _left() < 10:
            break
        try:
            d = wiki_q(host, action='query', prop='revisions', rvprop='content', rvslots='main', redirects='1',
                       titles='|'.join(titles[i:i + 40]))
        except Exception as ex:
            log('wiki batch failed', ex); continue
        for p in d.get('query', {}).get('pages', []):
            revs = p.get('revisions') or []
            if revs:
                out[p['title']] = revs[0].get('slots', {}).get('main', {}).get('content') or revs[0].get('content') or ''
    return out


def _field(wt, *names):
    for n in names:
        m = re.search(r'^\s*\|\s*' + n + r'\s*=\s*(.*?)(?=^\s*\||^\}\})', wt, re.M | re.S | re.I)
        if m:
            return m.group(1)
    return ''


def wiki_episodes(host, total):
    """Episode N pages -> {N: dict(title, season, ep, text)}"""
    pages = _contents(host, [f'Episode {n}' for n in range(1, total + 1)])
    out = {}
    for title, wt in pages.items():
        m = re.match(r'Episode (\d+)$', title)
        if not m:
            continue
        n = int(m.group(1))
        sn, en = _field(wt, 'season number', 'season'), _field(wt, 'ep number', 'episode number')
        tt = _clean(_field(wt, 'ep title', 'title', 'english title')).strip()
        body = wt.split('}}', 1)[1] if '}}' in wt else wt
        body = re.split(r'^==\s*(?:Characters in Order of Appearance|Characters|Navigation|Trivia|References|Gallery|Site Navigation)', body, flags=re.M | re.I)[0]
        out[n] = dict(title=tt, season=int(re.sub(r'\D', '', sn) or 0) or None, ep=int(re.sub(r'\D', '', en) or 0) or None,
                      text=_clean(body)[:20000])
    return out


def wiki_battles(host):
    """battle pages -> [dict(title, fighters (text), episodes [abs numbers])]"""
    titles, seen_cat = [], set()
    cats = ['Category:Battles']
    while cats and _left() > 20:
        cat = cats.pop(0)
        if cat in seen_cat or len(seen_cat) > 25:
            continue
        seen_cat.add(cat)
        cont = {}
        while True:
            try:
                d = wiki_q(host, action='query', list='categorymembers', cmtitle=cat, cmlimit='500', **cont)
            except Exception:
                break
            for m in d.get('query', {}).get('categorymembers', []):
                if m['ns'] == 14:
                    cats.append(m['title'])
                elif m['ns'] == 0:
                    titles.append(m['title'])
            if 'continue' not in d:
                break
            cont = d['continue']
    if len(titles) < 5:                                                # no battle category: battle-looking page titles
        try:
            d = wiki_q(host, action='query', list='search', srsearch='intitle:vs', srlimit='500')
            titles += [x['title'] for x in d.get('query', {}).get('search', [])]
        except Exception:
            pass
    titles = [t for t in dict.fromkeys(titles) if re.search(r'\bvs\.?\b', t, re.I)]
    out = []
    for title, wt in _contents(host, titles).items():
        ep_txt = _field(wt, 'episodes', 'episode', 'anime')
        eps = set()
        for a, b in re.findall(r'Episode (\d+)(?:[^\]]*\]\])?\s*(?:-|–|to)\s*\[\[Episode (\d+)', ep_txt):
            eps |= set(range(int(a), int(b) + 1))
        eps |= {int(x) for x in re.findall(r'Episode (\d+)', ep_txt)}
        if not eps:
            continue
        sides = ' '.join(m.group(2) for m in re.finditer(r'^\s*\|\s*(side[\w ]*|combatants?[\w ]*|participants?|fighters?)\s*=\s*(.*?)(?=^\s*\||^\}\})',
                                                          wt, re.M | re.S | re.I))
        out.append(dict(title=title, fighters=_clean(sides + ' ' + title), episodes=sorted(eps),
                        outcome=_clean(_field(wt, 'outcome', 'result')).strip()[:160]))
    return out


# ------------------------------------------------------------------ scoring
def _aliases(name, extra, all_names):
    toks = [t for t in re.split(r'[\s\-]+', name) if len(t) >= 3]
    al = {name.lower()} | {t.lower() for t in toks} | {a.lower() for a in extra if a and len(a) >= 3}
    shared = set()                                                     # a family name used by several characters is no alias
    for other in all_names:
        if other != name:
            ot = {t.lower() for t in re.split(r'[\s\-]+', other) if len(t) >= 3}
            shared |= al & ot
    return sorted(a for a in al if a not in shared or a == name.lower())


def _rx(aliases):
    return re.compile(r'\b(' + '|'.join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r")(?:'s)?\b", re.I)


def score_character(name, aliases, episodes, battles, mal_eps, code_of):
    rx = _rx(aliases)
    sc, src = {}, {}
    def add(n, v, why):
        if n in code_of and v > 0:
            sc[n] = sc.get(n, 0.0) + v
            src.setdefault(n, []).append(why)
    for b in battles:
        if rx.search(b['fighters']):
            span = len(b['episodes'])
            for n in b['episodes']:
                add(n, 4.0 if span <= 4 else 3.0, f"wiki battle: {b['title']}")
    for n, e in episodes.items():
        sents = re.split(r'(?<=[.!?])\s+', e['text'])
        named = [s for s in sents if rx.search(s)]
        fights = [s for s in named if FIGHT.search(s)]
        if fights:
            add(n, 0.5 * min(len(fights), 10) + 0.04 * min(len(named), 25), f'wiki plot: {len(fights)} fight lines naming them')
        if rx.search(e['title']):
            add(n, 1.5 if FIGHT.search(e['title']) else 1.0, f"wiki title: {e['title']}")
        elif FIGHT.search(e['title']) and named:
            add(n, 0.5, f"wiki title: {e['title']}")
    for n, e in mal_eps.items():
        txt = (e.get('title') or '') + '. ' + (e.get('synopsis') or '')
        named = [s for s in re.split(r'(?<=[.!?])\s+', txt) if rx.search(s)]
        f = [s for s in named if FIGHT.search(s)]
        if f:
            add(n, 0.75 * min(len(f), 3), f'MAL synopsis: {len(f)} fight lines naming them')
        elif named and FIGHT.search(e.get('title') or ''):
            add(n, 0.5, f"MAL title: {e['title']}")
    ranked = sorted(((n, s) for n, s in sc.items() if s >= MIN_SCORE), key=lambda x: -x[1])
    return [dict(ep=code_of[n], abs=n, score=round(s, 2), sources=list(dict.fromkeys(src[n]))[:4]) for n, s in ranked[:14]]


# ------------------------------------------------------------------ the research run
def research_series(series, lib, lore=None):
    T0[0] = time.time()
    drive = {k: v for k, v in lib.items() if v['series'] == series}
    if not drive:
        return None
    seasons_drive = {}
    for v in drive.values():
        seasons_drive[v['season']] = max(seasons_drive.get(v['season'], 0), v['ep'])
    n_seasons = max(seasons_drive)
    sources = []
    tv = jikan_series(series, n_seasons)
    if tv:
        sources.append('jikan')
        log('MAL seasons', [(s['mal_id'], s['title'], s['episodes']) for s in tv])
    cast = jikan_cast([s['mal_id'] for s in tv]) if tv else {}
    al_meta = {}
    if not cast:
        cast, al_meta = anilist_cast(series)
        if cast:
            sources.append('anilist')
    lore_s = (lore or {}).get(series, {})
    for nm, d in lore_s.items():
        cast.setdefault(nm, dict(role='Main', favorites=0))
        cast[nm]['alt'] = list(dict.fromkeys((cast[nm].get('alt') or []) + d.get('names', [])))
    # season sizes: MAL entries when they line up with the Drive seasons, else the Drive's highest episode numbers
    sizes = {}
    for si in range(1, n_seasons + 1):
        mal_n = tv[si - 1]['episodes'] if len(tv) >= si and tv[si - 1].get('episodes') else None
        sizes[si] = mal_n if mal_n and mal_n >= seasons_drive.get(si, 0) else seasons_drive.get(si, mal_n or 0)
    total = sum(sizes.values())
    host = find_wiki(series, [t for s in tv for t in (s['title'], s.get('title_english'))] + al_meta.get('titles', []))
    wiki_eps, battles = {}, []
    if host:
        try:
            wiki_eps = wiki_episodes(host, total)
            battles = wiki_battles(host)
            sources.append(host)
        except Exception as ex:
            log('wiki failed', ex)
    log(f'{series}: {len(cast)} characters, {len(wiki_eps)} wiki episode pages, {len(battles)} wiki battles, seasons {sizes}')
    # absolute episode number -> Drive code (wiki season/ep fields win, else cumulative season sizes)
    code_of, start = {}, 0
    for si in range(1, n_seasons + 1):
        for e in range(1, sizes[si] + 1):
            code_of[start + e] = f'{series}:S{si}E{e:02d}'
        start += sizes[si]
    off = {si: sum(sizes[k] for k in range(1, si)) for si in range(1, n_seasons + 1)}
    for n, e in wiki_eps.items():                                     # wiki "ep number" is per season on some wikis, absolute on others
        si, ep = e.get('season'), e.get('ep')
        if not (si and ep and si in sizes):
            continue
        if ep > sizes[si] and 1 <= ep - off[si] <= sizes[si]:
            ep -= off[si]
        if ep <= sizes[si] and off[si] + ep != n:
            log(f'wiki Episode {n} says S{si}E{ep}; using it')
        if ep <= sizes[si]:
            code_of[n] = f'{series}:S{si}E{ep:02d}'
    mal_eps = {}
    if tv and _left() > 40:
        try:
            raw = jikan_episodes(tv[:n_seasons])
            mal_eps = {off[si] + n: v for (si, n), v in raw.items() if si in off}
        except Exception as ex:
            log('MAL episodes failed', ex)
    names = list(cast)
    chars = {}
    for nm in names:
        al = _aliases(nm, cast[nm].get('alt') or [], names)
        ranked = score_character(nm, al, wiki_eps, battles, mal_eps, code_of)
        if ranked:
            chars[nm] = dict(aliases=al, role=cast[nm].get('role'), ranked=ranked)
    if not chars:
        return None
    return dict(updated=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), sources=sources, wiki=host,
                mal_ids=[s['mal_id'] for s in tv], seasons={str(k): v for k, v in sizes.items()},
                episodes_seen=sorted(drive), characters=chars, seconds=round(time.time() - T0[0]))


def load_cache():
    try:
        return json.load(open(CACHE_PATH))
    except Exception:
        return {'_doc': 'Researched fight episodes per series and character (research.py). Sources: Jikan/MyAnimeList, AniList, '
                        'the Fandom wiki battles + episode plots. Refreshed only when new episodes appear in the Drive folder.'}


def get_series(series, lib, refresh=False):
    """cached research for a series; researched now when missing or when the Drive has episodes it has not seen"""
    cache = load_cache()
    cur = cache.get(series)
    drive = sorted(k for k, v in lib.items() if v['series'] == series)
    new = [e for e in drive if e not in set((cur or {}).get('episodes_seen', []))]
    if cur and not new and not refresh:
        return cur, False
    log(f'researching {series}', f'({len(new)} new episodes)' if cur else '(first time)')
    try:
        lore = json.load(open(os.path.join(HERE, 'lore.json')))
    except Exception:
        lore = {}
    res = research_series(series, lib, lore)
    if not res:
        log('no research result, keeping', 'cache' if cur else 'old behaviour')
        return cur, False
    cache[series] = res
    json.dump(cache, open(CACHE_PATH, 'w'), indent=1, ensure_ascii=False)
    return res, True


def _find_char(res, name, slug):
    chars = res.get('characters', {})
    if name in chars:
        return name
    keys = [k.lower() for k in (name, slug) if k]
    for nm, d in chars.items():
        if any(k == nm.lower() or k in d.get('aliases', []) for k in keys):
            return nm
    for nm in chars:                                                   # "Gojo" vs "Satoru Gojo"
        if any(k and k in nm.lower().split() for k in keys):
            return nm
    return None


def fight_episodes(series, name, slug, lib):
    """ranked Drive episode codes where this character fights (only episodes present in the Drive), plus details.
    Never raises: returns ([], None) when research is unavailable."""
    try:
        res, fresh = get_series(series, lib)
        if not res:
            return [], None
        nm = _find_char(res, name, slug)
        if not nm and not fresh:                                       # a character the cache never scored: research again
            res, fresh = get_series(series, lib, refresh=True)
            nm = _find_char(res or {}, name, slug)
        if not nm:
            log(f'no fight episodes found for {name or slug} in {series}')
            return [], None
        ranked = [r for r in res['characters'][nm]['ranked'] if r['ep'] in lib]
        log(f'{nm} ({series}) fight episodes:', ', '.join(f"{r['ep'].split(':')[1]} {r['score']}" for r in ranked[:8]),
            '| sources', res.get('sources'))
        for r in ranked[:4]:
            log('  ', r['ep'], '<-', '; '.join(r['sources']))
        return [r['ep'] for r in ranked], dict(character=nm, ranked=ranked[:8], scores={r['ep']: r['score'] for r in ranked}, sources=res.get('sources'), wiki=res.get('wiki'))
    except Exception as ex:
        log('failed, old behaviour:', ex)
        return [], None


def character_names(series):
    """names + aliases the research found (for naming who a conversation is about when lore.json has no entry)"""
    try:
        return {nm: d.get('aliases', []) for nm, d in load_cache().get(series, {}).get('characters', {}).items()}
    except Exception:
        return {}


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    from drive_index import library
    lib, _ = library()
    s = sys.argv[1] if len(sys.argv) > 1 else 'jujutsu-kaisen'
    if len(sys.argv) > 2:
        eps, info = fight_episodes(s, sys.argv[2], sys.argv[2].lower(), lib)
        print(json.dumps(info, indent=1))
    else:
        res, fresh = get_series(s, lib, refresh=True)
        for nm, d in (res or {}).get('characters', {}).items():
            print(nm, [r['ep'].split(':')[1] + f"({r['score']})" for r in d['ranked'][:6]])
