"""Placement-feasibility helpers for source plates: contact-sheet splitting, can body detection (GrabCut), signboard detection (dark quadrilateral),
and zone metrics. PROPOSALS only: a human reviews every proposed region with `overlay` before it is used."""
import cv2
import numpy as np
from PIL import Image


def split_contact_sheet(img: Image.Image, min_gutter=3, thr=235, frac=.75, inset=3):
    """Split a white-gutter contact sheet into panels. Returns [(x0,y0,x1,y1)] in reading order (rows top->bottom, left->right)."""
    a = np.asarray(img.convert("RGB")).astype(int)
    white = a.min(axis=2) > thr

    def runs(v):
        r, s = [], None
        for i, x in enumerate(v):
            if x > frac and s is None:
                s = i
            if x <= frac and s is not None:
                r.append((s, i - 1)); s = None
        if s is not None:
            r.append((s, len(v) - 1))
        return [t for t in r if t[1] - t[0] + 1 >= 2]

    H, W = white.shape
    rows = runs(white.mean(axis=1))
    bands, y = [], 0
    for (s, e) in rows + [(H, H)]:
        if s - y > 20:
            bands.append((y, s - 1))
        y = e + 1
    out = []
    for (y0, y1) in bands:
        cols = runs(white[y0 + inset:y1 - inset].mean(axis=0))
        x = 0
        for (s, e) in cols + [(W, W)]:
            if s - x > 20:
                out.append((x + inset, y0 + inset, s - 1 - inset, y1 - inset))
            x = e + 1
    return out


def detect_can(img: Image.Image, rect_frac=(.3, .05, .4, .88)):
    """GrabCut with a centred rectangle prior. Returns dict(bbox, body_region, mask_ok) or None. Body region = between shoulder and base by can proportions."""
    a = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = a.shape[:2]
    s = 640 / max(h, w) if max(h, w) > 640 else 1.0
    sm = cv2.resize(a, (round(w * s), round(h * s)))
    mask = np.zeros(sm.shape[:2], np.uint8)
    rect = (int(sm.shape[1] * rect_frac[0]), int(sm.shape[0] * rect_frac[1]), int(sm.shape[1] * rect_frac[2]), int(sm.shape[0] * rect_frac[3]))
    bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(sm, mask, rect, bg, fg, 4, cv2.GC_INIT_WITH_RECT)
    m = np.where((mask == 1) | (mask == 3), 1, 0).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    x, y, bw, bh = cv2.boundingRect(c)
    cx0 = (x + bw * .0) / s
    bbox = [x / s, y / s, (x + bw) / s, (y + bh) / s]
    H = bbox[3] - bbox[1]
    # a slim can: ~13% shoulder taper at the top, ~6% base ring at the bottom
    region = [round(bbox[0]), round(bbox[1] + .13 * H), round(bbox[2]), round(bbox[3] - .07 * H)]
    return {"bbox": [round(v) for v in bbox], "body_region": region, "aspect_h_over_w": round(H / (bbox[2] - bbox[0]), 2), "mask_fill": round(float(m.sum()) / (m.shape[0] * m.shape[1]), 3)}


def detect_signboard(img: Image.Image, dark_v=85, max_std=7.0, min_area_frac=.012):
    """Largest dark, flat (low local variance), low-saturation, rectangular region in the upper 65% of the frame — a blank signboard.
    Returns dict(quad TL,TR,BR,BL, area_frac, rectangularity) or None. Trees, steel frames and sky are excluded by the flatness test."""
    a = np.asarray(img.convert("RGB"))
    h, w = a.shape[:2]
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float32)
    k = max(5, (min(h, w) // 60) | 1)
    mean = cv2.blur(g, (k, k)); sq = cv2.blur(g * g, (k, k))
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    m = ((hsv[..., 2] < dark_v) & (hsv[..., 1] < 110) & (std < max_std)).astype(np.uint8)
    m[int(h * .65):] = 0
    ker = np.ones((max(5, k), max(5, k)), np.uint8)
    m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, ker), cv2.MORPH_CLOSE, ker)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area_frac * h * w:
            continue
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect).astype(np.float32)
        rectness = area / max(cv2.contourArea(box), 1e-6)
        if rectness < .8:
            continue
        pts = cv2.approxPolyDP(c, .03 * cv2.arcLength(c, True), True).reshape(-1, 2).astype(float)
        if len(pts) != 4:
            pts = box.astype(float)
        s_ = pts.sum(axis=1); d_ = np.diff(pts, axis=1).ravel()
        quad = [pts[np.argmin(s_)], pts[np.argmin(d_)], pts[np.argmax(s_)], pts[np.argmax(d_)]]
        cand = {"quad": [[round(float(x)), round(float(y))] for x, y in quad], "area_frac": round(area / (h * w), 4), "rectangularity": round(rectness, 3)}
        if best is None or cand["area_frac"] > best["area_frac"]:
            best = cand
    return best


def zone_metrics(img: Image.Image, quad_or_region):
    """Busy-ness / specular occlusion of a placement zone. region = [x0,y0,x1,y1] or quad of 4 points."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    if len(quad_or_region) == 4 and not isinstance(quad_or_region[0], (list, tuple)):
        x0, y0, x1, y1 = [int(v) for v in quad_or_region]
    else:
        xs = [p[0] for p in quad_or_region]; ys = [p[1] for p in quad_or_region]
        x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
    z = a[y0:y1, x0:x1]
    g = z.mean(axis=2)
    lap = cv2.Laplacian(g, cv2.CV_32F)
    return {"zone_px": [x1 - x0, y1 - y0], "lum_std": round(float(g.std()), 2), "specular_fraction": round(float((g > 235).mean()), 4), "edge_density": round(float((np.abs(lap) > 25).mean()), 4)}
