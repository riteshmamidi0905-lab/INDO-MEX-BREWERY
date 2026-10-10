#!/usr/bin/env python3
"""ARC-02-C helper (no generation here). Prepares inputs for ONE masked generative Tank Hall night render, then composites it back so everything
outside the hall-glass interior (and the original mullions inside it) is pixel-identical to ARC-02-A.
  prepare                      -> visuals/generated/ARC-02-C-inputs/
  composite <edited_crop.png>  -> visuals/generated/ARC-02-C.png  (+ prints outside-hall drift)
Run from repo root. Crop box is generous (canopy, limestone, glazing, adjacent entrance) so the model can read perspective."""
import sys, os, numpy as np, cv2
from PIL import Image
OUT="visuals/generated/ARC-02-C-inputs"; A_PATH="visuals/generated/ARC-02-A.webp"; D_PATH="visuals/generated/ARC-01-D.png"
BOX=(40,250,1040,830); GLASS=(150,384,846,776); S=2
M=np.float32([[0.9734,0,6.0],[0,0.98,-16.0]])   # ARC-01-D -> ARC-02-A frame (mullion fit, from ARC-02-B work)
def load(p): return np.array(Image.open(p).convert("RGB"))
def frame_mask(im):
    H,W,_=im.shape; m=np.zeros((H,W),np.float32); reg=im[420:680,138:846].astype(int)
    dark=(reg.max(2)<90).mean(0); cols=np.where(dark>0.8)[0]+138
    for c in cols: m[GLASS[1]:GLASS[3],max(c-2,0):c+3]=1
    return cv2.GaussianBlur(m,(0,0),0.8)
def edit_mask(shape):
    m=np.zeros(shape,np.float32); m[GLASS[1]:GLASS[3],GLASS[0]:GLASS[2]]=1; return cv2.GaussianBlur(m,(0,0),3)
def prepare():
    os.makedirs(OUT,exist_ok=True); A=load(A_PATH); D=load(D_PATH); x0,y0,x1,y1=BOX; sz=((x1-x0)*S,(y1-y0)*S)
    up=lambda a:Image.fromarray(a).resize(sz,Image.LANCZOS)
    up(A[y0:y1,x0:x1]).save(f"{OUT}/1-ARC-02-A-hall-context-crop-2x.png")
    up((edit_mask(A.shape[:2])[y0:y1,x0:x1]*255).astype(np.uint8)).save(f"{OUT}/2-hall-interior-edit-mask-2x.png")
    up((frame_mask(A)[y0:y1,x0:x1]*255).astype(np.uint8)).save(f"{OUT}/3-mullion-frame-lock-mask-2x.png")
    Dw=cv2.warpAffine(D,M,(A.shape[1],A.shape[0]),flags=cv2.INTER_LANCZOS4)
    key=up(Dw[y0:y1,x0:x1]); key.save(f"{OUT}/4-ARC-01-D-layout-ref-registered-2x.png")   # DAYLIGHT: arrangement only
    print("wrote",OUT,sz)
def composite(edited):
    A=load(A_PATH).astype(np.float32); x0,y0,x1,y1=BOX
    e=np.array(Image.open(edited).convert("RGB").resize((x1-x0,y1-y0),Image.LANCZOS)).astype(np.float32)
    m=edit_mask(A.shape[:2]); fm=frame_mask(A.astype(np.uint8))
    keep=np.clip(m*(1-fm),0,1)[y0:y1,x0:x1,None]
    o=A.copy(); o[y0:y1,x0:x1]=A[y0:y1,x0:x1]*(1-keep)+e*keep
    out=np.clip(o,0,255).astype(np.uint8); Image.fromarray(out).save("visuals/generated/ARC-02-C.png")
    d=np.abs(out.astype(int)-A.astype(int)).max(2); outside=m<=1e-4
    print("saved ARC-02-C.png; outside-hall changed px:",int((d[outside]>0).sum()),"of",int(outside.sum()))
if __name__=="__main__":
    a=sys.argv[1:]
    if a[:1]==["prepare"]: prepare()
    elif a[:1]==["composite"] and len(a)>1: composite(a[1])
    else: print(__doc__)
