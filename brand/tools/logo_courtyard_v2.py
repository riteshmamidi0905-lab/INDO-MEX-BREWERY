#!/usr/bin/env python3
"""NASHA Direction A "The Courtyard" — refinement round 2 (status: EXPLORATION / provisional; NOT final, NOT cleared, no trademark search).

Refines the Direction A wordmark, symbol, monogram and lockups, adds small-size (<=96 px wide / <=32 px tall) cuts, and builds
(1) a refined identity board with signage, cans, glassware, apparel, menu and website applications, and
(2) a Direction B "botanical kit" for merchandise / secondary packaging only (not a primary logo).
Everything is flat vector (no gradients, no photo effects). Letters are drawn from scratch from circles and rectangles; no font file is used
for the mark. Board text uses Instrument Serif and Inter only as presentation type.

    CHROMIUM_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome python3 brand/tools/logo_courtyard_v2.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from logo_explorations import ROOT, leaf_path, poly, rect, render_png  # noqa: E402

OUT = ROOT / "brand/logo/CONTROLLED-MASTERS/courtyard-refined-2026-10-22"
FG, BG, SOOT = "#141110", "#EFE7D6", "#141110"
ACC = "#C2680B"
PAL = [("Limestone", "#EFE7D6"), ("Soot", "#141110"), ("Terracotta ink", "#A5461F"), ("Marigold ink", "#C2680B"), ("Indigo dusk", "#1A2142"), ("Stainless", "#C9CCCB")]


# --------------------------------------------------------------------- letters (one stem weight, optical corrections)
class Cut:
    """Geometry set. `text` = display cut; `small` = heavier stems, looser spacing for <= 96 px wide use."""
    def __init__(self, stem, bar, gaps, widths):
        self.w, self.h, self.gaps, self.W = stem, bar, gaps, widths


TEXT = Cut(14.0, 11.0, {"NA": 17, "AS": 15, "SH": 17, "HA": 17}, {"N": 70, "A": 80, "S": 60, "H": 70})
SMALL = Cut(19.0, 15.0, {"NA": 24, "AS": 22, "SH": 24, "HA": 24}, {"N": 76, "A": 86, "S": 64, "H": 76})


def letter(ch, c):
    w, h, W = c.w, c.h, c.W[ch]
    if ch == "N":
        return [rect(0, 0, w, 100), rect(W - w, 0, w, 100), poly((0, 0), (w * 1.3, 0), (W, 100), (W - w * 1.3, 100))]
    if ch == "H":
        return [rect(0, 0, w, 100), rect(W - w, 0, w, 100), rect(w - 1, 50 - h / 2, W - 2 * w + 2, h)]
    if ch == "A":
        r, o = W / 2, 1.5                      # 1.5 unit overshoot: round tops read as the same height as flat caps
        s = r - o
        outer = f"M0,100V{s:.2f}A{r:.2f},{r:.2f} 0 0 1 {W},{s:.2f}V100H{W - w}V{s:.2f}A{r - w:.2f},{r - w:.2f} 0 0 0 {w},{s:.2f}V100z"
        return [outer, rect(w - 1, 66 - h / 2, W - 2 * w + 2, h)]
    if ch == "S":                              # one stroked spine, two bowls, flat vertical-cut terminals
        r = 23.5 if c is TEXT else 24.5
        cx = W / 2
        top, bot = w / 2 - 1.2, 100 - w / 2 + 1.2
        return [("S", f'<path d="M{W - 6:.1f},{top + 3:.1f}A{r},{r} 0 1 0 {cx:.1f},50A{r},{r} 0 1 1 6,{bot - 3:.1f}" fill="none" stroke="currentColor" stroke-width="{w}" stroke-linecap="butt"/>')]
    raise ValueError(ch)


def wordmark(c=TEXT):
    x, out, word = 0.0, [], "NASHA"
    for i, ch in enumerate(word):
        for p in letter(ch, c):
            out.append(f'<g transform="translate({x:.1f},0)">{p[1]}</g>' if isinstance(p, tuple) else f'<path transform="translate({x:.1f},0)" d="{p}" fill="currentColor"/>')
        x += c.W[ch] + (c.gaps[word[i:i + 2]] if i < 4 else 0)
    return "".join(out), x, 100


def ring(r, t, cy=46, cx=50):
    s = f"M{cx - r},100V{cy}A{r},{r} 0 0 1 {cx + r},{cy}V100H{cx + r - t}V{cy}A{r - t},{r - t} 0 0 0 {cx - r + t},{cy}V100z"
    return s


def symbol(small=False):
    """Concentric thresholds (arches) opening onto an ember doorway. `small` = two heavier arches for <= 32 px use."""
    d = ring(46, 15) + ring(24, 15) if small else ring(46, 9) + ring(32, 9) + ring(18, 9)
    return f'<path d="{d}" fill="currentColor"/><rect x="45" y="{70 if not small else 66}" width="10" height="{30 if not small else 34}" fill="var(--accent,currentColor)"/>', 100, 100


def monogram():
    s = .56
    parts = "".join(f'<path transform="translate({50 - 70 * s / 2:.1f},{100 - 100 * s:.1f}) scale({s})" d="{p}" fill="currentColor"/>' for p in letter("N", TEXT))
    return f'<path d="{ring(46, 12)}" fill="currentColor"/>{parts}', 100, 100


def lockups():
    wm, ww, wh = wordmark()
    ws, wsw, _ = wordmark(SMALL)
    sy, sw, sh = symbol()
    mo, mw, mh = monogram()
    gap = 34
    horiz = f'<g>{sy}</g><g transform="translate({sw + gap},0)">{wm}</g>'
    stk_w = ww
    k = .62
    stacked = f'<g transform="translate({(stk_w - sw * k) / 2:.1f},0) scale({k})">{sy}</g><g transform="translate(0,{sh * k + 28:.1f})">{wm}</g>'
    seal = (f'<circle cx="70" cy="70" r="68" fill="none" stroke="currentColor" stroke-width="3"/><circle cx="70" cy="70" r="60" fill="none" stroke="currentColor" stroke-width="1.2"/>'
            f'<g transform="translate(43,22) scale(.54)">{sy}</g><g transform="translate({70 - ww * .2 / 2:.1f},88) scale(.2)">{wm}</g>')
    return {"wordmark": (wm, ww, wh), "wordmark-small": (ws, wsw, 100), "symbol": (sy, sw, sh), "symbol-small": symbol(True), "monogram": (mo, mw, mh),
            "horizontal": (horiz, sw + gap + ww, 100), "stacked": (stacked, stk_w, sh * k + 28 + 100), "seal": (seal, 140, 140)}


def svg_doc(inner, w, h, color, bg=None, accent=None, pad=8):
    vb = f"{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}"
    bgr = f'<rect x="{-pad}" y="{-pad}" width="{w + 2 * pad}" height="{h + 2 * pad}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" style="color:{color};--accent:{accent or color}" role="img" aria-label="NASHA logo refinement (provisional concept, not official)">{bgr}{inner}</svg>'


def write_files(lk):
    d = OUT / "vector"
    d.mkdir(parents=True, exist_ok=True)
    for name, (inner, w, h) in lk.items():
        for variant, col, bg, acc in (("color", FG, BG, ACC), ("color-reverse", BG, FG, ACC), ("black", "#000", None, "#000"), ("white", "#FFF", None, "#FFF")):
            (d / f"{name}-{variant}.svg").write_text(svg_doc(inner, w, h, col, bg if variant.startswith("color") else None, acc))


# --------------------------------------------------------------------- the refined identity board
def board(lk):
    W, H = 2400, 1500
    s = []
    add = s.append
    panel = lambda x, y, w, h, f, st="": f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{f}" {st}/>'
    txt = lambda x, y, t, size=14, fill="#444", fam="Inter,sans-serif", extra="": f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{fill}" {extra}>{t}</text>'

    def fit(name, box, color, acc=ACC, align="c"):
        inner, w, h = lk[name]
        x, y, bw, bh = box
        sc = min(bw / w, bh / h)
        ox = x + ((bw - w * sc) / 2 if align == "c" else 0)
        oy = y + (bh - h * sc) / 2
        return f'<g transform="translate({ox:.1f},{oy:.1f}) scale({sc:.4f})" style="color:{color};--accent:{acc}">{inner}</g>'

    add(panel(0, 0, W, H, "#E9E3D5"))
    add(txt(60, 72, "NASHA — Direction A, The Courtyard: refined identity (round 2)", 42, "#141110", "Instrument Serif,Georgia,serif"))
    add(txt(60, 104, "PROVISIONAL SELECTION FOR DEVELOPMENT · NOT FINAL · NOT CLEARED · NO TRADEMARK SEARCH DONE · D-66 GATE: EXPLORATION", 15, "#555", extra='letter-spacing="1.5"'))
    # row 1: hero + marks
    add(panel(60, 130, 1100, 360, BG) + fit("wordmark", (130, 190, 960, 240), FG))
    for i, (nm, dark) in enumerate((("symbol", False), ("monogram", True), ("seal", False))):
        x0 = 1190 + i * 390
        add(panel(x0, 130, 370, 360, FG if dark else BG) + fit(nm, (x0 + 55, 175, 260, 270), BG if dark else FG))
    # row 2: lockups, palette
    add(panel(60, 510, 760, 230, BG) + fit("horizontal", (100, 560, 680, 130), FG))
    add(panel(840, 510, 330, 230, FG) + fit("stacked", (900, 535, 210, 180), BG))
    for i, (n, hx) in enumerate(PAL):
        add(f'<rect x="{1190 + i * 195}" y="510" width="185" height="120" fill="{hx}" stroke="#999" stroke-width=".6"/>' + txt(1196 + i * 195, 654, n, 14, "#222") + txt(1196 + i * 195, 672, hx, 13, "#666"))
    add(txt(1190, 716, "Display: custom drawn mark.  Headings: Instrument Serif (OFL).  Body: Inter (OFL).  Licence records still required before any use.", 15, "#333"))
    # small-size ladder (actual pixel sizes)
    add(panel(60, 760, 1110, 260, "#F6F1E6", 'stroke="#bbb" stroke-width=".8"') + txt(76, 786, "SMALL-SIZE LADDER (true pixel sizes; small cut used at 96 px and below)", 13, "#555", extra='letter-spacing="1"'))
    x = 80
    for nm, wpx in (("wordmark", 300), ("wordmark", 180), ("wordmark-small", 96), ("wordmark-small", 64), ("wordmark-small", 44)):
        inner, w, h = lk[nm]
        add(f'<g transform="translate({x},{840 - h * wpx / w / 2 + 30:.1f}) scale({wpx / w:.4f})" style="color:{FG};--accent:{ACC}">{inner}</g>' + txt(x, 932, f"{wpx}px", 12, "#666"))
        x += wpx + 40
    x = 80
    for nm, px in (("symbol", 64), ("symbol-small", 40), ("symbol-small", 32), ("symbol-small", 24), ("symbol-small", 16), ("monogram", 32), ("monogram", 24)):
        inner, w, h = lk[nm]
        add(f'<g transform="translate({x},{946}) scale({px / 100:.4f})" style="color:{FG};--accent:{ACC}">{inner}</g>')
        x += px + 28
    add(txt(560, 1000, "symbol 64 / 40 / 32 / 24 / 16 px   ·   monogram 32 / 24 px", 12, "#666"))
    # clear space + min size spec
    add(panel(1190, 760, 1150, 260, "#F6F1E6", 'stroke="#bbb" stroke-width=".8"') + txt(1206, 786, "CLEAR SPACE & MINIMUMS (provisional rules)", 13, "#555", extra='letter-spacing="1"'))
    add(f'<rect x="1240" y="810" width="400" height="170" fill="none" stroke="{ACC}" stroke-dasharray="6 5"/>' + fit("wordmark", (1280, 850, 320, 90), FG))
    add(txt(1250, 830, "x", 14, ACC) + txt(1250, 975, "clear space = x = the stem width of the N  ·  on all four sides", 12, "#555"))
    for i, t in enumerate(("Minimum: wordmark 44 px / 12 mm wide (use the small cut ≤ 96 px)", "Minimum: symbol 16 px / 5 mm (use the two-arch cut ≤ 32 px)", "Monogram minimum 24 px / 8 mm", "Ember doorway is optional; mark must work in one colour", "Never: stretch, outline, add effects, recolour off-palette, rotate")):
        add(txt(1700, 830 + i * 34, t, 14, "#333"))
    # applications row 3
    y0 = 1050
    # signage: facade
    add(panel(60, y0, 620, 420, "#2a2420"))
    add(panel(60, y0 + 330, 620, 90, "#1a1512"))
    for ax in (110, 270, 430):                      # arched openings
        add(f'<path d="M{ax},{y0 + 330}V{y0 + 250}A50,50 0 0 1 {ax + 100},{y0 + 250}V{y0 + 330}z" fill="#E9B764" opacity=".9"/>')
    add(panel(150, y0 + 70, 440, 110, "#141110", 'stroke="#777" stroke-width="2"') + fit("wordmark", (190, y0 + 96, 360, 58), BG, ACC))
    add(txt(76, y0 + 400, "Entrance sign + arched windows (flat concept, not a rendering of a real building)", 13, "#bbb"))
    # cans + glass
    add(panel(700, y0, 600, 420, "#d9d0bd"))
    for cx, col, tx in ((775, BG, FG), (905, FG, BG)):
        add(f'<rect x="{cx - 45}" y="{y0 + 40}" width="90" height="270" rx="15" fill="{col}" stroke="#777" stroke-width="1.2"/><rect x="{cx - 40}" y="{y0 + 30}" width="80" height="13" rx="5" fill="#c9cccb"/><rect x="{cx - 40}" y="{y0 + 307}" width="80" height="13" rx="5" fill="#c9cccb"/>')
        add(fit("wordmark-small", (cx - 34, y0 + 90, 68, 26), tx, ACC) + fit("symbol", (cx - 24, y0 + 140, 48, 48), tx, ACC))
    gx = 1130                                       # pint glass: conical silhouette, etched symbol in white (one colour)
    add(f'<path d="M{gx - 62},{y0 + 40}L{gx + 62},{y0 + 40}L{gx + 46},{y0 + 320}L{gx - 46},{y0 + 320}Z" fill="#f4efe4" fill-opacity=".55" stroke="#8a8478" stroke-width="2"/><path d="M{gx - 58},{y0 + 110}L{gx + 58},{y0 + 110}L{gx + 49},{y0 + 318}L{gx - 49},{y0 + 318}Z" fill="#C98A1B" fill-opacity=".75"/>')
    add(fit("symbol", (gx - 26, y0 + 160, 52, 52), "#FFFFFF", "#FFFFFF"))
    add(txt(716, y0 + 400, "Cans (BADSHAH / AMBA HAZE would carry their own labels) · etched pint glass — flat concepts", 13, "#444"))
    # hoodie
    hx = 1320
    add(panel(hx, y0, 480, 420, "#d9d0bd"))
    hood = f"M{hx + 240},{y0 + 40}C{hx + 195},{y0 + 40} {hx + 160},{y0 + 65} {hx + 140},{y0 + 100}L{hx + 55},{y0 + 140}L{hx + 25},{y0 + 330}L{hx + 95},{y0 + 345}L{hx + 120},{y0 + 235}L{hx + 120},{y0 + 385}L{hx + 360},{y0 + 385}L{hx + 360},{y0 + 235}L{hx + 385},{y0 + 345}L{hx + 455},{y0 + 330}L{hx + 425},{y0 + 140}L{hx + 340},{y0 + 100}C{hx + 320},{y0 + 65} {hx + 285},{y0 + 40} {hx + 240},{y0 + 40}Z"
    add(f'<path d="{hood}" fill="{FG}" stroke="#555" stroke-width="1.5"/>' + fit("monogram", (hx + 290, y0 + 120, 40, 40), BG, ACC) + fit("symbol", (hx + 170, y0 + 210, 140, 150), BG, ACC))
    add(txt(hx + 14, y0 + 408, "THE COURTYARD hoodie: monogram left chest, symbol front (flat concept)", 13, "#444"))
    # menu cover + website
    mx = 1820
    add(panel(mx, y0, 520, 420, "#d9d0bd"))
    add(panel(mx + 30, y0 + 20, 190, 380, FG) + fit("symbol", (mx + 85, y0 + 60, 80, 80), BG, ACC) + fit("wordmark-small", (mx + 50, y0 + 170, 150, 40), BG, ACC) + txt(mx + 62, y0 + 250, "MENU CONCEPT", 12, "#D8C9A8", extra='letter-spacing="3"') + txt(mx + 62, y0 + 274, "not a priced menu", 11, "#bbb"))
    add(panel(mx + 250, y0 + 60, 250, 280, BG, 'stroke="#aaa"') + panel(mx + 250, y0 + 60, 250, 24, "#d2cab6") + fit("wordmark-small", (mx + 262, y0 + 92, 100, 22), FG, ACC, "l"))
    add(panel(mx + 250, y0 + 125, 250, 120, FG) + fit("wordmark", (mx + 270, y0 + 150, 210, 40), BG, ACC) + txt(mx + 270, y0 + 220, "Concept — nothing is open or for sale", 11, "#D8C9A8"))
    add(txt(mx + 14, y0 + 408, "Menu cover (left) · website nav + hero (right) — flat concepts", 13, "#444"))
    add(txt(60, 1488, "Provisional refinement for review. Marks are not final, not cleared and not approved. Mockups are flat vector concepts, not photographs; no photorealistic imagery has been generated.", 13, "#666"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>', W, H


# --------------------------------------------------------------------- Direction B botanical kit (secondary graphics only)
def leaf_set(small=False):
    """Fixed-proportion hibiscus-style leaf. `small` removes the midrib and widens the blade so it survives at <= 20 px."""
    return leaf_path(50, 50, 80, 36 if small else 26, -35)


def botanical_board():
    W, H = 1800, 1100
    s = []
    add = s.append
    FOR, HIB, TAM, BONE = "#3F5A1E", "#9B2447", "#5A3A25", "#F3ECDD"
    add(f'<rect width="{W}" height="{H}" fill="#E9E3D5"/><text x="60" y="70" font-family="Instrument Serif,Georgia,serif" font-size="40" fill="#141110">Direction B kept as a botanical language — secondary graphics only</text>')
    add('<text x="60" y="102" font-family="Inter,sans-serif" font-size="15" fill="#555" letter-spacing="1.5">NOT A PRIMARY LOGO · MERCHANDISE, ILLUSTRATION, SECONDARY PACKAGING · PROVISIONAL · CULTURAL REVIEW STILL REQUIRED</text>')

    def leaf(cx, cy, size, ang, fill, rib=None, small=False):
        sc = size / 100
        w = 34 if small else 24
        d = leaf_path(0, 0, 100, w, ang)
        r = ""
        if rib and not small:
            a = math.radians(ang)
            r = f'<line x1="{-math.cos(a) * 38:.1f}" y1="{-math.sin(a) * 38:.1f}" x2="{math.cos(a) * 38:.1f}" y2="{math.sin(a) * 38:.1f}" stroke="{rib}" stroke-width="2.2" stroke-linecap="round"/>'
        return f'<g transform="translate({cx},{cy}) scale({sc})"><path d="{d}" fill="{fill}"/>{r}</g>'

    # size ladder: full leaf -> small leaf (no midrib, wider blade)
    add('<rect x="60" y="130" width="860" height="250" fill="#F3ECDD"/><text x="76" y="156" font-family="Inter,sans-serif" font-size="13" fill="#555" letter-spacing="1">SMALL-SIZE CORRECTION: full leaf with midrib at ≥ 40 px; simplified small leaf (wider blade, no midrib) at 40 → 14 px</text>')
    x = 110
    for size, small in ((140, False), (90, False), (56, False), (40, True), (28, True), (20, True), (14, True)):
        add(leaf(x + size / 2, 260, size, -35, FOR, BONE, small) + f'<text x="{x}" y="360" font-family="Inter,sans-serif" font-size="12" fill="#666">{size}px</text>')
        x += size + 34
    # sprig + rosette
    add('<rect x="940" y="130" width="400" height="250" fill="#1E2A1C"/>')
    for ang, off in ((-70, -38), (-35, 0), (0, 38)):
        add(leaf(1140 + off, 270 - abs(off) * .3, 120, ang - 10, BONE if off else "#C2680B", "#1E2A1C"))
    add('<rect x="1360" y="130" width="380" height="250" fill="#F3ECDD"/>')
    for k in range(4):
        ang = k * 90
        add(leaf(1550 + math.cos(math.radians(ang)) * 42, 255 + math.sin(math.radians(ang)) * 42, 92, ang, HIB if k % 2 == 0 else FOR, None, True))
    # pattern tile + tee + packaging band
    add('<rect x="60" y="410" width="560" height="320" fill="#1E2A1C"/>')
    for r in range(5):
        for c in range(8):
            ox = 80 + c * 70 + (35 if r % 2 else 0)
            add(leaf(ox, 440 + r * 62, 44, 35 if (r + c) % 2 else -35, BONE if (r + c) % 3 else "#C2680B", None, True).replace("<g ", '<g opacity=".92" ', 1))
    add('<text x="76" y="752" font-family="Inter,sans-serif" font-size="13" fill="#444">Pattern tile (simplified leaves, no fine detail) for tissue, tape, linings</text>')
    tx = 660
    add(f'<rect x="{tx}" y="410" width="500" height="320" fill="#d9d0bd"/>')
    tee = f"M{tx + 250},450C{tx + 220},450 {tx + 205},465 {tx + 195},478L{tx + 110},505L{tx + 70},590L{tx + 130},610L{tx + 150},560L{tx + 150},700L{tx + 350},700L{tx + 350},560L{tx + 370},610L{tx + 430},590L{tx + 390},505L{tx + 305},478C{tx + 295},465 {tx + 280},450 {tx + 250},450Z"
    add(f'<path d="{tee}" fill="{BONE}" stroke="#999" stroke-width="1.5"/>' + leaf(tx + 250, 590, 110, -35, HIB, BONE) + leaf(tx + 300, 555, 70, 35, FOR, BONE))
    add(f'<text x="{tx + 14}" y="752" font-family="Inter,sans-serif" font-size="13" fill="#444">Graphic tee: botanical art only (flat concept)</text>')
    add('<rect x="1190" y="410" width="550" height="320" fill="#F3ECDD"/><rect x="1230" y="480" width="470" height="150" fill="#9B2447"/>')
    for i in range(8):
        add(leaf(1260 + i * 58, 555, 44, 35 if i % 2 else -35, BONE, None, True))
    add('<text x="1206" y="752" font-family="Inter,sans-serif" font-size="13" fill="#444">Secondary packaging band (carton wrap / sleeve) — flat concept</text>')
    notes = ["Rules", "• Leaf is a supporting graphic: never replaces, outlines or sits inside the NASHA wordmark or symbol.",
             "• The B-style leaf-crossbar wordmark is retired as a logo idea (read as slashes at small size).",
             "• Min 14 px / 4 mm (simplified leaf), 40 px / 12 mm for the version with a midrib.",
             "• Botanical subjects must be named and accurate before any caption; no 'exotic' framing. Cultural-authenticity review pending."]
    for i, t in enumerate(notes):
        add(f'<text x="60" y="{800 + i * 34}" font-family="Inter,sans-serif" font-size="{16 if i else 20}" fill="#222">{t}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>', W, H


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lk = lockups()
    write_files(lk)
    for name, fn in (("identity-board", lambda: board(lk)), ("botanical-kit", botanical_board)):
        svg, w, h = fn()
        p = OUT / f"{name}.svg"
        p.write_text(svg)
        render_png(p, OUT / f"{name}.png", w, h)
    print("written", len(list(OUT.rglob("*"))), "files in", OUT)


if __name__ == "__main__":
    main()
