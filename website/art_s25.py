"""Sprint 25 vision illustrations (original vector art). VISION layer: concept drawings of what NASHA could become.
None is a construction drawing, a photograph or a dimensioned design. Text inside the SVGs is kept to numbers so it stays legible on a phone."""
import math
from art import PAL, _svg

P = PAL


def court_plan(uid="cp"):
    """Top-down VISION FLAGSHIP plan. Numbered beats 1-7 follow the arrival story. Not to scale."""
    z = []
    z.append('<rect width="960" height="600" fill="#1d1815"/>')
    z.append('<rect x="0" y="520" width="960" height="80" fill="#2a2420"/>')
    z.append('<rect x="700" y="90" width="260" height="430" fill="#31402a"/>')
    for (x, y, r) in [(760, 170, 52), (850, 290, 62), (780, 420, 48), (905, 150, 36)]:
        z.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#233019"/><circle cx="{x}" cy="{y}" r="{r*.55:.0f}" fill="#2f4222"/>')
    z.append(f'<rect x="290" y="40" width="640" height="130" fill="{P["limestone"]}"/>')
    z.append('<rect x="290" y="40" width="190" height="130" fill="#d6c9ae"/>')
    z.append('<rect x="480" y="40" width="150" height="130" fill="#b9714a"/>')
    z.append('<rect x="630" y="40" width="300" height="130" fill="#d6c9ae"/>')
    z.append('<rect x="300" y="60" width="14" height="90" fill="#3a2a1f"/>')
    z.append(f'<rect x="40" y="170" width="250" height="350" fill="{P["limestone"]}"/>')
    z.append('<rect x="274" y="190" width="10" height="300" fill="#8fb4c6" opacity=".8"/><rect x="40" y="504" width="250" height="10" fill="#8fb4c6" opacity=".8"/>')
    for (x, y) in [(95, 460), (95, 360), (150, 266), (225, 266), (230, 360), (230, 460)]:
        z.append(f'<circle cx="{x}" cy="{y}" r="30" fill="{P["stainless"]}"/><circle cx="{x}" cy="{y}" r="30" fill="none" stroke="{P["marigold"]}" stroke-width="5"/><circle cx="{x}" cy="{y}" r="9" fill="#8d9291"/>')
    z.append('<rect x="120" y="176" width="140" height="30" fill="#8a8f90"/>')
    z.append('<rect x="290" y="170" width="410" height="50" fill="#5a4a3c" opacity=".55"/>')
    z.append('<rect x="290" y="470" width="410" height="50" fill="#5a4a3c" opacity=".55"/>')
    z.append('<rect x="290" y="220" width="40" height="250" fill="#5a4a3c" opacity=".55"/>')
    z.append('<rect x="330" y="220" width="370" height="250" fill="#a89a82"/>')
    z.append('<rect x="330" y="338" width="370" height="16" rx="8" fill="#5e8da3"/>')
    for y in (262, 410):
        z.append(f'<rect x="400" y="{y}" width="190" height="26" fill="#3a2a1f"/>')
    z.append('<rect x="40" y="40" width="230" height="110" fill="#2e2824"/>')
    z.append(f'<rect x="290" y="520" width="56" height="30" fill="{P["marigold"]}" opacity=".9"/>')
    z.append('<rect x="40" y="520" width="250" height="26" fill="#d6c9ae" opacity=".55"/>')
    pts = [(318, 574), (318, 535), (200, 533), (352, 400), (262, 312), (380, 110), (560, 306)]
    for i, (x, y) in enumerate(pts, 1):
        z.append(f'<circle cx="{x}" cy="{y}" r="22" fill="{P["marigold"]}"/><text x="{x}" y="{y+9}" text-anchor="middle" font-family="Inter,sans-serif" font-weight="700" font-size="26" fill="#141110">{i}</text>')
    return _svg("0 0 960 600", uid, "Vision flagship plan: the Court Brewhouse",
                "A top-down vision plan, not to scale and not a construction drawing. A limestone tank hall with six tanks at the west, a restaurant block on the north, arcades on three sides, a gravel court with a stone rill and long tables, and an oak lawn on the east. Seven numbered points follow the route from the street to the patio at night.",
                "".join(z), "plan-art")


