"""Character-on-screen + action scoring with CLIP, matched against real reference pictures.

refs(name, series)          -> 5-10+ reference stills of the character (Fandom wiki gallery via the MediaWiki API,
                               MyAnimeList/Jikan pictures, AniList), cached in work/refs/ (+ face crops in work/refs/faces/)
Bank(series)                -> CLIP embeddings of every character's refs / face crops in that anime (cached in work/refs/emb/)
Scorer(name, series).score  -> per-time dicts: char (does the character appear), rel (looks more like them than anyone
                               else in the anime, from the image refs), action (fight / power use)
scan_episode(src, series)   -> who is on screen how often in a whole episode (used by charmap.py)

Everything is CPU only. If anything fails (no network, no torch), callers get None and fall back to motion-only picks.
"""
import io, json, os, re, subprocess, time, urllib.request, urllib.parse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'anidoc-ai-automation/1.0 (github actions; contact via repo)'}
REF_DIR = os.path.join(HERE, 'work', 'refs')
FACE_DIR = os.path.join(REF_DIR, 'faces')
EMB_DIR = os.path.join(REF_DIR, 'emb')
MIN_REFS = int(os.environ.get('MIN_REFS', 5))
MAX_REFS = int(os.environ.get('MAX_REFS', 10))
REFETCH_DAYS = float(os.environ.get('REF_REFETCH_DAYS', 3))
FANDOM = {'jujutsu-kaisen': 'jujutsu-kaisen.fandom.com', 'demon-slayer-kimetsu-no-yaiba': 'kimetsu-no-yaiba.fandom.com'}
# gallery files that are not anime stills (manga panels, covers, merch, games, eyecatchers ...)
NOT_STILL = re.compile(r'\bch\d+\b|chapter|manga|volume|vol\.|cover|magazine|illustration|animage|animedia|jacket|bd&dvd|'
                       r'chronicles|render|chibi|eyecatcher|collab|pop-up|card|figure|merch|game|poster|visual|logo|icon|'
                       r'\bagf|festival|novel|fanbook|databook|colored|colour|sketch|design|concept|promo|stage|play|'
                       r'phantom parade|cursed clash|\.gif$|\.svg$', re.I)


def series_key(series):
    return re.sub(r'[^a-z0-9]+', '-', (series or '').lower()).strip('-')


def slug(name):
    return re.sub(r'\W+', '_', name.lower()).strip('_')


def _get(url, data=None, headers=None, timeout=30):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method='POST' if data else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _toks(name):
    return [t for t in re.split(r"[\s']+", name) if t]


# ------------------------------------------------------------------ reference sources
def _fandom(name, series):
    host = FANDOM.get(series_key(series)) or (series_key(series) + '.fandom.com')
    api = f'https://{host}/api.php?'
    q = lambda **p: json.loads(_get(api + urllib.parse.urlencode(dict(p, format='json'))))
    hits = q(action='opensearch', search=name, limit=5)[1] or q(action='opensearch', search=_toks(name)[0], limit=5)[1]
    page = next((h for h in hits if '/' not in h and ' vs' not in h.lower()), None)
    if not page:
        return []
    toks = [t.lower() for t in _toks(name)]
    titles = []
    for t in (f'{page}/Image Gallery', f'{page}/Gallery', page):
        try:
            js = q(action='query', titles=t, prop='images', imlimit=500, redirects=1)
            titles += [i['title'] for p in js['query']['pages'].values() for i in p.get('images', [])]
        except Exception:
            pass
        if len(titles) > 40:
            break
    titles = list(dict.fromkeys(titles))
    still = [t for t in titles if not NOT_STILL.search(t) and re.search(r'\.(png|jpe?g|webp)$', t, re.I)]

    def rank(t):
        low = t.lower()
        named = any(x in low for x in toks)
        first = any(low.startswith('file:' + x) for x in toks)          # the character is the subject of the still
        anime = '(anime)' in low or 'anime' in low or 'episode' in low
        return -(3 * first + 2 * named + 2 * anime)
    still = [t for t in sorted(still, key=rank) if rank(t) <= -2]
    tagged = [t for t in still if '(anime)' in t.lower()]
    if len(tagged) >= MIN_REFS:                                       # the wiki marks anime stills: use only those
        still = tagged
    still = still[:MAX_REFS + 6]
    if not still:
        return []
    js = q(action='query', titles='|'.join(still[:40]), prop='imageinfo', iiprop='url', iiurlwidth=640)
    info = {p['title']: p['imageinfo'][0] for p in js['query']['pages'].values() if p.get('imageinfo')}
    return [(info[t].get('thumburl') or info[t]['url']) for t in still if t in info]


