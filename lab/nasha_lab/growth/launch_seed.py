"""Seed data for the business-launch workspace of the two SYNTHETIC tenants. NASHA — The Courtyard is the flagship hospitality launch case study (a proposed brand, not an operating business); Meridian Fitness is a
second, unrelated business, so the platform stays industry-agnostic. Everything is labelled by provenance:
  * assumptions: 'synthetic_assumption' (planning inputs I chose, replaceable by the founder), never presented as measured;
  * supplier fixtures: the repository's existing SYNTHETIC supplier quotes (price class SYNTHETIC_QUOTE), reused, not re-invented;
  * three REAL supplier LEADS found through public web search on 2026-10-23: name/category/area and the page that mentions them ONLY. They are 'lead_unverified': no official website verified, no contact, no price;
  * research findings from those pages are 'search_result' with their URL, retrieval date and limitations.
No supplier has been contacted and no price from a real supplier is recorded."""
import json
from datetime import date, timedelta
from pathlib import Path

from ..recipes import model as RM, suppliers as SUPQ

SEARCHED = date(2026, 10, 23)
SYNTH_LIMIT = "Synthetic fixture generated from a planning-assumption base price with a seeded factor; not a supplier document and not a real price."
NO_PRICE = "No public price list was found; a real price requires a supplier quote, which has not been requested."

NASHA_PROJECT = dict(name="NASHA — The Courtyard", industry="Hospitality", location="Austin, TX",
                     concept="An independent, premium hospitality venue built around a courtyard: shared plates, house-brewed beer and a calm, craft-led atmosphere. A proposed concept used as the flagship launch case study.",
                     budget_cents=60_000_000, launch_target=date(2027, 9, 1))
NASHA_ASSUMPTIONS = [("weekly_orders", "Guest orders per week", 650, "orders", "synthetic_assumption", "Assumed average once the venue is established; not measured."), ("items_per_order", "Items per order", 2.5, "items", "synthetic_assumption", None),
                     ("avg_discount_pct", "Average discount", 2, "%", "synthetic_assumption", None), ("variable_overhead_pct", "Payment and platform fees", 3.2, "% of price", "synthetic_assumption", None),
                     ("price_elasticity", "Price elasticity of demand", -1.2, "ratio", "synthetic_assumption", "Assumed; no willingness-to-pay data exists."), ("cost_inflation_pct", "Ingredient cost inflation", 0, "%", "synthetic_assumption", None),
                     ("rent_monthly_cents", "Rent", 1_600_000, "cents/month", "synthetic_assumption", None), ("labor_monthly_cents", "Labour", 5_200_000, "cents/month", "synthetic_assumption", None),
                     ("utilities_monthly_cents", "Utilities", 350_000, "cents/month", "synthetic_assumption", None), ("marketing_monthly_cents", "Marketing", 500_000, "cents/month", "synthetic_assumption", None),
                     ("insurance_monthly_cents", "Insurance", 180_000, "cents/month", "synthetic_assumption", None), ("other_fixed_monthly_cents", "Other fixed costs", 450_000, "cents/month", "synthetic_assumption", None),
                     ("capex_buildout_cents", "Build-out and construction", 22_000_000, "cents", "synthetic_assumption", "Placeholder; no contractor quote exists."), ("capex_equipment_cents", "Kitchen, brewing and service equipment", 14_000_000, "cents", "synthetic_assumption", "Placeholder; no equipment quote exists."),
                     ("capex_furniture_cents", "Furniture and fixtures", 4_000_000, "cents", "synthetic_assumption", None), ("capex_technology_cents", "Technology and point of sale", 2_000_000, "cents", "synthetic_assumption", None), ("capex_other_cents", "Other capital items", 0, "cents", "synthetic_assumption", "None planned."),
                     ("startup_capex_cents", "Capital expenditure (lump sum)", 0, "cents", "synthetic_assumption", "Not used: capital items are itemised above."),
                     ("preopen_licences_permits_cents", "Licences and permits", 600_000, "cents", "synthetic_assumption", "Placeholder; actual fees depend on the permit set and have not been checked."), ("preopen_deposits_cents", "Deposits", 3_200_000, "cents", "synthetic_assumption", "Assumed two months of rent."),
                     ("preopen_professional_fees_cents", "Professional fees", 1_200_000, "cents", "synthetic_assumption", None), ("preopen_training_cents", "Pre-opening training and payroll", 1_800_000, "cents", "synthetic_assumption", None), ("preopen_other_cents", "Other pre-opening costs", 0, "cents", "synthetic_assumption", "None planned."),
                     ("preopen_launch_marketing_cents", "Launch marketing", 1_500_000, "cents", "synthetic_assumption", "Planning figure only; no campaign has been run or paid for."),
                     ("working_capital_months", "Working capital: months of fixed costs held in reserve", 2, "months", "synthetic_assumption", None), ("opening_inventory_weeks", "Opening inventory: weeks of ingredient cost", 2, "weeks", "synthetic_assumption", None),
                     ("contingency_pct", "Contingency on the start-up subtotal", 10, "%", "synthetic_assumption", "A common planning allowance; not derived from this project's risks.")]
