# NASHA analytics mart: evaluation

**SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.** NASHA has no restaurant, customers, sales, suppliers or staff. Prices, costs and recipes are placeholders or assumptions. Nothing here is a business result.

Every figure below is read from `lab/results/analytics/*.json` by `analytics/render_docs.py`. Same-author caveat: one author wrote the generator, the injected defects, the simulations, the rules and this evaluation; there is no independent review.

## 1. Mart integrity

Reconciliation equalities holding: 8 of 8. Orphan foreign keys: 0. Duplicate grain rows: 0. SCD2 problems: 0. Order lines outside their SCD2 window: 0.

| Check | Left | Right | Equal |
|---|---|---|---|
| orders: src = mart | 3983 | 3983 | True |
| order lines: src = mart | 10010 | 10010 | True |
| raw orders = mart + quarantined | 4047 | 4047 | True |
| raw order lines = mart + quarantined | 10143 | 10143 | True |
| gross sales: src = mart (cents) | 15468100 | 15468100 | True |
| order totals: src = mart (cents) | 15468100 | 15468100 | True |
| findings: src = mart | 83 | 83 | True |
| PO qty received = receipts in snapshots (<= last snapshot) | 1780.6 | 1780.6 | True |

## 2. Metric reconciliation (semantic layer)

14 of 14 metrics agree between the mart definition and an independent source-side definition (tolerance 1e-6).

| Metric | Groups | Max abs difference | OK |
|---|---|---|---|
| orders | 3 | 0.0e+00 | True |
| gross_sales_usd | 3 | 0.0e+00 | True |
| units_sold | 3 | 0.0e+00 | True |
| avg_order_value_usd | 3 | 0.0e+00 | True |
| items_per_order | 3 | 0.0e+00 | True |
| food_share_of_sales | 3 | 0.0e+00 | True |
| gobi_attach_rate | 3 | 0.0e+00 | True |
| theoretical_usage_kg | 3 | 0.0e+00 | True |
| contribution_margin_usd | 3 | 0.0e+00 | True |
| logged_waste_rate | 3 | 0.0e+00 | True |
| count_variance_pct | 3 | 0.0e+00 | True |
| supplier_on_time_rate | 5 | 0.0e+00 | True |
| avg_actual_lead_time_days | 5 | 0.0e+00 | True |
| dq_quarantine_rate | 1 | 0.0e+00 | True |

Caveat: for the metrics whose source-side definition is Python (usage, margin, waste, count variance, supplier timing) the Python re-derives from the same seeded simulation, so agreement checks the SQL load path, not the realism of the simulation.


## 3. SQL library (24 queries) and difficult cases (10)

| Id | Title | Rows returned |
|---|---|---|
| Q01 | Cumulative gross sales per site | 168 |
| Q02 | Week-over-week change and next-day look-ahead | 168 |
| Q03 | Seven-day moving average of daily orders | 168 |
| Q04 | Order-value quartiles and their share of sales | 4 |
| Q05 | Top three items per site by gross sales (ties kept) | 9 |
| Q06 | Weekly food-unit mix across the dish rename | 8 |
| Q07 | Contribution margin by item version (ASSUMPTION costs) | 11 |
| Q08 | Item pair affinity (support and lift) | 45 |
| Q09 | Weekly guest-cohort retention (SYNTHETIC guests) | 36 |
| Q10 | Inventory exception funnel (count event -> exception -> approval -> resolution) | 4 |
| Q11 | Latest days of cover versus supplier lead time | 24 |
| Q12 | Logged waste by ingredient and reason | 8 |
| Q13 | Supplier delivery reliability | 5 |
| Q14 | ABC classification of items by gross sales | 10 |
| Q15 | Missing site-days via a recursive calendar | 3 |
| Q16 | Streaks of above-average sales days (gaps and islands) | 42 |
| Q17 | Exact duplicate orders in the raw landing zone | 8 |
| Q18 | Near-duplicate orders by content signature (exact timestamp) | 8 |
| Q19 | Late-arriving facts and restated daily totals (inline fixture) | 3 |
| Q20 | Fan-out when joining an order header to its lines | 1 |
| Q21 | Median and 90th percentile of order value per site (no percentile function) | 3 |
| Q22 | Orphan keys in the raw landing zone | 8 |
| Q23 | Order header total versus the sum of its lines (raw landing) | 8 |
| Q24 | Line price versus item median price (raw landing) | 13 |

Each query has a test comparing its output with an independent Python or SQL computation (`tests/test_analytics_sql_library.py`). Findings from writing them:

