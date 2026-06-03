#!/usr/bin/env python3
"""按 src/hymnTimings.js 的逐字时间轴重新合成 9 首圣诗 mp3（管风琴音色，192kbps）。
旋律为公有领域圣诗标准曲调；音符起止严格跟随时间轴，保证前端逐字跟唱高亮对齐。
输出: emotion-sphere-ui/public/hymns/<id>.mp3
"""
import json, math, re, subprocess, wave, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
TIMINGS = ROOT / 'emotion-sphere-ui/src/hymnTimings.js'
OUT = ROOT / 'emotion-sphere-ui/public/hymns'
SR = 44100

NOTE = {n: i for i, n in enumerate(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'])}
def freq(name):
    m = re.match(r'([A-G]#?)(\d)', name)
    semi = NOTE[m.group(1)] + (int(m.group(2)) + 1) * 12
    return 440.0 * 2 ** ((semi - 69) / 12)

# 每行音高与 hymnTimings 字数一一对应（已核对）
MELODIES = {
 'amazing-grace': [  # NEW BRITAIN (G)
   ['D4','G4','B4','G4','B4','A4','G4','E4'],
   ['D4','G4','B4','G4','A4','G4']],
 'it-is-well': [  # VILLE DU HAVRE (C)
   ['E4','F4','E4','D4','C4','D4','E4','F4','E4','D4','G4'],
   ['G4','A4','G4','F4','E4','F4','G4','A4','G4','D4','C4']],
 'how-great-thou-art': [  # O STORE GUD (C)
   ['E4','G4','G4','G4','G4','F4','E4','F4','G4','F4','E4'],
   ['E4','F4','G4','A4','A4','G4','F4','G4','E4','C4']],
 'holy-holy-holy': [  # NICAEA (C)
   ['C4','C4','E4','E4','G4','G4'],
   ['A4','A4','G4','G4','E4'],
   ['E4','G4','C5','C5','B4','C5'],
   ['A4','G4','F4','E4','D4','C4']],
 'blessed-assurance': [  # ASSURANCE (C)
   ['E4','G4','C5','A4'],
   ['G4','A4','G4','E4'],
   ['F4','A4','D5','C5'],
   ['G4','E4','D4','C4']],
 'safe-in-arms': [  # W.H.Doane (C)
   ['C4','E4','G4','G4','A4','G4','E4'],
   ['G4','E4','G4','A4','G4','D4'],
   ['D4','E4','G4','A4','B4','A4','G4'],
   ['E4','G4','E4','D4','D4','C4']],
 'joy-to-the-world': [  # ANTIOCH (C) 标志性下行音阶
   ['C5','B4','A4','G4','F4','E4','D4','C4'],
   ['G4','A4','A4','B4','B4','C5'],
   ['C5','C5','B4','A4','G4','G4','F4','E4']],
 'when-i-survey': [  # HAMBURG (C)
   ['C4','D4','E4','F4','E4','D4','E4','E4'],
   ['G4','G4','A4','G4','F4','E4','F4','G4'],
   ['E4','F4','G4','F4','E4','D4','D4','C4']],
 'mighty-fortress': [  # EIN FESTE BURG (C)
   ['C5','C5','C5','G4','A4','B4','C5','B4'],
   ['A4','G4','F4','G4','E4','D4','C4'],
   ['C5','C5','C5','G4','A4','B4','C5','B4'],
   ['A4','G4','F4','G4','E4','D4','C4']],
}

def organ_tone(f, dur, vel=0.32):
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    # 加法合成：基频+泛音(8'+4'+2'+2/3') + 轻微合唱失谐
    w = (1.00*np.sin(2*np.pi*f*t) + 0.45*np.sin(2*np.pi*2*f*t)
       + 0.22*np.sin(2*np.pi*3*f*t) + 0.10*np.sin(2*np.pi*4*f*t)
       + 0.18*np.sin(2*np.pi*f*1.003*t) + 0.30*np.sin(2*np.pi*f/2*t))
    # ADSR：柔起音、满延音、自然释音
    a, r = int(0.04*SR), max(int(0.12*SR), 1)
    env = np.ones(n)
    env[:min(a,n)] = np.linspace(0, 1, min(a,n))
    env[-min(r,n):] *= np.linspace(1, 0, min(r,n))
    return (w * env * vel).astype(np.float32)

def reverb(x, sr=SR):
    out = x.copy()
    for d, g in [(0.043,0.28),(0.067,0.22),(0.097,0.16),(0.131,0.10)]:
        dn = int(d*sr); y = np.zeros_like(x); y[dn:] = x[:-dn]*g; out += y
    return out

def synth(hid, lines):
    mel = MELODIES[hid]
    assert len(mel) == len(lines), f'{hid}: 行数不符'
    # 时长 = 末字 + 3.2s 释音/混响尾
    end = lines[-1]['syls'][-1]['t'] + 3.2
    buf = np.zeros(int(end*SR) + SR, dtype=np.float32)
    for li, line in enumerate(lines):
        syls = line['syls']
        assert len(mel[li]) == len(syls), f'{hid} L{li+1}: {len(mel[li])} 音 vs {len(syls)} 字'
        for si, syl in enumerate(syls):
            t0 = syl['t']
            if si + 1 < len(syls): t1 = syls[si+1]['t']
            elif li + 1 < len(lines): t1 = lines[li+1]['syls'][0]['t']
            else: t1 = t0 + 2.4  # 终止音延长
            dur = min(max(t1 - t0, 0.25), 4.0) + 0.10  # 轻微连音重叠
            tone = organ_tone(freq(mel[li][si]), dur)
            i0 = int(t0*SR)
            buf[i0:i0+len(tone)] += tone[:len(buf)-i0]
    buf = reverb(buf)
    peak = np.max(np.abs(buf)) or 1.0
    buf = buf / peak * 0.89  # -1dBFS 归一化
    pcm = (buf * 32767).astype(np.int16)
    wav = pathlib.Path('/tmp') / f'{hid}.wav'
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    mp3 = OUT / f'{hid}.mp3'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(wav),
                    '-codec:a','libmp3lame','-b:a','192k',str(mp3)], check=True)
    wav.unlink()
    print(f'  ✅ {hid}.mp3  {mp3.stat().st_size/1024:.0f} KB  {end:.1f}s')

def main():
    src = TIMINGS.read_text(encoding='utf-8')
    data = json.loads(src[src.index('export default')+len('export default'):].strip().rstrip(';'))
    OUT.mkdir(parents=True, exist_ok=True)
    for hid, h in data.items():
        synth(hid, h['lines'])
    print('全部完成 →', OUT)

if __name__ == '__main__':
    main()
