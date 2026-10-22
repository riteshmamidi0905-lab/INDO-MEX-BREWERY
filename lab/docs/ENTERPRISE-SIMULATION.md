# Enterprise simulation (14 sites, 24 months): documentation

**SYNTHETIC DATA / SIMULATED OPERATION.** No business, customer, employee, sale or product exists. Ids are fictional; no names, emails or addresses. Prices, wages and volumes are placeholder planning inputs and are **UNCALIBRATED**: they have not been compared with public industry benchmarks, so none of the totals say anything about a real business. Scenario dates are not real time.

Code: `lab/nasha_lab/enterprise_sim.py`. The 3-site, 56-day baseline generator (`nasha_lab/generator.py`) is untouched and remains the byte-for-byte fixture for the existing evaluations.

## Run
`python -m nasha_lab.enterprise_sim --profile dev --out /tmp/sim-dev` (3 sites, 2 months, ~6,000 orders, ~1 s) or `--profile full` (14 sites, 24 months). `SimConfig` makes every size a parameter (sites, months, target orders, loyalty profiles, employees, seed). Output: gzip CSVs with zero mtime plus `manifest.json` (config, row counts, sha256 per file, timings).

## Tables
locations (format, size factor, open date, hourly capacity), menu_items (baseline catalog + concept SKUs labelled never brewed/never sold), suppliers, promotions, loyalty_profiles, employees, orders, order_lines, returns (merch), inventory_counts (weekly), waste_events, quality_events, shifts (scheduled vs actual labor hours), brew_batches (beer gardens; "simulated batch, never brewed").

## Assumptions (all placeholders)
Growth ramp +35% over the horizon; seasonal sine (+/-12%); weekday factors (Fri-Sat highest); sites open over the first 18 months with a 60-day ramp; hourly demand curves differ by format; 38% of orders carry a loyalty member (older members more active); six promotions applying to a share of loyalty orders; a 4% price step on 2025-01-01; happy hour 15:00-17:00 beer -10%; merchandise appears in about 1.2% of baskets at merch-selling sites with an 8% return rate; waste, quality events and brew yield are random draws. Capacity: orders above a site's hourly limit queue into later hours (three passes); what still exceeds it is counted, not hidden.

## Measured (this sandbox: 4 cores, 15 GB RAM; numpy 2.5.3, pandas 3.0.5)
Full profile, seed 20261022: **2,499,173 orders, 5,750,211 order lines, 150,000 loyalty profiles, 450 employees, 14 sites, 730 scenario days**; generation **46.9 s**, peak memory **about 1.4 GB**, **49.6 MB** on disk (gzip), integrity check **31.9 s with 0 problems**. 34,705 orders (1.4%) still exceed an hour's site capacity after queueing. Placeholder revenue total 7.65 billion cents (about 76.5 M dollars of placeholder-priced sales; average ticket about 30.6 dollars) is an artifact of placeholder inputs, not a forecast.
Not measured: runtime on other hardware; memory with other pandas/numpy versions; any warehouse load time.

## Checks (`enterprise_sim.check`)
unique order ids; every line has an order and a known item; positive qty and price; subtotal equals line sum; total equals subtotal minus discount; members exist and joined before ordering; employees and orders reference known sites; no order before a site opens; no forbidden protein terms in the catalog. 7 tests cover determinism, seed sensitivity, baseline preservation, corruption detection, labelling and manifest content.

## Calibration findings (2026-10-22): LOW-CONFIDENCE leads, not a calibration
A public-source pass (web-search summaries; no primary page could be opened; publication years mostly inferred) found the following. Treat every row as a lead to verify before it drives a parameter.
| Parameter | Simulation (full profile) | Public lead | Source and confidence |
|---|---|---|---|
| Average ticket | about $30.6 (placeholder prices) | about $21.80 for one fast-casual chain (Q2 2025); segment average NOT FOUND | Advan Research; low |
| Orders per site per day | about 245 | fast-casual AUV about $2.8-2.9M (Cava, Sweetgreen, 2024), consistent with the simulated annual sales per site | MarketBeat; medium for AUV |
| Loyalty member share of orders | 38% | 75th percentile 30%, 90th about 37% or more of transactions | Paytronix 2024; medium |
| COGS % of net sales | about 27% | food cost about 31-33% (garbled table, undated) | vendor page; low |
| Labor % of net sales | 16-29% by site | prime cost about 60% limited service (labor not isolated) | Toast, 7shifts; medium for prime cost only |
| Waste | about 0.4% of COGS | 4-10% of purchased food (primary source NOT FOUND; NRA attribution unconfirmed); check that the simulation counts the same thing | several secondary pages; low to medium |
| Employees per site | about 32 (450 / 14) | about 17.8 for limited service (derived from an aggregator; low); the directive fixes about 450 employees | low |
| Beer margin | n/a | Brewers Association survey: average beer gross margin 41% (2023 data), implying about 59% COGS | BA via Brewbound; medium |
**Decision.** The `full` profile is unchanged. A `calibrated` profile moves three parameters toward the leads: loyalty share 0.30, list prices x0.78 (ticket about $24), waste x10 (waste near the cited 4-10% range). Employees, labor and COGS are NOT changed (leads too weak). Everything else stays a placeholder. Re-verify each source against its primary document before quoting any figure.

## Remaining capacity-model limits
Orders above a site's hourly capacity queue into later hours for up to three passes; at full scale 34,705 orders (1.4%) still exceed capacity afterwards, concentrated in peak hours of the busiest sites. There is no balking or lost-sales model, no kitchen-throughput model by item, and no staff-constrained capacity; labor hours follow volume with a fixed baseline, so labor % is unrealistic in low-volume profiles.
