"""Original vector art for the NASHA site (no raster, no third-party assets). Every function returns an inline <svg> string.
These are concept illustrations and stand-ins for photographs that do not exist yet; they never depict a real dish, beer or place."""
import math

PAL = dict(soot="#141110", char="#241E1B", bone="#F3ECDD", marigold="#E8870E", limestone="#E4DAC6", stainless="#C9CCCB",
           smoke="#9A9087", copper="#C47A45", indigo="#1A2142", dusk="#2B3563", herb="#7D9A45", hibiscus="#9B2447",
           tamarind="#5A3A25", straw="#E9C46A", clay="#B5651D", brass="#C9A24B")

# (liquid, head colour, haze 0-1). Head height per style is in HEAD below. Colours follow style references in visuals/NASHA-FOOD-BEER-REFERENCE-LIBRARY.md.
# Working-name pilot ideas have no settled style, so they use a neutral "ghost" colour instead of an invented one.
BEER = {"hefeweizen": ("#F0C25A", "#FBF6EA", .22), "mexican-lager": ("#F6D56B", "#FFFDF4", 0), "vienna-amber": ("#C4691A", "#F2E6D0", 0),
        "pilsner": ("#F7DC7E", "#FFFFFF", 0), "witbier": ("#F3DFA0", "#FFFDF4", .38), "dunkelweizen": ("#8A4A1C", "#D9BE96", .18),
        "deccan-sol": ("#8f867d", "#b4aca2", 0), "goa-baja": ("#8f867d", "#b4aca2", 0), "malabar-dark": ("#8f867d", "#b4aca2", 0)} 
# Head height (px) per style, from the style descriptions: hefeweizen very thick and moussy, wit dense, dunkel thick and creamy, lagers medium
HEAD = {"hefeweizen": 34, "witbier": 30, "dunkelweizen": 30, "vienna-amber": 26, "mexican-lager": 22, "pilsner": 24}

def _svg(vb, label_id, title, desc, body, cls="", extra=""):
    return (f'<svg class="art {cls}" viewBox="{vb}" role="img" aria-labelledby="{label_id}-t {label_id}-d" xmlns="http://www.w3.org/2000/svg" {extra}>'
            f'<title id="{label_id}-t">{title}</title><desc id="{label_id}-d">{desc}</desc>{body}</svg>')

def glass(uid, beer="hefeweizen", fill=0.86, kind="weizen", animate=True, title=None, big=False):
    liquid, foam, haze = BEER.get(beer, BEER["hefeweizen"]); ghost = beer in ("deccan-sol", "goa-baja", "malabar-dark")
    if kind == "weizen":
        outline = "M30 14 C22 60 18 140 36 238 Q40 262 60 262 Q80 262 84 238 C102 140 98 60 90 14 Z"
        top, bottom = 14, 262
    elif kind == "pilsner":
        outline = "M33 14 L45 238 Q47 262 60 262 Q73 262 75 238 L87 14 Z"
        top, bottom = 14, 262
    else:
        outline = "M26 14 L40 238 Q42 262 60 262 Q78 262 80 238 L94 14 Z"
        top, bottom = 14, 262
    liq_top = bottom - (bottom - top - 26) * fill
    hh = HEAD.get(beer, 24)
    bubbles = "".join(f'<circle class="bub b{i}" cx="{48+ (i*9)%26}" cy="{235-i*8}" r="{1.2+(i%3)*.5}" fill="#fff" opacity=".55"/>' for i in range(9)) if animate else ""
    cond = "".join(f'<circle cx="{34+(i*17)%52}" cy="{70+(i*29)%150}" r="1.4" fill="#fff" opacity=".35"/>' for i in range(11))
    t = title or f"Concept glass of {beer.replace('-', ' ')}"
    if ghost:  # working-name beers: no style, no liquid, no foam, no bubbles: one generic outline glass
        outline = "M26 14 L40 238 Q42 262 60 262 Q78 262 80 238 L94 14 Z"
        body = (f'<ellipse cx="60" cy="272" rx="46" ry="6" fill="#000" opacity=".25"/><path d="{outline}" fill="none" stroke="#9A9087" stroke-opacity=".8" stroke-width="2.2" stroke-dasharray="6 5"/>'
                f'<path d="M34 214 Q60 222 86 214" fill="none" stroke="#9A9087" stroke-opacity=".8" stroke-width="3" stroke-dasharray="6 5"/>')
        return _svg("0 0 120 284", uid, t, "A faint dashed outline of a generic collar glass. The beer is a working name with no settled style, so no liquid is drawn.", body, "glass-art" + (" big" if big else ""))
    body = (f'<defs><clipPath id="{uid}c"><path d="{outline}"/></clipPath>'
            f'<linearGradient id="{uid}g" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".3" stop-color="#fff" stop-opacity="0"/><stop offset=".85" stop-color="#000" stop-opacity=".18"/></linearGradient>'
            f'<linearGradient id="{uid}l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{liquid}"/><stop offset="1" stop-color="{liquid}" stop-opacity=".82"/></linearGradient></defs>'
            f'<ellipse cx="60" cy="272" rx="46" ry="6" fill="#000" opacity=".35"/>'
            f'<g clip-path="url(#{uid}c)" opacity="{0.45 if ghost else 1}"><rect class="liq" x="0" y="{liq_top:.1f}" width="120" height="{bottom-liq_top+4:.1f}" fill="url(#{uid}l)"/>'
            f'<path class="foam" d="M0 {liq_top-hh:.1f} Q30 {liq_top-hh-10:.1f} 60 {liq_top-hh-2:.1f} T120 {liq_top-hh:.1f} V{liq_top+2:.1f} H0Z" fill="{foam}"/>'
            f'<rect x="0" y="{liq_top:.1f}" width="120" height="{bottom-liq_top+4:.1f}" fill="#fff" opacity="{haze}"/>{bubbles}{cond}<rect x="0" y="0" width="120" height="280" fill="url(#{uid}g)"/></g>'
            f'<path d="{outline}" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="2.2"/>'
            f'<path d="M34 {bottom-48} Q60 {bottom-40} 86 {bottom-48}" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="3.5"/>')  # collar ring
    return _svg("0 0 120 284", uid, t, "A tall beer glass with a raised ring (collar) near the base, drawn as a concept illustration. Not a dimensioned drawing and not a manufactured glass.", body, "glass-art" + (" big" if big else ""))

