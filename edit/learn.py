"""Learn from views: pull views (and retention when the Analytics API allows it) for the narrated Shorts this branch
uploaded, log them per song / voice / character in history.json, and turn them into small pick weights
(history.json "perf") that narrate.py / auto.py use to nudge least_used picks toward what viewers watched.

No-op (exit 0, history untouched) when there are no uploads, no matching Shorts, or no YouTube credentials.
"""
import json, math, os, re, sys, time, traceback
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
HIST = os.path.join(HERE, 'history.json')
UPLOADS = os.path.join(ROOT, 'metadata', 'youtube_upload_history.json')
MIN_AGE_H = float(os.environ.get('LEARN_MIN_AGE_HOURS', 24))       # too fresh to judge before this
SHRINK = float(os.environ.get('LEARN_SHRINK', 2))                  # few samples -> weight pulled toward 0


def parse_upload_ts(s):
    """'Mon 2026-11-09 10:31 PM IST (UTC+05:30)' -> aware datetime"""
    m = re.search(r'(\d{4}-\d\d-\d\d) (\d{1,2}:\d\d) ?([AP]M)?.*?UTC([+-]\d\d):?(\d\d)', s or '')
    if not m:
        return None
    d, hm, ap, oh, om = m.groups()
    dt = datetime.strptime(f'{d} {hm} {ap or ""}'.strip(), '%Y-%m-%d %I:%M %p' if ap else '%Y-%m-%d %H:%M')
    sign = 1 if oh.startswith('+') else -1
    return dt.replace(tzinfo=timezone(sign * timedelta(hours=abs(int(oh)), minutes=int(om))))


def parse_convo_ts(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M UTC').replace(tzinfo=timezone.utc)
    except Exception:
        return None


def norm_title(t):
    return re.sub(r'\s+', ' ', re.sub(r'#\w+', '', t or '')).strip().lower()


def main():
    hist = json.load(open(HIST))
    ups = json.load(open(UPLOADS)) if os.path.exists(UPLOADS) else []
    ups = [u for u in ups if u.get('video_id') and str(u.get('status', 'uploaded')).startswith('upload')]
    convos = [c for c in hist.get('convos', []) if c.get('title')]
    if not ups or not convos:
        print(f'learn: nothing to learn yet ({len(ups)} uploads, {len(convos)} narrated Shorts with titles)', flush=True); return
    # link each narrated Short to its upload: same title, uploaded soonest after it was rendered
    links = {}
    for c in convos:
        ct = parse_convo_ts(c.get('time', ''))
        best = None
        for u in ups:
            if norm_title(u.get('title')) != norm_title(c['title']):
                continue
            ut = parse_upload_ts(u.get('timestamp', ''))
            if ct and ut and not (timedelta(minutes=-30) <= ut - ct <= timedelta(days=3)):
                continue
            gap = abs((ut - ct).total_seconds()) if (ct and ut) else 1e9
            if best is None or gap < best[0]:
                best = (gap, u)
        if best and best[1]['video_id'] not in links:
            links[best[1]['video_id']] = (c, best[1])
    if not links:
        print('learn: no uploaded narrated Shorts matched yet', flush=True); return
    from publishers.youtube_publisher import get_valid_access_token
    import requests
    tok = get_valid_access_token()
    if not tok:
        print('learn: no YouTube credentials, skipping', flush=True); return
    H = {'Authorization': f'Bearer {tok}'}
    ids = list(links)
    stats = {}
    for i in range(0, len(ids), 50):
        r = requests.get('https://www.googleapis.com/youtube/v3/videos', headers=H, timeout=20,
                         params=dict(part='statistics,snippet', id=','.join(ids[i:i + 50])))
        r.raise_for_status()
        for it in r.json().get('items', []):
            st = it.get('statistics', {})
            stats[it['id']] = dict(views=int(st.get('viewCount', 0)), likes=int(st.get('likeCount', 0) or 0),
                                   published=it.get('snippet', {}).get('publishedAt'))
    # retention needs the yt-analytics.readonly scope; most upload-only tokens don't have it, so this is best-effort
    try:
        start = min(s['published'][:10] for s in stats.values() if s.get('published'))
        r = requests.get('https://youtubeanalytics.googleapis.com/v2/reports', headers=H, timeout=20, params=dict(
            ids='channel==MINE', startDate=start, endDate=time.strftime('%Y-%m-%d'), metrics='views,averageViewPercentage,averageViewDuration',
            dimensions='video', filters='video==' + ','.join(stats), maxResults=200))
        if r.status_code == 200:
            for row in r.json().get('rows', []):
                if row[0] in stats:
                    stats[row[0]].update(retention=float(row[2]), avg_view_s=float(row[3]))
            print('learn: retention from YouTube Analytics for', sum('retention' in s for s in stats.values()), 'videos', flush=True)
        else:
            print('learn: retention unavailable (analytics', r.status_code, ') - using views only', flush=True)
    except Exception as ex:
        print('learn: retention unavailable -', ex, flush=True)
    now = datetime.now(timezone.utc)
    vids = hist.setdefault('perf_videos', {})
    for vid, s in stats.items():
        c, u = links[vid]
        pub = datetime.fromisoformat(s['published'].replace('Z', '+00:00')) if s.get('published') else parse_upload_ts(u.get('timestamp'))
        age_h = (now - pub).total_seconds() / 3600 if pub else 0
        if age_h < MIN_AGE_H:
            continue
        # score: retention when we have it, otherwise views per day (log), both judged at the same age scale
        vpd = s['views'] / max(1.0, age_h / 24)
        vids[vid] = dict(character=c.get('character'), song=c.get('song'), voice=c.get('voice'), title=c.get('title'),
                         views=s['views'], likes=s['likes'], retention=s.get('retention'), age_h=round(age_h, 1),
                         score=round(math.log1p(vpd) + (s['retention'] / 25.0 if s.get('retention') is not None else 0), 4),
                         updated=now.strftime('%Y-%m-%d %H:%M UTC'))
    if len(vids) < 2:
        print(f'learn: {len(vids)} judged video(s) - need 2+ before weighting picks', flush=True)
        json.dump(hist, open(HIST, 'w'), indent=1); return
    scores = [v['score'] for v in vids.values()]
    mu = sum(scores) / len(scores); sd = (sum((x - mu) ** 2 for x in scores) / len(scores)) ** 0.5 or 1.0
    perf = dict(updated=now.strftime('%Y-%m-%d %H:%M UTC'), videos=len(vids))
    for dim in ('song', 'character', 'voice'):
        acc = {}
        for v in vids.values():
            if v.get(dim):
                acc.setdefault(v[dim], []).append((v['score'] - mu) / sd)
        # mean z, shrunk toward 0 for few samples, clipped to [-1, 1]: a nudge, never a lock-in
        perf[dim] = {k: round(max(-1.0, min(1.0, sum(z) / len(z) * len(z) / (len(z) + SHRINK))), 3) for k, z in acc.items()}
    hist['perf'] = perf
    json.dump(hist, open(HIST, 'w'), indent=1)
    print('learn: weights', json.dumps(perf), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        print('learn: skipped after an error (picks unchanged)', flush=True)
    sys.exit(0)