NASHA_MILESTONES = [("Define the concept and positioning", "idea", date(2026, 11, 15), "done"), ("Research the local market and suppliers", "research", date(2026, 12, 15), "doing"), ("Shortlist suppliers and request quotes (not yet requested)", "sourcing", date(2027, 1, 31), "todo"),
                    ("Sign off menu costing and pricing", "financial_plan", date(2027, 2, 28), "todo"), ("Review the financial plan against the budget", "financial_plan", date(2027, 3, 31), "todo"), ("Prepare the launch roadmap and permits checklist", "roadmap", date(2027, 5, 31), "todo")]
NASHA_FINDINGS = [
    ("Local produce supply", "Farm to Table LLC (Austin) is described by the Austin Chronicle as serving more than 200 restaurants and seven school districts in Austin and surrounding areas.", "search_result", 0.5,
     "A single news article; not confirmed with the company; no prices or terms found.", "https://www.austinchronicle.com/food/food-o-file-11764527/"),
    ("Dairy supply", "Hill Country Dairies (Austin) is described in a PNC investment profile as a value-added distributor of more than 200 milk, butter, cream and cheese products with vendor-managed inventory.", "search_result", 0.5,
     "An investor profile, not the company's own statement; confirm range, minimums and prices directly (not done).", "https://www.pnc.com/content/riverarch/us/en/portfolio/hill-country-dairies.html"),
    ("Regional produce coverage", "Brothers Produce lists Austin among the Texas metros it covers in a Restaurant365 vendor profile.", "search_result", 0.4, "A software vendor's partner listing; not verified with the company.", "https://www.restaurant365.com/partners/brothers-produce/"),
    ("Specialty dairy", "The search found no Austin-area supplier of fresh paneer; a dairy distributor or specialty wholesaler would need to be asked.", "search_result", 0.3, "Absence in search results is weak evidence, not proof that none exists.",
     "https://www.pnc.com/content/riverarch/us/en/portfolio/hill-country-dairies.html"),
    ("Menu economics", "Planning food cost across the 15 menu items is a small share of menu price, so fixed costs and volume dominate profitability in the base scenario.", "synthetic_fixture", 0.6, "Derived from planning-assumption ingredient costs and founder-approved concept prices; not measured.", None)]
REAL = json.loads((Path(__file__).parent / "data" / "real_suppliers.json").read_text())      # the research record: 12 real businesses, 31 dated public sources, none verified
_official = [x for x in REAL["suppliers"] if any(k in ("official_site", "contact_page") for k, _, _ in x["sources"])]
OFFICIAL_SITE_FINDING = ("Supplier verification", f"Of {len(REAL['suppliers'])} real businesses researched on {REAL['researched_on']}, none could be verified. Pages on their own domains appeared in search results for {len(_official)} of them (snippets only); the rest are known only from directories, press, "
                         "encyclopedia or investor pages. No page could be opened (network policy), no price was seen and nobody was contacted.", "search_result", 0.6,
                         "Search-result snippets only. A person would need to open each official site, confirm the business, a public contact channel and any published prices, and record the date.", "https://www.producemarketguide.com/company/549852/farm-to-table-llc")

MERIDIAN_PROJECT = dict(name="Second studio location", industry="Fitness", location="Cedar Park, TX", concept="A second boutique fitness studio for a growing member base, with the same class formats and memberships as the first.",
                        budget_cents=18_000_000, launch_target=date(2027, 6, 1))
