# D-84 migration log (Block 4.5, 2026-10-15)

Item-level change: **Mango Habanero Gobi** is an appetizer / shareable, not a taco, no tortilla. Internal id `gobi-taco` is kept as a legacy key (D-76 session gates hash it); display names and content migrated.

## Founder status (2026-10-15, final pre-merge)
D-84 APPROVED. Mango + habanero is the approved flavour DIRECTION. The exact recipe, including the mango-habanero glaze replacing the earlier tamarind-guajillo glaze, is an UNTESTED DESIGN HYPOTHESIS until founder cooking/testing. Cost: NOT COSTED / UNVERIFIED. Allergen validation: NOT COMPLETED. Sensory: NOT TESTED.

## Migrated (current state)
Core 5 matrix and narrative, allergen matrix (provisional, NOT validated), costing structure (`recipes.csv`: tortilla/slaw/onion rows removed, mango/habanero rows added, **no quantities**; `ingredients.csv`: two unpriced rows), kitchen capacity (comal range 0 = ASSUMPTION), business-plan data (`docs/company/data/*`), research/product-system, operational requirements, cultural-review pack, beer pilot briefs, generated docs (regenerated), website data, website family site (the withdrawn taco picture is replaced by a placeholder), synthetic enterprise menu v2, retrieval knowledge ("current" corpus), lab scenario fixtures (menu v2).

## Historical / unchanged on purpose
D-55/D-75/D-76 text, `food/sessions/*` (banner only), `OPENING-MENU-V2`, `MENU-DEVELOPMENT-MATRIX-V1`, `MENU-STORYTELLING-V1`, `OPENING-BEER-PROGRAM-V1` (banner only), visuals/vision provenance and manifests, validation logs, literature ledger, the frozen Block 3 baseline, scenario registry, question sets, result files, and the gzipped Block 3 corpus snapshot.

## Not done (no fabrication)
No recipe test, costing, allergen review, sensory result or pairing re-derivation exists for the new dish. Carried-over complexity/pairing scores are labelled UNVERIFIED. Fryer/char capacity ranges are unchanged assumptions.
