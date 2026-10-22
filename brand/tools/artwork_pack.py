#!/usr/bin/env python3
"""Transparent-PNG + SVG artwork pack for compositing onto approved source plates (all from verified vector masters; nothing model-drawn).
Large-format glass-A G1 pieces respect the 32 px cap-height minimum: the pack renders them at >= 400 px wide (cap height >= 80 px)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand_v3_art as A
import logo_courtyard_v2 as L
import logo_glass_a as G

OUT = A.OUTV3 / "artwork"
P = A.PAL


def piece(name, inner, w, h, color, accent, px_w, pad=6):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}" width="{px_w}" height="{round(px_w * (h + 2 * pad) / (w + 2 * pad))}" '
           f'style="color:{color};--accent:{accent}" role="img" aria-label="NASHA artwork (concept)">{inner}</svg>')
    (OUT / f"{name}.svg").write_text(svg)
    A.render(svg, OUT / f"{name}.png", px_w, round(px_w * (h + 2 * pad) / (w + 2 * pad)), transparent=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    g1t, w, h = G.VARIANTS["glass-G1"](False)
    g1s, ws, hs = G.VARIANTS["glass-G1"](True)
    orig, wo, ho = L.wordmark()
    sy, sw, sh = L.symbol()
    mo, mw, mh = L.monogram()
    crest = f'<g transform="scale(1)">{A.crest("currentColor", None, "currentColor", P["terra"])}</g>'
    # glassware etch/print: one colour, white (printed ink on glass), G1 alternate at large size + crest
    piece("glass-etch-g1-white", g1s, ws, hs, "#FFFFFF", "#FFFFFF", 600)
    piece("glass-etch-crest-white", crest, 100, 100, "#FFFFFF", "#FFFFFF", 500)
    # architectural sign: G1 text cut in antique gold / light gold on a dark board; original wordmark for secondary signs
    piece("sign-g1-gold", g1t, w, h, P["gold_lt"], P["gold"], 1600)
    piece("sign-original-gold", orig, wo, ho, P["gold_lt"], P["gold"], 1600)
    piece("sign-crest-gold", crest, 100, 100, P["gold"], P["gold"], 600)
    # hoodie print: gold symbol + monogram + crest (original marks; G1 is not used on apparel)
    piece("hoodie-symbol-gold", sy, sw, sh, P["gold_lt"], P["terra"], 900)
    piece("hoodie-monogram-gold", mo, mw, mh, P["gold_lt"], P["terra"], 400)
    piece("hoodie-crest-gold", crest, 100, 100, P["gold_lt"], P["gold_lt"], 600)
    print(sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
