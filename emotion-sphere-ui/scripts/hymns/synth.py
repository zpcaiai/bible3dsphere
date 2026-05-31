import sys, os, os, struct, wave, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from melodies import HYMNS

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","public","hymns")
os.makedirs(OUT, exist_ok=True)
SCALE = {1:0,2:2,3:4,4:5,5:7,6:9,7:11}

def midi2freq(m): return 440.0 * 2**((m-69)/12.0)

def organ_note(freq, dur, sr=SR):
    n = int(dur*sr)
    if n<=0: return np.zeros(0)
    t = np.arange(n)/sr
    # 加法合成：管风琴音色(基频+泛音)
    harm = [(1,1.0),(2,0.5),(3,0.32),(4,0.18),(6,0.10)]
    wave_ = np.zeros(n)
    for mult,amp in harm:
        wave_ += amp*np.sin(2*np.pi*freq*mult*t)
    # 轻微颤音
    vib = 1+0.004*np.sin(2*np.pi*5.0*t)
    wave_ *= vib
    # ADSR 包络
    env = np.ones(n)
    a=int(0.015*sr); r=int(min(0.12,dur*0.4)*sr); d=int(0.05*sr)
    if a>0: env[:a]=np.linspace(0,1,a)
    if d>0 and a+d<n: env[a:a+d]=np.linspace(1,0.85,d)
    if r>0: env[-r:]=np.linspace(env[-r],0,r)
    return wave_*env*0.5

def render(h):
    bps = 60.0/h["bpm"]
    buf=[]
    for ev in h["notes"]:
        if isinstance(ev,str): continue
        deg,octv,beats,_=ev
        dur=beats*bps
        if deg==0:
            buf.append(np.zeros(int(dur*SR)))
        else:
            m=h["do"]+SCALE[deg]+12*octv
            buf.append(organ_note(midi2freq(m),dur))
    audio=np.concatenate(buf) if buf else np.zeros(SR)
    # 简单尾混响(衰减延时)
    rev=np.zeros(len(audio)+int(0.3*SR))
    rev[:len(audio)]+=audio
    for delay,g in [(0.07,0.25),(0.13,0.16),(0.21,0.09)]:
        d=int(delay*SR); rev[d:d+len(audio)]+=audio*g
    audio=rev
    # 归一化
    peak=np.max(np.abs(audio)) or 1.0
    audio=audio/peak*0.89
    # 整体淡入淡出
    f=int(0.04*SR)
    audio[:f]*=np.linspace(0,1,f); audio[-f:]*=np.linspace(1,0,f)
    return (audio*32767).astype(np.int16)

for hid,h in HYMNS.items():
    pcm=render(h)
    import tempfile; wavp=os.path.join(tempfile.gettempdir(),f"{hid}.wav"); mp3p=f"{OUT}/{hid}.mp3"
    with wave.open(wavp,"w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wavp,"-codec:a","libmp3lame","-b:a","128k",mp3p],check=True)
    dur=len(pcm)/SR
    print(f"{hid}: {dur:.1f}s -> {os.path.getsize(mp3p)//1024}KB")
print("AUDIO DONE")
