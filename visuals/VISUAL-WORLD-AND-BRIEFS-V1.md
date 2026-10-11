# Visual World and Generation Briefs v1

**Status:** `[PROPOSED]` direction + briefs. **No new image was generated in Sprint 4.** Canonical rules remain `visuals/VISUAL-DNA.md` (v2.1) and `LOCKED-SCENE-DNA.md`; ARC-01-D is the canonical exterior; ARC-02-A is a night-mood reference only; BRW-01 is an equipment reference only (D-47, D-49). The 57-asset library (`ASSET-MANIFEST.md`, prompts in `visuals/prompts/V2-*.md`) and expansion library (`EXPANSION-MANIFEST.md`) already exist; this document maps the needs onto them and adds only the missing briefs.
**Labelling rule (every generated image):** record in metadata/caption, never in the picture: "**Concept visualization. Not a photograph of a real place, dish, beer or event. Not engineering.**" Food images depict *proposed* dishes that have not been cooked; beer images depict *intended* beers that have not been brewed.

## 1. The visual world (what it should feel like)
A **contemporary Texas hospitality interior-exterior**: limestone and concrete in strong shade, deep blackened steel, polished tanks as civic furniture, a copper hood in warm light, fire visible, long communal timber tables, bone terrazzo, one narrow marigold line, a ring that recurs. Light is warm and shielded; day is hard Texas sun with deep arcade shade. People are mixed, candid, unstaged. **Culture shows through ingredients, technique and craft objects, not costume.**
**Anti-cliché checklist (reject any image that shows):** terracotta walls, brass decoration, mosaic/Moorish tile, mandalas or jaali motifs, agave resort planting, string-light canopies, neon, sombreros/turbans/saris, deity or sacred imagery, papel-picado or paisley as décor, faux-Devanagari type, "cantina" signs, sports-bar screens, exposed-Edison industrial brewery clichés, beef or pork food (D-54). **The test:** if the image could be a generic cantina, Indian restaurant, sports bar or industrial brewery with the logo removed, it fails.

## 2. Requested assets → existing library (status all NOT GENERATED unless noted)
| Need | Existing ID(s) | Gap / note |
|---|---|---|
| Exterior hero | **ARC-01-D (canonical, exists)**; ARC-03, ARC-05 | Night exterior unresolved (tool limit, D-47) |
| Entrance | ARC-04 | none |
| Main dining room | INT-03 | none |
| Bar | INT-01, INT-02, NGT-01 | none |
| Brewery tanks | BRW-01..06 | BRW-01 run reviewed 68/100; reference only |
| Tandoor / open kitchen | KIT-01 | Needs the D-54 no-beef/no-pork discipline in props |
| Patio / Shade Court | CRT-01, CRT-02, CRT-03, CRT-04 | none |
| Evening atmosphere | CRT-01, NGT-01, WEB-04 | none |
| Family / social area | FAM-01, FAM-02, GAME-01 (expansion) | Blocked by D-34 release conditions: allowed when materially useful (D-52) |
| Signature food | FOD-01..09 | **Gaps:** Tandoori Lamb Taco, Chaat Elote, Dal-Frijol Dip, Cardamom Churros (briefs below) |
| Signature beer | BER-01..05 | none |
| Glassware | GLS-01..03 | Package ready (D-50) |
| Merchandise | MER-01, MER-02, RTL-01, RTL-02 | none |
| Signage | none | **Gap: SIG-01 (brief below)** |
| Packaging | PKG-01..03 | Packaging legality/viability unresolved (G-11) |

## 3. New briefs (gaps only; `NOT GENERATED`)
Common continuity for all: Visual DNA v2.1; black stoneware plates with raw rim and bone interior; katori for sauces; thali tray with bone paper; pecan table; window side-light; 85-105 mm food lens feel; 4:5 or 1:1; no logos, no readable text; no beef/pork; hands optional and anatomically correct.
| ID | Subject | Composition and must-include | Must avoid |
|---|---|---|---|
| **FOD-10** | Tandoori Lamb Taco (proposed dish) | Three small flour-tortilla tacos, charred sliced lamb with onion, herb-acid salsa, a lime; char marks visible; stoneware; side katori of raita-crema | Birria-style consommé, beef look-alike cuts (D-54), melted-cheese cliché, taco-holder props |
| **FOD-11** | Chaat Elote (proposed) | Charred corn pieces dressed with cream, chile, lime, crisp topping and herbs, in a bowl or on a tray with bone paper | Mexican-flag colours, props like maracas, overpowering orange |
| **FOD-12** | Dal-Frijol Dip (proposed) | Dark glossy lentil-and-bean dip with a tadka swirl, served with fried masa chips and flatbread crisps | Brown mush look, "hummus" look |
| **FOD-13** | Cardamom Churros with jaggery-chocolate (proposed) | Crisp churros, sugar-and-cardamom dusting, a small dark sauce vessel, steam only if plausible | Cartoon chocolate drips, candy colour |
| **SIG-01** | Signage concept (placeholder wordmark) | Blank blackened-steel monument panel on board-formed concrete beside the entrance recess (ARC-01-D context); a second view of a plain steel wordmark on limestone with soft wall-wash; **no real name, use a neutral placeholder text only if the tool requires, or leave blank** | Neon, string lights, faux-script type, cultural icons |
| **WEB-05** | Pairing diagram plate | Flat-lay: a Hefeweizen in the collar glass beside three small dishes on stoneware, shot top-down on bone terrazzo; no text | Busy props, branded labels |
Prompts for these are to be written in the existing `visuals/prompts/` style only when generation is approved; this table is the brief.

## 4. Sequence recommendation (visual work that helps decisions)
1. GLS-01/GLS-02 (package ready). 2. FOD-01, FOD-02, FOD-05 and BER-01 (hero food/beer, labelled proposed) for the website and menu storytelling. 3. KIT-01 and INT-01/03 (interior). 4. CRT-02 (shade and families) for investor narrative. 5. Night exterior only when a mask-aware workflow exists.
