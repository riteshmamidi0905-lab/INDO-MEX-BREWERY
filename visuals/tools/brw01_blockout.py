#!/usr/bin/env python3
"""BRW-01 layout block-out (NOT an image of the brewery). A simple perspective projection of the LOCKED-SCENE-DNA section 4 geometry, used only
as a layout/depth guide so a generator can count to six and see the true horseshoe. Plan units: feet; x east, y north, z up; origin = SW corner of
the production room (44 x 48 ft; the interior glass wall is the y=0 line). Camera = on the south promenade side of the interior glass wall (about 11 ft up the mezzanine edge), SE of the hall axis, looking NNW.
Run from repo root: python3 visuals/tools/brw01_blockout.py -> visuals/generated/BRW-01-inputs/ (blockout + annotated + plan)."""
import numpy as np, os
from PIL import Image, ImageDraw, ImageFont
OUT="visuals/generated/BRW-01-inputs"; W,H=2000,1125
CAM=np.array([28.0,-11.0,10.5]); TGT=np.array([17.0,32.0,11.0]); F=21.0   # 21 mm equivalent (36 mm sensor width)
TANKS={1:(6,16),2:(6,26),3:(6,38),4:(38,38),5:(38,26),6:(38,16)}       # centres (x,y); legs 1,2 west, 3 and 4 flank the deck, 5,6 east
R=2.5; LEG=3.0; CONE=4.0; SHELL=12.0
fwd=TGT-CAM; fwd/=np.linalg.norm(fwd); right=np.cross(fwd,[0,0,1]); right/=np.linalg.norm(right); up=np.cross(right,fwd)
fpx=F/36.0*W
def P(p):
    d=np.array(p,float)-CAM; z=d@fwd
    return None if z<0.5 else (W/2+fpx*(d@right)/z, H/2-fpx*(d@up)/z, z)
def poly(dr,pts,col,outline=None):
    q=[P(p) for p in pts]
    if any(v is None for v in q): return
    dr.polygon([(a,b) for a,b,_ in q],fill=col,outline=outline)
def cyl(dr,c,z0,z1,r,col,shade=True,n=28):
    cx,cy=c; ring=[(cx+r*np.cos(t),cy+r*np.sin(t)) for t in np.linspace(0,2*np.pi,n,endpoint=False)]
    for i in range(n):                                   # side quads, shaded by facing angle
        a,b=ring[i],ring[(i+1)%n]; mid=np.arctan2((a[1]+b[1])/2-cy,(a[0]+b[0])/2-cx)
        s=0.55+0.45*np.cos(mid-np.arctan2(-1,0.3)) if shade else 1
        poly(dr,[(*a,z0),(*b,z0),(*b,z1),(*a,z1)],tuple(int(v*max(s,0.35)) for v in col))
    poly(dr,[(x,y,z1) for x,y in ring],tuple(min(255,int(v*1.1)) for v in col))
def cone(dr,c,z0,z1,r0,r1,col,n=28):
    cx,cy=c; a0=[(cx+r0*np.cos(t),cy+r0*np.sin(t)) for t in np.linspace(0,2*np.pi,n,endpoint=False)]
    a1=[(cx+r1*np.cos(t),cy+r1*np.sin(t)) for t in np.linspace(0,2*np.pi,n,endpoint=False)]
    for i in range(n):
        j=(i+1)%n; poly(dr,[(*a0[i],z0),(*a0[j],z0),(*a1[j],z1),(*a1[i],z1)],col)
def box(dr,x0,y0,z0,x1,y1,z1,col):
    for pts,k in [([(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)],0.7),([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],1.0),([(x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)],0.55),([(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)],0.55),([(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)],0.85)]:
        poly(dr,pts,tuple(int(v*k) for v in col),(30,30,30))
