#!/usr/bin/env python3
"""Automated pre-checks for a generated or composited NASHA image (Sprint 9). They support, and never replace, the human gates in
visuals/nasha-v3/IMAGE-QA.md. Exit 1 on a HARD FAIL.
  python3 tools/visual_qa.py IMAGE [--beer STYLE_SRM_LO,HI --roi x0,y0,x1,y1] [--allow-text NASHA] [--min-width 1600]
Checks: size and dimensions; light frame on the edges; text in the image via offline OCR (a generator must not render names, signs or logos);
perceptual near-duplicate against existing sources and the rejected archive; optional liquid-colour sanity against an SRM range (approximate lookup)."""
import argparse, glob, os, sys
import numpy as np
from PIL import Image

SRM_HEX = {1: "FFE699", 2: "FFD878", 3: "FFCA5A", 4: "FFBF42", 5: "FBB123", 6: "F8A600", 7: "F39C00", 8: "EA8F00", 9: "E58500", 10: "DE7C00", 11: "D77200", 12: "CF6900",
           13: "CB6200", 14: "C35900", 15: "BB5100", 17: "B04500", 20: "A13700", 23: "8E2A00", 25: "7F2200", 30: "5E1500", 40: "3B0A00"}  # approximate display colours, not measurements

def dhash(im, n=16):
    g = np.asarray(im.convert("L").resize((n + 1, n), Image.LANCZOS)).astype(int)
    return (g[:, 1:] > g[:, :-1]).flatten()

def hexrgb(h): return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)])

def srm_distance(mean_rgb, lo, hi):
    """Smallest RGB distance from the mean to any table colour inside [lo, hi]."""
    pts = [hexrgb(h) for s, h in SRM_HEX.items() if lo <= s <= hi] or [hexrgb(SRM_HEX[min(SRM_HEX, key=lambda s: abs(s - lo))])]
    return min(float(np.linalg.norm(mean_rgb - p)) for p in pts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image"); ap.add_argument("--min-width", type=int, default=1600)
    ap.add_argument("--allow-text", default="", help="comma list of text allowed (e.g. the scripted placeholder)")
    ap.add_argument("--beer", help="SRM range lo,hi for the liquid"); ap.add_argument("--roi", help="x0,y0,x1,y1 fractions of the liquid area")
    a = ap.parse_args()
    fails, warns = [], []
    im = Image.open(a.image).convert("RGB"); w, h = im.size; arr = np.asarray(im).astype(int)
    print(f"{a.image}: {w}x{h}, {os.path.getsize(a.image)//1024} KB")
    if w < a.min_width: fails.append(f"width {w} < {a.min_width}")
    for side, v in (("top", arr[0].mean()), ("bottom", arr[-1].mean()), ("left", arr[:, 0].mean()), ("right", arr[:, -1].mean())):
        if v > 235: warns.append(f"light frame on the {side} edge (mean {v:.0f}): trim it")
    try:
        from rapidocr_onnxruntime import RapidOCR
        res, _ = RapidOCR()(arr.astype(np.uint8))
        allow = {t.strip().upper() for t in a.allow_text.split(",") if t.strip()}
        for box, txt, conf in (res or []):
            if float(conf) >= 0.5 and txt.strip().upper() not in allow:
                fails.append(f"TEXT FOUND in image: '{txt}' (conf {float(conf):.2f}): generators must not render text, names or logos")
    except Exception as e:
        warns.append(f"OCR unavailable ({e}); text/logo gate NOT checked")
    hs = dhash(im)
    for f in glob.glob("visuals/web-source/*") + glob.glob("visuals/archive/rejected/**/*", recursive=True):
        try:
            if os.path.abspath(f) == os.path.abspath(a.image) or not f.lower().endswith((".webp", ".png", ".jpg", ".jpeg")): continue
            if (hs != dhash(Image.open(f))).mean() < 0.06: warns.append(f"near-duplicate of {f}")
        except Exception: pass
    if a.beer:
        lo, hi = [float(x) for x in a.beer.split(",")]
        x0, y0, x1, y1 = [float(x) for x in (a.roi or "0,0,1,1").split(",")]
        roi = arr[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].reshape(-1, 3).mean(axis=0)
        d = srm_distance(roi, lo, hi)
        (warns if d > 45 else []).append(f"liquid colour {roi.astype(int).tolist()} is {d:.0f} RGB units from the SRM {lo:g}-{hi:g} range (approximate table): check the style") if d > 45 else print(f"liquid colour sanity OK ({d:.0f} units from SRM {lo:g}-{hi:g})")
    for m in warns: print("WARN", m)
    for m in fails: print("HARD FAIL", m)
    print("RESULT:", "REJECT (hard fail)" if fails else ("CAUTION" if warns else "pre-checks pass (human gates still required)"))
    sys.exit(1 if fails else 0)
main()
