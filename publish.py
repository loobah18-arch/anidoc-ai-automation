"""Upload out/meta.json's Short through the same protection layers as main / auto-clipper:
   Layer 0 (24 h spacing), Layer 1 (early momentum >= 2k views in 24 h), Layer 2 (velocity >= 2.5k views/h),
   plus block detection: a blocked upload is deleted, remediated and retried."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from publishers.youtube_publisher import upload_video_with_block_retry

meta = json.load(open('out/meta.json'))
res = upload_video_with_block_retry(Path(meta['file']), meta['title'], meta['description'], meta['tags'],
                                    privacy_status='public', gate_check=True)
print(json.dumps(res, indent=1, default=str))
if res.get('status') == 'error':
    sys.exit(1)
