---
name: nasha-core-product-review
description: Review one NASHA Core 5 food or beer end to end (heritage, culture, chef or brewer, food science, operations, pairing, evidence) and update the canonical matrices without claiming results. Use when a Core 5 product changes or a new physical result arrives.
---
# NASHA Core 5 product review
Canonical files: `food/CORE5-FOOD-MATRIX.csv`, `beer/CORE5-BEER-MATRIX.csv`, `food/CORE5-PAIRING-MATRIX.csv`, `research/CORE5-PRODUCT-SYSTEM.md`, decision D-75 (`python3 tools/nasha_search.py decision D-75`).
1. FIND: `python3 tools/nasha_search.py q "<product>" --food` (or `--beer`, `--evidence`). Read the product's matrix row first; do not re-research what the row already records.
2. HERITAGE AND CULTURE (food): agents indian-culinary-heritage-expert and mexican-culinary-heritage-expert; classify each element HS / CI / MF / OHC / UAR; never state a definitive origin; log claims in `research/heritage/HERITAGE-CLAIMS.csv` and sources in the ledger. Cultural-authenticity-auditor checks website copy drift.
3. CRAFT: executive-fusion-chef (food, three-yes test) or master-brewer (beer, brief not recipe); brewery-operations-engineer for capacity questions (G-6 open).
4. SCIENCE: food-scientist; literature via Consensus into `python3 tools/lit_ledger.py add ...` (peer-reviewed abstracts are T1; never fake product evidence).
5. OPERATIONS: restaurant-operations-director (station load, holding, MVP format fit, CONCEPTUAL labels).
6. PAIRING: edit the attr_* columns only with a stated reason, run `python3 tools/pairing_matrix.py write`, and keep the label PAIRING HYPOTHESIS, NOT SENSORY TESTED. Record disagreements between heuristic and expert picks; do not tune attributes to force an answer.
7. REAL RESULTS: only real rows in `food/t1-results/` change a status; D-74 thresholds are frozen; run `python3 tools/t1_record.py` and `python3 tools/experiment_stats.py`.
8. GATES: `python3 tools/validate_core5.py`, `python3 tools/validate_repo.py`, D-54 (`python3 tools/diet_audit.py`), then `/nasha-evidence-audit`. Evidence and design scores move only per their rules.
