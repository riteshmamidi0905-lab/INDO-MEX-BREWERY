#!/usr/bin/env python3
"""Brand identity board v3 (PROVISIONAL): refined Courtyard marks in the warmer forest/gold/ivory/terracotta/charcoal palette, secondary crest,
BADSHAH + AMBA HAZE label systems, procedural can renders, hoodie, signage, menu, website. Flat vector concepts and procedural renders only —
no photographs, no AI-generated imagery."""
import base64, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand_v3_art as A
import logo_courtyard_v2 as L
from logo_explorations import leaf_path

P = A.PAL
V3 = A.OUTV3
LK = L.lockups()


def b64(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def fit(name, box, color, acc, align="c"):
    inner, w, h = LK[name]
    x, y, bw, bh = box
    sc = min(bw / w, bh / h)
    ox = x + ((bw - w * sc) / 2 if align == "c" else 0)
    oy = y + (bh - h * sc) / 2
    return f'<g transform="translate({ox:.1f},{oy:.1f}) scale({sc:.4f})" style="color:{color};--accent:{acc}">{inner}</g>'


def crest_at(x, y, s, c, leaf, door):
    return f'<g transform="translate({x},{y}) scale({s / 100})">{A.crest(c, None, leaf, door)}</g>'


def board():
    W, H = 2400, 2330
    s = []
    r = lambda x, y, w, h, f, extra="": s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{f}" {extra}/>')
    t = lambda x, y, txt, size=14, fill="#444", fam="Inter", extra="": s.append(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{fill}" {extra}>{txt}</text>')
    r(0, 0, W, H, "#EAE3D2")
    t(60, 72, "NASHA — brand identity board v3 (Courtyard foundation, warmer palette)", 42, "#141110", "Instrument Serif")
    t(60, 104, "PROVISIONAL · NOT FINAL · NOT CLEARED · CONCEPT ONLY · FLAT VECTOR + PROCEDURAL RENDERS (NO PHOTOGRAPHS, NO AI IMAGERY) · D-66 GATE: EXPLORATION", 14, "#555", extra='letter-spacing="1.4"')
    # hero
    r(60, 130, 1180, 380, P["forest"])
    s.append(fit("wordmark", (130, 200, 760, 190), P["ivory"], P["gold"]))
    s.append(crest_at(960, 170, 230, P["gold"], P["gold"], P["terra"]))
    t(130, 450, "THE COURTYARD · BREWHOUSE · KITCHEN · CULTURE", 20, P["gold_lt"], extra='letter-spacing="6"')
    t(130, 480, "Tagline copy is a working placeholder, not approved.", 13, "#B9C6B8")
    # marks on palette grounds
    for i, (bg, fg, ac, nm) in enumerate(((P["ivory"], P["forest"], P["terra"], "symbol"), (P["charcoal"], P["gold_lt"], P["terra"], "monogram"), (P["ivory"], P["charcoal"], P["terra"], "seal"))):
        x0 = 1260 + i * 380
        r(x0, 130, 360, 380, bg)
        s.append(fit(nm, (x0 + 50, 175, 260, 290), fg, ac))
    # secondary crest set
    r(1260, 530, 1080, 250, "#F4EDDC")
    t(1276, 556, "SECONDARY SYMBOL — arch-and-botanical crest (not the primary mark)", 13, "#555", extra='letter-spacing="1"')
    for i, (bg, c) in enumerate(((P["forest"], P["gold"]), (P["ivory"], P["forest"]), (P["terra"], P["ivory"]), (P["charcoal"], P["gold_lt"]))):
        x0 = 1290 + i * 255
        r(x0, 575, 230, 185, bg)
        s.append(crest_at(x0 + 60, 590, 110, c, c, P["terra"] if bg != P["terra"] else P["ivory"]))
        t(x0 + 6, 750, ("gold on forest", "forest on ivory", "ivory on terracotta", "gold on charcoal")[i], 11, "#999" if bg != P["ivory"] else "#555")
    # lockups
    r(60, 530, 780, 250, P["ivory"]); s.append(fit("horizontal", (100, 580, 700, 150), P["forest"], P["terra"]))
    r(860, 530, 380, 250, P["charcoal"]); s.append(fit("stacked", (930, 550, 240, 210), P["ivory"], P["saffron"]))
    # palette + contrast
    t(60, 815, "PALETTE", 13, "#555", extra='letter-spacing="2"')
    for i, (n, hx) in enumerate(A.PALETTE):
        x0 = 60 + i * 232
        r(x0, 830, 220, 110, hx, 'stroke="#aaa" stroke-width=".6"')
        t(x0 + 4, 962, n, 14, "#222"); t(x0 + 4, 981, hx, 12, "#666")
    for i, (n, hx) in enumerate(A.SUPPORT):
        x0 = 60 + i * 232
        r(x0, 1000, 222, 36, hx, 'stroke="#aaa" stroke-width=".6"'); t(x0 + 4, 1054, f"{n} {hx}", 10, "#555")
    pairs = (("ivory on forest", P["ivory"], P["forest"]), ("gold on forest", P["gold"], P["forest"]), ("forest on ivory", P["forest"], P["ivory"]), ("terracotta on ivory", P["terra"], P["ivory"]), ("ivory on terracotta", P["ivory"], P["terra"]), ("ivory on terra deep", P["ivory"], P["terra_deep"]), ("ivory on charcoal", P["ivory"], P["charcoal"]), ("gold on charcoal", P["gold"], P["charcoal"]))
    t(1260, 815, "CONTRAST (WCAG 2.x ratio; ≥4.5 body text, ≥3 large text/graphics)", 13, "#555", extra='letter-spacing="1"')
    for i, (n, f, b) in enumerate(pairs):
        c = A.contrast(f, b)
        t(1260 + (i % 3) * 360, 850 + (i // 3) * 26, f"{n}: {c}  {'PASS' if c >= 4.5 else ('large only' if c >= 3 else 'FAIL')}", 15, "#222")
    # type
    r(1260, 930, 1080, 150, "#F4EDDC")
    t(1280, 985, "Instrument Serif — display & headings", 44, "#141110", "Instrument Serif")
    t(1280, 1030, "Aa Bb Cc 0123 — Inter for body, labels and UI (both SIL OFL; licence records still required)", 17, "#333")
    t(1280, 1062, "Wordmark and symbols are custom-drawn vectors; never retype the wordmark in a font.", 15, "#555")
    # labels + cans
    y0 = 1110
    t(60, y0 + 16, "LABEL SYSTEMS (front panels of the flat wraps) — placeholders mark every unverified spec", 13, "#555", extra='letter-spacing="1"')
    for i, n in enumerate(("badshah", "amba-haze")):
        s.append(f'<image href="{b64(V3 / f"labels/{n}-wrap.png")}" x="{60 + i * 760}" y="{y0 + 30}" width="740" height="357" />')
        t(60 + i * 760, y0 + 410, ("BADSHAH — regal: forest, antique gold, gateway arches, wheat", "AMBA HAZE — vibrant: ivory, terracotta, saffron, mango + leaves")[i], 13, "#444")
    s.append(f'<image href="{b64(V3 / "mockups/cans-pair-procedural.png")}" x="1620" y="{y0 + 20}" width="720" height="679" preserveAspectRatio="xMidYMid meet" />')
    t(1630, y0 + 718, "Procedural can renders (code), not photographs", 13, "#444")
    # applications row
    y1 = 1700
    r(60, y1 + 150, 740, 410, "#2b2622")
    r(60, y1 + 480, 740, 80, "#1a1512")
    for k, ax in enumerate((100, 280, 460, 640)):
        pass
    for ax in (110, 300, 490):
        s.append(f'<path d="M{ax},{y1 + 480}V{y1 + 360}A60,60 0 0 1 {ax + 120},{y1 + 360}V{y1 + 480}z" fill="{P["saffron"]}" opacity=".88"/>')
    r(150, y1 + 190, 560, 110, P["charcoal"], 'stroke="#8a7a50" stroke-width="2"')
    s.append(fit("wordmark", (200, y1 + 214, 360, 62), P["gold_lt"], P["gold"], "l"))
    s.append(crest_at(600, y1 + 205, 80, P["gold"], P["gold"], P["terra"]))
    for lx in range(80, 780, 46):
        s.append(f'<circle cx="{lx}" cy="{y1 + 172 + 8 * math.sin(lx / 40)}" r="4" fill="#F0C46A"/>')
    for px in (80, 730):
        for j in range(5):
            s.append(f'<path d="{leaf_path(px, y1 + 450 - j * 22, 70, 22, -60 if px < 400 else -120)}" fill="{P["leaf"]}"/>')
    t(76, y1 + 545, "Court Brewhouse facade concept (flat; NOT a photographic or architectural rendering)", 12, "#c9c0ae")
    # hoodie
    hx = 830
    r(hx, y1 + 150, 500, 410, "#d9d0bd")
    hood = f"M{hx + 250},{y1 + 190}C{hx + 205},{y1 + 190} {hx + 170},{y1 + 215} {hx + 150},{y1 + 250}L{hx + 65},{y1 + 290}L{hx + 35},{y1 + 480}L{hx + 105},{y1 + 495}L{hx + 130},{y1 + 385}L{hx + 130},{y1 + 535}L{hx + 370},{y1 + 535}L{hx + 370},{y1 + 385}L{hx + 395},{y1 + 495}L{hx + 465},{y1 + 480}L{hx + 435},{y1 + 290}L{hx + 350},{y1 + 250}C{hx + 330},{y1 + 215} {hx + 295},{y1 + 190} {hx + 250},{y1 + 190}Z"
    s.append(f'<path d="{hood}" fill="{P["forest"]}" stroke="#0c261d" stroke-width="2"/>')
    s.append(fit("monogram", (hx + 305, y1 + 270, 38, 38), P["gold_lt"], P["terra"]) + fit("symbol", (hx + 175, y1 + 350, 150, 150), P["gold_lt"], P["terra"]))
    t(hx + 12, y1 + 550, "THE COURTYARD hoodie (flat concept)", 12, "#444")
    # menu + website
    mx = 1350
    r(mx, y1 + 150, 990, 410, "#d9d0bd")
    r(mx + 30, y1 + 175, 230, 360, P["forest"]); s.append(crest_at(mx + 85, y1 + 215, 120, P["gold"], P["gold"], P["terra"]) + fit("wordmark-small", (mx + 52, y1 + 360, 186, 42), P["gold_lt"], P["gold"]))
    t(mx + 62, y1 + 440, "THE MENU — CONCEPT", 12, P["gold_lt"], extra='letter-spacing="1.5"'); t(mx + 78, y1 + 466, "not a priced menu", 11, "#B9C6B8")
    r(mx + 290, y1 + 175, 670, 360, P["ivory"], 'stroke="#aaa"')
    r(mx + 290, y1 + 175, 670, 36, "#E4DCC8"); s.append(fit("wordmark-small", (mx + 305, y1 + 184, 90, 20), P["forest"], P["terra"], "l"))
    for i, nm in enumerate(("Beverages", "Kitchen", "Merch", "Story", "Labs")):
        t(mx + 560 + i * 78, y1 + 199, nm, 11, "#555")
    r(mx + 290, y1 + 211, 670, 190, P["forest"]); s.append(fit("wordmark", (mx + 330, y1 + 255, 380, 90), P["ivory"], P["gold"], "l")); s.append(crest_at(mx + 800, y1 + 235, 110, P["gold"], P["gold"], P["terra"]))
    t(mx + 330, y1 + 372, "Concept — nothing is open or for sale.", 14, P["gold_lt"])
    for i, (bg, tx) in enumerate(((P["terra"], "BADSHAH"), (P["saffron"], "AMBA HAZE"), (P["charcoal"], "Kitchen"))):
        r(mx + 310 + i * 215, y1 + 420, 200, 90, bg); t(mx + 322 + i * 215, y1 + 470, tx + " · image pending", 12, P["ivory"] if bg != P["saffron"] else P["charcoal"])
    t(mx + 14, y1 + 550, "Menu cover (left) · website preview (right) — flat concepts; image slots marked pending", 12, "#444")
    t(60, 2310, "Reference: ChatGPT-generated exploratory board (2026-10-22, user-supplied) informed mood and palette only; nothing from it is reused. Not trademark-cleared; not approved.", 12, "#666")
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>', W, H


def main():
    svg, w, h = board()
    (V3 / "identity-board-v3.svg").write_text(svg)
    A.render(svg, V3 / "identity-board-v3.png", w, h)
    print("board ok")


if __name__ == "__main__":
    main()
