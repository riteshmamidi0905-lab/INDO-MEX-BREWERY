# Recipe-to-analytics integration (D-87, extended by D-88) — SYNTHETIC, concept prices

Chain: **menu item → recipe (version) → ingredient → supplier quote → inventory → order → cost → analytics**, built inside the existing warehouse, PostgreSQL variant, Ops AI, evaluation suite and THE WEIR. No parallel agent framework was created.

| # | Capability | Where | Verified by |
|---|---|---|---|
| 1 | Recipe version management (immutable versions, hash, human-only approval, audit chain) | `nasha_lab/recipes/store.py`, `food/recipes/v1` | `test_recipes_d87` (immutability, agent cannot approve, tamper detection) |
| 2 | Ingredient inventory tracking | `scn_inventory_week` (synthetic counts/receipts), `recipes/synth_ops.py` | `test_scenario_d87` |
| 3 | BOM calculations | `recipes/bom.py` → `scn_recipe_bom` | BOM cost == recipe cost identity |
| 4 | Inventory depletion from synthetic orders | SQL `scn_depletion_day/week` | exact match to an independent Python recomputation |
| 5 | Menu profitability | `scn_item_month`, `scn_menu_profitability_month`, `recipes/pricing.py` | restated revenue == units × approved price |
| 6 | Ingredient demand forecasting | `scenario.forecast_ingredient_demand` (seasonal naive / mean / Holt-Winters, rolling-origin backtest) | non-negative forecasts, backtest rows |
| 7 | Supplier cost comparison | `recipes/suppliers.py` (SYNTHETIC quotes, whole packs, lead time) | recommendation = cheapest valid quote |
| 8 | Waste / variance detection | `scenario.detect_variance` (median + MAD per site-ingredient; never reads the injected truth) | recall 11/11, precision ≥ 0.9 vs injected anomalies |
| 9 | Procurement recommendations | `scn_procurement_reco` (status PROPOSED) | whole packs; cheapest quote |
| 10 | Human approval through THE WEIR | `warehouse/procurement.py` (`procurement__propose_purchase_order`, effect write, `gate_write: approve`) | held until approved; nothing stored while pending; approval yields DRAFT_NOT_SENT |
| 11 | Auditable AI recommendations | `reco_id`/`inputs_hash`, rationale JSON, hash-chained store audit, Ops AI audit rows | tamper test; Ops AI audit count |
| 12 | Dashboard reporting | `menu-economics.html` (built only when the scenario exists) | `test_dashboard_page_is_built_and_labelled_synthetic` |

## Data versioning
* `food/pricing/price-v1-placeholder.json` — FROZEN record of the historical placeholder prices; a test proves it still equals the simulation catalog.
* `food/pricing/price-v2-2026-10-22.json` — approved concept prices; beer volumes were pending (kept unchanged as history).
* `food/pricing/price-v3-2026-10-23.json` — CURRENT: same prices plus the provisional serving sizes (16 and 60 US fl oz, stored exactly from fl oz) and the D-88 menu changes (Goat Birria retired).
* `scn_*` tables are added beside `dim_/fact_/mart_`; historical tables are never modified (table hashes compared before/after). Rebuilding the scenario is deterministic (hash-compared). `scn_scenario_run` records the config, recipe-set hash and quote-set hash.
* Differences from the previous simulation: see `docs/menu-research/PRICING-SCENARIO-D87.md`.

## D-88 additions
| Capability | Where | Verified by |
|---|---|---|
| Beer production costing and beverage margins (PRELIMINARY, planning assumptions) | `recipes/beer_costing.py`, `food/pricing/beer-cost-assumptions.v1.json`, `scn_beer_economics` | `test_recipes_d87` (exact volumes, scaling, labels), Ops AI `beer_economics` |
| Recipe-cost levers (portion with quality floor, yield, cheapest synthetic quote, waste); original scenario kept | `recipes/optimize.py`, `scn_cost_lever` | lamb levers test; Ops AI `cost_levers` |
| Supplier-price sensitivity (+15% per supplier under cheapest-quote sourcing) | `optimize.supplier_sensitivity`, `scn_supplier_sensitivity` | monotonicity test; Ops AI `supplier_sensitivity` |
| Menu engineering (star / plowhorse / puzzle / dog) | SQL `scn_menu_engineering` | rule-recomputation test; Ops AI `menu_engineering` |
| Goat Birria retired (history preserved) | `food/recipes/retired/`, ingredient flagged retired, no quotes/BOM | retirement test |
| Allergen cross-contact precautions + no-guarantee claim on every dish | recipe JSON, validator | allergen test |
| Reproducibility check includes scenario tables | `warehouse/repro.py`, `make eval`, `make repro` | `make repro`: 46 tables identical |
| PostgreSQL yield-ratio rounding fix | `models/22_fact_other.sql` | regression tests in `test_warehouse_pg.py` |

## Commands
```
python3 -m nasha_lab.warehouse.scenario   # (library) scenario.build(wh_path) rebuilds the scn_ tables
python3 tools/build_candidate_recipes.py   # recipes + ingredient master authoring script
python3 tools/build_menu_docs.py           # research dossier, pricing doc, recipe cards
python3 -m nasha_lab.recipes.suppliers     # regenerate the synthetic quotes
```

## Limits
No price elasticity; pitchers not simulated; serving sizes are provisional concept sizes and beer costs are preliminary planning estimates (pilot-scale labor dominates; excise, fees and depreciation excluded); only four dishes have simulated sales, so menu engineering covers four items; ingredient prices are planning assumptions, supplier quotes are synthetic; inventory counts and anomalies are synthetic (three injected anomalies, so detection scores are small-sample); detector thresholds were set once, not tuned on held-out data; nothing was cooked, tasted or purchased. PostgreSQL reconciliation covers the scenario tables, not ingestion or gates.