def scene(mode, uid):
    """Small hall-and-court scene for day / golden hour / night / rain."""
    sky = {"day": ("#9CC3D9", "#D7E7EE"), "golden": ("#F2B26B", "#F7D9A8"), "night": ("#12162B", "#2B3563"), "rain": ("#6F7C86", "#9AA5AC")}[mode]
    glow = mode in ("night", "golden", "rain")
    b = []
    b.append(f'<defs><linearGradient id="{uid}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[0]}"/><stop offset="1" stop-color="{sky[1]}"/></linearGradient></defs>')
    b.append(f'<rect width="400" height="300" fill="url(#{uid}s)"/>')
    if mode == "night":
        for (x, y) in [(40, 30), (120, 55), (300, 25), (350, 70), (210, 40)]:
            b.append(f'<circle cx="{x}" cy="{y}" r="1.6" fill="#fff" opacity=".7"/>')
    if mode == "golden":
        b.append('<circle cx="330" cy="70" r="34" fill="#FBE3AE" opacity=".9"/>')
    oak = "#1F2B1B" if mode == "night" else "#3F5A2E"
    b.append(f'<circle cx="345" cy="190" r="48" fill="{oak}"/><circle cx="310" cy="205" r="34" fill="{oak}"/><rect x="338" y="200" width="10" height="70" fill="#3a2a1f"/>')
    stone = "#6c6458" if mode == "night" else "#E4DAC6"
    b.append(f'<rect x="20" y="70" width="170" height="190" fill="{stone}"/>')
    gl = "#E8A64B" if mode in ("night", "golden") else ("#E9B968" if mode == "rain" else "#7FA7BD")
    b.append(f'<rect x="38" y="100" width="134" height="150" fill="{gl}" opacity="{.95 if mode in ("night","golden") else .8}"/>')
    for x in (62, 105, 148):
        b.append(f'<rect x="{x-12}" y="120" width="24" height="108" rx="12" fill="{P["stainless"]}"/><rect x="{x-12}" y="168" width="24" height="7" fill="{P["marigold"]}"/>')
    b.append(f'<rect x="190" y="150" width="130" height="14" fill="#4a3c30"/><rect x="190" y="164" width="130" height="96" fill="{"#262019" if mode=="night" else "#8c7c64"}" opacity=".9"/>')
    b.append(f'<rect x="190" y="260" width="210" height="40" fill="{"#3a342e" if mode=="night" else "#a89a82"}"/>')
    if mode == "rain":
        b.append('<rect x="190" y="260" width="210" height="40" fill="#4c5a63"/>')
        for i in range(34):
            x = (i * 37) % 400
            y = (i * 53) % 280
            b.append(f'<line x1="{x}" y1="{y}" x2="{x-5}" y2="{y+16}" stroke="#E6EEF2" stroke-opacity=".6" stroke-width="1.3"/>')
    if glow:
        b.append('<circle cx="230" cy="200" r="10" fill="#FF9A3C" opacity=".9"/><circle cx="230" cy="200" r="22" fill="#FF9A3C" opacity=".25"/>')
    b.append('<rect x="215" y="272" width="90" height="10" fill="#3a2a1f"/>')
    names = {"day": "Day", "golden": "Golden hour", "night": "Night", "rain": "Rain"}
    return _svg("0 0 400 300", uid, f"Vision scene: {names[mode].lower()} at the Court Brewhouse",
                f"A simple drawing of the stone and glass tank hall, the shaded arcade, the court and an oak in {names[mode].lower()} light. A concept drawing, not a photograph.", "".join(b), "scene-art")


