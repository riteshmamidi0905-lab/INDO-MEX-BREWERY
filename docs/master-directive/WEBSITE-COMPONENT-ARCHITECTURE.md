# Website component architecture (plan for the next milestone; not built)

Builds on the existing static pipeline (`website/build.py`, `website/data/*.json`, `website/src/styles.css`, dist QA via Playwright + axe). No framework is added (D-63).

## Data-driven collections
`website/data/products.json` (new): one record per product with `id`, `kind` (beer | dish | goods), `name_token` (the working name comes from one field, D-79/80), `status` (CONCEPT / DESIGNING / BACKLOG), `evidence_label`, `claims_not_made[]`, `asset_ids[]`, `source_docs[]`, `pairings[]`. Pages are generated from it, so a rename or a status change is one edit.
## Components
`ProductHero` (art + status chip + disclosure), `SpecTable` (ranges labelled hypotheses), `PairingHypothesis` (always says untested), `DisclosureBanner` (synthetic/concept, on every page), `AssetFigure` (picture element, AVIF/WebP/PNG, alt text, "Concept visualization" corner tag, provenance link), `StatusChip`, `EvidenceLink` (to the repo file), `DemoCommerceNotice` (no cart, no payment; only a labelled mock if ever added).
## Pages
Home, Story, BADSHAH, PAAPI, Kitchen (Core 5 + R&D candidates), Goods (two hoodies + tees), Spaces, Labs, Enterprise (simulation + warehouse + assistant), Engineering showcase.
## Gates (unchanged, run by `website/qa/run-qa.mjs`)
axe dark+light, overflow 320-1920 px, weight budget, reduced motion, keyboard path, noindex while any AI-made raster or the working name is present; the asset validator must pass before an asset enters `dist/`.
## Next step
Add `products.json`, generate the three collection pages from it with the existing build, import only validated assets from `visuals/concepts/` (web derivatives in a separate folder), run the QA suite.
