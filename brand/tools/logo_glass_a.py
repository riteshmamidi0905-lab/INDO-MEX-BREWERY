#!/usr/bin/env python3
"""Courtyard wordmark vs. glass-inspired variation (EXPLORATION; neither version is final).

Variation idea: both A's keep the arch construction and the crossbar (still unmistakably an A) but the arch top is separated from the legs by a thin
horizontal gap, like the head of foam sitting on a poured beer: arch top = foam, gap = meniscus, legs = glass walls. No glass picture is drawn.
Two proportions are tested: G1 (small head, gap 5) and G2 (taller head, gap 6.5). A heavier small cut widens the gap so it survives at <= 32 px.

Output: brand/logo/CONTROLLED-MASTERS/courtyard-refined-2026-10-22/glass-variation/  (SVGs, comparison PNG, readability.json)
    CHROMIUM_PATH=... python3 brand/tools/logo_glass_a.py
"""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import logo_courtyard_v2 as L  # noqa: E402
from logo_explorations import rect  # noqa: E402

OUT = L.OUT / "glass-variation"
SIZES = (16, 24, 32, 96, 256)           # wordmark cap height in px


def glass_a(c, head, gap):
    """Arch A whose rounded top is cut free from the legs by a horizontal gap (foam head). Returns path list."""
    w, h, W = c.w, c.h, c.W["A"]
    r, o = W / 2, 1.5
    s = r - o
    cx = W / 2
    y1 = head - o                       # bottom of the foam cap
    y2 = y1 + gap                       # top of the leg tops
    ri = r - w

    def half(y, rad):
        d = rad * rad - (y - s) ** 2
        return math.sqrt(d) if d > 0 else None

    ox1, ix1 = half(y1, r), half(y1, ri)
    ox2, ix2 = half(y2, r), half(y2, ri)
    cap = f"M{cx - ox1:.2f},{y1:.2f}A{r:.2f},{r:.2f} 0 0 1 {cx + ox1:.2f},{y1:.2f}"
    cap += f"L{cx + ix1:.2f},{y1:.2f}A{ri:.2f},{ri:.2f} 0 0 0 {cx - ix1:.2f},{y1:.2f}Z" if ix1 else "Z"
    left = f"M{cx - ox2:.2f},{y2:.2f}A{r:.2f},{r:.2f} 0 0 0 0,{s:.2f}V100H{w}V{s:.2f}A{ri:.2f},{ri:.2f} 0 0 1 {cx - ix2:.2f},{y2:.2f}Z"
    right = f"M{cx + ox2:.2f},{y2:.2f}A{r:.2f},{r:.2f} 0 0 1 {W},{s:.2f}V100H{W - w}V{s:.2f}A{ri:.2f},{ri:.2f} 0 0 0 {cx + ix2:.2f},{y2:.2f}Z"
    return [cap, left, right, rect(w - 1, 66 - h / 2, W - 2 * w + 2, h)]


def wordmark(cut, head=None, gap=None):
    x, out, word = 0.0, [], "NASHA"
    for i, ch in enumerate(word):
        paths = glass_a(cut, head, gap) if (ch == "A" and head) else L.letter(ch, cut)
        for p in paths:
            out.append(f'<g transform="translate({x:.1f},0)">{p[1]}</g>' if isinstance(p, tuple) else f'<path transform="translate({x:.1f},0)" d="{p}" fill="currentColor"/>')
        x += cut.W[ch] + (cut.gaps[word[i:i + 2]] if i < 4 else 0)
    return "".join(out), x, 100


VARIANTS = {
    "original": lambda small: L.wordmark(L.SMALL if small else L.TEXT),
    "glass-G1": lambda small: wordmark(L.SMALL, 24, 8) if small else wordmark(L.TEXT, 19, 5),
    "glass-G2": lambda small: wordmark(L.SMALL, 30, 9) if small else wordmark(L.TEXT, 25, 6.5),
}


def svg(inner, w, h, color="#141110", bg=None, pad=4):
    b = f'<rect x="{-pad}" y="{-pad}" width="{w + 2 * pad}" height="{h + 2 * pad}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}" style="color:{color}" role="img" aria-label="NASHA wordmark exploration (provisional)">{b}{inner}</svg>'


def chrome(html, png, w, h):
    exe = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    subprocess.run([exe, "--headless", "--no-sandbox", "--disable-gpu", "--force-device-scale-factor=1", f"--screenshot={png}", f"--window-size={w},{h}", "--hide-scrollbars", f"file://{html}"], capture_output=True, timeout=120)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in VARIANTS.items():
        for small in (False, True):
            inner, w, h = fn(small)
            tag = "small" if small else "text"
            (OUT / f"wordmark-{name}-{tag}.svg").write_text(svg(inner, w, h))
            (OUT / f"wordmark-{name}-{tag}-reverse.svg").write_text(svg(inner, w, h, "#EFE7D6", "#141110"))
    # comparison sheet at true pixel sizes (cap height = SIZES px), each variant on its own row, one image per size for OCR
    rows = []
    for name, fn in VARIANTS.items():
        cells = []
        for px in SIZES:
            inner, w, h = fn(px <= 96)
            sc = px / 100
            cells.append((px, f'<svg xmlns="http://www.w3.org/2000/svg" width="{math.ceil(w * sc) + 8}" height="{px + 8}" viewBox="-4 -4 {w + 8 / sc:.2f} {100 + 8 / sc:.2f}" style="color:#141110">{inner}</svg>'))
        rows.append((name, cells))
    html = "<!doctype html><meta charset=utf-8><style>body{margin:0;background:#EFE7D6;font:13px Inter,sans-serif;color:#333}.r{display:flex;align-items:flex-end;gap:36px;padding:18px 24px;border-bottom:1px solid #cbbf9f}.l{width:90px}svg{display:block}.c span{display:block;font-size:11px;color:#777;margin-top:4px}</style>"
    for name, cells in rows:
        html += f'<div class="r"><div class="l"><b>{name}</b></div>' + "".join(f'<div class="c">{s}<span>{px}px</span></div>' for px, s in cells) + "</div>"
    page = OUT / "_cmp.html"
    page.write_text(html)
    chrome(page, OUT / "comparison-true-size.png", 2000, 3 * 310 + 80)
    page.unlink()
    from PIL import Image
    Image.open(OUT / "comparison-true-size.png").crop((0, 0, 2000, 3 * 310 + 10)).save(OUT / "comparison-true-size.png")
    print("written", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
