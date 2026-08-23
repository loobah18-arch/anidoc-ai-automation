#!/bin/bash
# usage: build_smart.sh <tag> <track.mp3> <bpm> <out_name> <seed>
set -e
POOL=~/.cache/opencode/tmp/smart_clips
TRACK=~/antigravity/anidoc-ai-automation/assets/audio/phonk/$2
BPM=$3
OUTN=$4
SEED=$5
TAG=$1
W=~/.cache/opencode/tmp/amv_work_$OUTN
mkdir -p "$W"
BAR=$(python3 -c "print(240/$BPM)")
HB=$(python3 -c "print(120/$BPM)")
RAMPIN=$(python3 -c "print(320/$BPM)")
ENC=(-c:v libx264 -preset veryfast -crf 21 -threads 2 -pix_fmt yuv420p -an)
BASE="fps=30,scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,setsar=1"
SLOW="fps=30,scale=720:720:force_original_aspect_ratio=increase,crop=720:720,setpts=2*PTS,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs,scale=1080:1080,setsar=1"

mapfile -t CLIPS < <(ls "$POOL"/${TAG}_*.mp4 | sort -V)
N=${#CLIPS[@]}
echo "pool=$TAG n=$N"

mapfile -t IDX < <(python3 -c "
import random
r=random.Random($SEED)
[print(str(i%$N)) for i in r.sample(range(50),$N*3)[:15]]
")
offs=(); for k in $(seq 0 14); do offs+=("$(python3 -c "
import random
print(round(random.Random($SEED*100+$k).uniform(0,1.0),2))
")"); done

seg () { # pool_idx dur filter name [base_override]
  local b="${5:-$BASE}"
  local vf="$b"
  [ -n "$3" ] && vf="$b,$3"
  ffmpeg -y -v error -ss "${offs[$1]}" -t "$2" -i "${CLIPS[${IDX[$1]}]}" \
    -vf "$vf" "${ENC[@]}" "$W/s_$4.mp4"
}

seg 0 "$BAR" "" intro1 "$SLOW"
seg 1 "$BAR" "vignette" intro2 "$SLOW"
seg 2 "$BAR" "crop=w='iw/(1+0.28*pow(min(t/$BAR,1),0.4))':h='ih/(1+0.28*pow(min(t/$BAR,1),0.4))':x='(iw-ow)/2':y='(ih-oh)/2',scale=1080:1080" punch_in1
seg 3 "$BAR" "scale=1440:1440,crop=1400:1400:x='(iw-ow)/2+(random(0)-0.5)*40':y='(ih-oh)/2+(random(1)-0.5)*40',scale=1080:1080" shake1
seg 4 "$BAR" "rgbashift=rh=-6:bh=6" rgb1
seg 5 "$RAMPIN" "setpts=1.333*PTS" ramp1
seg 6 "$BAR" "crop=w='iw/(1.30-0.30*min(t/$BAR,1))':h='ih/(1.30-0.30*min(t/$BAR,1))':x='(iw-ow)/2':y='(ih-oh)/2',scale=1080:1080" punch_out
seg 7 "$BAR" "scale=1500:1500,crop=1440:1440:x='(iw-ow)/2+(random(0)-0.5)*73':y='(ih-oh)/2+(random(1)-0.5)*60',scale=1080:1080,eq=brightness=-0.03:contrast=1.08" shake_hard
seg 8 "$BAR" "rgbashift=rh=7:bh=-7,eq=brightness='0.30*exp(-18*t)'" rgbflash
FADE_ST=$(python3 -c "print(2*$BAR-0.55)")
ffmpeg -y -v error -ss 0.15 -t "$HB" -i "${CLIPS[0]}" -vf "$BASE,eq=brightness='0.45*exp(-25*t)':contrast=1.1" "${ENC[@]}" "$W/s_fc1.mp4"
ffmpeg -y -v error -ss 0.80 -t "$HB" -i "${CLIPS[1]}" -vf "$BASE,eq=brightness='0.40*exp(-25*t)',rgbashift=rh=-5:bh=5" "${ENC[@]}" "$W/s_fc2.mp4"
seg 11 "$BAR" "" outro "$SLOW,fade=t=in:d=0.2,fade=t=out:st=$FADE_ST:d=0.5,vignette"

{
echo "file 's_intro1.mp4'"; echo "file 's_intro2.mp4'"
echo "file 's_punch_in1.mp4'"; echo "file 's_shake1.mp4'"; echo "file 's_rgb1.mp4'"
echo "file 's_ramp1.mp4'"; echo "file 's_punch_out.mp4'"; echo "file 's_shake_hard.mp4'"
echo "file 's_rgbflash.mp4'"
echo "file 's_fc1.mp4'"; echo "file 's_fc2.mp4'"
echo "file 's_outro.mp4'"
} > "$W/list.txt"

VDUR=$(python3 -c "print(14*240/$BPM)")
AFADE=$(python3 -c "print(max(1,14*240/$BPM-1.5))")

ffmpeg -y -v error -f concat -safe 0 -i "$W/list.txt" -i "$TRACK" \
  -filter_complex "[0:v]format=yuv420p[v];[1:a]afade=t=out:st=$AFADE:d=1.5,loudnorm=I=-14:TP=-1.0[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 21 -threads 2 -r 30 -c:a aac -b:a 192k -shortest -movflags +faststart \
  ~/storage/downloads/jjk_${TAG}_amv_$OUTN.mp4

ffprobe -v error -show_entries format=duration,size -of default=nw=1 ~/storage/downloads/jjk_${TAG}_amv_$OUTN.mp4
