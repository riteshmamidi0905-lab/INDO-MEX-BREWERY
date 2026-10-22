# Pricing scenario v2 and how it differs from the placeholder-price simulation (D-87)

**Concept prices, not an operating menu.** Simulated revenue computed here is SYNTHETIC and is not NASHA revenue. No restaurant exists.

| | Historical simulation (price-v1-placeholder) | Scenario `scn-price-v2-recipes-v1` (price-v2-2026-10-22) |
|---|---|---|
| Food items | Placeholders $12.00-$16.00 each (M01 $14.00, M02 $13.00, M03 $16.00, M04 $12.00, M05 $15.00) | Appetizers $13.50, mains $18.50 |
| Beer | B01 hefe $8.00, B04 Amba Haze $9.00 | BADSHAH and AMBA HAZE glass $9.00; pitcher $31.00 (not simulated) |
| Other sim items (lager, amber, NA drinks, merch) | v1 placeholder | carried at v1 and labelled `v1_placeholder_carried` |
| Storage | dim_/fact_/mart_ tables, unchanged | `scn_*` tables added beside them; historical tables are never modified (tested by table hash) |
| Revenue basis | simulated quantity x placeholder price | the same simulated quantity x approved price (restatement) |

**Limits.** No price elasticity: volumes do not respond to the new prices. Pitchers and serving sizes are not simulated (volumes pending). Beer unit cost and margin are NOT COMPUTABLE until volumes and a costed batch exist. Food costs are planning assumptions. Inventory counts, receipts and the injected anomalies are synthetic; supplier quotes are SYNTHETIC_QUOTE.

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
| Goat Birria, Sealed-Pot Braise | $18.50 | $4.66 | 18.2% / 25.2% / 34.1% | $13.72 | $10.12 | 29.3% | 30.2% |
| Hyderabadi Birria-Style Chicken Tacos | $18.50 | $3.92 | 15.5% / 21.2% / 29.0% | $14.46 | $11.06 | 22.9% | 25.5% |
| Kerala Coconut Fish Tacos | $18.50 | $3.26 | 13.3% / 17.6% / 23.1% | $15.12 | $11.92 | 19.9% | 21.1% |
| Mango Habanero Gobi | $13.50 | $2.48 | 12.4% / 18.4% / 27.4% | $10.90 | $9.30 | 18.4% | 22.1% |
| Nawaabi Enchiladas | $18.50 | $3.60 | 14.6% / 19.5% / 26.1% | $14.78 | $11.58 | 20.8% | 23.4% |
| Paneer Makhani Pizza | $18.50 | $3.37 | 13.5% / 18.2% / 24.6% | $15.01 | $12.41 | 18.2% | 21.9% |
| Paneer Tikka Taco | $18.50 | $2.21 | 8.6% / 11.9% / 16.4% | $16.17 | $14.17 | 11.9% | 14.3% |
| Tandoori Lamb Tacos | $18.50 | $5.54 | 23.9% / 30.0% / 38.4% | $12.84 | $9.64 | 34.4% | 35.9% |
| Tandoori Paneer Quesadilla Bites | $13.50 | $3.59 | 19.4% / 26.6% / 36.7% | $9.79 | $7.59 | 26.6% | 31.9% |

Definitions: gross profit = price - ingredient cost - waste allowance - consumables ($0.12). Contribution = gross profit - direct labor minutes x $24/h loaded planning rate. Ingredient cost = qty / yield x unit price, with sub-recipes costed by batch yield.