def plate(uid, kind):
    ink = PAL
    base = (f'<circle cx="200" cy="200" r="188" fill="#0b0a09"/><circle cx="200" cy="200" r="176" fill="#241E1B"/><circle cx="200" cy="200" r="150" fill="{ink["bone"]}"/>'
            f'<circle cx="200" cy="200" r="150" fill="none" stroke="#d8cdb6" stroke-width="2"/>')
    if kind == "totopos":
        # INTEGRATED: thick irregular totopos in a loose open layer with Chicken 65 pieces distributed through them
        import random
        rnd = random.Random(65)
        parts = ""
        for i in range(13):
            a = i * 29 + rnd.randint(-8, 8); r = 30 + (i % 4) * 26
            x, y = 200 + r * math.cos(math.radians(a)), 200 + r * math.sin(math.radians(a))
            sc = rnd.uniform(.85, 1.15)
            parts += f'<polygon points="0,-33 31,25 -29,28" transform="translate({x:.0f} {y:.0f}) rotate({a+rnd.randint(0,60)}) scale({sc:.2f})" fill="#DDA84B" stroke="#A8731F" stroke-width="3" stroke-linejoin="round"/>'
        chick = ""
        for i, (x, y) in enumerate([(165, 175), (225, 165), (200, 215), (150, 240), (245, 235), (190, 140), (215, 265)]):
            chick += (f'<g transform="translate({x} {y}) rotate({i*47})"><rect x="-17" y="-12" width="34" height="24" rx="9" fill="#B5361C"/><rect x="-17" y="-12" width="34" height="24" rx="9" fill="none" stroke="#7a1e0c" stroke-width="2"/>'
                      f'<path d="M-9 -4 q6 -5 12 0 M-3 5 q6 -4 12 0" stroke="#E8870E" stroke-width="2.5" fill="none" opacity=".8"/></g>')
        leaves = "".join(f'<ellipse cx="{x}" cy="{y}" rx="9" ry="3.6" transform="rotate({r} {x} {y})" fill="{ink["herb"]}"/>' for x, y, r in [(180, 190, 30), (232, 200, 120), (205, 245, 60), (160, 215, 150)])
        chiles = "".join(f'<circle cx="{x}" cy="{y}" r="4.5" fill="#6B8F2C" stroke="#E4EDB0" stroke-width="1.5"/>' for x, y in [(210, 185), (170, 255), (240, 215), (195, 160)])
        food = parts + chick + leaves + chiles + f'<circle cx="300" cy="300" r="26" fill="#C9CCCB"/><circle cx="300" cy="300" r="20" fill="#F3ECDD"/><path d="M285 297 q15 -8 30 0" stroke="#fff" stroke-width="3" fill="none"/><path d="M318 262 a22 22 0 0 1 28 24 l-26 -8 z" fill="{ink["herb"]}" opacity=".9"/>'
    elif kind in ("taco", "taco2"):
        def tac(cx, cy, rot, filling):
            if filling == "paneer":
                inner = "".join(f'<rect x="{-52+i*26}" y="{-14-(i%2)*6}" width="22" height="20" rx="3" fill="#F1E3BE" stroke="#B5651D" stroke-width="3" transform="rotate({(i*17)%25-10} {-41+i*26} -4)"/>' for i in range(5))
                inner += '<path d="M-48 -26 q10 -8 20 0 M0 -30 q10 -8 20 0" stroke="#9B2447" stroke-width="3" fill="none"/>'
            else:
                inner = "".join(f'<g transform="translate({-50+i*25} {-10-(i%2)*8})"><circle r="11" fill="#D9A25A"/><circle cx="-6" cy="-5" r="6" fill="#C98A3E"/><circle cx="6" cy="-4" r="6" fill="#E3B46E"/><circle cx="0" cy="3" r="5" fill="#8a3a1c" opacity=".6"/></g>' for i in range(5))
                inner += '<path d="M-52 4 q20 -14 40 0 q20 -12 40 0 q20 -12 40 0" stroke="#D8E39A" stroke-width="4" fill="none"/>'
            return (f'<g transform="translate({cx} {cy}) rotate({rot})"><path d="M-80 12 A80 80 0 0 1 80 12 Z" fill="#E4C98D" stroke="#C9A25E" stroke-width="3"/>'
                    f'<path d="M-62 8 Q-40 -34 0 -34 Q40 -34 62 8" fill="#00000010"/>{inner}'
                    f'<circle cx="-24" cy="-30" r="4" fill="{ink["herb"]}"/><circle cx="30" cy="-32" r="4" fill="{ink["herb"]}"/></g>')
        fl = "paneer" if kind == "taco2" else "gobi"
        food = tac(200, 165, -6, fl) + tac(200, 262, 5, fl) + f'<path d="M300 300 a26 26 0 0 1 36 -26 l-22 38 z" fill="{ink["herb"]}"/><path d="M304 298 a20 20 0 0 1 26 -20" fill="none" stroke="#D8E39A" stroke-width="3"/>'
    elif kind == "florets":
        food = f'<circle cx="200" cy="205" r="92" fill="#F3ECDD" stroke="#C9CCCB" stroke-width="5"/>'
        for i, (x, y, r) in enumerate([(165, 180, 0), (215, 168, 40), (240, 215, 80), (190, 232, 20), (152, 228, 60), (205, 205, 100)]):
            food += (f'<g transform="translate({x} {y}) rotate({r})"><circle r="19" fill="#F2E4C3" stroke="#D9A25A" stroke-width="3"/><circle cx="-9" cy="-6" r="11" fill="#F6EBCF"/><circle cx="9" cy="-5" r="11" fill="#F1DFB4"/>'
                     f'<path d="M-14 -4 q8 -10 18 -2 M2 -12 q9 -4 14 6" stroke="#E8870E" stroke-width="5" fill="none" stroke-linecap="round"/></g>')
        food += f'<circle cx="300" cy="300" r="22" fill="#E8870E"/><circle cx="300" cy="300" r="12" fill="#F3B63E"/><ellipse cx="190" cy="140" rx="9" ry="3.6" fill="{ink["herb"]}"/>'
    elif kind == "quesadilla":
        food = ""
        for i in range(4):
            a = i * 90 + 20
            food += f'<path d="M0 0 L-70 -4 A70 70 0 0 1 0 -70 Z" transform="translate(205 205) rotate({a})" fill="#D99A3C" stroke="#7a4a14" stroke-width="3"/>'
            food += f'<path d="M-50 -10 h30 M-40 -30 h36" transform="translate(205 205) rotate({a})" stroke="#5a3010" stroke-width="3" opacity=".6"/>'
        food += f'<rect x="196" y="196" width="18" height="18" fill="{ink["herb"]}"/><circle cx="318" cy="300" r="20" fill="{ink["herb"]}"/><circle cx="318" cy="300" r="10" fill="#E8870E"/>'
    elif kind == "birria":
        def bt(cx, cy, rot):
            return (f'<g transform="translate({cx} {cy}) rotate({rot})"><path d="M-70 10 A70 70 0 0 1 70 10 Z" fill="#B8481F" stroke="#7a2a0e" stroke-width="3"/>'
                    f'<path d="M-62 6 Q-30 -22 0 -24 Q30 -22 62 6" fill="none" stroke="#D9722E" stroke-width="3" opacity=".8"/>'
                    f'<g fill="#5a2a14" opacity=".7"><rect x="-40" y="-8" width="18" height="6" rx="3"/><rect x="-8" y="-14" width="22" height="6" rx="3"/><rect x="24" y="-6" width="16" height="6" rx="3"/></g>'
                    f'<circle cx="-12" cy="-22" r="3" fill="#fff"/><circle cx="20" cy="-24" r="3" fill="{ink["herb"]}"/></g>')
        food = (bt(165, 140, -10) + bt(150, 235, 4) + bt(165, 322, 12)
                + f'<circle cx="300" cy="215" r="56" fill="#C9CCCB"/><circle cx="300" cy="215" r="48" fill="#3a1608"/><circle cx="300" cy="215" r="44" fill="#7a2410"/>'
                + "".join(f'<circle cx="{300+16*math.cos(i*1.3)}" cy="{215+16*math.sin(i*1.3)}" r="{4+i%3}" fill="#E8870E" opacity=".65"/>' for i in range(6))
                + f'<circle cx="332" cy="140" r="14" fill="{ink["herb"]}" opacity=".9"/><path d="M290 320 a24 24 0 0 1 34 -22 l-18 34 z" fill="{ink["herb"]}"/>')
    elif kind == "elote":
        food = (f'<rect x="90" y="170" width="220" height="62" rx="31" fill="#E6B93E" stroke="#6e4b12" stroke-width="3"/>'
                + "".join(f'<circle cx="{110+i*20}" cy="{190+(i%2)*20}" r="6" fill="#B8861F" opacity=".7"/>' for i in range(10))
                + f'<path d="M100 195 q50 -20 100 0 t100 0" stroke="#fff" stroke-width="9" fill="none" opacity=".85"/><path d="M110 215 q40 18 90 0 t90 0" stroke="{ink["hibiscus"]}" stroke-width="5" fill="none"/>'
                + "".join(f'<circle cx="{120+i*30}" cy="{178+(i%3)*14}" r="4" fill="{ink["herb"]}"/>' for i in range(7)))
    elif kind == "churros":
        def cs(i):
            x = 100 + i * 34; rot = i * 4 - 10
            ridges = "".join(f'<path d="M{x+4+k*5} 118 V268" stroke="#B9812E" stroke-width="2" opacity=".8"/>' for k in range(4))
            return f'<g transform="rotate({rot} 200 200)"><rect x="{x}" y="110" width="28" height="165" rx="13" fill="#DDA84E"/>{ridges}<g fill="#fff" opacity=".85">' + "".join(f'<circle cx="{x+5+(j*7)%20}" cy="{125+(j*23)%140}" r="1.6"/>' for j in range(16)) + '</g></g>'
        food = "".join(cs(i) for i in range(5)) + f'<circle cx="318" cy="318" r="34" fill="#C9CCCB"/><circle cx="318" cy="318" r="27" fill="#3a1f10"/><circle cx="310" cy="311" r="8" fill="#5a2f18" opacity=".7"/>'
    elif kind == "veg":
        food = (f'<circle cx="200" cy="205" r="104" fill="#E8D9B4"/><circle cx="200" cy="205" r="104" fill="none" stroke="#C9B890" stroke-width="2"/>'
                + "".join(f'<circle cx="{200+58*math.cos(math.radians(i*40))}" cy="{205+58*math.sin(math.radians(i*40))}" r="22" fill="{c}"/>' for i, c in enumerate([ink["herb"], "#C98A3E", ink["hibiscus"], "#E3B04B", ink["herb"], "#8a5a2a", ink["hibiscus"], "#E3B04B", "#C98A3E"]))
                + f'<circle cx="200" cy="205" r="30" fill="#F3ECDD"/><circle cx="200" cy="205" r="14" fill="{ink["marigold"]}"/>')
    else:
        food = f'<circle cx="200" cy="200" r="90" fill="{ink["tamarind"]}"/>'
    return _svg("0 0 400 400", uid, f"Concept plating of {kind}", "A top-down concept illustration of a plate on black stoneware. A stylised drawing, not a photograph of a cooked dish.", base + food, "plate-art")

