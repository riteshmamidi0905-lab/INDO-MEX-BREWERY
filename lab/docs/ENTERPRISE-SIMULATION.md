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

## Calibration (NOT DONE)
To calibrate, cite public sources for: restaurant orders per site per day and average check by format (for example National Restaurant Association and Technomic-type industry reports), labor hours and wages (Bureau of Labor Statistics), craft-brewery production and taproom sales (Brewers Association), loyalty member share (published program surveys). Until each parameter has a dated citation here, treat the data as a structural test bed, not a market model.
