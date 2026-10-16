# NASHA operations analytics: executive memo

**SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.** NASHA has no restaurant, customers, sales, suppliers or staff. Prices, costs and recipes are placeholders or assumptions. Nothing here is a business result.

**To:** founder. **From:** analytics workstream (P4). **Basis:** a 56-day synthetic operation of three scenario sites, a simulated supply chain, and assumed prices and costs. **Status:** conditional guidance for designing NASHA's data capture and decision rules, not a statement about demand or profit.

## Bottom line

Nothing here measures how NASHA would perform. What the exercise shows is which questions the data model can answer, how reliable the answers are when the truth is known, and what a real operation would need to record. Recommendations are ranked by how well the evidence supports them and each says what would invalidate it.

## Ranked recommendations (all conditional)

1. **Decide the data capture before the first service, not after.** Record receipts with dates, a waste log with reasons, weekly counts and purchase orders from day one. In the simulation, an unlogged 6% shrink on one ingredient was found (rank 1 of 21 candidate pairs; ranks across seeds 1 to 5: 1, 1, 1, 1, 1) *only* because counts, receipts and recipe-based usage existed. *Invalidated if* real counts are too noisy (the simulation used +/-3%) or recipes are far from the placeholders.
2. **Adopt the metric definitions and reconciliation tests as the starting contract** (`metrics.json`: 14 of 14 metrics reconcile mart to source). Cheap, and it removes arguments about what a number means. *Invalidated if* the real point-of-sale system cannot supply order-line grain.
3. **Track supplier on-time delivery as a first-class measure.** The query recovered the two suppliers whose lateness was injected (worst two = S03, S05), from only 21 to 39 deliveries each. *Invalidated if* real delivery windows are not recorded per line.
4. **Use simple forecasts and cover rules, and do not buy forecasting software yet.** On synthetic usage a 7-day average cut error (WAPE) from 0.46 (last day) to 0.34, and the best baseline reached 0.33. Daily usage is noise-dominated, so expect forecast error of this order even with a good model. Pair the forecast with days-of-cover against supplier lead time. *Invalidated if* real demand has strong, stable seasonality, which this data cannot show.
5. **Before changing the menu card for the Mango Habanero Gobi appetizer, size the test.** The simulated placement test (effect: one extra appetizer in 10% of treated guests' orders) needed roughly 955 guests per arm for 80% power; with 170 per arm its power was about 38% and the one observed run overstated the effect. Plan the sample from the pre-period variance and pre-register one primary metric. *Invalidated if* the real unit of randomisation is a table or a shift, which changes the variance entirely.
6. **Treat contribution margin as a template.** Under assumed costs the appetizer's margin per unit is $10.30 (new version) vs $10.21 (old taco version), a difference of little consequence; the item ordering was not stable even at the top under +/-25% on all costs. Real costs, labour and waste must replace the assumptions before any item decision. *Invalidated by:* real recipe costing, which does not exist yet.

## Risks

- Same-author synthetic evaluation: a clean result mostly proves the code does what its author intended. Example: every injected defect type was detected, while a defect type the author had not injected (timezone slip) was missed entirely.
- Over-reading simulated processes (guest retention, approval funnel, waste rates) as behaviour.
- A volume floor is needed for exception ranking; tiny-quantity ingredients generate false alarms.

## Data needed in a real operation

Point-of-sale order lines with timestamps and voids/returns; item master with dated changes; counts with unit and counter id; receipts and purchase orders with promised and actual dates; waste log with reason; costed recipes; supplier contracts; guest or loyalty identifier only with consent; staffing and opening hours for exposure normalisation.

## NOT CLAIMED

- Any real sales, revenue, margin, cost, demand, price acceptance or customer behaviour. NASHA has none.
- That the appetizer will sell, be profitable, or beat the taco it replaced.
- That the supplier reliability, waste rates, retention or approval rates are real; all are simulated.
- That forecast accuracy transfers to real data.
- That the data-quality rules would work on real data or that recall of 1.0 is meaningful outside this generator.
- Production deployment, users, or any business impact. Nothing here is deployed.

Evidence: `lab/docs/ANALYTICS-EVALUATION.md`, results in `lab/results/analytics/`, reproducible with `python -m analytics.run_all`.
