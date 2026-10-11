# Document map (what to read NOW; the repository is large, you do not need most of it)
Classes: CANONICAL, SUPPORTING, HISTORICAL, SUPERSEDED, ARCHIVE CANDIDATE. Nothing is deleted; superseded and historical files carry a one-line header pointing to what wins. Authority order: `docs/decisions/DECISIONS.md` > `research/CORE5-PRODUCT-SYSTEM.md` > the Core 5 CSV matrices > everything else. Full list with reasons: `docs/company/data/document-map.csv`.

**Read now, in order:** 1. `docs/FOUNDER-ACTION-BOARD.md` 2. `food/t1-test-sheets/15-SESSION-1-CHECKLISTS.md` (and the card `14-...FOUNDER-MODE.md`) 3. `docs/send-packs/` 4. `docs/FOUNDER-CONTROL-CENTER.md` 5. `docs/decisions/DECISIONS.md` (D-62, D-75 to D-80 only) 6. `research/CORE5-PRODUCT-SYSTEM.md` 7. `docs/company/NASHA-CONFLICT-FACTS.md` 8. `beer/pilot-briefs/00-BREWER-HANDOFF.md` 9. `docs/CULTURAL-REVIEW-PACK.md`.
**Tools:** one command validates everything: `bash tools/validate_all.sh`. One tool ingests real inputs: `python3 tools/intake.py` (and `route` shows where each kind goes). Tool list: `docs/tools/TOOL-MAP.md`.

## Added in Sprint 22 (D-81 pre-capital build; all CANONICAL, generated from CSV data by `tools/blueprint_views.py`)
`docs/BLUEPRINT-STATUS.md` (start here for the pre-capital picture), `docs/BUSINESS-MODEL-CONTROL.md`, `docs/PRODUCT-BIBLE.md`, `docs/OPERATING-BLUEPRINT.md`, `docs/INVESTOR-DATA-ROOM.md`. Fix facts in the CSV sources (`docs/company/data/bm-*.csv`, `bp-*.csv`, and the matrices), never in these views.
