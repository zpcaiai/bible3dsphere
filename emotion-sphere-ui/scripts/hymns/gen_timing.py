import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from melodies import HYMNS
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","src","hymnTimings.js")
data={}
for hid,h in HYMNS.items():
    bps=60.0/h["bpm"]; lines=[]; cur=[]; t=0.0
    def flush():
        global cur
        if cur:
            syls=[]
            for (st,dur,lyr) in cur:
                if not lyr: continue
                # 多字歌词(如"保护")在该音符时长内均分
                k=len(lyr)
                for j,ch in enumerate(lyr):
                    syls.append({"t":round(st+dur*j/k,2),"ch":ch})
            if syls:
                lines.append({"t":syls[0]["t"],"text":"".join(s["ch"] for s in syls),"syls":syls})
        cur=[]
    for ev in h["notes"]:
        if ev=="//": flush(); continue
        if ev=="|": continue
        deg,octv,beats,lyr=ev
        cur.append((t,beats*bps,lyr)); t+=beats*bps
    flush()
    data[hid]={"lines":lines,"end":round(t,2)}
with open(OUT,"w",encoding="utf-8") as f:
    f.write("// 自动生成：诗歌跟唱时间轴(逐行+逐字，由 melodies 旋律导出)。请勿手改。\n")
    f.write("export default "+json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print("wrote timings with syls")
import os; print("size",os.path.getsize(OUT),"bytes")
# sample
print(json.dumps(data["joy-to-the-world"]["lines"][0],ensure_ascii=False)[:160])