def fire_scene(uid="fire"):
    flames = "".join(f'<path class="flame f{i}" d="M{x} 330 Q{x-26} 280 {x} 232 Q{x+8} 270 {x+26} 250 Q{x+34} 300 {x} 330Z" fill="{c}"/>' for i, (x, c) in enumerate([(300, "#E8870E"), (360, "#F4B13E"), (420, "#E8870E"), (480, "#C94A0E"), (330, "#FFD27A"), (450, "#FFD27A")]))
    sparks = "".join(f'<circle class="spark s{i}" cx="{320+i*28}" cy="{200-i*6}" r="2.2" fill="#FFD27A"/>' for i in range(6))
    body = (f'<defs><radialGradient id="{uid}g" cx=".5" cy=".75" r=".7"><stop offset="0" stop-color="#E8870E" stop-opacity=".9"/><stop offset="1" stop-color="#141110" stop-opacity="0"/></radialGradient></defs>'
            f'<rect width="800" height="500" fill="#141110"/><rect class="glow" width="800" height="500" fill="url(#{uid}g)"/>'
            f'<path d="M180 460 V300 Q180 150 300 120 Q400 90 500 120 Q620 150 620 300 V460Z" fill="#8a4a22"/><path d="M180 460 V300 Q180 150 300 120 Q400 90 500 120" fill="none" stroke="#B5651D" stroke-width="6"/>'
            f'<path d="M250 460 V340 Q250 250 400 250 Q550 250 550 340 V460Z" fill="#1c0e06"/>{flames}{sparks}'
            f'<g fill="none" stroke="#C9A24B" stroke-width="3"><path d="M250 300 H550" opacity=".0"/></g>'
            f'<rect x="120" y="455" width="560" height="14" fill="#3a2a22"/><ellipse cx="660" cy="438" rx="70" ry="14" fill="#2a1f1a"/><ellipse cx="660" cy="432" rx="64" ry="11" fill="#3a2e28"/><ellipse cx="660" cy="428" rx="56" ry="8" fill="#6b3a1c"/>')
    return _svg("0 0 800 500", uid, "Concept illustration: fire", "A stylised clay tandoor with flames and a round flat comal beside it, drawn as a concept illustration.", body, "fire-art")

