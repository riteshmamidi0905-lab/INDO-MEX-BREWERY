# Evidence intake: where each real input goes (one page; no new databases)
When a real input arrives, send it to Claude as it is. Claude files it with the tool below, keeps the original untouched, and never fills a gap with a guess (missing = NOT MEASURED / NOT PROVIDED). Nothing here is populated today; every file named is a header-only template or an existing recorder.

| Real input | Preserve the original | Record it in | Tool / check |
|---|---|---|---|
| Food photographs (Session 1-5) | the originals folder the tool creates for each run (read-only, SHA-256); edits and web exports kept separate | the `provenance.csv` the tool creates beside the originals | `tools/photo_ingest.py` (blur/exposure flags are screening only; a human reviews) |
| Temperatures, weights, times, scores, failure codes | the paper sheets (photograph them) | Session 1: `food/t1-results/t1-results.csv`; Sessions 2-5: `food/sessions/results.csv` | `tools/t1_record.py`, `tools/session_record.py` (frozen gates; real_cook rows only), `tools/experiment_stats.py` (small-n guard) |
| Index of each real iteration | n/a | `ops/rd/iteration-log.csv` (IDs like FOOD-C65-001) | ties the rows above together |
| Ingredient receipts and actual expenses | the receipt photo or file, untouched | `ops/templates/expenses-receipts.csv` (flag name-dependent spend) and prices into `food/costing/ingredients.csv` with `price_class` | `tools/food_costing.py` (refuses unit mismatches; flags non-quote prices) |
| Supplier quotes | the email or document verbatim | `ops/templates/vendor-rfq-comparison.csv`; equipment in `ops/templates/capex-quotes.csv` | one quote is never a market average |
| Professional or advisor feedback (brewer, culinary advisors, attorneys, architect, glass maker) | raw reply saved FIRST in `docs/professional-reviews/raw/` | `docs/professional-reviews/RECORD-TEMPLATE.md` copy, then `docs/decisions/DECISIONS.md` if a decision changes | advisory vs sign-off recorded; a cautious legal answer is never rewritten as clearance |
| Customer interviews and tastings | paper forms kept outside git; consent noted | interviews: `research/customer-discovery/responses.csv`; tastings: `tasting-responses.csv`; quotes: `coded-quotes.csv`; purchases and return intent: `purchase-conversion-tracker.csv`, `repeat-intent-tracker.csv` | `research/customer-discovery/analyze_interviews.py`; synthetic data only for form tests, tagged SYNTHETIC-FORM-TEST, never counted |
| Events and sales (first real event) | POS or tally sheet | `validation/traction-event-log.csv` | `validation/analyze_traction.py` |
| Legal, regulatory or site documents | the document as received | `docs/professional-reviews/` record; questions stay in `docs/company/data/regulatory-question-tree.csv` | record jurisdiction, date, question, assumptions |
| Third-party data or datasets | download untouched | `ops/templates/dataset-provenance.csv` | tier T0-T4 stated |
| Contacts | n/a | `ops/templates/founder-crm.csv` (consent_to_store first) | no outreach without founder approval |
Rules: photos and receipts are never edited (crop/exposure/white balance/rotation only on derivatives, recorded); never use AI to enhance or replace evidence; failures are kept; scores and gates change only under their own rules; after any real input, re-run `python3 tools/validate_repo.py`.