def render(label):
    im=Image.new("RGB",(W,H),(48,48,50)); dr=ImageDraw.Draw(im)
    poly(dr,[(0,-12,0),(44,-12,0),(44,48,0),(0,48,0)],(150,146,140))                      # warm-grey floor
    for x in range(0,45,4): 
        a,b=P((x,0.6,0)),P((x,48,0)); 
        if a and b: dr.line([a[:2],b[:2]],fill=(135,132,127),width=1)
    for y in range(0,49,4):
        a,b=P((0,max(y,0.6),0)),P((44,max(y,0.6),0))
        if a and b: dr.line([a[:2],b[:2]],fill=(135,132,127),width=1)
    poly(dr,[(0,48,0),(44,48,0),(44,48,38),(0,48,38)],(92,90,88)); poly(dr,[(0,0,0),(0,48,0),(0,48,38),(0,0,38)],(80,78,76))   # north wall, west wall
    poly(dr,[(0,0,38),(44,0,38),(44,48,38),(0,48,38)],(70,66,62))
    items=[]                                                                           # painter's order: far to near
    items.append(("deck",np.linalg.norm(np.array([22,42,2])-CAM)))
    for n,c in TANKS.items(): items.append((n,np.linalg.norm(np.array([c[0],c[1],8])-CAM)))
    for k,_ in sorted(items,key=lambda t:-t[1]):
        if k=="deck":
            box(dr,10,36,0,34,48,4,(120,122,126))                                      # raised deck 24 x 12, +4 ft
            cyl(dr,(18,43),4,12,3.5,(176,100,52)); cone(dr,(18,43),12,14,3.5,2.0,(176,100,52))   # two copper vessels, dia ~7 ft
            cyl(dr,(26,43),4,12,3.5,(176,100,52)); cone(dr,(26,43),12,14,3.5,2.0,(176,100,52))
            poly(dr,[(15,40,17),(29,40,17),(22,43,22),(22,43,22)],(150,86,46))           # hood (schematic)
            cyl(dr,(22,43),20,38,1.0,(150,150,155))                                    # stack to roof
            for x in (10,34):                                                          # 42-in guardrail posts
                for y in (36,48): cyl(dr,(x,y),4,7.5,0.15,(60,60,64),shade=False,n=6)
        else:
            cx,cy=TANKS[k]; z=LEG
            for lx,ly in [(1.8,1.8),(-1.8,1.8),(1.8,-1.8),(-1.8,-1.8)]: cyl(dr,(cx+lx,cy+ly),0,LEG+1,0.25,(70,70,74),shade=False,n=6)
            cone(dr,(cx,cy),LEG,LEG+CONE,0.5,R,(55,54,52))                              # graphite cone
            cyl(dr,(cx,cy),LEG+CONE,LEG+CONE+SHELL,R,(190,192,196))                     # stainless shell
            cyl(dr,(cx,cy),LEG+CONE+5.6,LEG+CONE+6.1,R+0.04,(232,135,14),shade=False)    # ~6 in marigold sleeve
            cone(dr,(cx,cy),LEG+CONE+SHELL,LEG+CONE+SHELL+0.8,R,R*0.55,(200,202,206))   # dished top
    poly(dr,[(0,0.2,0),(44,0.2,0),(44,0.2,38),(0,0.2,38)],(0,0,0)) if False else None
    ann=im.copy(); d2=ImageDraw.Draw(ann)
    try: ft=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",54)
    except Exception: ft=ImageFont.load_default()
    for n,c in TANKS.items():
        p=P((c[0],c[1],LEG+CONE+SHELL+3.5)); d2.text((p[0]-18,p[1]-30),str(n),fill=(255,255,255),font=ft,stroke_width=4,stroke_fill=(0,0,0))
    for i,(x,y) in enumerate([(18,43),(26,43)]):
        p=P((x,y,15)); d2.text((p[0]-18,p[1]-30),"CU",fill=(255,200,120),font=ft,stroke_width=4,stroke_fill=(0,0,0))
    return im,ann
def plan():
    s=18; im=Image.new("RGB",(44*s+80,48*s+80),(245,243,238)); d=ImageDraw.Draw(im); ox,oy=40,40
    X=lambda x:ox+x*s; Y=lambda y:oy+(48-y)*s
    d.rectangle([X(0),Y(48),X(44),Y(0)],outline=(40,40,40),width=3); d.rectangle([X(10),Y(48),X(34),Y(36)],fill=(210,205,198),outline=(60,60,60))
    for x in (18,26): d.ellipse([X(x-3.5),Y(43+3.5),X(x+3.5),Y(43-3.5)],fill=(176,100,52))
    for n,(cx,cy) in TANKS.items(): d.ellipse([X(cx-R),Y(cy+R),X(cx+R),Y(cy-R)],fill=(190,192,196),outline=(40,40,40)); d.text((X(cx)-4,Y(cy)-6),str(n),fill=(0,0,0))
    cx,cy=CAM[0],CAM[1]; d.polygon([(X(cx),Y(cy)),(X(cx)-10,Y(cy)+22),(X(cx)+10,Y(cy)+22)],fill=(30,90,200))
    d.line([(X(cx),Y(cy)),(X(TGT[0]),Y(TGT[1]))],fill=(30,90,200),width=2)
    d.text((X(1),Y(0)+8),"S: interior glass wall (guests/promenade beyond)   camera = blue triangle (promenade, SE of axis, looking NNW)",fill=(0,0,0))
    return im
if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True); a,b=render("x"); a.save(f"{OUT}/BRW-01-layout-blockout.png"); b.save(f"{OUT}/BRW-01-layout-blockout-annotated.png"); plan().save(f"{OUT}/BRW-01-plan-camera.png"); print("ok",[ (n,[round(v) for v in P((c[0],c[1],10))[:2]]) for n,c in TANKS.items()])
