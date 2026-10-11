# Financial Model Architecture v1

**Status:** `[DESIGN]` of a future model. **No forecast, proforma or valuation exists and none is claimed.** Inputs live in `business/model/assumptions-template.csv` (70 variables, **all values blank**). Benchmarks in `business/AUSTIN-FEASIBILITY-V1.md` are weak and are **not** quotes. This document defines structure, rules and gates so that when evidence arrives the model is built correctly and honestly.

## 1. Model maturity states (the model may only claim the state it has reached)
| State | Meaning | Reached? |
|---|---|---|
| **M0 Architecture** | Structure, variables, rules defined | **Yes (this document)** |
| **M1 Illustrative** | Scenario shapes using clearly labelled illustrative or benchmark values, never presented as forecasts | No |
| **M2 Evidence-fed** | Key inputs replaced by observed prices, interview/pop-up data, brewer and supplier inputs | No |
| **M3 Quoted** | Capex lines backed by architect/vendor quotes; legal/insurance confirmed | No |
| **M4 Investor-grade** | Reviewed by an accountant/financial adviser; sensitivity and downside tested | No |

## 2. Input rules
Every input row carries `value`, `source_class`, `source_ref`, `status`. **Allowed source classes:** `founder_assumption` · `benchmark_T3` · `benchmark_T1` · `observation_LOW` · `interview_real` · `popup_real` · `supplier_quote` · `vendor_quote` · `architect_estimate` · `professional_advice` · `calculated` (from other inputs) · `illustrative` (placeholder to show a mechanism; must not leave the repo as a forecast). A value may **not** be entered without a class and a reference; a benchmark may **not** be relabelled a quote. Status flow: UNSET → ASSUMED → SOURCED → QUOTED → CONFIRMED.

## 3. Model structure (sheets/modules)
1. **Inputs** (the CSV, grouped CAPEX, REVENUE, BREWERY, COGS, OPEX). 2. **Capacity** (seats, fermenter capacity vs beer demand, kitchen throughput). 3. **Revenue build** (streams R1-R15 as selected; `BUSINESS-MODEL-MAP-V1.md`). 4. **COGS** (food and beer separately; protein costs from quotes). 5. **Labour** (FTE × wage × burden; ramp). 6. **Occupancy and operating costs** (rent or loan service, utilities incl. CO₂/trade waste, insurance, maintenance, marketing, technology, professional, licences, glass breakage). 7. **Startup CAPEX and pre-opening** (all categories below). 8. **Cash flow and funding** (draws, working capital, contingency, debt/equity placeholders). 9. **Scenarios** (phase A / A+B / C; conservative/base/upside only at M2+). 10. **Sensitivities** (seats, check, turns, beer/seat, labour %, prime cost, rent, ramp). 11. **Checks** (below).

## 4. Startup uses (CAPEX and pre-opening categories)
Land/lease; sitework and utilities; core construction; family phase construction; glazing/canopy premium; court structure/cooling; brewing equipment; glycol/CO₂/boiler/CIP; trade-waste pretreatment; kitchen equipment; bar draft system; FF&E; technology; signage; professional fees; licences/permits/impact fees; deposits; opening inventory; pre-opening expenses; working capital; contingency; financing cost. **Sources of funds** are a separate block (founder, equity, debt, grants, landlord contribution): **unknown**.

## 5. Operating model lines
Revenue: food, beverage (draft, flights, NA/cocktails if any), takeaway, merchandise, events/private dining, memberships, packaged beer (only within legal caps), collaborations, family/arcade (if built). COGS: food, beer, merch, packaging. Operating: labour, occupancy, utilities, insurance, maintenance, marketing, technology, professional services, licences, breakage. **EBITDA** = revenue − COGS − operating costs; below EBITDA: depreciation, interest, tax (accountant).
Expansion model: **not designed yet**; depends on a proven single-site model.

## 6. Built-in checks (to implement in the model)
Capacity vs demand (`N × V × turns × utilisation` vs `S × bbl/seat`); packaged volume ≤ legal caps; seats vs code occupancy (architect); CAPEX completeness (no blank category at M3); prime cost within plausible band; labour % vs benchmark; breakeven sanity; every input has a source class; no `illustrative` value in an investor output.

## 7. Presentation rules (for investors)
Show three layers on every output page: **Evidence** (what is sourced), **Assumption** (what is assumed), **Gap** (what is blank). A forecast without its gap list is not allowed. **No IRR, valuation or return claims until M4.**

## 8. Evidence tasks that move the model forward (in order)
Vessel size (brewer) → architect ROM → kitchen/brewhouse vendor quotes → observed prices (survey) → interviews (spend, frequency, family value) → supplier quotes (goat, lamb, paneer, fish) → attorney (permitted streams) → insurance indication → accountant review.
