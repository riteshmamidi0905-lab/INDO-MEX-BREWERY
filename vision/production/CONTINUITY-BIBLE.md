# NASHA VISUAL CONTINUITY BIBLE (Sprint 26)

*A practical image-generation specification, not brand strategy. VISION layer: nothing here is a real place, product or photograph. VISION FLAGSHIP — NOT CONSTRUCTION DESIGN. Six tanks, about eight taps and every material below are Vision assumptions (V-02, V-03, V-06); a professional design overrides them.*

Source of truth for each image: `VP-AUDIT.csv`. The paste-ready requests are generated into `CHATGPT-HANDOFF.md` by `python3 tools/vision_handoff.py`. The reusable text blocks are `GLOBAL-LOCK-BLOCK.txt` and `GLOBAL-NEGATIVES.txt`.

## 1. The one-line world
A warm limestone-and-glass brewery hall beside a shaded gravel court, in Austin, where people eat and drink well-matched food, beer and zero-proof drinks, with the brewing visible and never the point of showing off.

## 2. Court geometry (the continuity map)
North is up. The hall is always WEST of the court.
```
                       N
  service (hidden)  ┌───────────────────────────────────────┐
  ┌────────────┐    │ RESTAURANT BLOCK: bar+dining W | kitchen centre | dining E
  │ TANK HALL  │    │ north arcade: pass windows + oven mouth glow
  │ 6 tanks in │ W  ├───────────────────────────────────────┤
  │ a horseshoe│ arc│      COURT: gravel, one thin rill E-W,       LAWN +
  │ glass S+E  │ ade│      long pecan tables, cedar elms           LIVE OAKS (E)
  │ lobby      │    ├───────────────────────────────────────┤
  └──┬─────────┘    │ south arcade + perforated screens     │
     [ENTRANCE RECESS at the hall's SE corner, plain steel sign panel on a concrete plinth]
        street / entry drive (S)   ◄ VP-01 camera stands SE, looks NNW
```
Route: STREET (S) → THRESHOLD (entrance recess) → COMPRESSION (lobby along the hall glass) → COURT (reveal) → GLASS BREWERY (west of the court) → BAR and DINING (north-west, backbar window into the hall) → PATIO (court and arcades at night).

**Camera positions that keep the world stable**
| Asset | Camera stands | Looks | Brewery appears |
|---|---|---|---|
| VP-01 | SE, entry drive | NNW | Left third, lit glass; entrance just right of the hall corner |
| VP-02 | South end of the west arcade | North-north-east across the court | Left edge, glass and one tank |
| VP-03 | East-side bar stool | West, across the bar to the window in the hall wall | Last tanks and the brew deck through the window |
| VP-04 | East lawn edge | West | Far left, glowing |
| VP-14a | Lobby promenade, about 5 m from the glass | North into the tanks | Centre, through glass |
Never: the hall on the east, a second court, more than one rill, a basement, a roof terrace, a different number of tanks.

**Known conflicts with `visuals/LOCKED-SCENE-DNA.md` (older canonical scene), resolved for Vision only**
- Copper-clad brewhouse vessels in the DNA: Vision uses plain stainless (V-03).
- 24 taps in the DNA: Vision uses about eight (V-06).
- The DNA puts the backbar against the hall's west side; the plan above has the bar against the hall's east wall, so the bar window looks west into the hall.
- The DNA's 24-ft brew deck between tanks 3 and 4 does not fit 9-ft tank spacing; keep the deck small and let a brewer decide.
- The DNA has one brewers' door at the north; a real design needs a second exit, and the oven mouth in the arcade wall needs fire separation (professional review).
- The court is small (about 96 x 42 ft between arcades). A centreline rill is a Vision assumption and must stay thin and restrained; an accessibility reviewer decides whether it can exist.

## 3. Material palette (one vocabulary)
Honed pale limestone with natural weathering · board-formed warm-grey concrete · matte blackened steel (perforated screens in three hole sizes, used sparingly) · brushed stainless (tanks with charcoal cones and one thin orange sleeve; no copper cladding) · cedar elm (beams, soffits) · dark pecan (bar top, tables) · bone terrazzo indoors · decomposed-granite gravel and stone pavers outdoors · dark-bronze glass frames · brass only as small touch points (lamp shades, door hardware, a footrail cap) · unglazed terracotta only as a few planters · greenery: native grasses, yaupon, cedar elm, live oak.
Do not decorate every surface. Quiet walls are the point.

