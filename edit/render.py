import json,subprocess,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from pro_fx import build_shot_fx, pair_transitions, default_transition_pattern
from concurrent.futures import ThreadPoolExecutor
W,H=int(os.environ.get('W',1920)),int(os.environ.get('H',1080))
OUT=os.environ.get('OUTDIR','segfx')
shots=json.load(open('shots.json'));P=0.4616
plan=[l.split() for l in open('plan.txt')]
os.makedirs(OUT,exist_ok=True)
def fr(j): return round(j*P*30)
n=len(plan); drop_i=next(i for i,p in enumerate(plan) if int(p[0])==17)
drop2=next(i for i,p in enumerate(plan) if int(p[0])==113)
kinds=default_transition_pattern(n,drop_i)
kinds[drop2-1]='flash'
fxl=pair_transitions(n,kinds)
IMPACT={54,64,68,163,164,166,240,251,284,301,128,211,197}
jobs=[]
for k,(a,b,s) in enumerate(plan):
    a,b,s=int(a),int(b),int(s); nf=fr(b)-fr(a); dur=nf/30
    e,sa,sb=shots[s]; L=sb-sa-0.08; sa+=0.04
    fx=list(fxl[k])
    if a<17 or 109<=a<113: fx.append('drift')
    elif b-a>=2: fx.append('pulse')
    if s in IMPACT and a>=17: fx.append('shake')
    spd=1.0
    if L>=dur: st=sa+(L-dur)/2
    else: st=sa; spd=max(0.5,L/dur)
    vf=build_shot_fx(dur,W,H,fx,beat=P,speed=spd)
    vf+=',eq=contrast=1.12:saturation=1.18:gamma=0.97,vignette=PI/5'
    if k==n-1: vf+=f",fade=out:st={dur-0.6:.2f}:d=0.6"
    jobs.append(['ffmpeg','-nostdin','-v','error','-y','-ss',f'{st:.3f}','-i',f'src/{e}.mp4','-an','-vf',vf,'-frames:v',str(nf),'-r','30','-fps_mode','cfr','-c:v','libx264','-preset','veryfast','-crf','18',f'{OUT}/{k:03d}.mp4'])
only=os.environ.get('ONLY')
if only: jobs=[jobs[int(i)] for i in only.split(',')]
def run(c):
    r=subprocess.run(c,capture_output=True,text=True)
    if r.returncode: print(c[-1],r.stderr[-600:])
with ThreadPoolExecutor(2) as ex: list(ex.map(run,jobs))
open(f'{OUT}/list.txt','w').write(''.join(f"file '{i:03d}.mp4'\n" for i in range(n)))
print('kinds',kinds[15:30])
