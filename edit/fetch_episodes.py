"""Download the three JJK episodes the Gojo AMV is cut from, straight from the Google Drive folder."""
import json, os, subprocess, sys
os.makedirs('src', exist_ok=True)
eps = json.load(open('episodes.json'))
for code, e in eps.items():
    dst = f'src/{code}.mp4'
    if os.path.exists(dst) and os.path.getsize(dst) > 50_000_000:
        continue
    for attempt in range(3):
        r = subprocess.run([sys.executable, '-m', 'gdown', '--fuzzy', f"https://drive.google.com/uc?id={e['drive_id']}", '-O', dst])
        if r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 50_000_000:
            break
    else:
        sys.exit(f'download failed: {code} ({e["name"]})')
    print(code, os.path.getsize(dst))