- **Q08 (basket affinity): every pair lift is below 1 (0.8 to 1.0).** There is no planted affinity. The generator draws 1 to 4 *distinct* items per order, which mechanically lowers every pair's co-occurrence. This is a sampling artifact, not substitution behaviour; reading it as 'cannibalisation' would be wrong.
- **Q06 first draft returned a share of 1.0 for the renamed dish** because the `WHERE item_id='M04'` sat in the same SELECT as the window, shrinking the window's partition. The committed query computes shares in a CTE before filtering. This is one of the traps worth testing for.
- Q09 (cohort retention) and Q10 (funnel) run on SIMULATED guests and SIMULATED approval stages; their numbers describe the simulation processes only.


The ten difficult-case answer keys are private (not in this repository). Public check only: each fixture loads and each candidate-facing trap query executes. Correctness of the keys is verified privately when `NASHA_PRIVATE_KEYS` is set.

| Difficult case | Trap query executes | Trap rows returned | Private key files removed (sha256 in manifest) |
|---|---|---|---|
| 01_fan_out_double_count | True | 2 | 3 |
| 02_not_in_null | True | 0 | 3 |
| 03_scd2_boundary | True | 2 | 3 |
| 04_timezone_day_boundary | True | 3 | 3 |
| 05_duplicate_events | True | 1 | 3 |
| 06_orphan_keys | True | 2 | 3 |
| 07_returns_netting | True | 2 | 3 |
| 08_partial_month | True | 3 | 3 |
| 09_islands_with_duplicates | True | 2 | 3 |
| 10_ratio_of_sums | True | 1 | 3 |

## 4. Data-quality framework: detection of injected defects

SQL rules over the raw landing zone (`analytics/dqf.py`), 15 rules across completeness, validity, timeliness, uniqueness, consistency, referential integrity, range and policy; freshness and row-conservation are dataset-level checks. Scored on seeds 1 to 10, 8 injected defects per type per seed.

| Defect type (injected) | Found by any rule | Total | Recall (framework) | Recall (lab `dq.py`) |
|---|---|---|---|---|
| duplicate_order | 80 | 80 | 1.000 | 1.000 |
| forbidden_protein | 30 | 30 | 1.000 | 1.000 |
| future_timestamp | 80 | 80 | 1.000 | 1.000 |
| malformed_timestamp | 80 | 80 | 1.000 | 1.000 |
| missing_location | 80 | 80 | 1.000 | 1.000 |
| near_duplicate_order | 80 | 80 | 1.000 | 1.000 |
| near_duplicate_shifted | 80 | 80 | 1.000 | 0.000 |
| nonpositive_qty | 80 | 80 | 1.000 | 1.000 |
| order_total_mismatch | 80 | 80 | 1.000 | 1.000 |
| orphan_item | 80 | 80 | 1.000 | 1.000 |
| price_drift | 80 | 80 | 1.000 | 1.000 |
| unit_mismatch | 80 | 80 | 1.000 | 1.000 |

Per rule against its target defect type (precision counts every flag that is not a labelled defect of the target type; `other` = the flag is a different injected defect, `clean` = a flag on a row with no injected defect):

| Rule | Target | TP | FP other | FP clean | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| COMP-01 order site missing/unknown | missing_location | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| COMP-02 order timestamp missing | (control) | 0 | 0 | 0 | 0 | - | - |
| VALID-01 timestamp not parseable | malformed_timestamp | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| TIME-01 timestamp after as-of | future_timestamp | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| UNIQ-01 order_id appears more than once | duplicate_order | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| UNIQ-02 same site, timestamp and basket under another id | near_duplicate_order | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| UNIQ-03 same site and basket within 2 seconds under another id | near_duplicate_shifted | 80 | 80 | 0 | 0 | 0.500 | 1.000 |
| CONS-01 header total differs from sum of lines | order_total_mismatch | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| RI-01 line item not in menu | orphan_item | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| RI-02 line without a parent order | (control) | 0 | 0 | 0 | 0 | - | - |
| RANGE-01 quantity not positive | nonpositive_qty | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| RANGE-02 price outside 0.8-1.2 x item median (n >= 5) | price_drift | 80 | 3 | 0 | 0 | 0.964 | 1.000 |
| UNIT-01 count unit differs from ingredient's expected unit | unit_mismatch | 80 | 0 | 0 | 0 | 1.000 | 1.000 |
| RANGE-03 inventory quantity not positive or implausibly large | (control) | 0 | 0 | 0 | 0 | - | - |
| POLICY-01 forbidden ingredient token on a menu item | forbidden_protein | 30 | 0 | 0 | 0 | 1.000 | 1.000 |