def aromatic_glass(uid, beer="vienna-amber"):
    from art import BEER
    liquid, foam, haze = BEER.get(beer, BEER["vienna-amber"])
    body = (f'<ellipse cx="60" cy="272" rx="40" ry="6" fill="#000" opacity=".35"/><rect x="56" y="196" width="8" height="64" fill="#fff" opacity=".55"/>'
            f'<path d="M30 40 Q22 120 46 190 Q60 204 74 190 Q98 120 90 40 Z" fill="{liquid}" stroke="#fff" stroke-opacity=".75" stroke-width="2.2"/>'
            f'<path d="M30 40 Q60 24 90 40 Q92 58 88 64 Q60 76 32 64 Q28 56 30 40Z" fill="{foam}"/>'
            f'<ellipse cx="60" cy="258" rx="28" ry="5" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="2.2"/>')
    return _svg("0 0 120 284", uid, "Concept aromatic glass", "A short stemmed tulip glass for amber beer or witbier, drawn as a concept. Not a manufactured glass.", body, "glass-art")


def na_glass(uid, color, garnish="lime"):
    g = {"lime": '<circle cx="82" cy="60" r="14" fill="#8DB04A"/><circle cx="82" cy="60" r="9" fill="#C9DC8A"/>',
         "herb": '<path d="M70 70 Q58 24 84 20 Q92 48 70 70Z" fill="#6E8E3A"/>',
         "peel": '<path d="M30 56 Q50 38 78 62" fill="none" stroke="#F0B13A" stroke-width="5" stroke-linecap="round"/>',
         "none": ""}[garnish]
    body = (f'<ellipse cx="60" cy="272" rx="40" ry="6" fill="#000" opacity=".35"/>'
            f'<path d="M30 60 L40 236 Q42 262 60 262 Q78 262 80 236 L90 60 Z" fill="{color}" fill-opacity=".92"/>'
            f'<path d="M30 60 L40 236 Q42 262 60 262 Q78 262 80 236 L90 60 Z" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="2.2"/>'
            f'<path d="M36 84 Q60 92 84 84" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="2"/>'
            + "".join(f'<circle cx="{46+(i*11)%30}" cy="{210-i*17}" r="{1.4+(i%2)}" fill="#fff" opacity=".6"/>' for i in range(8)) + g)
    return _svg("0 0 120 284", uid, "Concept zero-proof glass", "A clear tumbler of a zero-proof drink in a natural colour with one simple garnish, drawn as a concept. Not a tested recipe.", body, "glass-art")


