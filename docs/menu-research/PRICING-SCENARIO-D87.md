# Pricing scenario v2 and how it differs from the placeholder-price simulation (D-87)

**Concept prices, not an operating menu.** Simulated revenue computed here is SYNTHETIC and is not NASHA revenue. No restaurant exists.

| | Historical simulation (price-v1-placeholder) | Scenario `scn-price-v2-recipes-v1` (price-v2-2026-10-22) |
|---|---|---|
| Food items | Placeholders $12.00-$16.00 each (M01 $14.00, M02 $13.00, M03 $16.00, M04 $12.00, M05 $15.00) | Appetizers $13.50, mains $18.50; M03 (Goat Birria) retired by D-88, so its historical sales keep the v1 placeholder and have no BOM |
| Beer | B01 hefe $8.00, B04 Amba Haze $9.00 | BADSHAH and AMBA HAZE glass $9.00; pitcher $31.00 (not simulated); provisional serving sizes 16 and 60 US fl oz |
| Other sim items (lager, amber, NA drinks, merch) | v1 placeholder | carried at v1 and labelled `v1_placeholder_carried` |
| Storage | dim_/fact_/mart_ tables, unchanged | `scn_*` tables added beside them; historical tables are never modified (tested by table hash) |
| Revenue basis | simulated quantity x placeholder price | the same simulated quantity x approved price (restatement) |

**Limits.** No price elasticity: volumes do not respond to the new prices. Pitchers are not simulated and serving sizes are provisional concept sizes. Beer costs are PRELIMINARY PLANNING ESTIMATES, not verified production costs. Food costs are planning assumptions. Inventory counts, receipts and the injected anomalies are synthetic; supplier quotes are SYNTHETIC_QUOTE.

## Per-dish economics (base scenario)

Food cost % shown low / base / high price scenario; last two columns = food cost % if protein prices rise 20% / all ingredients rise 20%.

| Dish | Price | Food cost (incl. 5% waste) | Food cost % L/B/H | Gross profit | Contribution (after labor) | +20% protein | +20% all |
|---|---|---|---|---|---|---|---|
| Butter Chicken & Roasted Poblano Quesadilla | $18.50 | $1.92 | 7.5% / 10.4% / 14.4% | $16.46 | $14.66 | 10.7% | 12.5% |
| Chaat Elote | $13.50 | $1.08 | 5.5% / 8.0% / 11.4% | $12.30 | $11.10 | 8.0% | 9.6% |
| Chicken 65 Totopos | $13.50 | $2.16 | 12.0% / 16.0% / 21.5% | $11.22 | $8.62 | 18.0% | 19.2% |
| Chicken Tikka Tacos | $18.50 | $2.77 | 11.0% / 15.0% / 20.4% | $15.61 | $12.61 | 16.5% | 18.0% |
| Crispy Aloo Chaat Nachos | $13.50 | $1.23 | 6.3% / 9.1% / 12.9% | $12.15 | $9.75 | 9.1% | 10.9% |
| Goan Chicken Vindaloo Pizza | $18.50 | $2.51 | 10.3% / 13.6% / 18.1% | $15.87 | $13.07 | 14.7% | 16.3% |
| Goan Peri-Peri Wings | $13.50 | $2.07 | 11.6% / 15.3% / 21.1% | $11.31 | $8.91 | 17.5% | 18.4% |
| Hyderabadi Birria-Style Chicken Tacos | $18.50 | $3.92 | 15.5% / 21.2% / 29.0% | $14.46 | $11.06 | 22.9% | 25.5% |
| Kerala Coconut Fish Tacos | $18.50 | $3.26 | 13.3% / 17.6% / 23.1% | $15.12 | $11.92 | 19.9% | 21.1% |
| Mango Habanero Gobi | $13.50 | $2.48 | 12.4% / 18.4% / 27.4% | $10.90 | $9.30 | 18.4% | 22.1% |
| Nawaabi Enchiladas | $18.50 | $3.60 | 14.6% / 19.5% / 26.1% | $14.78 | $11.58 | 20.8% | 23.4% |
| Paneer Makhani Pizza | $18.50 | $3.37 | 13.5% / 18.2% / 24.6% | $15.01 | $12.41 | 18.2% | 21.9% |
| Paneer Tikka Taco | $18.50 | $2.21 | 8.6% / 11.9% / 16.4% | $16.17 | $14.17 | 11.9% | 14.3% |
| Tandoori Lamb Tacos | $18.50 | $5.54 | 23.9% / 30.0% / 38.4% | $12.84 | $9.64 | 34.4% | 35.9% |
| Tandoori Paneer Quesadilla Bites | $13.50 | $3.59 | 19.4% / 26.6% / 36.7% | $9.79 | $7.59 | 26.6% | 31.9% |


