#!/usr/bin/env python3
"""ARC-02 helper (no generation here). Cuts the Tank Hall crop and masks from an ARC-02 candidate for a masked, hall-glass-only correction,
and composites an edited crop back so everything outside the hall glass stays identical.
  prepare   <arc02_candidate>            -> visuals/generated/ARC-02-B-inputs/
  composite <arc02_candidate> <edited_crop>  -> visuals/generated/ARC-02-B.png   (log the tool that made the edited crop)
Run from repo root."""
import sys, os, numpy as np, cv2
from PIL import Image
OUT="visuals/generated/ARC-02-B-inputs"; BOX=(130,372,1000,795); GLASS=(150,384,846,776); S=2
def load(p): return np.array(Image.open(p).convert("RGB"))
def frame_mask(im):
    H,W,_=im.shape; m=np.zeros((H,W),np.float32); reg=im[420:680,138:846].astype(int)
    dark=(reg.max(2)<90).mean(0); cols=np.where(dark>0.8)[0]+138
    for c in cols: m[GLASS[1]:GLASS[3],max(c-2,0):c+3]=1
    return cv2.GaussianBlur(m,(0,0),0.8)
def prepare(p):
    os.makedirs(OUT,exist_ok=True); im=load(p); x0,y0,x1,y1=BOX; sz=((x1-x0)*S,(y1-y0)*S)
    Image.fromarray(im[y0:y1,x0:x1]).resize(sz,Image.LANCZOS).save(f"{OUT}/ARC-02-A-hall-crop-2x.png")
    m=np.zeros(im.shape[:2],np.float32); m[GLASS[1]:GLASS[3],GLASS[0]:GLASS[2]]=1; m=cv2.GaussianBlur(m,(0,0),3)
    Image.fromarray((m[y0:y1,x0:x1]*255).astype(np.uint8)).resize(sz,Image.LANCZOS).save(f"{OUT}/hall-edit-mask-2x.png")
    Image.fromarray((frame_mask(im)[y0:y1,x0:x1]*255).astype(np.uint8)).resize(sz,Image.LANCZOS).save(f"{OUT}/hall-frame-lock-mask-2x.png")
    print("wrote",OUT,sz)
def composite(p,edited):
    im=load(p).astype(np.float32); x0,y0,x1,y1=BOX
    e=np.array(Image.open(edited).convert("RGB").resize((x1-x0,y1-y0),Image.LANCZOS)).astype(np.float32)
    m=np.zeros(im.shape[:2],np.float32); m[GLASS[1]:GLASS[3],GLASS[0]:GLASS[2]]=1; m=cv2.GaussianBlur(m,(0,0),3)
    keep=np.clip(m*(1-frame_mask(im.astype(np.uint8))),0,1)[y0:y1,x0:x1,None]
    o=im.copy(); o[y0:y1,x0:x1]=im[y0:y1,x0:x1]*(1-keep)+e*keep
    Image.fromarray(np.clip(o,0,255).astype(np.uint8)).save("visuals/generated/ARC-02-B.png"); print("saved visuals/generated/ARC-02-B.png")
if __name__=="__main__":
    a=sys.argv[1:]
    if a[:1]==["prepare"] and len(a)>1: prepare(a[1])
    elif a[:1]==["composite"] and len(a)>2: composite(a[1],a[2])
    else: print(__doc__)