def ferment_scene(uid="ferm"):
    bubs = "".join(f'<circle class="fb fb{i%6}" cx="{300+(i*37)%160}" cy="{360-(i*23)%240}" r="{3+i%4}" fill="#fff" opacity=".6"/>' for i in range(16))
    body = (f'<rect width="800" height="500" fill="#141110"/><defs><linearGradient id="{uid}s" x1="0" x2="1"><stop offset="0" stop-color="#8d9091"/><stop offset=".4" stop-color="#E4E6E5"/><stop offset="1" stop-color="#6f7273"/></linearGradient>'
            f'<clipPath id="{uid}c"><rect x="300" y="150" width="200" height="240" rx="16"/></clipPath></defs>'
            f'<path d="M300 390 H500 L420 470 H380Z" fill="#3a3a3a"/><rect x="300" y="150" width="200" height="240" rx="16" fill="url(#{uid}s)"/><rect x="300" y="250" width="200" height="22" fill="#E8870E"/>'
            f'<g clip-path="url(#{uid}c)"><rect x="318" y="190" width="164" height="190" rx="12" fill="#E3A02B" opacity=".0"/></g>'
            f'<circle cx="400" cy="205" r="26" fill="#1c1a19" stroke="#C9CCCB" stroke-width="5"/><g clip-path="url(#{uid}c)">{bubs}</g>'
            f'<path d="M340 150 q60 -50 120 0" fill="none" stroke="#C9CCCB" stroke-width="8"/><g stroke="#C9CCCB" stroke-width="5"><path d="M310 390 v70 M490 390 v70"/></g>')
    return _svg("0 0 800 500", uid, "Concept illustration: fermentation", "A stylised stainless fermentation tank with a marigold band and rising bubbles, drawn as a concept illustration. Not a final tank size.", body, "ferment-art")