def table_top(uid="tt"):
    """Top-down table system. Numbers match the list beside it."""
    b = [f'<rect width="640" height="460" fill="#3a2a1f"/><rect x="0" y="228" width="640" height="3" fill="{P["stainless"]}" opacity=".5"/>']
    b.append('<circle cx="230" cy="230" r="120" fill="#0b0a09"/><circle cx="230" cy="230" r="108" fill="#241E1B"/><circle cx="230" cy="230" r="86" fill="#E4D5B5"/>')
    b.append('<circle cx="215" cy="222" r="26" fill="#C8512A"/><circle cx="252" cy="240" r="22" fill="#C8512A"/><circle cx="228" cy="258" r="20" fill="#D4852E"/>')
    b.append('<circle cx="470" cy="120" r="70" fill="#B58A52"/>' + "".join(f'<circle cx="470" cy="120" r="{r}" fill="none" stroke="#8d6a3c" stroke-width="3"/>' for r in (62, 50, 38, 26)) + '<circle cx="470" cy="120" r="22" fill="#E6C98B"/>')
    b.append(f'<circle cx="360" cy="360" r="30" fill="{P["stainless"]}"/><circle cx="360" cy="360" r="22" fill="#9a2b1e"/>')
    b.append(f'<g transform="rotate(-12 80 380)"><rect x="20" y="340" width="130" height="80" fill="#EFE6D2"/><rect x="20" y="340" width="130" height="30" fill="#1A2142"/><rect x="20" y="376" width="130" height="5" fill="{P["bone"]}"/></g>')
    b.append('<circle cx="520" cy="300" r="32" fill="#F0C25A" opacity=".9"/><circle cx="520" cy="300" r="32" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="3"/>')
    b.append('<circle cx="580" cy="370" r="28" fill="#D45A5A" opacity=".85"/><circle cx="580" cy="370" r="28" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="3"/>')
    b.append('<circle cx="440" cy="400" r="26" fill="#DCE9EE" opacity=".6"/><circle cx="440" cy="400" r="26" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="3"/>')
    b.append(f'<rect x="395" y="262" width="26" height="50" rx="8" fill="{P["stainless"]}"/>')
    pts = [(230, 120), (470, 40), (360, 318), (80, 330), (520, 258), (585, 328), (440, 360), (408, 236)]
    for i, (x, y) in enumerate(pts, 1):
        b.append(f'<circle cx="{x}" cy="{y}" r="17" fill="{P["marigold"]}"/><text x="{x}" y="{y+7}" text-anchor="middle" font-family="Inter,sans-serif" font-weight="700" font-size="20" fill="#141110">{i}</text>')
    return _svg("0 0 640 460", uid, "Vision table system, seen from above",
                "A top-down drawing of one place setting: a black stoneware plate, a woven basket, a steel sauce cup, an indigo and bone napkin, a beer glass, a zero-proof glass, a water glass and a small condiment cruet. A concept, not final tableware.", "".join(b), "table-art")


def pattern_set(uid="pt"):
    """Three structural swatches: perforation, weave, tile; one grammar."""
    def swatch(x, body):
        return f'<g transform="translate({x} 0)"><rect width="260" height="260" fill="{P["char"]}"/>{body}</g>'
    perf = ""
    for r in range(8):
        for c in range(8):
            ox = 16 + c * 32 + (16 if r % 2 else 0)
            rad = (3, 6, 9)[(r + c) % 3]
            perf += f'<circle cx="{ox}" cy="{20 + r*32}" r="{rad}" fill="{P["bone"]}" opacity=".85"/>'
    weave = ""
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 0:
                weave += f'<rect x="{10 + c*30}" y="{14 + r*30}" width="28" height="12" rx="2" fill="{P["bone"]}" opacity=".85"/>'
            else:
                weave += f'<rect x="{10 + c*30}" y="{14 + r*30}" width="12" height="28" rx="2" fill="{P["marigold"]}" opacity=".85"/>'
    tile = ""
    for r in range(6):
        for c in range(6):
            tile += f'<rect x="{12 + c*40}" y="{12 + r*40}" width="36" height="36" fill="none" stroke="{P["bone"]}" stroke-opacity=".75" stroke-width="2"/>'
    for c in range(6):
        if c != 2:
            tile += f'<rect x="{12 + c*40}" y="{12 + 2*40 + 16}" width="36" height="6" fill="{P["marigold"]}"/>'
    body = swatch(0, perf) + swatch(280, weave) + swatch(560, tile)
    return _svg("0 0 820 260", uid, "Vision pattern grammar: perforation, weave, tile",
                "Three swatches that share one grammar: a perforation of circles in three sizes on an offset grid, a weave of over and under strips, and a square tile grid with a broken marigold stripe. A concept; no sacred or protected motif is copied.", body, "pattern-art")