MERIDIAN_ASSUMPTIONS = [("weekly_orders", "Billed sales per week (memberships, class packs and sessions)", 100, "sales", "synthetic_assumption", "Assumed once established; not measured."), ("items_per_order", "Items per sale", 1.0, "items", "synthetic_assumption", None),
                        ("avg_discount_pct", "Average discount", 4, "%", "synthetic_assumption", None), ("variable_overhead_pct", "Payment fees", 2.9, "% of price", "synthetic_assumption", None),
                        ("price_elasticity", "Price elasticity of demand", -0.9, "ratio", "synthetic_assumption", "Assumed."), ("cost_inflation_pct", "Supply cost inflation", 0, "%", "synthetic_assumption", None),
                        ("rent_monthly_cents", "Rent", 900_000, "cents/month", "synthetic_assumption", None), ("labor_monthly_cents", "Instructors and front desk", 1_400_000, "cents/month", "synthetic_assumption", None),
                        ("utilities_monthly_cents", "Utilities", 150_000, "cents/month", "synthetic_assumption", None), ("marketing_monthly_cents", "Marketing", 200_000, "cents/month", "synthetic_assumption", None),
                        ("insurance_monthly_cents", "Insurance", 90_000, "cents/month", "synthetic_assumption", None), ("other_fixed_monthly_cents", "Other fixed costs", 120_000, "cents/month", "synthetic_assumption", None),
                        ("capex_buildout_cents", "Studio fit-out (walls, mirrors, lighting)", 2_800_000, "cents", "synthetic_assumption", "Placeholder; no contractor quote exists."), ("capex_equipment_cents", "Studio equipment", 3_200_000, "cents", "synthetic_assumption", "Planning figure; the procurement recommendation prices the itemised requirements separately."),
                        ("capex_furniture_cents", "Reception, lockers and furniture", 800_000, "cents", "synthetic_assumption", None), ("capex_technology_cents", "Booking, access and sound systems", 600_000, "cents", "synthetic_assumption", None),
                        ("capex_other_cents", "Other capital items", 0, "cents", "synthetic_assumption", "None planned."), ("startup_capex_cents", "Capital expenditure (lump sum)", 0, "cents", "synthetic_assumption", "Not used: capital items are itemised above."),
                        ("preopen_licences_permits_cents", "Licences, permits and insurance set-up", 200_000, "cents", "synthetic_assumption", "Placeholder; actual fees were not checked."), ("preopen_deposits_cents", "Deposits", 1_800_000, "cents", "synthetic_assumption", "Assumed two months of rent."),
                        ("preopen_professional_fees_cents", "Professional fees", 350_000, "cents", "synthetic_assumption", None), ("preopen_training_cents", "Instructor training and pre-opening payroll", 450_000, "cents", "synthetic_assumption", None),
                        ("preopen_launch_marketing_cents", "Launch marketing", 300_000, "cents", "synthetic_assumption", "Planning figure only; no campaign has been run or paid for."), ("preopen_other_cents", "Other pre-opening costs", 0, "cents", "synthetic_assumption", "None planned."),
                        ("working_capital_months", "Working capital: months of fixed costs held in reserve", 2, "months", "synthetic_assumption", None), ("opening_inventory_weeks", "Opening supplies: weeks of supply cost", 2, "weeks", "synthetic_assumption", None),
                        ("contingency_pct", "Contingency on the start-up subtotal", 6, "%", "synthetic_assumption", "A planning allowance; not derived from this project's risks.")]
MERIDIAN_MILESTONES = [("Confirm demand from the waiting list", "research", date(2026, 12, 1), "doing"), ("Compare equipment and cleaning-service suppliers", "sourcing", date(2027, 1, 20), "todo"), ("Review the financial plan", "financial_plan", date(2027, 2, 15), "todo"),
                       ("Install and test equipment", "roadmap", date(2027, 3, 10), "todo"), ("Launch roadmap", "roadmap", date(2027, 4, 1), "todo")]
MERIDIAN_FINDINGS = [("Demand", "The first studio has a waiting list of 140 people (synthetic figure).", "synthetic_fixture", 0.4, "Synthetic planning input; not a real waiting list."),
                     ("Equipment lead time", "Bulk spin-bike orders are assumed to take two to four weeks to arrive, which sets the earliest opening date (synthetic planning figure).", "synthetic_fixture", 0.4, "A planning assumption; no supplier has been asked."),
                     ("Competition", "Two other boutique studios are assumed to operate within a short drive (synthetic planning figure).", "synthetic_fixture", 0.3, "Not researched; a real study would list and verify them.")]