def jali(uid, fg="#E8870E", bg="#1A2142", op=.12):
    """Jali-inspired lattice meeting a tile-like grid. Contemporary geometry, no claim of historical link."""
    body = (f'<defs><pattern id="{uid}" width="80" height="80" patternUnits="userSpaceOnUse"><rect width="80" height="80" fill="{bg}"/>'
            f'<path d="M40 6 L74 40 L40 74 L6 40Z" fill="none" stroke="{fg}" stroke-width="2" opacity="{op*3}"/><circle cx="40" cy="40" r="12" fill="none" stroke="{fg}" stroke-width="2" opacity="{op*3}"/>'
            f'<rect x="0" y="0" width="80" height="80" fill="none" stroke="{fg}" stroke-width="1" opacity="{op}"/><circle cx="40" cy="40" r="3" fill="{fg}" opacity="{op*3}"/></pattern></defs>'
            f'<rect width="100%" height="100%" fill="url(#{uid})"/>')
    return f'<svg class="art pat" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">{body}</svg>'

MOTIFS = {
 "chile": '<path d="M20 70 Q30 20 70 14 Q86 12 88 24 Q60 30 46 78 Q36 94 24 84 Z" fill="#9B2447"/><path d="M70 14 q6 -10 14 -8" stroke="#7D9A45" stroke-width="5" fill="none"/>',
 "spice": '<g fill="#C9A24B"><ellipse cx="40" cy="40" rx="8" ry="14" transform="rotate(30 40 40)"/><ellipse cx="66" cy="52" rx="8" ry="14" transform="rotate(-20 66 52)"/><ellipse cx="50" cy="74" rx="8" ry="14" transform="rotate(70 50 74)"/><circle cx="76" cy="26" r="7" fill="#5A3A25"/></g>',
 "acid": '<circle cx="50" cy="50" r="34" fill="#7D9A45"/><circle cx="50" cy="50" r="28" fill="#D9E39A"/><g stroke="#7D9A45" stroke-width="3"><path d="M50 22 V78 M22 50 H78 M30 30 L70 70 M70 30 L30 70"/></g>',
 "smoke": '<path d="M50 8 Q18 44 34 70 Q50 92 66 70 Q82 46 58 28 Q58 46 50 52 Q44 34 50 8Z" fill="#E8870E"/><path d="M50 40 Q36 60 50 76 Q62 60 50 40Z" fill="#FFD27A"/>',
 "flatbreads": '<circle cx="50" cy="50" r="34" fill="#E4C98D"/><g fill="#B5651D"><circle cx="36" cy="40" r="4"/><circle cx="60" cy="34" r="4"/><circle cx="64" cy="60" r="4"/><circle cx="42" cy="64" r="4"/></g>',
 "rice": '<path d="M18 52 H82 Q80 82 50 84 Q20 82 18 52Z" fill="#E4DAC6"/><g fill="#C9A24B"><ellipse cx="36" cy="44" rx="5" ry="3"/><ellipse cx="50" cy="40" rx="5" ry="3"/><ellipse cx="64" cy="44" rx="5" ry="3"/><ellipse cx="43" cy="47" rx="5" ry="3"/><ellipse cx="57" cy="47" rx="5" ry="3"/></g>',
 "legumes": '<g fill="#8a5a2a"><ellipse cx="38" cy="40" rx="14" ry="9" transform="rotate(-30 38 40)"/><ellipse cx="62" cy="54" rx="14" ry="9" transform="rotate(20 62 54)"/><ellipse cx="40" cy="68" rx="14" ry="9" transform="rotate(10 40 68)"/></g>',
 "fermentation": '<circle cx="36" cy="64" r="12" fill="none" stroke="#E4DAC6" stroke-width="4"/><circle cx="62" cy="44" r="9" fill="none" stroke="#E4DAC6" stroke-width="4"/><circle cx="44" cy="26" r="6" fill="none" stroke="#E4DAC6" stroke-width="4"/><circle cx="72" cy="72" r="5" fill="none" stroke="#E4DAC6" stroke-width="4"/>',
 "table": '<rect x="10" y="38" width="80" height="24" rx="4" fill="#5A3A25"/><circle cx="28" cy="50" r="8" fill="#F3ECDD"/><circle cx="50" cy="50" r="8" fill="#F3ECDD"/><circle cx="72" cy="50" r="8" fill="#F3ECDD"/>',
}
def motif(name, uid):
    return _svg("0 0 100 100", uid, f"{name} motif", f"A simple drawn symbol for {name}.", MOTIFS.get(name, MOTIFS["table"]), "motif")

