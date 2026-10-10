#!/usr/bin/env python3
"""ARC-02-B: scripted composite (NOT a generated image). Source of the night exterior = ARC-02-A (pixel-identical outside the Tank Hall glass);
source of the Tank Hall geometry = ARC-01-D (canonical daytime hall), registered to ARC-02-A's frame and given a physically motivated
blue-hour/night grade (reflection removal, exposure/depth shaping, warm uplight at tank bases, sleeve/copper colour control).
Run from repo root: python3 visuals/tools/composite_arc02b.py   -> visuals/generated/ARC-02-B.png"""
import numpy as np, cv2
from PIL import Image
D=np.array(Image.open("visuals/generated/ARC-01-D.png").convert("RGB"))
A=np.array(Image.open("visuals/generated/ARC-02-A.webp").convert("RGB"))
H,W=A.shape[:2]
# ---- 1. registration (mullion-based fit): x' = 0.9734 x + 6.0 ; y' = 0.98 y - 16 ----
M=np.float32([[0.9734,0,6.0],[0,0.98,-16.0]])
Dw=cv2.warpAffine(D,M,(W,H),flags=cv2.INTER_LANCZOS4)
# glass interior mask (D coordinates: inside the outer frame), warped to A
gm=np.zeros(D.shape[:2],np.float32); gm[406:770,180:822]=1
gm=cv2.warpAffine(gm,M,(W,H),flags=cv2.INTER_LINEAR); gm=cv2.GaussianBlur(gm,(0,0),2.2)
x0,x1,y0,y1=130,900,340,800
f=Dw.astype(np.float32)/255.0
hsv=cv2.cvtColor(Dw,cv2.COLOR_RGB2HSV_FULL).astype(np.float32); Hh=hsv[...,0]*360/255; S=hsv[...,1]/255; V=hsv[...,2]/255
lum=0.2126*f[...,0]+0.7152*f[...,1]+0.0722*f[...,2]
# ---- 2. remove daylight reflections: foliage (green/yellow-green), sky (blue), golden foliage haze in the left panes ----
green=np.clip((S-0.20)/0.2,0,1)*((Hh>58)&(Hh<150)).astype(np.float32)
sky=np.clip((S-0.10)/0.2,0,1)*((Hh>180)&(Hh<260)).astype(np.float32)
xx=np.arange(W)[None,:].repeat(H,0).astype(np.float32); yy=np.arange(H)[:,None].repeat(W,1).astype(np.float32)
leftpanes=np.clip((700-xx)/120,0,1)*np.clip((640-yy)/60,0,1)       # tree reflections concentrate in the left/upper panes above the tank tops
gold=((Hh>26)&(Hh<62)&(S>0.22)&(V>0.30)).astype(np.float32)*leftpanes*0.95
cone_free=np.clip((700-yy)/25,0,1)                                    # never touch the cone/base zone
prot=1-np.clip((lum-0.78)/0.12,0,1)                                    # protect true light sources
refl=np.clip(1.3*green+1.3*sky+gold,0,1)*cone_free*prot; refl=cv2.GaussianBlur(refl,(0,0),1.2)
upper=np.clip((560-xx)/140,0,1)*np.clip((500-yy)/50,0,1)*prot*cone_free  # residual haze in the upper-left panes: pull toward dark interior
refl=np.clip(refl+0.55*upper*(S>0.18),0,1)
night_bg=np.stack([0.085+0*lum,0.062+0*lum,0.050+0*lum],2)*(0.6+0.8*lum[...,None])      # dim warm interior shadow
indigo=np.array([0.030,0.036,0.070],np.float32)[None,None,:]*(0.5+lum[...,None])           # faint indigo sky reflection
tint=np.where(sky[...,None]>0.25,indigo,night_bg)
f=f*(1-0.88*refl[...,None])+tint*(0.88*refl[...,None])
# ---- 3. night exposure: deepen shadows/mids, keep light-source and specular highlights ----
ev=-0.9
f=np.clip(f,0,1)**1.28
hi=np.clip((lum-0.55)/0.35,0,1)[...,None]
f=f*(2**ev*(1-hi)+1.0*hi)
# warm 2300K interior balance: push toward orange without yellow-green
r,g,b=f[...,0],f[...,1],f[...,2]
f=np.stack([r*1.04,g*0.97,b*0.82],2)
# ---- 4. depth: darker back wall / ceiling, brighter equipment zone ----
cx,cy=(500*0.9734+6),(640*0.98-16)
d=np.sqrt(((xx-cx)/380)**2+((yy-(cy-40))/230)**2); vig=np.clip(1.08-0.38*d**1.5,0.52,1.08)
f*=vig[...,None]
# ---- 5. narrow-beam warm uplight at tank bases (reflecting on lower shells, not on glass) ----
tx=[(236,250),(305,300),(440,445),(676,676),(745,748),(786,786)]   # approximate tank axes in D coords (x)
up=np.zeros((H,W),np.float32)
for xd,_ in tx:
    xa=0.9734*xd+6; ya=0.98*735-16
    up+=np.exp(-((xx-xa)/34)**2-((yy-ya+ (yy<ya)*0)/70)**2*(yy<ya)-((yy-ya)/22)**2*(yy>=ya))