# (name, category, [(product, requirement ref, unit, price cents, pack, lead days, minimum order cents)]): two or more synthetic suppliers per need, so the comparison is real
MERIDIAN_SUPPLIERS = [("Synthetic Studio Equipment Supplier", "Fitness equipment", [("Spin bike", "equip.spin-bike", "each", 98000, 1, 14, 0), ("Rubber flooring", "equip.rubber-floor", "m2", 4200, 10, 7, 30000), ("Dumbbell rack set", "equip.dumbbell-set", "each", 64000, 1, 10, 0)]),
                      ("Synthetic Fitness Equipment Wholesale", "Fitness equipment", [("Spin bike", "equip.spin-bike", "each", 94500, 1, 28, 200000), ("Rubber flooring", "equip.rubber-floor", "m2", 4650, 10, 5, 0), ("Dumbbell rack set", "equip.dumbbell-set", "each", 61500, 1, 21, 0), ("Studio sound system", "equip.sound-system", "each", 215000, 1, 12, 0)]),
                      ("Synthetic Linen and Towel Service", "Laundry service", [("Towel service (per pickup)", "svc.towel-service", "pickup", 25000, 1, 3, 0)]),
                      ("Synthetic Fresh Fold Laundry", "Laundry service", [("Towel service (per pickup)", "svc.towel-service", "pickup", 23500, 1, 5, 0)]),
                      ("Synthetic Studio Cleaning Co", "Cleaning service", [("Studio cleaning (per visit)", "svc.studio-cleaning", "visit", 8500, 1, 2, 0), ("Surface sanitiser", "sup.sanitiser", "L", 1800, 5, 3, 0)]),
                      ("Synthetic Facility Supply", "Janitorial supplies", [("Studio cleaning (per visit)", "svc.studio-cleaning", "visit", 9200, 1, 2, 0), ("Surface sanitiser", "sup.sanitiser", "L", 1650, 10, 4, 5000)])]
MERIDIAN_REQUIREMENTS = [("equip.spin-bike", "Spin bike", "equipment", 20, "each", "one_time"), ("equip.rubber-floor", "Rubber flooring", "equipment", 180, "m2", "one_time"), ("equip.dumbbell-set", "Dumbbell rack set", "equipment", 2, "each", "one_time"),
                         ("equip.sound-system", "Studio sound system", "equipment", 1, "each", "one_time"), ("svc.towel-service", "Towel service (per pickup)", "service", 2, "pickup", "per_week"),
                         ("svc.studio-cleaning", "Studio cleaning (per visit)", "service", 3, "visit", "per_week"), ("sup.sanitiser", "Surface sanitiser", "consumable", 6, "L", "per_week")]