def table_scene(uid="tbl"):
    dishes = ""
    kinds = [(180, 170), (330, 150), (480, 175), (630, 150), (780, 170)]
    cols = ["#E3B04B", "#8a2e12", "#C98A3E", "#7D9A45", "#D99A3C"]
    for (x, y), c in zip(kinds, cols):
        dishes += f'<circle cx="{x}" cy="{y}" r="58" fill="#0b0a09"/><circle cx="{x}" cy="{y}" r="50" fill="#F3ECDD"/><circle cx="{x}" cy="{y}" r="30" fill="{c}"/>'
    glasses = "".join(f'<g><circle cx="{x}" cy="{y}" r="22" fill="{c}" opacity=".9"/><circle cx="{x}" cy="{y}" r="22" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="3"/><circle cx="{x}" cy="{y}" r="14" fill="#fff" opacity=".35"/></g>'
                      for x, y, c in [(100, 300, "#E3A02B"), (250, 320, "#EEC04A"), (410, 310, "#C4691A"), (560, 325, "#E3A02B"), (700, 305, "#EEC04A"), (860, 315, "#C4691A")])
    body = (f'<rect width="960" height="420" fill="#2a1d14"/><rect y="40" width="960" height="340" fill="#5A3A25"/><g stroke="#4a2f1e" stroke-width="3"><path d="M0 120 H960 M0 210 H960 M0 300 H960"/></g>'
            f'<rect x="60" y="60" width="840" height="14" fill="#1A2142"/><rect x="60" y="62" width="840" height="3" fill="#E8870E"/>{dishes}{glasses}'
            f'<g fill="#1A2142"><rect x="30" y="390" width="120" height="10"/><rect x="810" y="390" width="120" height="10"/></g>')
    return _svg("0 0 960 420", uid, "Concept illustration: a shared table", "A top-down drawing of a long wooden table with five shared plates and six beer glasses between them. A concept illustration, with no people.", body, "table-art")

