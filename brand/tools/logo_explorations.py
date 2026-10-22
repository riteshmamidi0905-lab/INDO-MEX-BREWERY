#!/usr/bin/env python3
"""NASHA logo EXPLORATIONS (status: EXPLORATION per brand/NASHA-LOGO-GOVERNANCE.md; CONCEPT, NOT OFFICIAL; nothing approved, nothing cleared).

Three provisional directions drawn from scratch as vector paths (no font file is used for A and C; B customises outlines of the open-licence
Instrument Serif Italic). Output: brand/logo/CONTROLLED-MASTERS/explorations-2026-10-22/<direction>/ editable SVGs (wordmark, symbol, monogram,
horizontal, stacked, seal; plus black, white and one-colour variants) and an application board PNG per direction. Never deployed: the website
build does not read brand/logo/.   python3 brand/tools/logo_explorations.py
"""
import math
import os
import re
import subprocess
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "brand/logo/CONTROLLED-MASTERS/explorations-2026-10-22"
FONT_ITALIC = ROOT / "website/dist/fonts/instrument-serif-latin-400-italic.woff2"
LETTERS = "NASHA"


# ------------------------------------------------------------------ small helpers
def rect(x, y, w, h):
    return f"M{x:.2f},{y:.2f}h{w:.2f}v{h:.2f}h{-w:.2f}z"


def poly(*pts):
    return "M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + "z"