def signage(uid="sg"):
    b = ['<rect width="900" height="320" fill="#2a2420"/>']
    b.append(f'<rect x="40" y="60" width="170" height="210" fill="#8b8579"/><rect x="60" y="80" width="130" height="140" fill="#141110"/><rect x="100" y="140" width="50" height="6" fill="{P["bone"]}" opacity=".8"/>')
    b.append(f'<rect x="300" y="40" width="200" height="8" fill="#141110"/><rect x="330" y="48" width="4" height="36" fill="#141110"/><rect x="466" y="48" width="4" height="36" fill="#141110"/><rect x="310" y="84" width="180" height="90" rx="3" fill="#141110"/><rect x="360" y="124" width="80" height="6" fill="{P["bone"]}" opacity=".8"/>')
    b.append('<rect x="590" y="40" width="270" height="250" fill="#5a3f22"/><rect x="610" y="60" width="110" height="210" fill="#8fb4c6" opacity=".5"/><rect x="740" y="60" width="100" height="210" fill="#8fb4c6" opacity=".5"/><rect x="760" y="140" width="60" height="30" rx="3" fill="#141110"/>')
    return _svg("0 0 900 320", uid, "Vision signage system",
                "Three signage positions drawn as plain blackened-steel shapes: a panel on a plinth, a blade sign under the arcade and a small door plaque. The lettering is a placeholder; the name is not cleared and no logo exists.", "".join(b), "sign-art")


def uniforms(uid="un"):
    def apron(x, shirt, ap, trim):
        return (f'<g transform="translate({x} 0)"><rect x="40" y="20" width="120" height="150" rx="10" fill="{shirt}"/><rect x="62" y="70" width="76" height="140" rx="6" fill="{ap}"/>'
                f'<rect x="82" y="20" width="36" height="52" fill="{ap}"/><rect x="62" y="196" width="76" height="6" fill="{trim}"/></g>')
    body = ('<rect width="860" height="240" fill="#8a8478"/>' + apron(0, "#E8E0CE", "#3a3a3c", "#C9C0AE") + apron(215, "#E8E0CE", "#3a3a3c", "#C9C0AE") +
            apron(430, "#1b1b1c", "#2a2a2c", "#555") + apron(645, "#2b2b2d", "#d8d8d8", "#888"))
    return _svg("0 0 860 240", uid, "Vision uniform concepts", "Four simple garment drawings: floor, bar, brewery and kitchen. Charcoal canvas aprons over bone shirts with a small marigold stitch; black work shirts for the brewery; dark jackets for the kitchen. Concept only.", body, "uniform-art")


def packaging(uid="pk"):
    b = ['<rect width="860" height="260" fill="#241E1B"/>']
    b.append(f'<circle cx="120" cy="130" r="86" fill="{P["bone"]}"/>' + "".join(f'<circle cx="{120+int(46*math.cos(a*math.pi/6))}" cy="{130+int(46*math.sin(a*math.pi/6))}" r="{(4,6,8)[a%3]}" fill="#241E1B"/>' for a in range(12)) + f'<circle cx="120" cy="130" r="10" fill="{P["indigo"]}"/>')
    b.append(f'<rect x="270" y="60" width="130" height="170" fill="#E4D5B5"/><rect x="270" y="60" width="130" height="24" fill="#D4C4A0"/><rect x="270" y="130" width="130" height="8" fill="{P["indigo"]}"/><path d="M310 60 Q335 20 360 60" fill="none" stroke="#8b6a3c" stroke-width="5"/>')
    b.append(f'<path d="M460 100 L600 100 L620 230 L440 230 Z" fill="#E4D5B5"/><rect x="458" y="86" width="144" height="22" fill="#D4C4A0"/><rect x="450" y="150" width="160" height="26" fill="#1A2142"/><rect x="450" y="180" width="160" height="5" fill="{P["bone"]}"/>')
    b.append(f'<g transform="rotate(-8 740 140)"><rect x="680" y="90" width="130" height="100" fill="#EFE6D2"/><rect x="680" y="90" width="130" height="34" fill="#1A2142"/><rect x="680" y="128" width="130" height="5" fill="{P["bone"]}"/></g>')
    return _svg("0 0 860 260", uid, "Vision packaging concepts", "Drawings of a perforated coaster, a paper bag with a marigold stripe, a takeout box with an indigo band and an indigo and bone napkin. Placeholder only: no label, no logo and no regulatory claim.", "".join(b), "pack-art")