def bar_scene(uid="bar"):
    taps = "".join(f'<g><rect x="{80+i*60}" y="170" width="14" height="46" rx="4" fill="#141110"/><rect x="{80+i*60}" y="176" width="14" height="5" fill="#E8870E"/><rect x="{83+i*60}" y="216" width="8" height="26" fill="#C9CCCB"/></g>' for i in range(12))
    glasses = "".join(f'<path d="M{70+i*90} 108 l6 60 h26 l6 -60Z" fill="#fff" fill-opacity=".14" stroke="#fff" stroke-opacity=".5" stroke-width="2"/>' for i in range(8))
    tiles = "".join(f'<rect x="{20+i*50}" y="330" width="46" height="46" fill="{"#F3ECDD" if (i%3) else "#E8870E"}"/>' for i in range(18))
    stools = "".join(f'<g><ellipse cx="{110+i*130}" cy="410" rx="30" ry="9" fill="#141110"/><rect x="{106+i*130}" y="412" width="8" height="60" fill="#141110"/></g>' for i in range(7))
    body = (f'<rect width="960" height="500" fill="#1c1410"/><rect class="glow" width="960" height="500" fill="#E8870E" opacity=".08"/>'
            f'<rect x="0" y="94" width="960" height="12" fill="#3a2a1e"/><rect x="0" y="106" width="960" height="3" fill="#E8870E" opacity=".6"/>{glasses}'
            f'<rect x="40" y="150" width="880" height="14" fill="#141110"/>{taps}<rect x="0" y="300" width="960" height="30" fill="#2b1d12"/><rect x="0" y="296" width="960" height="8" fill="#141110"/>{tiles}{stools}'
            f'<circle cx="480" cy="40" r="18" fill="#E9C46A" opacity=".9"/><circle cx="260" cy="48" r="12" fill="#E9C46A" opacity=".8"/><circle cx="700" cy="46" r="12" fill="#E9C46A" opacity=".8"/>')
    return _svg("0 0 960 500", uid, "Concept illustration: the bar", "A drawn bar front in bone and marigold tile, a row of taps above a dark counter, glasses on a shelf, and stools. A concept illustration.", body, "bar-art")