## 4. Camera
Image models ignore millimetres and centimetres, so the camera is written as framing.
| Subject | Framing |
|---|---|
| Architecture | Eye-level, slightly wide, straight verticals, no tilt |
| Guest scenes | Eye-level at the table, natural framing |
| Food | Three-quarter overhead, close but with the table visible; straight down for the full table |
| Beer and zero-proof | Table height, slightly angled |
Avoid: ultra-wide, drone, cinematic bars, fake depth of field everywhere, HDR, hyper-saturated food. Set the 3:2 landscape ratio in the ChatGPT size option, not in the prompt; keep the key subject in the central half so the 16:9 desktop and 4:5 mobile crops both work.

## 5. Light
Day: warm Austin sun, deep arcade shade. Golden hour: restrained low sun. Night: warm tungsten pools (about 2200-2400K in the design intent), tanks gently uplit, oven glow; no string lights, no blue or purple, no orange cast. In prompts write "warm tungsten pools, no orange cast" and "dusk, deep blue sky", never a Kelvin number. Food stays readable at all times.

## 6. People
Recurring archetypes (invent no identities): A) couple, B) four friends, C) family with children, D) solo bar guest, E) server, F) bartender, G) brewer, H) cook. Natural, mid-action, varied adults of different ages and backgrounds, nobody posing, nobody identifiable, no text on clothing. **Children never hold or sit near beer or beer-family glassware; a child's drink is a plain short tumbler of water or juice.** Image models handle negatives badly, so a family prompt never mentions beer at all (VP-13c), and every family image is checked by eye.

## 7. Staff
FOH and bar: bone shirt, charcoal canvas apron (bar: shorter apron, sleeves rolled). Brewery: dark work shirt, work trousers, boots, safety glasses where the task needs them. Kitchen: dark practical jacket, plain cap. No logos, no costumes, no leather items.

## 8. Table
Matte black stoneware with a bone interior and a raw rim · stainless katori · round steel tray with bone paper · natural woven basket · indigo-and-bone linen napkin (no stripe or print) · water glass · beer glass and zero-proof glass from the three-glass family · optional small coaster · one small cruet. Eight objects at most per setting.

## 9. Glass
Signature Hefe (tall, ring a quarter up) · Lager and Pils (refined cone) · Aromatic (short stemmed tulip) · flight tulip. Zero-proof drinks use the same clear glasses. No logos, no print, no colour on the glass.

## 10. Pattern, signage
Pattern appears only as the screen perforation, a menu or coaster detail, one small tile moment and one textile detail. It never wallpapers a room. Signage: a plain blank steel panel on a concrete plinth; no readable name in any image; the building must work if the name changes (D-66: no logo, no trademark symbols).

## 11. Global negatives
`GLOBAL-NEGATIVES.txt` is the single exclusion list. Every request appends it plus its own asset-specific list.

## 12. Provenance
Every accepted image gets a row in `IMAGE-PROVENANCE.csv` (generation date, prompt version, class, source, edit status, website use, Blueprint relation, known inaccuracies, what it supersedes, file, SHA-256). Use `python3 tools/vision_check.py register VP-01 path/to/image.png --date YYYY-MM-DD --edit "none"`. AI imagery is never called photography.

## 13. Generation sequence and gates
1. **Round 1: VP-01.** Accept only if: hall west, six tanks, plain sign, people natural, no car, no text. If the world is wrong, fix `GLOBAL-LOCK-BLOCK.txt`, not the single prompt.
2. **Round 2: VP-02, VP-03, VP-04.** Attach VP-01. Accept only if stone, columns, beams, tables, chairs and glass match VP-01.
3. **Round 3: VP-05 to VP-09, then VP-12.** Attach VP-02 for the stoneware and table. Accept only if each dish keeps its identity (see the success criteria) and the plates, napkin and katori are the same family.
4. **Round 4: VP-10, VP-11.** Attach VP-02. Accept only if five beers are distinct and the zero-proof drinks look equally intentional.
5. **Round 5: VP-13 (four requests), VP-14 (two requests).** Attach VP-01 and one food image. Accept only if the children-and-beer rule and the uniform rule hold.
If a round fails twice, change the lock block, not the wording of one asset.

## 14. ChatGPT workflow
Expect drift without references: stone, wood, tank count, chairs and tableware vary unless the accepted VP-01 and a food image are attached. The lock block lists the look first and keeps compass words out; the geometry map above is for the founder and Claude, not for the model.
One asset per chat message. Paste the full block from `CHATGPT-HANDOFF.md`, attach the named reference images, ask for a 3:2 landscape image. Save the accepted file and register it as above. Existing renders in `visuals/web-source/` are loose geometry references only, never style masters, and carry provisional rights.
