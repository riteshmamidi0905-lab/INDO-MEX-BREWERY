-- NASHA ANALYTICS MART: star schema DDL (SQLite dialect; portable except where marked).
-- SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.
-- Conventions: *_key = integer surrogate key; key 0 = the 'Unknown' member of a dimension; *_id = natural/business key.
-- date_key = YYYYMMDD integer (smart key by convention, joined to dim_date); 0 = no date (e.g. not yet received).

-- ============ DIMENSIONS ============
CREATE TABLE dim_date(
  date_key INTEGER PRIMARY KEY, date TEXT NOT NULL UNIQUE, year INTEGER, month INTEGER, month_start TEXT,
  iso_week INTEGER, week_start TEXT, week_index INTEGER,          -- week_index: 0-based week number from the first data date
  dow INTEGER, day_name TEXT, is_weekend INTEGER);                -- dow: 0=Monday ... 6=Sunday
CREATE TABLE dim_site(
  site_key INTEGER PRIMARY KEY, site_id TEXT NOT NULL UNIQUE, site_name TEXT, volume_factor REAL, synthetic INTEGER NOT NULL DEFAULT 1);
CREATE TABLE dim_channel(channel_key INTEGER PRIMARY KEY, channel TEXT NOT NULL UNIQUE);
-- SCD TYPE 2: one row per (item_id, version). valid_from inclusive, valid_to EXCLUSIVE ('9999-12-31' = open). Exactly one is_current=1 per item_id.
CREATE TABLE dim_menu_item(
  item_key INTEGER PRIMARY KEY, item_id TEXT NOT NULL, item_name TEXT, category TEXT, course TEXT, menu_version TEXT,
  list_price_cents INTEGER, valid_from TEXT NOT NULL, valid_to TEXT NOT NULL, is_current INTEGER NOT NULL,
  UNIQUE(item_id, valid_from));
CREATE TABLE dim_supplier(supplier_key INTEGER PRIMARY KEY, supplier_id TEXT NOT NULL UNIQUE, supplier_name TEXT, status TEXT, synthetic INTEGER NOT NULL DEFAULT 1);
CREATE TABLE dim_ingredient(ingredient_key INTEGER PRIMARY KEY, ingredient TEXT NOT NULL UNIQUE, unit TEXT, is_perishable INTEGER,
  assumed_cost_per_kg REAL,                                       -- ASSUMPTION (analytics/config.py), not a NASHA cost
  primary_supplier_key INTEGER, lead_time_days INTEGER);          -- from the lab's supplier_ingredients (planning inputs)
CREATE TABLE dim_guest(guest_key INTEGER PRIMARY KEY, guest_id TEXT NOT NULL UNIQUE, home_site_key INTEGER, first_order_date_key INTEGER,
  cohort_week_start TEXT, synthetic INTEGER NOT NULL DEFAULT 1);  -- SYNTHETIC guest ids; NASHA has no guests
CREATE TABLE dim_dq_rule(rule_key INTEGER PRIMARY KEY, rule TEXT NOT NULL UNIQUE, dq_dimension TEXT, default_severity TEXT);
CREATE TABLE dim_waste_reason(reason_key INTEGER PRIMARY KEY, reason TEXT NOT NULL UNIQUE, is_logged INTEGER);
CREATE TABLE bridge_item_ingredient(                              -- recipe per menu-item VERSION (placeholder planning inputs, not tested recipes)
  item_key INTEGER NOT NULL REFERENCES dim_menu_item, ingredient_key INTEGER NOT NULL REFERENCES dim_ingredient, kg_per_unit REAL NOT NULL,
  PRIMARY KEY(item_key, ingredient_key));

-- ============ FACTS ============
-- GRAIN: one row per accepted (non-quarantined) order.
CREATE TABLE fact_order(
  order_key INTEGER PRIMARY KEY, order_id TEXT NOT NULL UNIQUE, date_key INTEGER NOT NULL REFERENCES dim_date, site_key INTEGER NOT NULL REFERENCES dim_site,
  channel_key INTEGER NOT NULL REFERENCES dim_channel, guest_key INTEGER NOT NULL REFERENCES dim_guest, order_ts TEXT NOT NULL, order_total_cents INTEGER NOT NULL);
-- GRAIN: one row per accepted order line (order_id, line_no). item_key is the SCD2 version in effect on the order date.
CREATE TABLE fact_order_line(
  order_line_key INTEGER PRIMARY KEY, order_key INTEGER NOT NULL REFERENCES fact_order, order_id TEXT NOT NULL, line_no INTEGER NOT NULL,
  date_key INTEGER NOT NULL REFERENCES dim_date, site_key INTEGER NOT NULL REFERENCES dim_site, item_key INTEGER NOT NULL REFERENCES dim_menu_item,
  channel_key INTEGER NOT NULL REFERENCES dim_channel, guest_key INTEGER NOT NULL REFERENCES dim_guest,
  qty INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL, gross_sales_cents INTEGER NOT NULL, price_flag INTEGER NOT NULL,
  UNIQUE(order_id, line_no));