_JIKAN_FAILS = [0]


def _jikan(name):
    if _JIKAN_FAILS[0] >= 2:                                          # unreachable from this runner (Errno 101 on GitHub): stop asking
        return []
    try:
        js = json.loads(_get('https://api.jikan.moe/v4/characters?' + urllib.parse.urlencode(dict(q=name, limit=3, order_by='favorites', sort='desc')), timeout=12))
        _JIKAN_FAILS[0] = 0
    except Exception:
        _JIKAN_FAILS[0] += 1
        if _JIKAN_FAILS[0] == 2:
            print('jikan unreachable twice, skipping it for the other characters', flush=True)
        raise
    out = []
    for c in js.get('data', [])[:1]:
        out.append(c['images']['jpg']['image_url'])
        time.sleep(1.2)                                               # jikan rate limit
        try:
            pics = json.loads(_get(f"https://api.jikan.moe/v4/characters/{c['mal_id']}/pictures"))
            out += [p['jpg']['image_url'] for p in pics.get('data', [])[:8]]
        except Exception as ex:
            print('jikan pictures skipped', ex, flush=True)
    return out


def _anilist(name):
    q = 'query($s:String){Page(perPage:5){characters(search:$s){name{full native alternative} image{large}}}}'
    toks = name.split()
    variants = [name, ' '.join(reversed(toks)), toks[0], toks[-1]]
    out = []
    for v in dict.fromkeys(variants):
        body = json.dumps(dict(query=q, variables=dict(s=v))).encode()
        js = json.loads(_get('https://graphql.anilist.co', body, {'Content-Type': 'application/json'}))
        for c in js['data']['Page']['characters']:
            full = ' '.join([c['name']['full'] or ''] + (c['name'].get('alternative') or [])).lower()
            if sum(t.lower()[:4] in full for t in toks) >= 1:
                out.append(c['image']['large']); break
        if out:
            break
        time.sleep(0.8)
    return out[:2]


_CASC = None


def cascade():
    global _CASC
    if _CASC is None:
        try:
            import cv2
            _CASC = cv2.CascadeClassifier(os.path.join(HERE, 'lbpcascade_animeface.xml'))
        except Exception:
            _CASC = False
    return _CASC or None


