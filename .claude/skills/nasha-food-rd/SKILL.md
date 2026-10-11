---
name: nasha-food-rd
description: Route a NASHA dish through heritage research, chef review, food-science review and test design before any claim of a result. Use when a new dish, construction or iteration is proposed.
---
# NASHA food R&D routing

1. HERITAGE: separate COMMON MODERN PATTERN / REGIONAL VARIATION / CONTESTED ORIGIN / NASHA R&D CHOICE. Use research/heritage/HERITAGE-CLAIMS.csv and ledger rows V-59.. ; never state a definitive origin. Agents: indian-culinary-heritage-expert, mexican-culinary-heritage-expert.
2. D-54 check on every ingredient and hidden derivative (`python3 tools/diet_audit.py`). Allergens go in food/ALLERGEN-MATRIX.csv; no allergen-free claim.
3. CHEF: agent executive-fusion-chef (three-yes test: India yes, Mexico yes, NASHA yes). Kitchen feasibility, second person, probe thermometer (74 C / 165 F).
4. FOOD SCIENCE: agent food-scientist gives hypotheses and what to measure; it never predicts a score.
5. TEST DESIGN: agent sensory-scientist. Frozen rules are not edited after tasting; new rules are new decisions for the next session. Randomize with `python3 tools/t1_randomize.py <run>`; record with `python3 tools/t1_record.py`; analyse with `python3 tools/experiment_stats.py` (n<8: raw values only, "small directional R&D panel").
6. QUANTITIES: `python3 tools/recipe_scale.py` (yields are ASSUMED until weighed). COSTING: `python3 tools/food_costing.py` (no invented prices).
7. Outcome language: PROTOTYPE at most after a first cook; never "tested recipe" without scored rows.