stainless=((S<0.38)&(V>0.28)).astype(np.float32)
f+=np.array([1.0,0.62,0.28],np.float32)[None,None,:]*(0.20*up*stainless)[...,None]
# ---- 8. match exposure/colour continuity to ARC-02-A's own hall glow (soft histogram anchoring on luminance mean) ----
Af=A.astype(np.float32)/255.0; Al=0.2126*Af[...,0]+0.7152*Af[...,1]+0.0722*Af[...,2]
core=(gm>0.9)
fl_=0.2126*f[...,0]+0.7152*f[...,1]+0.0722*f[...,2]
gain=np.clip(np.median(Al[core])/max(np.median(fl_[core]),1e-4),0.7,1.4)
f=np.clip(f*gain**0.6,0,1)
# ---- 6. colour control: sleeves to #E8870E, copper keeps copper, graphite cones stay dark ----
band=((S>0.84)&(V>0.58)&(Hh>10)&(Hh<34)).astype(np.float32)
band[:, :int(0.9734*480+6)]*=1; 
copper_zone=np.zeros((H,W),np.float32); copper_zone[int(0.98*455-16):int(0.98*680-16),int(0.9734*484+6):int(0.9734*578+6)]=1
band*= (1-copper_zone)
band=cv2.GaussianBlur(band,(0,0),0.6)
mar=np.array([232,135,14],np.float32)/255.0
mar_shaded=mar[None,None,:]*np.clip(0.68+0.45*lum[...,None],0.6,1.0)
f=f*(1-band[...,None])+mar_shaded*band[...,None]
cu=((Hh>12)&(Hh<32)&(S>0.45)&(S<0.85)&(V>0.35)).astype(np.float32)*copper_zone
cu=cv2.GaussianBlur(cu,(0,0),1.0)[...,None]
f=f+cu*np.array([0.10,0.045,0.012],np.float32)*(0.4+lum[...,None])               # warm copper highlights
# ---- 7. floor: keep matte-satin (compress specular glare in the floor sliver) ----
fl=np.clip((yy-(0.98*748-16))/10,0,1)*gm
fb=cv2.GaussianBlur(f,(0,0),1.5)
f=f*(1-0.5*fl[...,None])+np.minimum(f,fb*0.9)*(0.5*fl[...,None])
cz=np.clip((yy-(0.98*600-16))/20,0,1)
lum_f=0.2126*f[...,0]+0.7152*f[...,1]+0.0722*f[...,2]
dark=np.clip((0.20-lum_f)/0.10,0,1)*(S>0.3)*(Hh<40)*cz*(1-band)
dark=cv2.GaussianBlur(dark.astype(np.float32),(0,0),1.0)[...,None]
g=(cv2.medianBlur((np.clip(lum_f,0,1)*255).astype(np.uint8),5)/255.0)[...,None]
f=f*(1-dark)+np.concatenate([g*1.02,g*0.98,g*0.95],2)*dark
f=np.clip(f,0,1)
out=(A.astype(np.float32)/255.0)*(1-gm[...,None])+f*gm[...,None]
Image.fromarray((np.clip(out,0,1)*255+0.5).astype(np.uint8)).save("visuals/generated/ARC-02-B.png")
print("saved visuals/generated/ARC-02-B.png; hall gain",round(float(gain),2),"glass mask px",int((gm>0.5).sum()))
