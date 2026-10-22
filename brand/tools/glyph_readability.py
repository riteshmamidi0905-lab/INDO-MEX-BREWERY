#!/usr/bin/env python3
"""[SUPERSEDED: correlation-vs-Inter approach was invalid (arch A vs triangular Inter A); see main() below for the metrics actually used]
Readability proxy for the NASHA wordmark variants. OCR cannot read the custom letterforms at any size (checked), so instead each isolated A is
rendered at true pixel size (cap height 16/24/32/96/256) and classified by normalised correlation against reference capitals (Inter Bold A,H,N,M,R,D,O,U
and the wordmark's own N,S,H). Margin = corr(A) - best wrong class; margin <= 0 means the glyph would be confused with another letter.
This is a PROXY, not a user study: it measures shape confusability, not brand feel. Output: glass-variation/readability.json
"""
import json, math, os, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parent))
import logo_glass_a as G, logo_courtyard_v2 as L

EXE = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
BOX = 64


def norm(im):
    a = np.asarray(im.convert("L").resize((BOX, BOX), Image.LANCZOS), dtype=float)
    a = 255 - a
    a -= a.mean()
    n = np.linalg.norm(a)
    return a / n if n else a


def render_svg(inner, w, h, px, tag):
    """Render at 8x then box-filter down to the true pixel size (headless Chromium mis-sizes very small windows)."""
    K = max(1, min(8, 480 // px))
    im = _render(inner, w, h, px * K, tag)
    return im.resize((max(1, round(im.width / K)), max(1, round(im.height / K))), Image.BOX)


def _render(inner, w, h, px, tag):
    sc = px / 100
    W, H = math.ceil(w * sc) + 8, px + 8
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="-4 -4 {w + 8 / sc:.3f} {100 + 8 / sc:.3f}" style="color:#000"><rect x="-500" y="-500" width="2000" height="2000" fill="#fff"/>{inner}</svg>'
    p = f"/tmp/gr_{tag}.html"; open(p, "w").write("<style>body{margin:0}svg{display:block}</style>" + svg)
    o = f"/tmp/gr_{tag}.png"
    subprocess.run([EXE, "--headless", "--no-sandbox", "--disable-gpu", "--force-device-scale-factor=1", f"--screenshot={o}", f"--window-size={W + 20},{H + 240}", "--hide-scrollbars", f"file://{p}"], capture_output=True, timeout=60)
    return Image.open(o).convert("RGB").crop((0, 0, W, H))


def trim(im):
    a = np.asarray(im.convert("L")); ys, xs = np.where(a < 200)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)) if len(xs) else im


def inter_ref(ch, px):
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", max(8, int(px * 1.38)))
    im = Image.new("RGB", (px * 3, px * 3), "white"); ImageDraw.Draw(im).text((px // 2, px // 2), ch, font=f, fill="black")
    return trim(im)


def main():
    """Metrics actually used (a shape-damage proxy, not a user study):
    gap_px   = thickness of the foam-line gap in true pixels (< 1.0 px will anti-alias into a grey smear)
    iou      = overlap of the glass A's dark mask with the original A's dark mask at the same pixel size (1.0 = identical silhouette)
    """
    out = {}
    for px in G.SIZES:
        small = px <= 96
        cut = L.SMALL if small else L.TEXT
        base = trim_to_canvas(render_svg("".join(f'<path d="{p}" fill="currentColor"/>' for p in L.letter("A", cut)), cut.W["A"], 100, px, f"o{px}"))
        for name, (head, gap) in {"glass-G1": (24, 8) if small else (19, 5), "glass-G2": (30, 9) if small else (25, 6.5)}.items():
            im = trim_to_canvas(render_svg("".join(f'<path d="{p}" fill="currentColor"/>' for p in G.glass_a(cut, head, gap)), cut.W["A"], 100, px, f"{name}{px}"))
            a, b = base < 128, im < 128
            h = min(a.shape[0], b.shape[0]); w = min(a.shape[1], b.shape[1])
            iou = float((a[:h, :w] & b[:h, :w]).sum() / max(1, (a[:h, :w] | b[:h, :w]).sum()))
            out[f"{name}@{px}"] = {"gap_px": round(gap * px / 100, 2), "foam_cap_px": round(head * px / 100, 2), "iou_vs_original": round(iou, 3), "cut": "small" if small else "text"}
            print(name, px, out[f"{name}@{px}"])
    (G.OUT / "readability.json").write_text(json.dumps(out, indent=1))


def trim_to_canvas(im):
    return np.asarray(im.convert("L"))


if __name__ == "__main__":
    main()
