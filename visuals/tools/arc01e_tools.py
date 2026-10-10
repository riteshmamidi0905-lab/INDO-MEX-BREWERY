#!/usr/bin/env python3
"""ARC-01-E helper (no image generation happens here).
  prepare   : cut the Tank Hall crop (2x upscaled) + edit mask + frame-lock mask out of ARC-01-D, for use in an external image editor/generator.
  composite : paste an externally edited hall crop back into ARC-01-D with feathering and mullion lock, so everything outside the hall glass stays pixel-identical.
  compare   : numeric drift check of a finished ARC-01-E against ARC-01-D (outside-hall difference, hall sharpness proxy).
Run from repo root, e.g.  python3 visuals/tools/arc01e_tools.py prepare
                          python3 visuals/tools/arc01e_tools.py composite path/to/edited_crop.png
                          python3 visuals/tools/arc01e_tools.py compare visuals/generated/ARC-01-E.png"""
import sys, os, numpy as np, cv2
from PIL import Image
D="visuals/generated/ARC-01-D.png"; OUTDIR="visuals/generated/ARC-01-E-inputs"
BOX=(130,380,1000,800)          # crop box (x0,y0,x1,y1) in the 2000x1128 frame; margin around the glass
GLASS=(150,392,846,780)          # interior-behind-glass region that may change
SCALE=2
def load(p): return np.array(Image.open(p).convert("RGB"))
def frame_mask(im):
    """mullion columns in the hall glass (very dark warm bronze), widened by 2 px; these are pasted back unchanged after any edit"""
    H,W,_=im.shape; m=np.zeros((H,W),np.float32)
    reg=im[420:680,138:846].astype(int); dark=(reg.max(2)<85).mean(0); cols=np.where(dark>0.8)[0]+138
    for c in cols: m[392:782,max(c-2,0):c+3]=1
    m[392:402,150:846]=1   # head transom line
    return cv2.GaussianBlur(m,(0,0),0.8)
def prepare():
    os.makedirs(OUTDIR,exist_ok=True); im=load(D); x0,y0,x1,y1=BOX
    crop=Image.fromarray(im[y0:y1,x0:x1]).resize(((x1-x0)*SCALE,(y1-y0)*SCALE),Image.LANCZOS); crop.save(f"{OUTDIR}/ARC-01-D-hall-crop-2x.png")
    mask=np.zeros(im.shape[:2],np.float32); gx0,gy0,gx1,gy1=GLASS; mask[gy0:gy1,gx0:gx1]=1
    mask=cv2.GaussianBlur(mask,(0,0),3)
    mc=(mask[y0:y1,x0:x1]*255).astype(np.uint8); Image.fromarray(mc).resize(crop.size,Image.LANCZOS).save(f"{OUTDIR}/hall-edit-mask-2x.png")
    fm=(frame_mask(im)[y0:y1,x0:x1]*255).astype(np.uint8); Image.fromarray(fm).resize(crop.size,Image.LANCZOS).save(f"{OUTDIR}/hall-frame-lock-mask-2x.png")
    print("wrote",OUTDIR,crop.size)
def composite(edited):
    im=load(D).astype(np.float32); x0,y0,x1,y1=BOX
    e=Image.open(edited).convert("RGB").resize((x1-x0,y1-y0),Image.LANCZOS); e=np.array(e).astype(np.float32)
    mask=np.zeros(im.shape[:2],np.float32); gx0,gy0,gx1,gy1=GLASS; mask[gy0:gy1,gx0:gx1]=1; mask=cv2.GaussianBlur(mask,(0,0),3)
    fm=frame_mask(im.astype(np.uint8)); keep=np.clip(mask*(1-fm),0,1)[y0:y1,x0:x1,None]
    out=im.copy(); out[y0:y1,x0:x1]=im[y0:y1,x0:x1]*(1-keep)+e*keep
    Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save("visuals/generated/ARC-01-E.png"); print("saved visuals/generated/ARC-01-E.png (composite; log the tool/model that produced the edited crop)")
def compare(p):
    a=load(D).astype(int); b=load(p).astype(int)
    if a.shape!=b.shape: b=np.array(Image.fromarray(b.astype(np.uint8)).resize((a.shape[1],a.shape[0]),Image.LANCZOS)).astype(int); print("note: resized E to D size (a pure generator output will usually drift globally)")
    d=np.abs(a-b).sum(2); inside=np.zeros(d.shape,bool); gx0,gy0,gx1,gy1=GLASS; inside[gy0-6:gy1+6,gx0-6:gx1+6]=True
    out_rmse=np.sqrt(((a-b)**2)[~inside].mean()); print(f"outside-hall RMSE (0-255 scale): {out_rmse:.2f}   (<=3 = essentially unchanged; >10 = global re-render/drift)")
    def lapvar(x): g=cv2.cvtColor(x.astype(np.uint8),cv2.COLOR_RGB2GRAY); return cv2.Laplacian(g[gy0:gy1,gx0:gx1],cv2.CV_64F).var()
    la,lb=lapvar(a),lapvar(b); print(f"hall-glass sharpness proxy (Laplacian variance): D={la:.1f}  E={lb:.1f}  ratio={lb/la:.2f}  (a proxy only: judge realism by eye)")
if __name__=="__main__":
    c=sys.argv[1] if len(sys.argv)>1 else ""
    if c=="prepare": prepare()
    elif c=="composite" and len(sys.argv)>2: composite(sys.argv[2])
    elif c=="compare" and len(sys.argv)>2: compare(sys.argv[2])
    else: print(__doc__)
