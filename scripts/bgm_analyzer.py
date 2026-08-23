import subprocess, numpy as np, wave, os, json

DIR = os.path.expanduser("~/antigravity/anidoc-ai-automation/assets/audio/phonk")
TMP = os.path.expanduser("~/.cache/opencode/tmp/bpm_tmp.wav")
SR_OUT = 22050
HOP = 512

def analyze(path):
    subprocess.run(["ffmpeg","-y","-v","error","-t","90","-i",path,
                    "-ac","1","-ar",str(SR_OUT),TMP],check=True)
    w = wave.open(TMP); n=w.getnframes(); sr=w.getframerate()
    x=np.frombuffer(w.readframes(n),dtype=np.int16).astype(np.float32)/32768
    m=len(x)//HOP*HOP
    fr=x[:m].reshape(-1,HOP)
    e=fr.sum(1)                      # low-freq-weighted energy (bass/kick)
    d=np.maximum(0,np.diff(np.abs(fr).sum(1)))
    d-=d.mean(); 
    ac=np.correlate(d,d,'full')[len(d)-1:]; ac/=ac[0]+1e-9
    # fine tempo search via comb filter 85-185 BPM, 0.1 BPM steps
    best=(0,0)
    for bpm100 in range(8500,18500,10):
        bpm=bpm100/100
        lag=sr/HOP*60/bpm
        i=int(lag)
        if i+2>=len(ac): continue
        frac=i+1-lag
        v=ac[i]*(1-frac)+ac[i+1]*frac          # interpolate
        # comb: sum harmonics
        h2=i//2; h4=i//4
        if h4>2: v=v*0.6+(ac[h2]*0.25+ac[h4]*0.15)
        if v>best[0]: best=(v,bpm)
    bpm=best[1]
    lagf=sr/HOP*60/bpm
    # phase: pick beat grid offset maximizing onset hits over 90s
    beats=np.arange(0,len(d)-1,lagf)
    offs=np.linspace(0,lagf,24,endpoint=False)
    bestph=0;bestsc=-1
    for o in offs:
        idx=((beats+o)%len(d)).astype(int)
        sc=d[idx].mean()
        if sc>bestsc: bestsc=sc;bestph=o
    hop_s=HOP/sr
    return {"bpm":round(bpm,1),"phase_s":round(bestph*hop_s,3),
            "energy":round(float(e.std()*np.sqrt((d>2*d.std()).mean())),4),
            "onset_rate":round(float((d>2*d.std()).sum()/(m/sr)),3)}

res={}
for f in sorted(os.listdir(DIR)):
    if f.endswith(".mp3"):
        res[f]=analyze(os.path.join(DIR,f))
        print(f,res[f])
json.dump(res,open(os.path.expanduser("~/.cache/opencode/tmp/track_analysis.json"),"w"),indent=1)