-- GRAIN: site x ingredient x date. Theoretical (recipe-implied) usage, DERIVED from fact_order_line x bridge_item_ingredient.
CREATE TABLE fact_usage_daily(
  date_key INTEGER NOT NULL REFERENCES dim_date, site_key INTEGER NOT NULL REFERENCES dim_site, ingredient_key INTEGER NOT NULL REFERENCES dim_ingredient,
  theoretical_qty REAL NOT NULL, PRIMARY KEY(date_key, site_key, ingredient_key));
-- GRAIN: site x ingredient x count date (periodic snapshot, start-of-day count).
CREATE TABLE fact_inventory_snapshot(
  date_key INTEGER NOT NULL REFERENCES dim_date, site_key INTEGER NOT NULL REFERENCES dim_site, ingredient_key INTEGER NOT NULL REFERENCES dim_ingredient,
  on_hand_qty REAL NOT NULL, unit TEXT NOT NULL, prev_date_key INTEGER NOT NULL,
  usage_since_prev REAL, receipts_since_prev REAL, logged_waste_since_prev REAL, expected_on_hand REAL, variance_qty REAL,
  avg_daily_usage_14d REAL, PRIMARY KEY(date_key, site_key, ingredient_key));
-- GRAIN: one row per purchase-order line. received_date_key = 0 while the PO is open.
CREATE TABLE fact_po_line(
  po_line_key INTEGER PRIMARY KEY, po_id TEXT NOT NULL, line_no INTEGER NOT NULL, supplier_key INTEGER NOT NULL REFERENCES dim_supplier,
  site_key INTEGER NOT NULL REFERENCES dim_site, ingredient_key INTEGER NOT NULL REFERENCES dim_ingredient,
  order_date_key INTEGER NOT NULL REFERENCES dim_date, expected_date_key INTEGER NOT NULL REFERENCES dim_date, received_date_key INTEGER NOT NULL,
  qty_ordered REAL NOT NULL, qty_received REAL NOT NULL, unit TEXT, status TEXT NOT NULL, days_late INTEGER,
  source TEXT NOT NULL,                                           -- 'ANALYTICS_SYNTH': generated by analytics/synth.py (seeded, labelled), not by the lab generator
  UNIQUE(po_id, line_no));
-- GRAIN: one row per waste / adjustment event. qty > 0 = loss. adj_kind LOGGED_WASTE (synthetic log) or COUNT_ADJUSTMENT (derived from snapshot variance).
CREATE TABLE fact_waste_adjustment(
  waste_key INTEGER PRIMARY KEY, date_key INTEGER NOT NULL REFERENCES dim_date, site_key INTEGER NOT NULL REFERENCES dim_site,
  ingredient_key INTEGER NOT NULL REFERENCES dim_ingredient, reason_key INTEGER NOT NULL REFERENCES dim_waste_reason, adj_kind TEXT NOT NULL, qty REAL NOT NULL);
-- GRAIN: one row per data-quality finding raised by the lab pipeline (includes rows that were quarantined and are NOT in the order facts).
CREATE TABLE fact_quality_finding(
  finding_key INTEGER PRIMARY KEY, rule_key INTEGER NOT NULL REFERENCES dim_dq_rule, severity TEXT NOT NULL, entity_table TEXT NOT NULL, entity_key TEXT NOT NULL,
  site_key INTEGER NOT NULL, detail TEXT, was_quarantined INTEGER NOT NULL);
-- GRAIN: one row per inventory EXCEPTION (low cover or large count variance). Detection is derived from the mart; approval/resolution
-- timestamps are SIMULATED by a seeded process (analytics/synth.py) and carry no information about real operators.
CREATE TABLE fact_exception_event(
  event_key INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, site_key INTEGER NOT NULL REFERENCES dim_site, ingredient_key INTEGER NOT NULL REFERENCES dim_ingredient,
  detected_date_key INTEGER NOT NULL REFERENCES dim_date, kind TEXT NOT NULL, detected_ts TEXT NOT NULL, approved_ts TEXT, resolved_ts TEXT);

CREATE INDEX ix_fol_date_site ON fact_order_line(date_key, site_key);
CREATE INDEX ix_fol_item ON fact_order_line(item_key);
CREATE INDEX ix_fol_guest ON fact_order_line(guest_key);
CREATE INDEX ix_fo_guest ON fact_order(guest_key);
