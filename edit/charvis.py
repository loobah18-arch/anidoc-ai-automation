"""Character-on-screen + action scoring with CLIP.

refs(name, series)        -> reference pictures of the character (AniList + MyAnimeList/Jikan), cached in work/refs/
Scorer(name, series)      -> .score(src, times) returns per-time dicts: char (does the character appear), action (fight / power use)

Everything is CPU only. If anything fails (no network, no torch), callers get None and fall back to the old motion-only picks.
"""
import json, os, re, subprocess, time, urllib.request, urllib.parse
import numpy as np

UA = {'User-Agent': 'anidoc-ai-automation/1.0'}
REF_DIR = 'work/refs'


def _get(url, data=None, headers=None, timeout=30):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method='POST' if data else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _anilist(name):
    q = 'query($s:String){Page(perPage:5){characters(search:$s){name{full native alternative} image{large}}}}'
    toks = name.split()
    variants = [name, ' '.join(reversed(toks)), toks[0], toks[-1], re.sub(r'o\b', 'ou', toks[0]) + (' ' + toks[-1] if len(toks) > 1 else '')]
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
    return out[:2]


def _jikan(name):
    js = json.loads(_get('https://api.jikan.moe/v4/characters?' + urllib.parse.urlencode(dict(q=name, limit=3, order_by='favorites', sort='desc'))))
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


def refs(name, series=''):
    os.makedirs(REF_DIR, exist_ok=True)
    slug = re.sub(r'\W+', '_', name.lower())
    have = sorted(f for f in os.listdir(REF_DIR) if f.startswith(slug))
    if len(have) >= 3:
        return [os.path.join(REF_DIR, f) for f in have]
    urls = []
    for fn in (_anilist, _jikan):
        try:
            urls += fn(name)
        except Exception as ex:
            print('ref source failed', fn.__name__, ex, flush=True)
    paths = []
    for i, u in enumerate(dict.fromkeys(urls)):
        try:
            p = os.path.join(REF_DIR, f'{slug}_{i:02d}.jpg')
            open(p, 'wb').write(_get(u))
            paths.append(p)
        except Exception as ex:
            print('ref download failed', u, ex, flush=True)
    print(f'{len(paths)} reference pictures for {name}', flush=True)
    return paths


ACTION = ['an anime fight scene with a sword slash', 'an anime character unleashing a glowing energy attack',
          'an anime battle with an explosion and debris', 'an anime character punching an enemy at high speed',
          'an anime character using a magic technique with fire, water or lightning effects']
CALM = ['two anime characters calmly talking', 'an anime character standing still in a quiet room',
        'an anime landscape with no people', 'an anime close-up of a character eating or smiling',
        'a dark blank frame or title card']


class Scorer:
    def __init__(self, name, series=''):
        import torch, open_clip
        from PIL import Image
        self.torch, self.Image = torch, Image
        torch.set_num_threads(max(1, os.cpu_count() or 2))
        self.model, _, self.pre = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        self.model.eval(); self.tok = open_clip.get_tokenizer('ViT-B-32')
        try:
            import cv2
            self.casc = cv2.CascadeClassifier(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lbpcascade_animeface.xml'))
        except Exception:
            self.casc = None
        imgs = []
        for p in refs(name, series):
            try:
                imgs.append(Image.open(p).convert('RGB'))
            except Exception:
                pass
        crops = [c for im in imgs for c in self._faces(im)]
        self.ref = self._img(imgs) if imgs else None
        self.ref_face = self._img(crops) if crops else None
        look = ''
        try:
            for d in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lore.json'))).values():
                look = (d.get(name) or {}).get('look', '') or look
        except Exception:
            pass
        self.look = look
        names_t = [f'{name} from {series}, anime screenshot', f'anime screenshot of {look}' if look else f'{name}, anime character',
                   f'{name}, {look}' if look else f'{name} fighting']
        t = self._txt(names_t + ACTION + CALM)
        nn = len(names_t); self.t_name, self.t_act, self.t_calm = t[:nn], t[nn:nn + len(ACTION)], t[nn + len(ACTION):]
        print(f'charvis ready: {len(imgs)} refs, {len(crops)} ref faces, look: {look or "-"}', flush=True)

    def _img(self, ims):
        with self.torch.no_grad():
            x = self.torch.stack([self.pre(i) for i in ims])
            e = self.model.encode_image(x)
        return (e / e.norm(dim=-1, keepdim=True)).numpy()

    def _txt(self, ts):
        with self.torch.no_grad():
            e = self.model.encode_text(self.tok(ts))
        return (e / e.norm(dim=-1, keepdim=True)).numpy()

    def _faces(self, im):
        if self.casc is None:
            return []
        g = np.asarray(im.convert('L'))
        fs = self.casc.detectMultiScale(g, 1.1, 4, minSize=(max(24, g.shape[0] // 14),) * 2)
        out = []
        for x, y, w, h in fs:
            pad = int(0.35 * w)
            out.append(im.crop((max(0, x - pad), max(0, y - pad), min(im.width, x + w + pad), min(im.height, y + h + pad))))
        return out

    def frame(self, src, t, w=448):
        raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1',
                              '-vf', f'scale={w}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
        import io
        return self.Image.open(io.BytesIO(raw)).convert('RGB') if raw else None

    def score(self, items, batch=48):
        """items: list of (src, t). returns list of dict(char, action, ...) (None where the frame could not be read).
        Two passes: score against the downloaded references, then add the most confident on-screen matches from
        this very anime as extra references (same art style, same season look) and score again."""
        feats = [None] * len(items)
        for b0 in range(0, len(items), batch):
            chunk = [(k, self.frame(s, t)) for k, (s, t) in enumerate(items[b0:b0 + batch], b0)]
            chunk = [(k, im) for k, im in chunk if im is not None]
            if not chunk:
                continue
            E = self._img([im for _, im in chunk])
            for (k, im), e in zip(chunk, E):
                fc = self._faces(im)
                feats[k] = dict(e=e, f=self._img(fc) if fc else None)
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
            whole = float((self.ref @ e).max()) if self.ref is not None else 0.0
            named = float((self.t_name @ e).max())
            face = float((self.ref_face @ f.T).max()) if (self.ref_face is not None and f is not None) else 0.0
            act = float((self.t_act @ e).max() - (self.t_calm @ e).max())
            out.append(dict(char=max(whole, face) + 1.0 * named, face=face, whole=whole, named=named, action=act))
        return out


def get(name, series=''):
    if not name or os.environ.get('CHARVIS', '1') == '0':
        return None
    try:
        return Scorer(name, series)
    except Exception as ex:
        print('charvis unavailable, motion-only picks:', ex, flush=True)
        return None
