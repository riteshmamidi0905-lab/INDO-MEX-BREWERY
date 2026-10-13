# NASHA VISION LAYER (Sprint 25)

**ASSUME FOR VISION. VERIFY BEFORE IMPLEMENTATION.**

NASHA now has two layers. They never merge silently.

| Layer | Where | What it is |
|---|---|---|
| 1. Blueprint / Truth | `docs/`, `docs/company/`, `food/`, `beer/`, the frozen PRE-CAPITAL DIGITAL BLUEPRINT v1.0 | Facts, research, evidence, unknowns, risks, professional gates. Not rewritten to make design prettier. |
| 2. Vision / Future state | `vision/` | A creative simulation of NASHA at its best. It resolves open questions *temporarily* so one coherent world can be drawn, written and walked through. |

## Rules
1. Every consequential vision choice is a row in `data/VISION-ASSUMPTIONS.csv` and is labelled VISION ASSUMPTION, never fact.
2. Vision content is never evidence, a validated product, a professional or legal approval, an actual cost, customer or site data, an equipment selection, a recipe, a sale or traction.
3. Vision assets live in their own classes (see `data/VISION-ASSET-MANIFEST.csv`): VISION FOOD, VISION BEER, VISION NA, VISION PLACE. They are stored apart from founder prototype media and never move between classes silently.
4. Vision flagship = **VISION FLAGSHIP — NOT CONSTRUCTION DESIGN.** No square footage, occupancy, code compliance, engineering or site feasibility is claimed.
5. Where vision disagrees with Blueprint v1.0 (three glasses instead of five, a service style, a brewery size), Blueprint is unchanged. Future evidence may reject the vision.
6. D-66 stands: no final logo, no ™/®. The wordmark is a typographic placeholder. The name is legally unresolved, so every sign concept must survive a rename.
7. Nothing is deployed, public, sold or announced. Scores stay: evidence 4/95, design 43/95.

## Files
- `VISION-WORLD-BIBLE.md` — north star, materials, light, colour, sound, seasons, the Court Brewhouse, arrival, rooms, bar, brewery, kitchen.
- `VISION-PRODUCT-AND-TABLE.md` — five dishes, five beers, zero-proof, glassware, ritual, table, menu, pairing language.
- `VISION-BRAND-SYSTEM.md` — uniforms, signage, pattern, packaging, sound, day to night, people, cultural flags.
- `VISION-SCENARIO-AND-WALKTHROUGH.md` — one future evening and the 4-minute investor path.
- `production/` — Sprint 26 visual production system: `CONTINUITY-BIBLE.md`, `VP-AUDIT.csv` (source of truth for VP-01..VP-14), `CHATGPT-HANDOFF.md` (generated), `GLOBAL-LOCK-BLOCK.txt`, `GLOBAL-NEGATIVES.txt`, `IMAGE-PROVENANCE.csv`, `WEBSITE-IMAGE-SLOT-MAP.csv`.
- `IMAGE-PROMPT-PACK.md` — superseded Sprint 25 prompts (history).
- `data/VISION-ASSUMPTIONS.csv`, `data/VISION-ASSET-MANIFEST.csv`, `data/VISION-CULTURAL-FLAGS.csv`.
- `production/SPRINT26-REVIEW.md` — simulated review of the production system.
- `SPRINT25-REVIEW.md` — the creative red-team, the one-thing test and the coherence test.

## Status (2026-10-13)
- **Round 2 architecture is frozen:** VP-01 (primary master), VP-02 (court, furniture, material), VP-03 (bar layout and hospitality; not the glassware master) and VP-04 (night court and dinner service). Hashes are in `production/ROUND2-FREEZE.csv`; `tools/vision_check.py` fails if any of the four files changes.
- **VB-01** is the founder-approved Vision board: creative direction only, not used on the site; where a panel conflicts with a written specification, the specification wins.
- **Round 3 (food)** starts with VP-05 Chicken 65 Totopos, which becomes the Core 5 food continuity master; VP-06 to VP-09 and VP-12 then attach VP-05 and VP-02. VP-10 sets the glassware master.
- **Full-resolution pass (2026-10-13):** VP-05 to VP-13 are registered as full-resolution founder-confirmed Vision assets (VP-10 glass-family direction frozen to the extent it matches the written system; VP-11 current zero-proof family). VP-14 is retained as provenance only because its wooden barrel, leather straps and copper-gold tank cast are noncanonical. VB-01 and VB-02 and the low-resolution panel crops are history and creative direction only.