- **Clean data (no injected defects), seeds 1 to 5:** 0 flags over 20,462 orders.
- Freshness: newest valid order 2026-04-26 vs as-of 2026-05-01 = 5 days (limit 7): pass. The as-of is the generator's scenario date, so this passes by construction.
- Row conservation through the lab pipeline (raw = modeled + quarantined): True.

**Honest reading.** Recall is 1.0 for all twelve types because the injected defects are simple, labelled by the same author, and the rules were written for them. Two things deserve candour: (1) the lab's own rules find 0 of 80 `near_duplicate_shifted` copies (they are shifted by one second); the framework catches them with a 2-second tolerance rule (UNIQ-03) that I added after seeing that miss, so it is *not* a blind result; (2) UNIQ-03 also flags the exact-timestamp copies, so its precision against its own target is 0.5 (no clean rows are flagged). The price rule flags 3 lines that are orphan items (a cross-flag, not a clean-row false alarm).

Defects the generator does *not* inject, planted by `dqf.novel_probe` without tuning any rule to them:

| Planted defect kind | Planted | Detected |
|---|---|---|
| duplicate_order_line | 10 | 10 |
| absurd_quantity | 10 | 10 |
| negative_inventory_qty | 10 | 10 |
| timezone_slip_5h | 10 | 0 |

The 5-hour timezone slip is structurally valid and **no rule can see it**. Duplicated lines and x100 quantities are detected only because the planted header total was left unchanged (consistency rule); a consistent forgery would pass. Real data would present many defect kinds that none of this has been exposed to.

## 5. Do the mart analyses recover what the simulation injected?

- **Unlogged shrink (L03 goat, 6% of usage, no waste entry):** observed net count variance -6.3% of usage. Rank among all 24 site x ingredient pairs by most negative variance: **2** (the top pair is L03 hops at -11.4% on only 1.1 kg of usage: small-quantity noise, a false lead). Among pairs with at least 20 kg usage: rank **1** of 21; across seeds 1 to 5 the rank is 1, 1, 1, 1, 1. A volume floor is needed to find it; without one the top hit is noise.
- **Unreliable suppliers (injected late probability S03 0.40, S05 0.25, others at most 0.10):** observed on-time order worst first: S03 0.64 (n=22), S05 0.71 (n=24), S02 0.91 (n=21), S01 0.96 (n=23), S04 1.00 (n=39). The two worst match the injected two: True. Sample sizes are 21 to 39 lines per supplier, so the middle of the ranking is not reliable.
- **About the menu-change date.** 2026-04-13 is a **SYNTHETIC SCENARIO DATE / DESIGN ASSUMPTION** chosen so orders exist on both sides of the SCD2 change inside the 56-day window. It is not a real menu-change date. No existing NASHA source proves one: a search of `lab/` and the repository docs found only D-84 (2026-10-15), which records the design direction (Mango Habanero Gobi, an appetizer, replacing the Gobi Taco concept) and no effective date; nothing has been cooked or sold.
- **Recipe change through SCD2:** corn masa theoretical usage 6.633 kg/day (all sites) before the SYNTHETIC SCENARIO DATE 2026-04-13 (design assumption, not a real date) and 5.35 kg/day after, because the v2 dish drops the tortilla. The SCD2 as-of join is what makes this appear.

## 6. Contribution margin (ASSUMPTION costs) and its sensitivity

| Item version | Units | Sales (USD, placeholder prices) | Margin (USD, assumed costs) | Margin per unit (USD) |
|---|---|---|---|---|
| M05 Butter Chicken Quesadilla | 1516 | 22,760 | 18,256 | 12.04 |
| M01 Chicken 65 Totopos | 1470 | 20,593 | 16,813 | 11.44 |
| M03 Goat Birria | 1443 | 23,102 | 16,622 | 11.52 |
| M02 Paneer Tikka Taco | 1485 | 19,305 | 15,236 | 10.26 |
| M04 Gobi Taco | 1156 | 13,872 | 11,803 | 10.21 |
| B03 Amber | 1539 | 12,218 | 9,779 | 6.35 |
| B01 Signature Hefe | 1480 | 11,723 | 9,377 | 6.34 |
| B02 Lager | 1556 | 10,788 | 8,322 | 5.35 |
| N02 Tamarind zero-proof | 1537 | 8,445 | 7,062 | 4.59 |
| N01 Lime zero-proof | 1484 | 7,434 | 6,098 | 4.11 |
| M04 Mango Habanero Gobi | 370 | 4,440 | 3,811 | 10.30 |

