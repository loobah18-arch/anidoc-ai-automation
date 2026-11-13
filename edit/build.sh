#!/usr/bin/env bash
# Rebuilds the Gojo AMV (DYGO - Funk Infernal) shot for shot: 71 beat-synced cuts at 130 BPM, 1920x1080, 60 s.
set -euo pipefail
cd "$(dirname "$0")"
python3 fetch_episodes.py
rm -rf segfx && OUTDIR=segfx python3 render.py
mkdir -p ../out
ffmpeg -nostdin -v error -y -f concat -safe 0 -i segfx/list.txt -c copy ../out/video.mp4
ffmpeg -nostdin -v error -y -i ../out/video.mp4 -ss 7.573 -i music/dygo_funk_infernal.mp3 \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -af "afade=t=out:st=58.8:d=1.2" -shortest -movflags +faststart ../out/Gojo_AMV_Funk_Infernal.mp4
rm ../out/video.mp4
ffprobe -v error -show_entries format=duration:stream=width,height -of compact ../out/Gojo_AMV_Funk_Infernal.mp4