def patio_scene(uid="patio"):
    lights = "".join(f'<circle cx="{40+i*50}" cy="{80+ (i%2)*10 + abs(math.sin(i/2.2))*18:.0f}" r="5" fill="#E9C46A"/>' for i in range(19))
    body = (f'<defs><linearGradient id="{uid}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1A2142"/><stop offset="1" stop-color="#C47A45"/></linearGradient></defs>'
            f'<rect width="960" height="500" fill="url(#{uid}s)"/><g fill="#141110"><rect x="760" y="170" width="16" height="250"/><ellipse cx="768" cy="150" rx="150" ry="100"/><ellipse cx="660" cy="200" rx="90" ry="60"/><ellipse cx="880" cy="200" rx="90" ry="60"/></g>'
            f'<rect x="0" y="420" width="960" height="80" fill="#141110"/><path d="M0 70 Q480 140 960 70" fill="none" stroke="#3a312c" stroke-width="2"/>{lights}'
            f'<rect x="60" y="270" width="520" height="14" fill="#5A3A25"/><rect x="80" y="284" width="10" height="136" fill="#3a2418"/><rect x="540" y="284" width="10" height="136" fill="#3a2418"/>'
            f'<g fill="#3a2418"><rect x="70" y="330" width="500" height="10"/></g><g fill="#F3ECDD" opacity=".9"><circle cx="160" cy="262" r="12"/><circle cx="260" cy="262" r="12"/><circle cx="360" cy="262" r="12"/><circle cx="460" cy="262" r="12"/></g>'
            f'<g fill="#E3A02B"><circle cx="210" cy="260" r="8"/><circle cx="310" cy="260" r="8"/><circle cx="410" cy="260" r="8"/></g><rect x="0" y="0" width="960" height="46" fill="#141110" opacity=".5"/>')
    return _svg("0 0 960 500", uid, "Concept illustration: the patio", "A drawn evening patio with string lights, a long communal table with plates and beer glasses, and a large oak tree. A concept illustration.", body, "patio-art")

def popup_scene(uid="pop"):
    stripes = "".join(f'<rect x="{150+i*50}" y="150" width="50" height="60" fill="{"#1A2142" if i%2==0 else "#F3ECDD"}"/>' for i in range(12))
    body = (f'<defs><linearGradient id="{uid}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2B3563"/><stop offset="1" stop-color="#C47A45"/></linearGradient></defs>'
            f'<rect width="960" height="500" fill="url(#{uid}s)"/><rect y="400" width="960" height="100" fill="#141110"/>'
            f'<path d="M130 210 L150 150 H750 L770 210Z" fill="#1A2142"/>{stripes}<rect x="150" y="145" width="600" height="8" fill="#E8870E"/>'
            f'<rect x="170" y="210" width="560" height="190" fill="#241E1B"/><rect x="170" y="300" width="560" height="100" fill="#5A3A25"/><rect x="170" y="300" width="560" height="10" fill="#141110"/>'
            f'<g fill="#E9C46A"><circle cx="230" cy="190" r="6"/><circle cx="450" cy="190" r="6"/><circle cx="670" cy="190" r="6"/></g>'
            f'<rect x="300" y="236" width="300" height="44" fill="#141110"/><text x="450" y="268" text-anchor="middle" font-family="Instrument Serif,Georgia,serif" font-size="30" letter-spacing="9" fill="#F3ECDD">NASHA</text>'
            f'<g fill="#C9CCCB"><rect x="206" y="318" width="10" height="30"/><rect x="232" y="318" width="10" height="30"/></g>'
            f'<rect x="790" y="300" width="110" height="100" rx="6" fill="#F3ECDD" opacity=".92"/><rect x="800" y="312" width="90" height="10" fill="#141110"/><rect x="800" y="332" width="70" height="8" fill="#9A9087"/><rect x="800" y="348" width="80" height="8" fill="#9A9087"/>')
    return _svg("0 0 960 500", uid, "Concept illustration: an early pop-up", "A drawn pop-up stand with a striped canopy, a counter, and a NASHA sign at dusk. One possible early form, not a final vehicle or a booked event.", body, "popup-art")

def menu_cover(uid="menucov"):
    body = (f'<rect width="420" height="580" rx="6" fill="#1A2142"/><g opacity=".5" fill="none" stroke="#E8870E" stroke-width="2">'
            + "".join(f'<path d="M{20+c*80} {20+r*80} l40 40 l-40 40 l-40 -40Z"/>' for c in range(6) for r in range(8)) + '</g>'
            f'<rect x="60" y="160" width="300" height="260" fill="#1A2142"/><text x="210" y="270" text-anchor="middle" font-family="Instrument Serif,Georgia,serif" font-size="64" letter-spacing="14" fill="#F3ECDD">NASHA</text>'
            f'<text x="210" y="338" text-anchor="middle" font-family="Inter,sans-serif" font-size="14" letter-spacing="4" fill="#E9C46A">FOOD · BEER · FIRE</text>'
            f'<text x="210" y="540" text-anchor="middle" font-family="Inter,sans-serif" font-size="11" letter-spacing="3" fill="#C3C8DD">PROPOSED MENU DESIGN</text>')
    return _svg("0 0 420 580", uid, "Proposed NASHA menu cover", "A deep indigo menu cover with a faint lattice pattern, the temporary typographic NASHA wordmark. A proposed design, not a printed menu.", body, "menu-cover")
