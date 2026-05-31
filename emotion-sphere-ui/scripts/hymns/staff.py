import sys, os, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from melodies import HYMNS

OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","public","hymns")
CJK="/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
LAT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LATB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

GOLD=(255,215,0,255); NOTE=(238,238,242,255); DIM=(255,255,255,150)
LINE=(255,255,255,95); LYR=(220,220,230,235)

def catmull(pts, n=16):
    P=np.array(pts,float); out=[]
    ext=np.vstack([P[0],P,P[-1]])
    for i in range(1,len(ext)-2):
        p0,p1,p2,p3=ext[i-1],ext[i],ext[i+1],ext[i+2]
        for t in np.linspace(0,1,n,endpoint=False):
            t2=t*t;t3=t2*t
            x=0.5*((2*p1[0])+(-p0[0]+p2[0])*t+(2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2+(-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y=0.5*((2*p1[1])+(-p0[1]+p2[1])*t+(2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2+(-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            out.append((x,y))
    out.append((float(P[-1][0]),float(P[-1][1]))); return out

def stroke(d,pts,w,fill):
    d.line(pts,fill=fill,width=max(1,int(w)),joint="curve")
    r=w/2
    for x,y in (pts[0],pts[-1]): d.ellipse([x-r,y-r,x+r,y+r],fill=fill)

def draw_clef(d,x0,topY,S):
    cp=[(2.0,4.8),(2.0,3.0),(2.0,-1.0),(2.0,-1.55),(1.4,-1.45),(1.0,-0.7),(1.1,0.2),
        (1.8,0.9),(2.35,1.8),(2.1,2.85),(1.35,3.35),(0.55,3.0),(0.35,2.15),(0.95,1.55),
        (1.75,1.7),(2.05,2.45),(1.7,3.05),(1.15,2.9)]
    pts=[(x0+x*S, topY+y*S) for x,y in cp]
    stroke(d,catmull(pts),max(2,S*0.42),NOTE)
    bx,by=x0+2.0*S, topY+4.8*S; r=S*0.34
    d.ellipse([bx-r,by-r,bx+r,by+r],fill=NOTE)

def render(hid,h):
    S=13; PADX=42; LEFT=PADX+int(S*4.4); SLOT=int(S*3.6)
    notes=h["notes"]
    x=LEFT+int(S*2.4); layout=[]
    for ev in notes:
        if ev=="|": layout.append(("bar",x)); x+=14; continue
        if isinstance(ev,str): continue
        deg,octv,beats,lyr=ev
        layout.append(("note",x,deg,octv,beats,lyr)); x+=max(int(SLOT*beats),int(SLOT*0.8))
    W=x+PADX; TITLE=80; topY=TITLE+42; H=topY+int(S*4)+88
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    fT=ImageFont.truetype(CJK,30); fE=ImageFont.truetype(LAT,16)
    fMeta=ImageFont.truetype(LAT,14); fTS=ImageFont.truetype(LATB,28); fL=ImageFont.truetype(CJK,19)
    d.text((PADX,18),h["title"],font=fT,fill=GOLD)
    tw=d.textlength(h["title"],font=fT); d.text((PADX+tw+12,30),h["en"],font=fE,fill=DIM)
    d.text((W-PADX,30),f'Key C   {h["bpm"]}bpm   {h["beats_per_bar"]}/4',font=fMeta,fill=DIM,anchor="ra")
    for i in range(5):
        y=topY+i*S; d.line([(PADX,y),(W-PADX,y)],fill=LINE,width=1)
    draw_clef(d,PADX+4,topY,S)
    d.text((LEFT-2,topY-7),str(h["beats_per_bar"]),font=fTS,fill=NOTE,anchor="la")
    d.text((LEFT-2,topY+int(S*2)-7),"4",font=fTS,fill=NOTE,anchor="la")
    def y_of(step): return topY+(10-step)*(S/2.0)
    nh_rx=S*0.72; nh_ry=S*0.52
    for it in layout:
        if it[0]=="bar":
            bx=it[1]; d.line([(bx,topY),(bx,topY+4*S)],fill=LINE,width=1); continue
        _,nx,deg,octv,beats,lyr=it
        cx=nx+nh_rx
        if deg==0:
            ry=topY+1.6*S
            d.rectangle([cx-S*0.5,ry,cx+S*0.5,ry+S*0.45],fill=DIM)
        else:
            step=octv*7+(deg-1); cy=y_of(step)
            # 加线(底线以下偶数step / 顶线以上偶数step)
            for ss in range(0,step-1)[::-1] if step<2 else []:
                if ss%2==0 and ss<2:
                    yy=y_of(ss); d.line([(cx-S*1.15,yy),(cx+S*1.15,yy)],fill=LINE,width=1)
            for ss in range(12,step+1) if step>10 else []:
                if ss%2==0 and ss>10:
                    yy=y_of(ss); d.line([(cx-S*1.15,yy),(cx+S*1.15,yy)],fill=LINE,width=1)
            box=[cx-nh_rx,cy-nh_ry,cx+nh_rx,cy+nh_ry]
            if beats>=2: d.ellipse(box,outline=NOTE,width=2)
            else: d.ellipse(box,fill=NOTE)
            up = cy>=topY+2*S
            sx = cx+nh_rx-1 if up else cx-nh_rx+1
            sy2 = cy-3.3*S if up else cy+3.3*S
            d.line([(sx,cy),(sx,sy2)],fill=NOTE,width=2)
            if beats==0.5:
                d.line([(sx,sy2),(sx+S*0.9, sy2+(S*0.9 if up else -S*0.9))],fill=NOTE,width=2)
            if beats==3:
                d.ellipse([cx+nh_rx+4,cy-2,cx+nh_rx+8,cy+2],fill=NOTE)
        if lyr:
            lw=d.textlength(lyr,font=fL); d.text((cx-lw/2,topY+4*S+22),lyr,font=fL,fill=LYR)
    img.save(f"{OUT}/{hid}.png"); return W,H

ids = sys.argv[1:] or list(HYMNS)
for hid in ids:
    w,hh=render(hid,HYMNS[hid]); print(hid,w,hh)
print("ok")