Uniform +/-25% change in all assumed costs: ranking identical across multipliers = **False**; top three identical = **False**. Why this can or cannot be invariant: with uniform multiplier m each item has margin_i(m) = S_i - m*C_i (sales S_i, assumed cost C_i), a straight line in m, so two items swap rank exactly when m = (S_i - S_j)/(C_i - C_j) lies inside the tested range. A uniform scaling does NOT structurally preserve the ranking (it would only if the cost-to-sales ratio were identical across items); the flags above are measured results, not guarantees. The ordering by *total* margin is also driven by exposure (the pre-change `Gobi Taco` version has six weeks of sales, `Mango Habanero Gobi` two), so compare per-unit margin. Margins of 70 to 80% for food reflect that labour, rent, overhead and waste cost are **excluded**; this is an illustration of the calculation, not a margin NASHA would earn.

## 7. Forecast backtest (rolling origin)

Series: theoretical daily usage per site x ingredient (24 per seed) for seeds [1, 2, 3, 4, 5]. Expanding window, forecast horizon 7 days, origins at days [28, 35, 42, 49] (minimum 28 training days), 480 seven-day forecasts per model. **The data are synthetic, so these accuracies say nothing about real demand.**

| Model | MAE (kg) | WAPE | MAPE % (non-zero days) | Bias % of actual | WAPE vs naive (95% CI) | WAPE vs seasonal naive (95% CI) | 80% interval coverage |
|---|---|---|---|---|---|---|---|
| naive | 0.656 | 0.462 | 68.4 | 19.1 | baseline | +0.048 [+0.026, +0.069] | 0.756 |
| seasonal_naive | 0.589 | 0.414 | 56.3 | 1.9 | -0.048 [-0.069, -0.026] | baseline | 0.795 |
| moving_average_7 | 0.480 | 0.338 | 48.7 | 1.9 | -0.124 [-0.145, -0.103] | -0.077 [-0.088, -0.065] | 0.790 |
| seasonal_mean | 0.470 | 0.331 | 46.4 | 2.3 | -0.131 [-0.153, -0.109] | -0.084 [-0.094, -0.072] | 0.795 |
| ses | 0.487 | 0.343 | 51.5 | 6.6 | -0.119 [-0.139, -0.100] | -0.072 [-0.084, -0.060] | 0.793 |
| holt_winters_add | 0.487 | 0.342 | 48.2 | 2.0 | -0.119 [-0.141, -0.098] | -0.072 [-0.081, -0.062] | 0.820 |

- Best by WAPE: **seasonal_mean** at 0.331 versus 0.462 for last-value naive (28% lower) and 0.414 for seasonal naive. Differences among the four smoothing models are small compared with the gap to naive; the intervals above were computed only against the two naive baselines, so do not read the ranking among the smoothers as established.
- **Surprise:** seasonal naive (copy the same weekday last week) is much worse than a plain 7-day average. Daily ingredient usage is dominated by random basket composition, and the weekday effect (Friday to Sunday x1.3 orders) is small relative to that noise. Seasonal naive wins on only 53% of units against naive.
- **Intervals:** a normal interval from in-sample one-step errors was nominal 80%; empirical coverage is in the last column (0.76 to 0.82), so calibration is acceptable on this synthetic data. It would not be assumed on real data.
- Bias is positive for naive (it follows the last day, including the Friday to Sunday peak). Hops and malt are identical series up to scale, which inflates the apparent number of independent series; origins within one series are also not independent, so the bootstrap intervals are optimistic.
- Corn masa contains a structural break (recipe change). WAPE at the last origin: naive 0.354, seasonal_naive 0.322, moving_average_7 0.296, seasonal_mean 0.326, ses 0.341, holt_winters_add 0.294. No model was given the break; this is the case where a metric definition change, not a forecaster, matters most.

## 8. Synthetic experiment: does the analysis recover the injected effect?

SIMULATED experiment on synthetic guests with an injected effect. No real guests, no real placement test. Unit: synthetic guest; 341 guests (176 treated, 165 control; SRM chi-square p = 0.55). Effect injected: each order of a treated guest gains one M04 unit with probability 0.1; all else unchanged. Primary metric: m04_units per guest in the experiment window. Guardrails / negative controls (true effect zero): orders, other_food_units, spend_usd. Multiplicity: primary tested alone at 0.05; the 3 guardrail metrics are a Holm-corrected family at 0.05.

