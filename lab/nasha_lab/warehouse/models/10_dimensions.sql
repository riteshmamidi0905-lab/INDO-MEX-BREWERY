-- model: dimensions
-- kind: tables
-- depends: stg_locations, stg_menu_items, stg_loyalty_profiles, stg_employees, stg_promotions, stg_suppliers
CREATE TABLE ref_cost_assumptions (category TEXT PRIMARY KEY, cost_pct REAL, note TEXT);
INSERT INTO ref_cost_assumptions VALUES ('food', 0.30, 'PLACEHOLDER planning input'), ('beer', 0.22, 'PLACEHOLDER planning input'), ('na', 0.15, 'PLACEHOLDER planning input'), ('merch', 0.45, 'PLACEHOLDER planning input');
CREATE TABLE ref_ingredient_cost (ingredient TEXT PRIMARY KEY, cents_per_kg INTEGER, note TEXT);
INSERT INTO ref_ingredient_cost VALUES ('chicken thigh',700,'PLACEHOLDER'),('paneer',1100,'PLACEHOLDER'),('goat',1500,'PLACEHOLDER'),('cauliflower',250,'PLACEHOLDER'),('corn masa',200,'PLACEHOLDER'),('malt',250,'PLACEHOLDER'),('hops',3000,'PLACEHOLDER'),('cheese',900,'PLACEHOLDER');
CREATE TABLE dim_location AS SELECT ROW_NUMBER() OVER (ORDER BY location_id) AS location_key, location_id, name, format, size_factor, sells_merch, capacity_orders_per_hour, open_date FROM stg_locations;
CREATE UNIQUE INDEX ux_dim_location ON dim_location(location_id);
CREATE TABLE dim_product AS SELECT ROW_NUMBER() OVER (ORDER BY item_id) AS product_key, m.item_id, m.name, m.category, m.price_cents AS list_price_cents, c.cost_pct, CAST(round(m.price_cents * c.cost_pct) AS INTEGER) AS unit_cost_cents, m.status, CASE WHEN m.status LIKE 'concept%' THEN 1 ELSE 0 END AS is_concept_sku FROM stg_menu_items m JOIN ref_cost_assumptions c ON c.category = m.category;
CREATE UNIQUE INDEX ux_dim_product ON dim_product(item_id);
CREATE TABLE dim_member AS SELECT ROW_NUMBER() OVER (ORDER BY member_id) AS member_key, member_id, join_date, substr(join_date,1,7) AS cohort_month, home_location_id, signup_channel FROM stg_loyalty_profiles;
CREATE UNIQUE INDEX ux_dim_member ON dim_member(member_id);
CREATE TABLE dim_employee AS SELECT ROW_NUMBER() OVER (ORDER BY employee_id) AS employee_key, employee_id, location_id, role, hire_date, hourly_rate_cents_placeholder AS hourly_rate_cents FROM stg_employees;
CREATE TABLE dim_promotion AS SELECT ROW_NUMBER() OVER (ORDER BY promo_id) AS promo_key, promo_id, name, start_date, end_date, discount_fraction FROM stg_promotions;
CREATE UNIQUE INDEX ux_dim_promo ON dim_promotion(promo_id);
CREATE TABLE dim_supplier AS SELECT ROW_NUMBER() OVER (ORDER BY supplier_id) AS supplier_key, supplier_id, name, category FROM stg_suppliers;
