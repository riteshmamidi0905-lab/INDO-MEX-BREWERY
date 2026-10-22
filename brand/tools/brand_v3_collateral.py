#!/usr/bin/env python3
"""Brand v3 collateral (PROVISIONAL, flat vector concepts): menu cover + inner page, restaurant signage set, merchandise set.
Rules: original Courtyard wordmark is primary; glass-A G1 appears only on large-format signage (>= 32 px cap height); exact brand-v3 palette; no prices,
no ABV/volume/ingredients/certifications (placeholders); dishes are concept names only (never cooked or tasted); no beef or pork; no halal claim."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand_v3_art as A
import logo_courtyard_v2 as L
import logo_glass_a as G

P = A.PAL
OUT = A.OUTV3 / "collateral"
LK = L.lockups()


def fit(inner, w, h, box, color, acc="#B8923A", align="c"):
    x, y, bw, bh = box
    sc = min(bw / w, bh / h)
    ox = x + ((bw - w * sc) / 2 if align == "c" else 0)
    oy = y + (bh - h * sc) / 2
    return f'<g transform="translate({ox:.1f},{oy:.1f}) scale({sc:.4f})" style="color:{color};--accent:{acc}">{inner}</g>'


def lk(name, *a, **k):
    i, w, h = LK[name]
    return fit(i, w, h, *a, **k)


def crest(x, y, s, c, acc=None):
    return f'<g transform="translate({x},{y}) scale({s / 100})">{A.crest(c, None, c, acc or P["terra_deep"])}</g>'


def T(x, y, t, size=16, fill="#222", fam="Inter", extra=""):
    return f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{fill}" {extra}>{t}</text>'


def ph(x, y, w, h, text, col):
    return A.placeholder(x, y, w, h, text, col, .75, 15)


def menu():
    W, H = 2400, 1500
    s = [f'<rect width="{W}" height="{H}" fill="#EAE3D2"/>', T(60, 62, "Menu design — concept (not a priced or tested menu)", 38, "#141110", "Instrument Serif"),
         T(60, 92, "PROVISIONAL · dishes are concept names that have not been cooked, tasted or costed · no prices · no ABV/ingredients/allergens claimed · no beef or pork", 14, "#555")]
    # cover
    s.append(f'<rect x="60" y="120" width="560" height="1300" fill="{P["forest"]}"/>')
    s.append(crest(210, 260, 260, P["gold"]) + lk("wordmark-small", (130, 620, 420, 110), P["gold_lt"]))
    s.append(T(340, 800, "THE MENU — CONCEPT", 20, P["gold_lt"], extra='text-anchor="middle" letter-spacing="6"'))
    s.append(f'<rect x="240" y="830" width="200" height="2" fill="{P["gold"]}"/>' + T(340, 880, "Brewhouse · Kitchen · Courtyard", 17, "#B9C6B8", extra='text-anchor="middle"'))
    # inner page
    s.append(f'<rect x="680" y="120" width="1660" height="1300" fill="{P["ivory"]}" stroke="#cdbf9c"/>')
    s.append(lk("wordmark-small", (760, 170, 200, 48), P["forest"], P["terra"], "l"))
    cols = [("BREWS", [("BADSHAH", "Hefeweizen — working concept"), ("AMBA HAZE", "Mango-forward juicy IPA — working concept")], "ABV · size · price — TBD"),
            ("KITCHEN", [("Chicken 65 Totopos", "Concept dish — not yet tested"), ("Mango Habanero Gobi", "Concept dish — not yet tested")], "Price — TBD"),
            ("COURTYARD", [("Shared plates", "To be developed"), ("Non-alcoholic options", "To be developed")], "Allergen information — TBD (required before service)")]
    for i, (hd, items, note) in enumerate(cols):
        x = 760 + i * 520
        s.append(T(x, 330, hd, 22, P["terra_deep"], extra='letter-spacing="5" font-weight="600"') + f'<rect x="{x}" y="346" width="440" height="2" fill="{P["gold"]}"/>')
        for j, (n, d) in enumerate(items):
            s.append(T(x, 410 + j * 110, n, 34, P["forest"], "Instrument Serif") + T(x, 442 + j * 110, d, 16, "#4a4540"))
        s.append(ph(x, 650, 440, 74, note, P["forest"]))
    s.append(f'<rect x="760" y="1100" width="1500" height="2" fill="{P["gold"]}"/>' + crest(1470, 1130, 90, P["forest"]) + T(1515, 1262, "Concept — nothing is open or for sale.", 16, "#4a4540", extra='text-anchor="middle"'))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>', W, H


def signage():
    W, H = 2400, 1500
    g1t, gw, gh = G.VARIANTS["glass-G1"](False)
    s = [f'<rect width="{W}" height="{H}" fill="#EAE3D2"/>', T(60, 62, "Restaurant signage set — concept (flat; not engineered, not permitted)", 38, "#141110", "Instrument Serif"),
         T(60, 92, "PROVISIONAL · glass-A G1 only on large-format signage at ≥ 32 px cap height · original wordmark elsewhere · dimensions and materials are placeholders", 14, "#555")]
    # facade sign: G1
    s.append(f'<rect x="60" y="130" width="1500" height="420" fill="{P["charcoal"]}"/><rect x="100" y="170" width="1420" height="340" fill="none" stroke="{P["gold"]}" stroke-width="3"/>')
    s.append(fit(g1t, gw, gh, (260, 250, 1100, 180), P["gold_lt"], P["gold"]) + T(810, 480, "THE COURTYARD", 22, P["gold"], extra='text-anchor="middle" letter-spacing="10"'))
    s.append(T(70, 575, "Facade sign: glass-A G1 alternate (large format), antique gold on charcoal; illuminated-letter build is a placeholder, not specified", 14, "#444"))
    # blade sign
    s.append(f'<rect x="1620" y="130" width="720" height="420" fill="#d9d0bd"/><rect x="1620" y="150" width="720" height="8" fill="{P["charcoal"]}"/><rect x="1900" y="158" width="4" height="60" fill="{P["charcoal"]}"/><rect x="2060" y="158" width="4" height="60" fill="{P["charcoal"]}"/>')
    s.append(f'<rect x="1840" y="218" width="300" height="300" rx="150" fill="{P["forest"]}" stroke="{P["gold"]}" stroke-width="4"/>' + crest(1930, 262, 120, P["gold"]) + lk("wordmark-small", (1910, 400, 160, 38), P["gold_lt"]))
    s.append(T(1630, 575, "Blade sign: crest + original wordmark", 14, "#444"))
    # wayfinding
    labels = [("TAPROOM", P["forest"], P["ivory"]), ("KITCHEN", P["charcoal"], P["gold_lt"]), ("COURTYARD", P["terra_deep"], P["ivory"]), ("RESTROOMS", P["forest"], P["ivory"])]
    for i, (t, bg, fg) in enumerate(labels):
        x = 60 + i * 585
        s.append(f'<rect x="{x}" y="650" width="560" height="170" fill="{bg}"/>' + crest(x + 24, 670, 80, fg, fg) + T(x + 140, 755, t, 40, fg, "Instrument Serif", 'letter-spacing="6"'))
    s.append(T(60, 850, "Wayfinding plates: Instrument Serif caps on palette grounds (ivory on terracotta deep 5.4:1)", 14, "#444"))
    # window decal + entrance door
    s.append(f'<rect x="60" y="900" width="1100" height="480" fill="#c9d3cf"/><path d="M360,1380V1120A190,190 0 0 1 740,1120V1380Z" fill="#9fb5ae" stroke="{P["charcoal"]}" stroke-width="6"/>')
    s.append(crest(470, 1090, 160, "#FFFFFF", "#FFFFFF") + T(80, 1420, "Entrance arch with one-colour white vinyl crest (concept)", 14, "#333"))
    s.append(f'<rect x="1240" y="900" width="1100" height="500" fill="{P["ivory"]}" stroke="#cdbf9c"/>' + lk("stacked", (1500, 960, 580, 380), P["forest"], P["terra"]))
    s.append(T(1250, 1385, "Stacked lockup for door plate / hours panel (hours: TBD)", 14, "#333"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>', W, H


def tee_path(x, y, w, h):
    return (f"M{x + w * .35},{y}C{x + w * .42},{y + h * .07} {x + w * .58},{y + h * .07} {x + w * .65},{y}L{x + w * .98},{y + h * .1}L{x + w * .88},{y + h * .3}L{x + w * .76},{y + h * .24}L{x + w * .76},{y + h}L{x + w * .24},{y + h}L{x + w * .24},{y + h * .24}L{x + w * .12},{y + h * .3}L{x + w * .02},{y + h * .1}Z")


def merch():
    W, H = 2400, 1300
    s = [f'<rect width="{W}" height="{H}" fill="#EAE3D2"/>', T(60, 62, "Merchandise set — concept (never made or sold)", 38, "#141110", "Instrument Serif"),
         T(60, 92, "PROVISIONAL · original marks only (G1 is not approved for apparel) · no prices · no sizes or fabric specifications claimed", 14, "#555")]
    items = [("THE COURTYARD hoodie — front", P["forest"], "front"), ("THE COURTYARD hoodie — back", P["forest"], "back"), ("Tee 1 — crest", P["ivory"], "crest"), ("Tee 2 — symbol", P["charcoal"], "symbol"), ("Tee 3 — wordmark", P["terra_deep"], "word")]
    for i, (nm, col, kind) in enumerate(items):
        x = 60 + i * 465
        s.append(f'<rect x="{x}" y="130" width="440" height="560" fill="#d9d0bd"/>')
        if kind in ("front", "back"):
            hx, hy = x + 20, 160
            hood = f"M{hx + 200},{hy}C{hx + 160},{hy} {hx + 135},{hy + 20} {hx + 120},{hy + 50}L{hx + 40},{hy + 85}L{hx + 12},{hy + 330}L{hx + 75},{hy + 340}L{hx + 100},{hy + 170}L{hx + 100},{hy + 480}L{hx + 300},{hy + 480}L{hx + 300},{hy + 170}L{hx + 325},{hy + 340}L{hx + 388},{hy + 330}L{hx + 360},{hy + 85}L{hx + 280},{hy + 50}C{hx + 265},{hy + 20} {hx + 240},{hy} {hx + 200},{hy}Z"
            s.append(f'<path d="{hood}" fill="{col}" stroke="#0c261d" stroke-width="2"/>')
            if kind == "front":
                s.append(lk("monogram", (hx + 250, hy + 120, 34, 34), P["gold_lt"], P["terra"]) + lk("symbol", (hx + 130, hy + 210, 140, 150), P["gold_lt"], P["terra"]))
            else:
                s.append(lk("wordmark", (hx + 120, hy + 150, 160, 40), P["gold_lt"], P["gold"]) + crest(hx + 160, hy + 215, 80, P["gold_lt"], P["gold_lt"]) + f'<rect x="{hx + 120}" y="{hy + 330}" width="160" height="2" fill="{P["gold"]}"/>')
        else:
            ink = {"crest": P["forest"], "symbol": P["gold_lt"], "word": P["ivory"]}[kind]
            s.append(f'<path d="{tee_path(x + 40, 170, 360, 500)}" fill="{col}" stroke="#777" stroke-width="1.5"/>')
            if kind == "crest":
                s.append(crest(x + 150, 260, 140, ink, P["terra_deep"]))
            elif kind == "symbol":
                s.append(lk("symbol", (x + 150, 270, 140, 150), ink, P["terra"]))
            else:
                s.append(lk("wordmark", (x + 135, 345, 170, 42), ink, P["gold_lt"]))
        s.append(T(x, 720, nm, 15, "#333"))
    s.append(T(60, 790, "Placement notes: hoodie front = symbol centre chest + monogram left chest; back = wordmark + crest below the neck; tees are single-position prints. Ink colours stay inside the brand-v3 palette.", 14, "#555"))
    s.append(T(60, 830, "Botanical pattern (Direction B language) may be used for lining, tape and tags — never as a replacement for the NASHA marks.", 14, "#555"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>', W, H


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("menu-concept", menu), ("signage-set", signage), ("merchandise-set", merch)):
        svg, w, h = fn()
        (OUT / f"{name}.svg").write_text(svg)
        A.render(svg, OUT / f"{name}.png", w, h)
    print(sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
