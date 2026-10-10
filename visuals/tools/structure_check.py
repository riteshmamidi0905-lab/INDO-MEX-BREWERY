#!/usr/bin/env python3
"""Geometry-drift proxy between a reference image and a candidate of the SAME scene (e.g. ARC-01-D vs ARC-02).
Compares strong structural edges (building lines, mullions, columns, canopy, roof) so lighting changes matter little.
Prints edge recall (share of the reference's strong edges that reappear within a 5 px tolerance) and the reverse (precision).
It is a PROXY: calibrate with known pairs (see ARC-02 review sheet) and always judge by eye as well.
Usage: python3 visuals/tools/structure_check.py visuals/generated/ARC-01-D.png candidate.png"""
import sys, numpy as np, cv2
from PIL import Image
def edges(path,size):
    im=Image.open(path).convert("L").resize(size,Image.LANCZOS); g=np.array(im)
    g=cv2.createCLAHE(2.0,(8,8)).apply(g)                      # normalise day/night exposure
    b=cv2.GaussianBlur(g,(0,0),1.6)
    gx=cv2.Sobel(b,cv2.CV_32F,1,0); gy=cv2.Sobel(b,cv2.CV_32F,0,1); mag=np.hypot(gx,gy)
    thr=np.percentile(mag[170:960],88); e=(mag>thr).astype(np.uint8)
    e[:170]=0; e[960:]=0                                       # ignore sky and near foreground
    return e
def score(ref,cand):
    size=(2000,1128); a=edges(ref,size); b=edges(cand,size)
    k=np.ones((11,11),np.uint8)
    rec=(a&cv2.dilate(b,k)).sum()/max(a.sum(),1); pre=(b&cv2.dilate(a,k)).sum()/max(b.sum(),1)
    return rec,pre
if __name__=="__main__":
    if len(sys.argv)<3: print(__doc__); sys.exit()
    r,p=score(sys.argv[1],sys.argv[2]); print(f"edge recall {r:.2f}  edge precision {p:.2f}")
