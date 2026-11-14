"""Lists every episode in the Google Drive folder (and its sub-folders) so new anime and new
episodes are picked up automatically, with no list to edit by hand.

Each video becomes   <series-slug>:S<season>E<episode>   ->  {name, drive_id, series, season, ep}
The folder must stay shared as "anyone with the link".  If Drive can't be read, the pinned
episodes.json is used instead so a run never breaks because of a listing hiccup.
"""
import html, json, os, re, urllib.request

FOLDER = os.environ.get('DRIVE_FOLDER', '1e5_IF3GRHNr315hP5zK_qlyfsKXm3Ox4')
VIDEO = re.compile(r'\.(mp4|mkv|webm|mov|avi|m4v)$', re.I)
SKIP_FOLDERS = re.compile(r'output|amv|render|export|music|song', re.I)
EP_PATTERNS = [
    re.compile(r'[Ss](\d{1,2})[ ._-]*[Ee](\d{1,4})'),                      # S01_E07, S1E7
    re.compile(r'(?:season|s)[ ._-]*(\d{1,2}).*?(?:episode|ep)[ ._-]*(\d{1,4})', re.I),
    re.compile(r'(?:episode|ep)[ ._-]*(\d{1,4})', re.I),                     # Episode 7, Ep07
    re.compile(r'(?:^|[ ._-])-[ ._]*(\d{1,4})(?:[ ._\[(v-]|$)'),             # "Show - 07"
]


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'ignore')


def list_folder(fid):
    page = _get(f'https://drive.google.com/embeddedfolderview?id={fid}')
    out = []
    for url, title in re.findall(r'<a href="(https://drive\.google\.com/[^"]+)"[^>]*>.*?flip-entry-title">([^<]+)<', page, re.S):
        title = html.unescape(title).strip()
        m = re.search(r'/folders/([\w-]+)', url)
        if m:
            out.append(('folder', m.group(1), title))
            continue
        m = re.search(r'/file/d/([\w-]+)', url)
        if m:
            out.append(('file', m.group(1), title))
    return out


def slug(text):
    t = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', text).replace('_', ' ').replace('.', ' ')
    t = re.sub(r'\b\d{3,4}[pP]\b|\b(english|eng|dub|sub|hindi|dual|audio|x26[45]|hevc|web|bluray|hd)\b', ' ', t, flags=re.I)
    t = re.sub(r'[^A-Za-z0-9]+', '-', t).strip('-').lower()
    return t


def parse(name, folder_name=''):
    base = VIDEO.sub('', name)
    for i, pat in enumerate(EP_PATTERNS):
        m = pat.search(base)
        if not m:
            continue
        if i < 2:
            season, ep = int(m.group(1)), int(m.group(2))
        else:
            season, ep = 1, int(m.group(1))
            ms = re.search(r'(?:season|[Ss])[ ._-]*(\d{1,2})\b', folder_name + ' ' + base[:m.start()])
            if ms:
                season = int(ms.group(1))
        if ep > 1900:                                                       # a year, not an episode
            continue
        series = slug(base[:m.start()]) or slug(re.sub(r'season[ ._-]*\d+', '', folder_name, flags=re.I))
        if series:
            return series, season, ep
    return None                                                             # a movie or something else: not used


def build(folder=FOLDER, depth=0, folder_name='', lib=None):
    lib = {} if lib is None else lib
    for kind, fid, title in list_folder(folder):
        if kind == 'folder':
            if depth < 3 and not SKIP_FOLDERS.search(title):
                build(fid, depth + 1, title, lib)
            continue
        if not VIDEO.search(title):
            continue
        p = parse(title, folder_name)
        if not p:
            continue
        series, season, ep = p
        key = f'{series}:S{season}E{ep:02d}'
        lib.setdefault(key, dict(name=title, drive_id=fid, series=series, season=season, ep=ep))
    return lib


def pinned():
    lib = {}
    for code, e in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'episodes.json'))).items():
        p = parse(e['name']) or ('jujutsu-kaisen', int(code[1]), int(code[3:]))
        lib[f'{p[0]}:S{p[1]}E{p[2]:02d}'] = dict(name=e['name'], drive_id=e['drive_id'], series=p[0], season=p[1], ep=p[2])
    return lib


def library():
    try:
        lib = build()
        if lib:
            return lib, 'drive'
    except Exception as ex:
        print('drive listing failed, using episodes.json:', ex, flush=True)
    return pinned(), 'pinned'


if __name__ == '__main__':
    lib, src = library()
    by = {}
    for k, v in lib.items():
        by.setdefault(v['series'], []).append(k)
    print(src, len(lib), 'episodes')
    for s, ks in sorted(by.items()):
        print(f'  {s}: {len(ks)}  ({min(ks)} .. {max(ks)})')