**A-priori power.** Pre-period sd of M04 units per guest = 1.76; with 170 guests per arm the minimum detectable effect (80% power, alpha 0.05, unadjusted) is **0.53 units per guest**. The injected truth is **0.226** units per treated guest, well below the MDE. About 955 guests per arm would be needed for 80% power at that effect. The design is **underpowered by construction**; I left it that way to report the consequence. It is kept unchanged as historical evidence and is **not retroactively resized**. A separate prospective sample-size design (80% and 90% power, unadjusted and CUPED, with a Monte Carlo confirmation and a sensitivity table) is in [`ANALYTICS-PROSPECTIVE-DESIGN.md`](ANALYTICS-PROSPECTIVE-DESIGN.md).

| Estimator (primary metric) | Estimate | 95% CI | p | CI contains truth |
|---|---|---|---|---|
| unadjusted | 0.282 | [0.012, 0.552] | 0.041 | True |
| cuped | 0.301 | [0.037, 0.566] | 0.026 | True |
| stratified | 0.300 | [0.027, 0.572] | 0.031 | True |

Single run (truth 0.226): the estimates overshoot the truth and are nominally significant at 0.05 in an experiment with about 38% power: the classic winner's-curse situation. CUPED variance reduction on the primary metric is only 4.1% (pre/post correlation 0.20): **CUPED is not justified here**; guests' short pre-periods carry little information.

**Repeated randomisation + injection (1000 reps) on this guest panel:**

| Estimator | Mean estimate (truth 0.226) | Bias | SD of estimate | 95% CI coverage | Power (reject rate) | A/A false-positive rate |
|---|---|---|---|---|---|---|
| unadjusted | 0.230 | +0.004 | 0.140 | 95.1% | 37.7% | 4.9% |
| cuped | 0.230 | +0.004 | 0.135 | 95.3% | 38.8% | 4.6% |
| stratified | 0.231 | +0.005 | 0.139 | 95.3% | 38.1% | 4.6% |

The analysis **recovers the injected effect without bias and with near-nominal coverage**; power at this effect size is 38% (unadjusted), CUPED/stratification changing it by only a few points. Guardrail family (3 metrics, true effect zero): chance of at least one false positive is 9.4% uncorrected vs 2.2% with Holm (A/A: 7.0% vs 2.8%).

**Process note (a failure caught by this check).** My first version of the experiment code indexed the wrong column, so the 'primary metric' was actually orders per guest. The Monte Carlo recovery check showed a bias of minus the injected effect and a large false effect on 'orders'; fixing the column mapping gave the results above. A recovery test on a known injected effect is the reason that was found.

**Causal limitations (what this cannot show):**

- Randomisation is simulated; the 'effect' is whatever the injection code says. Recovering it proves the ANALYSIS is unbiased on this data-generating process, not that any real menu change works.
- No guests exist: guest ids come from a seeded assignment process (config.GUEST_*). Real repeat-visit dynamics, interference between guests at one table, novelty effects and seasonality are absent.
- The effect is on a single appetizer count; cannibalisation, margin and long-run retention are not modelled, so the experiment cannot say whether the change is good for the business.
- Only 4 weeks and a few hundred guests: heavy tails, repeated visits per guest and new guests arriving after assignment are handled crudely (new guests have a pre-period covariate of zero).
- Monte Carlo coverage is relative to the finite-population truth of this guest panel (fixed baseline behaviour, random assignment and injection), i.e. randomisation inference, not a superpopulation claim.
- Same author wrote the injection and the analysis (no independent review).

## 9. Failures, surprises, and limits

- Lab DQ rules miss every one-second-shifted near-duplicate; the new rule that catches them was written after seeing that.
- Net count variance for tiny-quantity ingredients (hops) is noisy and produced the top false lead for the injected shrink.
- Seasonal naive lost to a plain moving average; the generator's weekday signal is weak against basket noise.
- The synthetic experiment is underpowered at its injected effect, CUPED barely helps, and the one observed run overstates the effect.
- Q08 lifts below 1 are a generator artifact; Q06's first draft had a window-before-filter bug; the experiment code's first draft had a column-mapping bug.
- Contribution-margin ordering by total margin is exposure-driven for the SCD2 dish; costs are assumptions.
- Everything in sections 5 to 8 uses simulations whose parameters are in `analytics/config.py`; agreement with them shows the analysis code works, not that the world behaves that way.

## 10. Dashboard check

`lab/results/analytics/dashboard.html` is static and has no external requests. See the screenshot check recorded in `lab/results/analytics/dashboard_check.json` (generated by `analytics/dashboard_check.js`).

