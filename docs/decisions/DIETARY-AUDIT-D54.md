# Dietary Audit for D-54 (no beef, no pork)

**Method:** repository-wide search (`.md`, `.py`) for beef, pork, bacon, lard, carnitas, carne asada, gelatin, brisket, chorizo, pastor, barbacoa, ham, sausage; every hit classified. **Re-run:** `python3 tools/diet_audit.py` (checks that current-product files contain no unmarked beef/pork).
Classes: **CURRENT PRODUCT** (must comply: updated) · **SUPERSEDED** (old decision/menu: marked) · **HISTORICAL RESEARCH** (retained) · **REJECTED PROVENANCE** (retained, labelled) · **COMPETITOR/REFERENCE** (retained).

| File | Occurrence | Class | Action |
|---|---|---|---|
| `food/OPENING-MENU-V2.md` | Tandoori Carne Asada (menu table, dossier, shared-ingredient list) | CURRENT PRODUCT → SUPERSEDED | Replaced by **Tandoori Lamb**; original rows kept marked SUPERSEDED |
| `food/OPENING-MENU-V2.md` | "Dum Goat Birria (beef option)" | CURRENT PRODUCT | Beef option removed; goat only |
| `food/OPENING-MENU-V2.md` | Achari Carnitas | REJECTED PROVENANCE | Marked **REJECTED (D-54)** |
| `food/OPENING-MENU-V2.md` | Kathal "Barbacoa" taco (jackfruit) | CURRENT PRODUCT (special) | Retained: jackfruit; no meat |
| `food/OPENING-MENU-V2.md` | "Beef, pork, goat... need policy" | CURRENT | Replaced by D-54 statement |
| `food/MENU-DEVELOPMENT-MATRIX-V1.md` | Item 8 Carne Asada; allergen row; M-1, M-2, M-3, M-6 | CURRENT PRODUCT / SUPERSEDED | Item 8 → Lamb; M-1/M-2 struck as SUPERSEDED; M-3 beef option removed; counts updated |
| `food/SAUCE-SYSTEM.md` | Adobo-Dum "beef option" | CURRENT PRODUCT | Removed |
| `beer/OPENING-BEER-PROGRAM-V1.md` | Pairing "Tandoori Carne Asada" | CURRENT PRODUCT | → Tandoori Lamb Taco |
| `PROJECT-ROADMAP.md` | FD-3 diet policy | CURRENT | Closed by D-54 |
| `docs/decisions/DECISIONS.md` | D-52 menu M-1..M-3 | SUPERSEDED | Marked SUPERSEDED by D-54 (history kept) |
| `docs/decisions/OPEN-QUESTIONS.md` | Halal/beef/pork question (2 places) | SUPERSEDED | Struck and answered |
| `docs/decisions/REJECTED.md` | Achari Carnitas, Chilli Chicken Taco | REJECTED PROVENANCE | Retained; reason now also "pork (D-54)" |
| `phase-one/06-food-program.md` | Carne Asada, Carnitas, Cochinita Pibil Naan Pizza, "halal/beef" note | SUPERSEDED | Banner added: superseded for the menu by D-54; retained |
| `phase-one/01-regional-research-and-pairings.md` | Goa pork, Sonora carne asada, al pastor, carnitas, Puebla pork | HISTORICAL RESEARCH | Banner added; retained |
| `research/PAIRING-MATRIX-V2.md` | Goa × Yucatán pork pairing; Punjab × Sonora beef | HISTORICAL RESEARCH | Annotated RESEARCH-ONLY |
| `research/MEXICAN-CULINARY-BENCHMARKS.md` | El Califa beef taco; birria beef form; al pastor pork; carnitas | COMPETITOR/HISTORICAL | Retained; birria line annotated |
| `research/RESEARCH-QUALITY-AUDIT.md`, `INDIA-MEXICO-HISTORICAL-CONNECTIONS.md`, `SOURCES.md`, `RESEARCH-BACKLOG.md` | Al pastor / birria source notes | HISTORICAL RESEARCH | Retained |
| `research/AUSTIN-COMPETITIVE-LANDSCAPE.md` | "pastor" = founder's occupation (Lazarus) | FALSE POSITIVE | None |
| `brand/BRAND-WORLDS.md` | al pastor as migrant-technique example | HISTORICAL RESEARCH | Retained |
| `research/HISTORICAL-CLAIMS-AUDIT.md`, others | none beyond the above | n/a | n/a |

**Indirect derivatives** (lard, stocks, gelatin, rennet, fining): not found as menu text; specified as supplier/recipe rules in `food/DIETARY-POLICY-AND-INGREDIENT-SPEC.md`.
**Open check:** flour-tortilla supplier lard status, refried-bean method, cheese rennet, brewery fining agent (all `[TEST]`/supplier).
**Result:** no current-product file contains an unmarked beef or pork item.