def leaf_path(cx, cy, length, width, angle):
    """Lanceolate leaf centred at (cx,cy)."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    h, w = length / 2, width / 2
    p0 = (cx - ux * h, cy - uy * h)
    p1 = (cx + ux * h, cy + uy * h)
    c1 = (cx - ux * h * .2 + nx * w * 1.35, cy - uy * h * .2 + ny * w * 1.35)
    c2 = (cx + ux * h * .45 + nx * w * 1.1, cy + uy * h * .45 + ny * w * 1.1)
    d1 = (cx + ux * h * .45 - nx * w * 1.1, cy + uy * h * .45 - ny * w * 1.1)
    d2 = (cx - ux * h * .2 - nx * w * 1.35, cy - uy * h * .2 - ny * w * 1.35)
    return f"M{p0[0]:.2f},{p0[1]:.2f}C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p1[0]:.2f},{p1[1]:.2f}C{d1[0]:.2f},{d1[1]:.2f} {d2[0]:.2f},{d2[1]:.2f} {p0[0]:.2f},{p0[1]:.2f}z"


# ------------------------------------------------------------------ DIRECTION A: THE COURTYARD (constructed, architectural)
A_W = 15.0


def a_letter(ch):
    w = A_W
    if ch == "N":
        W = 72
        return W, [rect(0, 0, w, 100), rect(W - w, 0, w, 100), poly((0, 0), (w * 1.35, 0), (W, 100), (W - w * 1.35, 100))]
    if ch == "A":
        W = 82
        r = W / 2
        outer = f"M0,100V{r:.1f}A{r:.1f},{r:.1f} 0 0 1 {W},{r:.1f}V100H{W - w}V{r:.1f}A{r - w:.1f},{r - w:.1f} 0 0 0 {w},{r:.1f}V100z"
        return W, [outer, rect(w - 1, 66, W - 2 * w + 2, w * .85)]
    if ch == "S":
        W = 62
        return W, [f"S_STROKE"]
    if ch == "H":
        W = 72
        return W, [rect(0, 0, w, 100), rect(W - w, 0, w, 100), rect(w - 1, 50 - w * .4, W - 2 * w + 2, w * .8)]


def s_stroke_path(w):
    r = 24.0
    return f'<path d="M{54:.1f},{w / 2 + 3:.1f}A{r},{r} 0 1 0 {31:.1f},50A{r},{r} 0 1 1 {8:.1f},{100 - w / 2 - 3:.1f}" fill="none" stroke="currentColor" stroke-width="{w}" stroke-linecap="butt"/>'


def wordmark_a(gap=20):
    x, parts = 0, []
    for ch in LETTERS:
        W, ps = a_letter(ch)
        for p in ps:
            if p == "S_STROKE":
                parts.append(f'<g transform="translate({x:.1f},0)">{s_stroke_path(A_W)}</g>')
            else:
                parts.append(f'<path transform="translate({x:.1f},0)" d="{p}" fill="currentColor"/>')
        x += W + gap
    return "".join(parts), x - gap, 100


def symbol_a():
    """Concentric thresholds: three nested arches opening onto a small courtyard square."""
    d = ""
    for i, half in enumerate((46, 32, 18)):
        d += f"M{50 - half},100V{50 - half + 22}A{half},{half} 0 0 1 {50 + half},{50 - half + 22}V100h-9V{50 - half + 22}A{half - 9},{half - 9} 0 0 0 {50 - half + 9},{50 - half + 22}V100z"
    return f'<path d="{d}" fill="currentColor"/><rect x="45" y="78" width="10" height="22" fill="var(--accent,currentColor)"/>', 100, 100


def monogram_a():
    inner = ""
    for p in a_letter("N")[1]:
        inner += f'<path transform="translate(28,36) scale(.6)" d="{p}" fill="currentColor"/>'
    frame = "M2,100V50A48,48 0 0 1 98,50V100h-7V50A41,41 0 0 0 9,50V100z"
    return f'<path d="{frame}" fill="currentColor"/>{inner}', 100, 100


# ------------------------------------------------------------------ DIRECTION B: TWO WORLDS (Instrument Serif Italic outlines + botanical A)
_font = None


def glyph_path(ch):
    global _font
    if _font is None:
        _font = TTFont(str(FONT_ITALIC))
    gs = _font.getGlyphSet()
    name = _font.getBestCmap()[ord(ch)]
    pen = SVGPathPen(gs)
    gs[name].draw(pen)
    return pen.getCommands(), gs[name].width


def wordmark_b(gap=-6):
    upm = 1000.0
    cap = _font_cap()
    scale = 100.0 / cap
    x, parts = 0.0, []
    for i, ch in enumerate(LETTERS):
        d, adv = glyph_path(ch)
        parts.append(f'<path transform="translate({x:.2f},100) scale({scale:.4f},{-scale:.4f})" d="{d}" fill="currentColor"/>')
        if ch == "A":
            # a leaf replaces the visual weight of the crossbar: it lies across the legs (first A points up-right, second down-right)
            ang = -14 if i == 1 else 14
            cx = x + adv * scale * .5
            parts.append(f'<path d="{leaf_path(cx, 67, adv * scale * .8, 12.5, ang)}" fill="var(--accent,currentColor)"/>')
        x += adv * scale + gap
    return "".join(parts), x - gap, 100


def _font_cap():
    d, _ = glyph_path("H")
    ys = [float(v) for v in re.findall(r"[-\d.]+", d)][1::2]
    return max(ys)


def symbol_b():
    """Four leaves (two long curry-leaf shapes and two broad mango-type shapes) turned toward one another around a small open courtyard square."""
    parts = []
    for k, (ang, ln, wd) in enumerate(((-45, 54, 18), (45, 44, 24), (135, 54, 18), (-135, 44, 24))):
        a = math.radians(ang)
        cx, cy = 50 + math.cos(a) * 25, 50 + math.sin(a) * 25
        parts.append(f'<path d="{leaf_path(cx, cy, ln, wd, ang + 180)}" fill="currentColor"/>')
    return "".join(parts) + '<path d="M42,42h16v16h-16z" fill="var(--accent,currentColor)" transform="rotate(45 50 50)"/>', 100, 100


def monogram_b():
    d, adv = glyph_path("N")
    cap = _font_cap()
    s = 70.0 / cap
    x = 50 - adv * s / 2
    return (f'<circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" stroke-width="3"/><path transform="translate({x:.2f},{50 + 35}) scale({s:.4f},{-s:.4f})" d="{d}" fill="currentColor"/>'
            f'<path d="{leaf_path(50, 90, 26, 6.5, -8)}" fill="var(--accent,currentColor)"/>'), 100, 100


# ------------------------------------------------------------------ DIRECTION C: NASHA AFTER DARK (heavy, stencil, a single seam of light)
C_W = 27.0


def c_letter(ch):
    w = C_W
    if ch == "N":
        W = 78
        return W, [rect(0, 0, w, 100), rect(W - w, 0, w, 100), poly((0, 0), (w * 1.1, 0), (W, 100), (W - w * 1.1, 100))]
    if ch == "A":
        W = 92
        return W, [poly((0, 100), (W / 2 - w * .55, 0), (W / 2 + w * .55, 0), (W, 100), (W - w * 1.05, 100), (W / 2, 30), (w * 1.05, 100))]
    if ch == "S":
        W = 70
        return W, ["S_STROKE"]
    if ch == "H":
        W = 78
        return W, [rect(0, 0, w, 100), rect(W - w, 0, w, 100), rect(w - 1, 50 - w * .4, W - 2 * w + 2, w * .8)]


def wordmark_c(gap=11):
    x, parts = 0, []
    for ch in LETTERS:
        W, ps = c_letter(ch)
        for p in ps:
            if p == "S_STROKE":
                parts.append(f'<g transform="translate({x - 4:.1f},0) scale({(W + 8) / 62:.3f},1)">{s_stroke_path(C_W * .95)}</g>')
            else:
                parts.append(f'<path transform="translate({x:.1f},0)" d="{p}" fill="currentColor"/>')
        x += W + gap
    total = x - gap
    # the seam: a thin cut through all letters, lit in the accent colour
    seam = f'<rect x="-4" y="61" width="{total + 8:.1f}" height="3.2" fill="var(--seam,var(--bg,#000))"/>'
    return "".join(parts) + seam, total, 100


def symbol_c():
    """A doorway left ajar: a solid arch with a vertical seam of light."""
    return ('<path d="M10,100V46A40,40 0 0 1 90,46V100z" fill="currentColor"/>'
            '<path d="M47,100V30A3,3 0 0 1 53,30V100z" fill="var(--seam,var(--bg,#000))"/><rect x="0" y="95" width="100" height="5" fill="currentColor"/>'), 100, 100


def monogram_c():
    inner = "".join(f'<path transform="translate(20,24) scale(.6)" d="{p}" fill="currentColor"/>' for p in c_letter("N")[1])
    return f'<rect x="2" y="2" width="96" height="96" rx="0" fill="none" stroke="currentColor" stroke-width="5"/>{inner}<rect x="2" y="63" width="96" height="3" fill="var(--seam,var(--bg,#000))"/>', 100, 100


DIRECTIONS = {
    "A-courtyard": dict(title="Direction A: The Courtyard", wm=wordmark_a, sym=symbol_a, mono=monogram_a, bg="#EFE7D6", fg="#141110", accent="#C2680B", seam="#EFE7D6",
                        palette=[("Limestone", "#EFE7D6"), ("Soot", "#141110"), ("Terracotta ink", "#A5461F"), ("Marigold ink", "#C2680B"), ("Indigo dusk", "#1A2142"), ("Stainless", "#C9CCCB")], dark_bg="#141110", dark_fg="#EFE7D6", head="Instrument Serif", body="Inter",
                        tag="Thresholds. Symmetry. Warm material.", note="Constructed from one stroke weight; the A is a doorway."),
    "B-two-worlds": dict(title="Direction B: Two Worlds", wm=wordmark_b, sym=symbol_b, mono=monogram_b, bg="#F3ECDD", fg="#1E2A1C", accent="#9B2447", seam="#F3ECDD",
                         palette=[("Bone", "#F3ECDD"), ("Leaf", "#3F5A1E"), ("Hibiscus", "#9B2447"), ("Tamarind", "#5A3A25"), ("Marigold ink", "#B8700C"), ("Ink green", "#1E2A1C")], dark_bg="#1E2A1C", dark_fg="#F3ECDD", head="Instrument Serif Italic", body="Inter",
                         tag="Two floras. One courtyard.", note="Italic capitals with a leaf for the crossbar; symbol = two leaves around a doorway."),
    "C-after-dark": dict(title="Direction C: NASHA After Dark", wm=wordmark_c, sym=symbol_c, mono=monogram_c, bg="#141110", fg="#F3ECDD", accent="#E8870E", seam="#E8870E",
                         palette=[("Soot", "#141110"), ("Char", "#241E1B"), ("Bone", "#F3ECDD"), ("Ember", "#E8870E"), ("Copper", "#C47A45"), ("Dusk", "#2B3563")], dark_bg="#141110", dark_fg="#F3ECDD", head="Inter (heavy, custom caps)", body="Inter",
                         tag="After the doors close.", note="Heavy stencil caps cut by one seam of light; symbol = a doorway left ajar."),
}


def svg_doc(inner, w, h, color, bg=None, extra="", pad=8, accent=None, seam=None):
    vb = f"{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}"
    style = f"color:{color};--accent:{accent or color};--seam:{seam or bg or 'transparent'};"
    bgr = f'<rect x="{-pad}" y="{-pad}" width="{w + 2 * pad}" height="{h + 2 * pad}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" style="{style}" role="img" aria-label="NASHA logo exploration (concept, not official)">{bgr}{inner}{extra}</svg>'


def lockups(d):
    wm, ww, wh = d["wm"]()
    sy, sw, sh = d["sym"]()
    mo, mw, mh = d["mono"]()
    # horizontal: symbol left of wordmark, symbol height = 1.15 x cap
    s = 1.0
    horiz = f'<g transform="translate(0,0) scale(1)">{sy}</g><g transform="translate({sw + 28},0)">{wm}</g>'
    hw = sw + 28 + ww
    # stacked: symbol above wordmark, centred
    stk_w = max(ww, sw)
    stacked = f'<g transform="translate({(stk_w - sw) / 2:.1f},0)">{sy}</g><g transform="translate({(stk_w - ww) / 2:.1f},{sh + 26})">{wm}</g>'
    stk_h = sh + 26 + wh
    seal = (f'<circle cx="60" cy="60" r="58" fill="none" stroke="currentColor" stroke-width="2.5"/><circle cx="60" cy="60" r="51" fill="none" stroke="currentColor" stroke-width="1"/>'
            f'<g transform="translate(40,24) scale(.4)">{sy}</g><g transform="translate({60 - ww * .17 / 2:.1f},78) scale(.17)">{wm}</g>')
    return {"wordmark": (wm, ww, wh), "symbol": (sy, sw, sh), "monogram": (mo, mw, mh), "horizontal": (horiz, hw, sh), "stacked": (stacked, stk_w, stk_h), "seal": (seal, 120, 120)}


def write_variants(key, d):
    folder = OUT / key
    folder.mkdir(parents=True, exist_ok=True)
    lk = lockups(d)
    for name, (inner, w, h) in lk.items():
        for variant, color, bg in (("color", d["fg"], d["bg"]), ("black", "#000000", None), ("white", "#FFFFFF", None)):
            acc = d["accent"] if variant == "color" else color
            seam = d["seam"] if variant == "color" else ("#FFFFFF" if variant == "black" else "#000000")
            (folder / f"{name}-{variant}.svg").write_text(svg_doc(inner, w, h, color, bg if variant == "color" else None, accent=acc, seam=seam if name in ("wordmark", "horizontal", "stacked", "symbol", "monogram", "seal") else None))
    return lk


# ------------------------------------------------------------------ application boards
def board(key, d, lk):
    W, H = 1800, 1250
    fg, bg, acc = d["fg"], d["bg"], d["accent"]
    dbg, dfg = d["dark_bg"], d["dark_fg"]
    wm, ww, wh = lk["wordmark"]
    s = []

    def fit(name_or_tuple, box, color, a=None, seam=None, align="c"):
        seam = seam if seam is not None else None
        inner, w, h = lk[name_or_tuple] if isinstance(name_or_tuple, str) else name_or_tuple
        x, y, bw, bh = box
        sc = min(bw / w, bh / h)
        ox = x + (bw - w * sc) / (2 if align == "c" else 1e9)
        oy = y + (bh - h * sc) / 2
        return f'<g transform="translate({ox:.1f},{oy:.1f}) scale({sc:.4f})" style="color:{color};--accent:{a or color};--seam:{(SEAM(seam) if seam else bg)}">{inner}</g>'

    SEAM = lambda panel_bg: d["seam"] if key.startswith("C") and panel_bg == dbg else panel_bg

    def panel(x, y, w, h, fill):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
    s.append(panel(0, 0, W, H, "#E9E3D5"))
    s.append(f'<text x="60" y="70" font-family="Instrument Serif,Georgia,serif" font-size="40" fill="#141110">{d["title"]}</text><text x="60" y="100" font-family="Inter,sans-serif" font-size="16" fill="#555" letter-spacing="2">EXPLORATION · CONCEPT, NOT OFFICIAL · NOT CLEARED · {d["tag"].upper()}</text>')
    s.append(panel(60, 130, 860, 330, bg) + fit("wordmark", (110, 190, 760, 210), fg, acc, SEAM(bg)))
    for i, (nm, onlight) in enumerate((("symbol", True), ("monogram", False), ("seal", True))):
        x0 = 60 + i * 290
        s.append(panel(x0, 480, 270, 250, bg if onlight else dbg) + fit(nm, (x0 + 45, 525, 180, 160), fg if onlight else dfg, acc, bg if onlight else dbg))
    for i, (n, hx) in enumerate(d["palette"]):
        s.append(f'<rect x="{60 + i * 144}" y="750" width="134" height="86" fill="{hx}" stroke="#999" stroke-width=".5"/><text x="{66 + i * 144}" y="860" font-family="Inter,sans-serif" font-size="13" fill="#222">{n}</text><text x="{66 + i * 144}" y="878" font-family="Inter,sans-serif" font-size="12" fill="#666">{hx}</text>')
    s.append(f'<text x="60" y="935" font-family="Instrument Serif,Georgia,serif" font-size="46" fill="#141110">{d["head"]}</text><text x="60" y="975" font-family="Inter,sans-serif" font-size="18" fill="#333">Body: {d["body"]}. {d["note"]}</text>')
    X = 960
    s.append(panel(X, 130, 780, 250, "#2a2420") + panel(X, 330, 780, 50, "#1a1512") + panel(X + 150, 165, 480, 130, dbg))
    s.append(f'<rect x="{X + 150}" y="165" width="480" height="130" fill="none" stroke="#666" stroke-width="2"/>' + fit("wordmark", (X + 195, 195, 390, 70), dfg, acc, dbg))
    s.append(f'<text x="{X + 20}" y="365" font-family="Inter,sans-serif" font-size="13" fill="#bbb">Entrance signage (flat concept, not a rendering of a real building)</text>')
    s.append(panel(X, 400, 380, 330, "#d9d0bd"))
    for cx, col, txt in ((X + 100, bg, fg), (X + 280, dbg, dfg)):
        s.append(f'<rect x="{cx - 52}" y="425" width="104" height="270" rx="16" fill="{col}" stroke="#777" stroke-width="1.2"/><rect x="{cx - 46}" y="414" width="92" height="14" rx="5" fill="#c9cccb"/><rect x="{cx - 46}" y="692" width="92" height="14" rx="5" fill="#c9cccb"/>')
        s.append(fit("wordmark", (cx - 40, 480, 80, 30), txt, acc, col) + fit("symbol", (cx - 28, 535, 56, 56), txt, acc, col))
    s.append(f'<text x="{X + 14}" y="716" font-family="Inter,sans-serif" font-size="13" fill="#444">Can labels (flat concept, not photographs)</text>')
    hx = X + 400
    s.append(panel(hx, 400, 380, 330, "#d9d0bd"))
    hood = f"M{hx + 190},425 C{hx + 150},425 {hx + 120},445 {hx + 105},470 L{hx + 40},500 L{hx + 15},640 L{hx + 70},650 L{hx + 90},560 L{hx + 90},700 L{hx + 290},700 L{hx + 290},560 L{hx + 310},650 L{hx + 365},640 L{hx + 340},500 L{hx + 275},470 C{hx + 260},445 {hx + 230},425 {hx + 190},425 Z"
    s.append(f'<path d="{hood}" fill="{dbg}" stroke="#555" stroke-width="1.5"/>' + fit("monogram", (hx + 226, 492, 34, 34), dfg, acc, dbg) + fit("symbol", (hx + 140, 590, 100, 95), dfg, acc, dbg))
    s.append(f'<text x="{hx + 14}" y="716" font-family="Inter,sans-serif" font-size="13" fill="#444">Hoodie: chest monogram + front symbol (flat concept)</text>')
    s.append(panel(X, 750, 780, 225, dbg) + fit("wordmark", (X + 40, 790, 560, 110), dfg, acc, dbg, align="l") + f'<text x="{X + 40}" y="940" font-family="Instrument Serif,Georgia,serif" font-size="30" fill="{dfg}">{d["tag"]}</text>')
    s.append(f'<text x="{X + 520}" y="775" font-family="Inter,sans-serif" font-size="12" fill="#999">Website hero treatment (flat concept)</text>')
    s.append(panel(60, 1000, 560, 200, bg) + fit("horizontal", (90, 1040, 500, 120), fg, acc, bg))
    s.append(panel(640, 1000, 280, 200, dbg) + fit("stacked", (690, 1020, 180, 160), dfg, acc, dbg))
    s.append(f'<text x="{X}" y="1030" font-family="Inter,sans-serif" font-size="14" fill="#333">One-colour check (no gradients, no effects):</text>')
    for i, (col, bgc) in enumerate((("#000", "#fff"), ("#fff", "#000"))):
        s.append(panel(X + i * 390, 1050, 380, 130, bgc) + f'<rect x="{X + i * 390}" y="1050" width="380" height="130" fill="none" stroke="#999"/>' + fit("wordmark", (X + i * 390 + 30, 1085, 320, 60), col, col, bgc))
    s.append(f'<text x="60" y="1236" font-family="Inter,sans-serif" font-size="12" fill="#666">Provisional exploration. No trademark search done. D-66 gate: EXPLORATION. Names and marks are not final.</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>'


def render_png(svg_path, png_path, w, h):
    chrome = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    html = svg_path.with_suffix(".html")
    fonts = ROOT / "website/dist/fonts"
    html.write_text(f'<!doctype html><meta charset=utf-8><style>@font-face{{font-family:"Instrument Serif";src:url("file://{fonts}/instrument-serif-latin-400-normal.woff2")}}@font-face{{font-family:Inter;src:url("file://{fonts}/inter-latin-wght-normal.woff2")}}html,body{{margin:0}}svg{{display:block}}</style>' + svg_path.read_text().split("</style>", 1)[-1].join(["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' height='%d'>" % (w, h, w, h), ""]) if False else
                    f'<!doctype html><meta charset=utf-8><style>@font-face{{font-family:"Instrument Serif";src:url("file://{fonts}/instrument-serif-latin-400-normal.woff2")}}@font-face{{font-family:Inter;src:url("file://{fonts}/inter-latin-wght-normal.woff2")}}html,body{{margin:0}}svg{{display:block}}</style>' + re.sub(r"<style>.*?</style>", "", svg_path.read_text(), flags=re.S))
    subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", f"--screenshot={png_path}", f"--window-size={w},{h + 240}", "--hide-scrollbars", f"file://{html}"], capture_output=True, timeout=120)
    html.unlink()
    from PIL import Image
    Image.open(png_path).crop((0, 0, w, h)).save(png_path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, d in DIRECTIONS.items():
        lk = write_variants(key, d)
        b = board(key, d, lk)
        p = OUT / key / "application-board.svg"
        p.write_text(b)
        render_png(p, OUT / key / "application-board.png", 1800, 1250)
        # preview PNGs of the wordmark on its colour background, for quick review
        wm, ww, wh = lk["wordmark"]
        prev = OUT / key / "wordmark-preview.svg"
        prev.write_text(svg_doc(wm, ww, wh, d["fg"], d["bg"], accent=d["accent"], seam=d["bg"], pad=30))
        render_png(prev, OUT / key / "wordmark-preview.png", int(ww + 60) * 4, int(wh + 60) * 4) if False else None
    print("written", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