def seed_nasha_launch(svc, today=None):
    today = today or date.today()          # synthetic quotes are valid for 30 days from the seeding date (the fixture's own window is fixed in the past)
    pid = svc.create_project(**NASHA_PROJECT, basis="synthetic")
    for k, label, v, unit, basis, note in NASHA_ASSUMPTIONS:
        svc.set_assumption(pid, k, label, v, unit, basis, note)
    for title, phase, due, st in NASHA_MILESTONES:
        m = svc.add_milestone(pid, title, phase, due)
        if st != "todo":
            svc.set_milestone_status(m, st)
    for topic, finding, kind, conf, limit, url in NASHA_FINDINGS:
        svc.add_finding(pid, topic, finding, kind, conf, limit, url, SEARCHED if kind == "search_result" else None)
    svc.add_finding(pid, *OFFICIAL_SITE_FINDING[:5], OFFICIAL_SITE_FINDING[5], SEARCHED)
    master = RM.load_master(); q = SUPQ.load(); sid = {}; kinds = {"goat and lamb": "specialty meats"}
    for s in q["suppliers"]:
        sid[s["supplier_id"]] = svc.add_supplier(f"{s['name']} ({kinds.get(s['kind'], s['kind'])})", kinds.get(s["kind"], s["kind"]).capitalize(), "Synthetic (no real service area)", "synthetic_fixture", "synthetic_fixture", notes="Fictional supplier from the repository's synthetic quote set.")
    for qt in q["quotes"]:
        ing = master[qt["ingredient_id"]]
        svc.add_supplier_product(sid[qt["supplier_id"]], ing["name"], qt["unit"], "SYNTHETIC_QUOTE", SYNTH_LIMIT, unit_price_cents=round(qt["unit_price"] * 100, 4), ingredient_ref=qt["ingredient_id"], pack_qty=qt["pack_qty"],
                                 lead_days=qt["lead_days"], min_order_cents=int(qt["min_order_usd"] * 100), valid_from=today - timedelta(days=1), valid_to=today + timedelta(days=29))
    leads = {}
    for r in REAL["suppliers"]:
        name = r["name"]
        leads[name] = svc.add_supplier(name, r["category"], r["service_area"], "lead_unverified", "search_result", source_url=r["sources"][0][1], verified_on=None, notes=r["notes"])
        for kind, url2, claim in r["sources"]:
            svc.add_supplier_source(leads[name], kind, url2, claim, "search_snippet", SEARCHED)
        svc.add_supplier_product(leads[name], "Wholesale catalogue (no published prices seen)", "n/a", "NONE_PUBLISHED", NO_PRICE, source_url=r["sources"][0][1])
        if r["shortlist"]:
            svc.set_project_supplier(pid, leads[name], "shortlisted", "Candidate to ask for a quote later. No contact has been made.")
    for fx in ("S03", "S04", "FS01"):
        svc.set_project_supplier(pid, sid[fx], "shortlisted", "Synthetic fixture used to exercise the comparison.")
    econ = {e["name"]: e for e in svc.product_economics()}
    seg = svc.create_segment("courtyard-launch-neighbours", "icp", {"description": "residents and workers within a short walk of the proposed venue", "basis": "assumption"}, "synthetic_assumption", 0.3)
    for nm, pname, disc in (("Opening week appetizer offer", "Chaat Elote", 15), ("Weekday lunch main offer", "Paneer Tikka Taco", 10)):
        if pname in econ:
            off = svc.create_offer(nm, econ[pname]["id"], disc, today + timedelta(days=60), today + timedelta(days=67))
            svc.create_campaign(f"{nm} — planning draft", off, seg)
    svc.set_project_stage(pid, "sourcing")
    return dict(project=pid, suppliers=sid, leads=leads)


def seed_meridian_launch(svc, today=None):
    """A complete second-industry launch: the same tables, workflow and authorisation as the flagship; what differs is DATA (requirements, suppliers, assumptions), never code."""
    today = today or date.today()
    pid = svc.create_project(**MERIDIAN_PROJECT, basis="synthetic")
    for k, label, v, unit, basis, note in MERIDIAN_ASSUMPTIONS:
        svc.set_assumption(pid, k, label, v, unit, basis, note)
    for title, phase, due, st in MERIDIAN_MILESTONES:
        m = svc.add_milestone(pid, title, phase, due)
        if st != "todo":
            svc.set_milestone_status(m, st)
    for topic, finding, kind, conf, limit in MERIDIAN_FINDINGS:
        svc.add_finding(pid, topic, finding, kind, conf, limit, None, None)
    for ref, name, kind, qty, unit, rec in MERIDIAN_REQUIREMENTS:
        svc.add_requirement(pid, ref, name, kind, qty, unit, rec, "Synthetic planning requirement")
    sids = {}
    for name, cat, prods in MERIDIAN_SUPPLIERS:
        s = svc.add_supplier(name, cat, "Synthetic (no real service area)", "synthetic_fixture", "synthetic_fixture", notes="Fictional supplier.")
        sids[name] = s
        for pn, ref, unit, cents, pack, lead, mn in prods:
            svc.add_supplier_product(s, pn, unit, "SYNTHETIC_QUOTE", SYNTH_LIMIT, unit_price_cents=cents, ingredient_ref=ref, pack_qty=pack, lead_days=lead, min_order_cents=mn, valid_from=today - timedelta(days=1), valid_to=today + timedelta(days=29))
        svc.set_project_supplier(pid, s, "shortlisted", "Synthetic fixture.")
    svc.set_project_stage(pid, "financial_plan")
    return dict(project=pid, suppliers=sids)
