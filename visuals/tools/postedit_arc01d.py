#!/usr/bin/env python3
"""ARC-01-D: documented post-production edit of ARC-01-C (NOT an image-generator output).
Five refinements, applied only inside the Tank Hall glass region: (1) matte-charcoal cones, (2) uniform narrow deep-marigold bands,
(3) removal of the small ambiguous vessel, (4) dark-bronze mullions, (5) fine-detail sharpening.
Run from repo root: python3 visuals/tools/postedit_arc01d.py"""
import numpy as np, cv2
from PIL import Image
SRC="visuals/generated/ARC-01-C.webp"; OUT="visuals/generated/ARC-01-D.png"
im=np.array(Image.open(SRC).convert("RGB")).astype(np.float32)
H,W,_=im.shape
bgr=cv2.cvtColor(im.astype(np.uint8),cv2.COLOR_RGB2BGR)
hsv=cv2.cvtColor(im.astype(np.uint8),cv2.COLOR_RGB2HSV_FULL).astype(np.float32)  # H 0-255
Hh=hsv[...,0]*360/255; S=hsv[...,1]/255; V=hsv[...,2]
out=im.copy()
def feather(mask,r=2):
    m=cv2.GaussianBlur(mask.astype(np.float32),(0,0),r); return np.clip(m,0,1)

# ---------- 1. cones -> matte charcoal (RAL 7016 ~ 56,62,66) ----------
polys=[ [(204,694),(292,694),(262,764),(236,764)],   # tank 1
        [(291,698),(353,698),(335,764),(310,764)],   # tank 2
        [(410,700),(473,700),(452,764),(430,764)],   # tank 3
        [(640,688),(711,688),(678,767),(668,767)],   # big nearest tank
        [(729,694),(762,694),(749,771),(737,771)],   # tank 5
        [(766,699),(801,699),(791,769),(777,769)] ]  # tank 6
pm=np.zeros((H,W),np.uint8)
for p in polys: cv2.fillPoly(pm,[np.array(p,np.int32)],255)
# soft colour-model weighting: cone pixels cluster tightly around a dull dark brown-grey; gold legs, pipes and bright background fall far from it
cone_rgb=np.array([84,64,46],np.float32)
dist=np.linalg.norm(im-cone_rgb,axis=2)
wcol=np.clip(1.0-(dist-16.0)/34.0,0,1)          # 1 inside ~16, fades to 0 by ~50
cm=feather((pm>0).astype(np.float32),1.5)*wcol*0.9
tgt=np.array([64,62,60],np.float32)             # neutral graphite, matte
lum=np.clip(V/90.0,0.62,1.15)[...,None]
charcoal=tgt*lum
out=out*(1-cm[...,None])+charcoal*cm[...,None]

# ---------- 2. bands: uniform narrow deep marigold ----------
band=(S>0.84)&(V>150)&(Hh>10)&(Hh<34)
reg=np.zeros((H,W),bool); reg[590:672,196:480]=True; reg[590:672,580:812]=True   # exclude deck copper (x480-580)
band&=reg
tanks=[(196,293,9.0),(293,356,6.0),(405,478,6.0),(632,716,8.0),(726,764,6.0),(766,806,5.5)]  # x0,x1,target px height
remove=np.zeros((H,W),np.uint8)
newband=np.zeros((H,W),np.float32)
for x0,x1,th in tanks:
    for x in range(x0,x1):
        ys=np.where(band[:,x])[0]
        if len(ys)==0: continue
        # largest contiguous run
        runs=np.split(ys,np.where(np.diff(ys)>1)[0]+1); r=max(runs,key=len)
        ya,yb=r[0],r[-1]; h=yb-ya+1
        if h<=th+0.5:
            newband[ya:yb+1,x]=1; continue
        c=(ya+yb)/2.0; ka=int(round(c-th/2)); kb=int(round(c+th/2))
        remove[ya:ka,x]=255; remove[kb+1:yb+1,x]=255; newband[ka:kb+1,x]=1
remove=cv2.dilate(remove,np.ones((3,1),np.uint8))
# keep the retained band pixels out of the inpaint mask
remove[newband>0]=0
tmp=cv2.inpaint(cv2.cvtColor(np.clip(out,0,255).astype(np.uint8),cv2.COLOR_RGB2BGR),remove,3,cv2.INPAINT_TELEA)
out=cv2.cvtColor(tmp,cv2.COLOR_BGR2RGB).astype(np.float32)
bm=feather(newband,0.6)
vb=np.clip(V/215.0,0.7,1.15)[...,None]
marigold=np.clip(np.array([232,135,14],np.float32)*vb,0,255)
out=out*(1-bm[...,None])+marigold*bm[...,None]

# ---------- 3. remove small ambiguous vessel beside the west stair ----------
# clone a same-size strip from the clean background immediately to the right, then feather-blend (inpaint alone smeared a light block)
x0,x1,y0,y1=351,370,702,766; wv=x1-x0
src=out[y0:y1,x1+4:x1+4+wv].copy()
vm=np.zeros((H,W),np.float32); vm[y0:y1,x0:x1]=1; vm=feather(vm,2.0)
patch=out.copy(); patch[y0:y1,x0:x1]=src
out=out*(1-vm[...,None])+patch*vm[...,None]

# ---------- 4. mullions -> very dark warm bronze ----------
Vn=np.max(out,axis=2)
regm=np.zeros((H,W),bool); regm[380:782,138:846]=True; regm[400:548,880:992]=True
dark=regm&(Vn<80)
dm=feather(dark,0.8)*np.clip((80-Vn)/30.0,0,1)
bronze=np.stack([out[...,0]*1.12+16, out[...,1]*1.02+10, out[...,2]*0.92+6],axis=2)
out=out*(1-dm[...,None])+np.clip(bronze,0,255)*dm[...,None]

# ---------- 5. fine detail inside the glass ----------
rm=np.zeros((H,W),np.float32); rm[392:775,150:845]=1; rm=feather(rm,6)
blur=cv2.GaussianBlur(out,(0,0),1.6)
sharp=out+0.7*(out-blur)
out=out*(1-rm[...,None])+sharp*rm[...,None]
Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(OUT)
print("saved",OUT,out.shape)