def faces(im, biggest_only=False, loose=False):
    """anime face crops (PIL) found by lbpcascade_animeface, padded so hair / eyes are included"""
    casc = cascade()
    if casc is None:
        return []
    g = np.asarray(im.convert('L'))
    fs = casc.detectMultiScale(g, 1.05 if loose else 1.1, 3 if loose else 4, minSize=(max(24, g.shape[0] // 16),) * 2)
    fs = sorted(fs, key=lambda f: -f[2] * f[3])[:1 if biggest_only else 4]
    out = []
    for x, y, w, h in fs:
        pad = int(0.35 * w)
        out.append(im.crop((max(0, x - pad), max(0, y - pad), min(im.width, x + w + pad), min(im.height, y + h + pad))))
    return out


def refs(name, series=''):
    """reference stills for a character (paths). Fetched once, then served from the cache (work/refs, Actions cache)."""
    os.makedirs(REF_DIR, exist_ok=True); os.makedirs(FACE_DIR, exist_ok=True)
    sl = slug(name)
    pat = re.compile(re.escape(sl) + r'_\d+\.jpg$')
    have = sorted(f for f in os.listdir(REF_DIR) if pat.match(f))
    man_p = os.path.join(REF_DIR, sl + '.json')
    man = json.load(open(man_p)) if os.path.exists(man_p) else {}
    fresh = time.time() - man.get('t', 0) < REFETCH_DAYS * 86400
    if len(have) >= MIN_REFS or (have and fresh) or (fresh and man.get('n', 0) == 0 and man.get('tries', 0) >= 2):
        return [os.path.join(REF_DIR, f) for f in have]
    from PIL import Image
    urls, src_n = [], {}
    # wiki anime stills first, then MAL portraits (clean faces), then AniList
    for nm_, fn, cap in (('fandom', lambda: _fandom(name, series), MAX_REFS - 2), ('jikan', lambda: _jikan(name), 4), ('anilist', lambda: _anilist(name), 2)):
        try:
            got = fn()[:cap]
            src_n[nm_] = len(got)
            urls += got
        except Exception as ex:
            print('ref source failed for', name, nm_, ex, flush=True)
    paths, i = [os.path.join(REF_DIR, f) for f in have], len(have)
    seen = set(man.get('urls', []))
    for u in dict.fromkeys(urls):
        if len(paths) >= MAX_REFS + 4:
            break
        if u in seen:
            continue
        try:
            im = Image.open(io.BytesIO(_get(u))).convert('RGB')
            if min(im.size) < 80:
                continue
            hsv = np.asarray(im.convert('HSV').resize((64, 64)))
            if hsv[..., 1].mean() < 28:                                # black-and-white manga panel, not an anime still
                continue
            im.thumbnail((640, 640))
            p = os.path.join(REF_DIR, f'{sl}_{i:02d}.jpg')
            im.save(p, quality=90)
            fc = faces(im, biggest_only=True, loose=True)                           # the largest face is the subject of the still
            if fc:
                fc[0].save(os.path.join(FACE_DIR, f'{sl}_{i:02d}.jpg'), quality=92)
            paths.append(p); seen.add(u); i += 1
        except Exception as ex:
            print('ref download failed', u[:120], ex, flush=True)
    json.dump(dict(t=time.time(), n=len(paths), tries=man.get('tries', 0) + 1, sources=src_n, urls=sorted(seen)), open(man_p, 'w'))
    nf = len([f for f in os.listdir(FACE_DIR) if f.startswith(sl + '_')])
    print(f'{len(paths)} reference pictures for {name} ({nf} face crops)', flush=True)
    return paths


def face_refs(name):
    sl = slug(name)
    return sorted(os.path.join(FACE_DIR, f) for f in os.listdir(FACE_DIR) if re.match(re.escape(sl) + r'_\d+\.jpg$', f)) if os.path.isdir(FACE_DIR) else []


def lore_series(series):
    try:
        return json.load(open(os.path.join(HERE, 'lore.json'))).get(series_key(series), {})
    except Exception:
        return {}


# ------------------------------------------------------------------ CLIP
_MODEL = None


def model():
    global _MODEL
    if _MODEL is None:
        import torch, open_clip
        torch.set_num_threads(max(1, os.cpu_count() or 2))
        m, _, pre = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        m.eval()
        _MODEL = (torch, m, pre, open_clip.get_tokenizer('ViT-B-32'))
    return _MODEL


def embed_images(ims, batch=48):
    torch, m, pre, _ = model()
    out = []
    for b in range(0, len(ims), batch):
        with torch.no_grad():
            e = m.encode_image(torch.stack([pre(i) for i in ims[b:b + batch]]))
        out.append((e / e.norm(dim=-1, keepdim=True)).numpy())
    return np.vstack(out) if out else np.zeros((0, 512), np.float32)


def embed_text(ts):
    torch, m, _, tok = model()
    with torch.no_grad():
        e = m.encode_text(tok(ts))
    return (e / e.norm(dim=-1, keepdim=True)).numpy()


def _emb_files(paths, key):
    """embeddings of image files, cached by file name + size"""
    from PIL import Image
    os.makedirs(EMB_DIR, exist_ok=True)
    cp = os.path.join(EMB_DIR, key + '.npz')
    sig = [f'{os.path.basename(p)}:{os.path.getsize(p)}' for p in paths]
    if os.path.exists(cp):
        try:
            z = np.load(cp, allow_pickle=False)
            if list(z['sig']) == sig:
                return z['e']
        except Exception:
            pass
    ims = []
    for p in paths:
        try:
            ims.append(Image.open(p).convert('RGB'))
        except Exception:
            pass
    e = embed_images(ims) if ims else np.zeros((0, 512), np.float32)
    if len(ims) == len(paths):
        np.savez(cp, e=e, sig=np.array(sig))
    return e


class Bank:
    """image-reference embeddings of every character of one anime"""
    def __init__(self, series, names=None, fetch=True):
        self.series = series_key(series)
        lore = lore_series(series)
        self.names = list(names or lore.keys())
        self.look = {n: lore.get(n, {}).get('look', '') for n in self.names}
        self.whole, self.face = {}, {}
        for n in self.names:
            ps = refs(n, series) if fetch else []
            w = _emb_files(ps, slug(n)) if ps else None
            fp = face_refs(n)
            f = _emb_files(fp, slug(n) + '_face') if fp else None
            if w is not None and len(w):
                self.whole[n] = w
            if f is not None and len(f):
                self.face[n] = f
        self._clean_faces()
        print(f'reference bank {self.series}: {len(self.whole)}/{len(self.names)} characters with stills, '
              f'{len(self.face)} with face crops, {sum(len(v) for v in self.whole.values())} stills, '
              f'{sum(len(v) for v in self.face.values())} faces', flush=True)

    def _clean_faces(self):
        """drop face crops that are really someone else (a still often shows two characters)"""
        cent = {n: f.mean(0) / (np.linalg.norm(f.mean(0)) + 1e-9) for n, f in self.face.items()}
        dropped = 0
        for n, F in list(self.face.items()):
            if len(F) < 2:
                continue
            keep = []
            for i in range(len(F)):
                rest = np.delete(F, i, axis=0).mean(0); rest /= np.linalg.norm(rest) + 1e-9
                own = float(F[i] @ rest)
                other = max((float(F[i] @ c) for m, c in cent.items() if m != n), default=-1)
                keep.append(own >= other - 0.01)
            if sum(keep) >= 1 and not all(keep):
                dropped += len(keep) - sum(keep)
                self.face[n] = F[np.array(keep)]
        if dropped:
            print(f'reference bank: dropped {dropped} face crops that look like another character', flush=True)

    def stats(self):
        return dict(characters=len(self.names), with_stills=len(self.whole), with_faces=len(self.face),
                    stills=int(sum(len(v) for v in self.whole.values())), faces=int(sum(len(v) for v in self.face.values())))


_BANKS = {}


def bank(series):
    k = series_key(series)
    if k not in _BANKS:
        _BANKS[k] = Bank(series)
    return _BANKS[k]


def frame(src, t, w=448):
    from PIL import Image
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1',
                          '-vf', f'scale={w}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert('RGB') if raw else None


def frames_every(src, step, lo, hi, w=448, h=252):
    """one ffmpeg pass: a frame every `step` seconds between lo and hi -> [(t, PIL image)]"""
    from PIL import Image
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{lo:.2f}', '-t', f'{hi - lo:.2f}', '-i', src,
                          '-vf', f'fps=1/{step},scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    arr = np.frombuffer(raw[:n * w * h * 3], np.uint8).reshape(n, h, w, 3)
    return [(lo + k * step, Image.fromarray(arr[k])) for k in range(n)]


ACTION = ['an anime fight scene with a sword slash', 'an anime character unleashing a glowing energy attack',
          'an anime battle with an explosion and debris', 'an anime character punching an enemy at high speed',
          'an anime character using a magic technique with fire, water or lightning effects']
CALM = ['two anime characters calmly talking', 'an anime character standing still in a quiet room',
        'an anime landscape with no people', 'an anime close-up of a character eating or smiling',
        'a dark blank frame or title card']
# shots that are never combat even inside a fight window: crowds, costumes, title cards, empty scenery, dark frames.
# noncombat = best match here minus best ACTION match (> 0: reads more like these than like any fight)
NONCOMBAT = ['a crowd of people in halloween costumes on a city street at night',
             'a person in clown or joker face paint in a crowd',
             'a crowd of ordinary people standing in a train station',
             'an anime episode title card with white text on a black screen',
             'an anime title logo with japanese text',
             'an empty sky over dark mountains with no people',
             'a nearly black frame with a small light in the darkness']


def _best(M, x):
    """max cosine between reference rows M and one or more query rows x"""
    if M is None or x is None or not len(M):
        return None
    return float((M @ np.atleast_2d(x).T).max())


class Scorer:
    def __init__(self, name, series=''):
        self.name, self.series = name, series
        self.bank = bank(series)
        self.ref = self.bank.whole.get(name)
        self.ref_face = self.bank.face.get(name)
        if name not in self.bank.names:                               # a character not in lore.json: fetch just them
            ps = refs(name, series)
            self.ref = _emb_files(ps, slug(name)) if ps else None
            fp = face_refs(name)
            self.ref_face = _emb_files(fp, slug(name) + '_face') if fp else None
        self.others_w = {n: v for n, v in self.bank.whole.items() if n != name}
        self.others_f = {n: v for n, v in self.bank.face.items() if n != name}
        look = self.bank.look.get(name, '')
        self.look_names = [k for k, v in self.bank.look.items() if k != name and v]
        others = [f'anime screenshot of {self.bank.look[k]}' for k in self.look_names]
        self.has_look = bool(look)
        self.t_others = embed_text(others) if others else None
        names_t = [f'{name} from {series}, anime screenshot', f'anime screenshot of {look}' if look else f'{name}, anime character',
                   f'{name}, {look}' if look else f'{name} fighting']
        t = embed_text(names_t + ACTION + CALM)
        nn = len(names_t); self.t_name, self.t_act, self.t_calm = t[:nn], t[nn:nn + len(ACTION)], t[nn + len(ACTION):]
        self.t_non = embed_text(NONCOMBAT)
        self.image_mode = self.ref is not None and len(self.others_w) >= 2
        print(f'charvis ready for {name}: {0 if self.ref is None else len(self.ref)} stills, '
              f'{0 if self.ref_face is None else len(self.ref_face)} face refs, {len(self.others_w)} other characters with refs, '
              f'matching by {"image refs" if self.image_mode else "text description"}', flush=True)

    def frame(self, src, t, w=448):
        return frame(src, t, w)

    def feats(self, ims):
        E = embed_images(ims)
        out = []
        for im, e in zip(ims, E):
            fc = faces(im)
            out.append(dict(e=e, f=embed_images(fc) if fc else None))
        return out

    def score(self, items, batch=48):
        """items: list of (src, t). returns list of dict(char, rel, action, ...) (None where the frame could not be read).
        Two passes: score against the reference pictures, then add the most confident on-screen matches from
        this very anime as extra references (same art style, same season look) and score again."""
        feats = [None] * len(items)
        for b0 in range(0, len(items), batch):
            chunk = [(k, self.frame(s, t)) for k, (s, t) in enumerate(items[b0:b0 + batch], b0)]
            chunk = [(k, im) for k, im in chunk if im is not None]
            if not chunk:
                continue
            for (k, _), ft in zip(chunk, self.feats([im for _, im in chunk])):
                feats[k] = ft
        res = self._rate(feats)
        good = sorted((k for k, r in enumerate(res) if r), key=lambda k: -res[k]['char'])[:max(3, len(items) // 40)]
        if self.ref is not None and good:
            self.ref = np.vstack([self.ref] + [feats[k]['e'][None] for k in good])
            fs = [feats[k]['f'] for k in good if feats[k]['f'] is not None]
            if fs:
                self.ref_face = np.vstack(([self.ref_face] if self.ref_face is not None else []) + fs)
            res = self._rate(feats)
        return res

    def _rate(self, feats):
        out = []
        for ft in feats:
            if ft is None:
                out.append(None); continue
            e, f = ft['e'], ft['f']
            whole = _best(self.ref, e) or 0.0
            face = (_best(self.ref_face, f) or 0.0) if f is not None else 0.0
            named = float((self.t_name @ e).max())
            act = float((self.t_act @ e).max() - (self.t_calm @ e).max())
            noncombat = float((self.t_non @ e).max() - (self.t_act @ e).max())
            if self.image_mode:                                      # image refs: how much more like them than anyone else
                if f is not None and self.ref_face is not None and self.others_f:
                    mine, vs = face, {n: _best(v, f) for n, v in self.others_f.items()}
                else:
                    mine, vs = whole, {n: _best(v, e) for n, v in self.others_w.items()}
                rel = mine - max(vs.values())
                char = max(whole, face) + 0.5 * named + 2.0 * rel
            else:                                                    # no refs: the old text look description
                look_self = float(self.t_name[1] @ e)
                rel = look_self - float((self.t_others @ e).max()) if self.t_others is not None else 0.0
                char = max(whole, face) + 1.0 * named + 2.0 * rel
                mine, vs = None, {}
            look_me = float(self.t_name[1] @ e) if self.has_look else None
            look_vs = dict(zip(self.look_names, (self.t_others @ e).tolist())) if self.t_others is not None else {}
            out.append(dict(char=char, rel=rel, face=face, whole=whole, named=named, action=act, noncombat=noncombat,
                            has_face=f is not None, mine=mine, vs=vs,   # vs: every other character's score (rival margins)
                            look_me=look_me, look_vs=look_vs))          # CLIP look-description scores (rival look veto)
        return out

    def present(self, items, margin=-0.02):
        """True where the character looks like the best match among the anime's characters (None = unreadable)"""
        res = self.score(items)
        return [None if r is None else bool(r['rel'] >= margin) for r in res]


def scan_episode(src, series, step=5.0, skip_head=150, skip_tail=150, bk=None):
    """who is on screen how often: every `step` s, which character's reference stills the frame matches best
    (face crops blended in when the frame shows an anime face). returns dict(frames, face_frames, chars={name: dict(share, top3, peak)})"""
    bk = bk or bank(series)
    names = list(bk.whole)
    if len(names) < 2:
        return None
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src],
                               capture_output=True, text=True).stdout or 0)
    lo, hi = min(skip_head, dur * 0.1), max(dur - skip_tail, dur * 0.9)
    fr = frames_every(src, step, lo, hi, w=640, h=360)
    if not fr:
        return None
    E = embed_images([im for _, im in fr])
    S = np.array([[float((bk.whole[n] @ e).max()) for n in names] for e in E])
    nface = 0
    for k, (_, im) in enumerate(fr):
        fc = faces(im)
        if not fc:
            continue
        nface += 1
        F = embed_images(fc)
        for j, n in enumerate(names):
            if n in bk.face:
                S[k, j] = 0.5 * S[k, j] + 0.5 * float((bk.face[n] @ F.T).max())
    order = np.argsort(-S, axis=1)
    margin = S[np.arange(len(S)), order[:, 0]] - S[np.arange(len(S)), order[:, 1]]
    wins = np.bincount(order[margin > 0.004, 0], minlength=len(names))
    top3 = np.zeros(len(names))
    for row in order[:, :3]:
        top3[row] += 1
    chars = {n: dict(share=round(float(wins[j]) / len(fr), 4), top3=round(float(top3[j]) / len(fr), 4),
                     peak=round(float(np.mean(np.sort(S[:, j])[-10:])), 4)) for j, n in enumerate(names)}
    return dict(frames=len(fr), face_frames=nface, step=step, chars=chars)


def get(name, series=''):
    if not name or os.environ.get('CHARVIS', '1') == '0':
        return None
    try:
        return Scorer(name, series)
    except Exception as ex:
        print('charvis unavailable, motion-only picks:', ex, flush=True)
        return None


# ------------------------------------------------------------------ who is this scene about (conversation character)
# The rules below are the offline prototype that got the S1E13 459-476 s Tanjiro scene right (Tanjiro 11-13 of 23
# votes, where the earlier draft said Zenitsu 5 / Mitsuri 3 / Tanjiro 2): short title in the name prompt (the long
# "Demon Slayer Kimetsu No Yaiba, anime screenshot" title washed the names out), background = plain frames every 25 s
# of the episode, no face-crop blending, one vote per frame.
SHORT_TITLE = {'demon-slayer-kimetsu-no-yaiba': 'Demon Slayer', 'jujutsu-kaisen': 'Jujutsu Kaisen'}
_BG = {}


def short_title(series, title=''):
    k = series_key(series)
    if k in SHORT_TITLE:
        return SHORT_TITLE[k]
    t = title or k.replace('-', ' ').title()
    t = re.split(r'\s*[:(\u2013\u2014]\s*|\s+-\s+|\s+season\s+', t, flags=re.I)[0].strip()
    return ' '.join(t.split()[:3]) or t


def _embed_frames(src, ts, w=448, dark=18):
    """(times kept, whole-frame embeddings). Pure black / fade frames (mean < dark) say nothing about who it is."""
    kept, ims = [], []
    for t in ts:
        im = frame(src, t, w)
        if im is not None and (dark is None or np.asarray(im.convert('L')).mean() > dark):
            kept.append(t); ims.append(im)
    if not ims:
        return [], np.zeros((0, 512), np.float32)
    return kept, embed_images(ims)


def background(src, lo, hi, skip=None, step=25.0, min_n=24):
    """frames every `step` s of the same episode (outside `skip(t)`): the baseline every character score is measured
    against. A short range gets a finer step so there are still min_n frames."""
    key = (src, int(lo), int(hi), step)
    if key not in _BG:
        ts = [t for t in np.arange(lo, hi, step) if not (skip and skip(t))]
        if len(ts) < min_n and hi - lo > 0:
            ts = [t for t in np.linspace(lo, hi, min_n * 2) if not (skip and skip(t))]
        _BG[key] = _embed_frames(src, ts, dark=None)
    return _BG[key]


def validate_refs(bk, EB, expected=(), log=print):
    """reference pictures that match too broadly. A still that is the best match of 10%+ of an episode's frames is a
    composition match (a dark room, a screaming close-up, Enmu#4's big blue close-up), not the character: dropped.
    A character whose refs win 20%+ of the episode's frames (and 3x the typical share) without being expected in it is
    dropped entirely (Enmu's refs - flesh blobs, game art, a blue close-up - were the 'clear' match of 223 Demon Slayer
    shots)."""
    names = [n for n in bk.whole]
    R = np.vstack([bk.whole[n] for n in names])
    win = np.bincount((EB @ R.T).argmax(1), minlength=len(R)) / max(1, len(EB))
    keep = {n: np.ones(len(bk.whole[n]), bool) for n in names}
    i, hubs = 0, []
    for n in names:
        for j in range(len(bk.whole[n])):
            if win[i] >= 0.10 and len(bk.whole[n]) >= 3:
                keep[n][j] = False; hubs.append(f'{n}#{j}')
            i += 1
    S = np.stack([(EB @ bk.whole[n].T).max(1) for n in names], 1)
    o = np.sort(S, 1); top = S.argmax(1); mar = o[:, -1] - o[:, -2]
    share = np.bincount(top[mar >= 0.02], minlength=len(names)) / max(1, len(EB))
    med = float(np.median(share))
    exp = {e.lower() for e in expected}
    broad = [names[k] for k in range(len(names)) if share[k] >= 0.20 and share[k] >= 3 * med and names[k].lower() not in exp]
    log(f'reference check: {len(hubs)} over-broad stills dropped {hubs[:8]}; characters matching too broadly: '
        f'{[(n, round(float(share[names.index(n)]), 2)) for n in broad]}')
    return {n: bk.whole[n][keep[n]] for n in names if n not in broad and keep[n].any()}, broad


def identify(src, t0, t1, series, lo, hi, skip=None, expected=(), target=None, log=print, series_title='',
             weights=(0.7, 0.15, 0.15)):
    """who a scene (t0..t1 s of src) is about. A frame every 0.75 s is scored for every character of the anime by
    CLIP's knowledge of the name ("{name} from {short title}"), of the look description and of the reference stills,
    each as a z-score against background frames every 25 s of the same episode (so a reference that matches every dark
    close-up, or the hero who is in every frame, does not win by default). One vote per frame for its best character;
    the scene's character needs 30%+ of the votes and 1.6x the runner-up.
    returns dict(name or None, votes, share, runner, margin, target_share, target_top)."""
    bk = bank(series)
    if len(bk.whole) < 2:
        return dict(name=None, reason='no reference bank')
    ts = list(np.arange(t0 + 0.25, t1, 0.75))
    if len(ts) > 40:
        ts = list(np.linspace(t0 + 0.25, t1 - 0.25, 40))
    if len(ts) < 8:
        ts = list(np.linspace(t0 + 0.1, t1 - 0.1, 8))
    tk, ET = _embed_frames(src, ts)
    _, EB = background(src, lo, hi, skip=skip)
    if len(ET) < 4 or len(EB) < 12:
        return dict(name=None, reason='too few readable frames')
    whole, broad = validate_refs(bk, EB, expected, log)
    names = list(whole)
    z = lambda St, Sb: (St - Sb.mean(0)) / (Sb.std(0) + 1e-6)
    st = short_title(series, series_title)
    tn = embed_text([f'{n} from {st}' for n in names])
    C = weights[0] * z(ET @ tn.T, EB @ tn.T)
    if weights[1]:
        tl = embed_text([f'anime screenshot of {bk.look.get(n) or n}' for n in names])
        C = C + weights[1] * z(ET @ tl.T, EB @ tl.T)
    if weights[2]:
        C = C + weights[2] * np.stack([z(ET @ whole[n].T, EB @ whole[n].T).max(1) for n in names], 1)
    if os.environ.get('CHARVIS_DEBUG'):
        for k in range(len(C)):
            oo = np.argsort(-C[k])[:3]; print(' frame', k, [(names[j].split()[0], round(float(C[k, j]), 2)) for j in oo])
    votes = np.bincount(C.argmax(1), minlength=len(names))
    order = np.argsort(-votes)
    top, run = names[order[0]], names[order[1]]
    share = float(votes[order[0]]) / len(C)
    margin = float(votes[order[0]]) / max(1.0, float(votes[order[1]]))
    mean = C.mean(0)
    res = dict(votes={names[k]: int(votes[k]) for k in order[:5] if votes[k]}, frames=len(C), share=round(share, 3),
               runner=run, margin=round(margin, 2), mean={names[k]: round(float(mean[k]), 2) for k in np.argsort(-mean)[:4]},
               broad=broad, prompt=f'{{name}} from {st}', name=top if share >= 0.30 and margin >= 1.6 else None)
    res['per_frame'] = [(float(t), names[k]) for t, k in zip(tk, C.argmax(1))]     # (time, its vote)
    if target:
        ti = next((k for k, n in enumerate(names) if n.lower() == target.lower() or n.split()[0].lower() == target.lower()), None)
        res['target_share'] = round(float(votes[ti]) / len(C), 3) if ti is not None else 0.0
        res['target_top'] = ti is not None and int(votes[ti]) == int(votes.max()) and votes[ti] > 0
        # clearly about the target: strictly the most votes and a quarter of the frames (a 6-6 tie with Hanami is not)
        res['target_clear'] = bool(ti is not None and votes[ti] > max([votes[k] for k in range(len(names)) if k != ti] or [0])
                                   and res['target_share'] >= 0.25)
    log(f'scene {t0:.0f}-{t1:.0f}s: votes {res["votes"]} of {len(C)} frames (bg {len(EB)}, prompt "{res["prompt"]}"); '
        f'top {top} {share:.0%}, {margin:.1f}x {run} -> {res["name"] or "unsure"}')
    return res