## Tandoori Lamb Tacos: portion, yield and supplier analysis (D-88; analysis only, nothing applied)

The ORIGINAL costing scenario is the first row and is retained. Quality is not traded for margin: portion cuts below 95% of the primary protein are marked as below the quality floor and shown for information only.

| Lever | Setting | Food cost | Gross margin | Change | Quality impact |
|---|---|---|---|---|---|
| original | planning-assumption base prices, as costed | $5.54 | 69.4% | +0.0 pts | none |
| portion | i-lamb-leg x0.90 | $5.13 | 71.6% | +2.2 pts | BELOW QUALITY FLOOR: needs tasting; do not apply |
| portion | i-lamb-leg x0.95 | $5.33 | 70.5% | +1.1 pts | tasting needed |
| portion | i-lamb-leg x1.05 | $5.75 | 68.3% | -1.1 pts | tasting needed |
| yield | i-lamb-leg yield 75% -> 80% | $5.28 | 70.8% | +1.4 pts | none if cut spec/supplier delivers it |
| yield | i-lamb-leg yield 75% -> 85% | $5.06 | 72.0% | +2.6 pts | none if cut spec/supplier delivers it |
| supplier | cheapest valid SYNTHETIC quote per ingredient | $5.26 | 70.9% | +1.5 pts | none if specs are equivalent |
| waste | waste allowance 3% | $5.44 | 70.0% | +0.6 pts | none |
| waste | waste allowance 7% | $5.65 | 68.8% | -0.6 pts | none |

Information only: the planning margin would reach exactly 70% at about 97% of the current lamb portion, which is inside the quality floor and therefore inconclusive without tasting. Better first steps are the yield and supplier levers (a pre-trimmed lamb spec is cost-neutral up to a price premium equal to its yield gain) and waste control.

## Beer: preliminary costing and margins at provisional serving sizes (D-88)

Serving sizes (founder-approved concept sizes): glass 16 US fl oz = 473.176 mL, pitcher 60 US fl oz = 1774.412 mL (stored exactly from fl oz at 29.5735295625 mL per fl oz; the message quoted 1,774.414 mL, a 0.002 mL rounding difference). Real glassware capacity, headspace and fill lines need physical validation.

PLANNING ESTIMATES, NOT VERIFIED PRODUCTION COSTS: nothing has been brewed. Basis: 100 L pilot batch, 92% packaged, 4% service waste, assumed ingredient prices and overheads in `food/pricing/beer-cost-assumptions.v1.json`. Excluded: excise tax, TABC/TTB fees, equipment depreciation, serving labor.

| Beer | Size | Price | Cost ex brew labor | Margin ex labor | Cost incl. pilot brew labor | Margin incl. labor |
|---|---|---|---|---|---|---|
| badshah | glass | $9.00 | $0.61 | 93.2% | $1.81 | 79.9% |
| badshah | pitcher | $31.00 | $2.29 | 92.6% | $6.79 | 78.1% |
| amba-haze | glass | $9.00 | $1.07 | 88.1% | $2.27 | 74.8% |
| amba-haze | pitcher | $31.00 | $4.01 | 87.1% | $8.51 | 72.5% |

A pitcher equals 3.75 glasses; buying that volume as glasses costs $33.75 against $31.00 per pitcher, an implied volume discount of 8.1%.

Definitions: gross profit = price - ingredient cost - waste allowance - consumables ($0.12). Contribution = gross profit - direct labor minutes x $24/h loaded planning rate. Ingredient cost = qty / yield x unit price, with sub-recipes costed by batch yield.
