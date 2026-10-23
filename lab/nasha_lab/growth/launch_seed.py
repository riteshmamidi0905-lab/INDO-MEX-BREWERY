"""Seed data for the business-launch workspace of the two SYNTHETIC tenants. NASHA — The Courtyard is the flagship hospitality launch case study (a proposed brand, not an operating business); Meridian Fitness is a
second, unrelated business, so the platform stays industry-agnostic. Everything is labelled by provenance:
  * assumptions: 'synthetic_assumption' (planning inputs I chose, replaceable by the founder), never presented as measured;
  * supplier fixtures: the repository's existing SYNTHETIC supplier quotes (price class SYNTHETIC_QUOTE), reused, not re-invented;
  * three REAL supplier LEADS found through public web search on 2026-10-23: name/category/area and the page that mentions them ONLY. They are 'lead_unverified': no official website verified, no contact, no price;
  * research findings from those pages are 'search_result' with their URL, retrieval date and limitations.
No supplier has been contacted and no price from a real supplier is recorded."""
from datetime import date

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
                     ("startup_capex_cents", "Start-up capital expenditure", 42_000_000, "cents", "synthetic_assumption", "Build-out and equipment placeholder; no quote exists.")]
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
REAL_LEADS = [("Farm to Table LLC", "Produce, eggs and dairy wholesale", "Austin and surrounding areas (per the source)", "https://www.austinchronicle.com/food/food-o-file-11764527/", "Reported by the Austin Chronicle; official website not verified."),
              ("Hill Country Dairies", "Dairy distribution", "Austin, TX (per the source)", "https://www.pnc.com/content/riverarch/us/en/portfolio/hill-country-dairies.html", "Described in a PNC investment profile; official website not verified."),
              ("Brothers Produce", "Produce distribution", "Greater Houston, Dallas/Fort Worth, Austin, San Antonio and other Texas metros (per the source)", "https://www.restaurant365.com/partners/brothers-produce/", "Described in a Restaurant365 partner profile; official website not verified.")]

MERIDIAN_PROJECT = dict(name="Second studio location", industry="Fitness", location="Cedar Park, TX", concept="A second boutique fitness studio for a growing member base, with the same class formats and memberships as the first.",
                        budget_cents=18_000_000, launch_target=date(2027, 6, 1))
MERIDIAN_ASSUMPTIONS = [("weekly_orders", "New sales per week", 38, "sales", "synthetic_assumption", "Assumed once established."), ("items_per_order", "Items per sale", 1.0, "items", "synthetic_assumption", None), ("avg_discount_pct", "Average discount", 4, "%", "synthetic_assumption", None),
                        ("variable_overhead_pct", "Payment fees", 2.9, "% of price", "synthetic_assumption", None), ("price_elasticity", "Price elasticity of demand", -0.9, "ratio", "synthetic_assumption", "Assumed."),
                        ("rent_monthly_cents", "Rent", 900_000, "cents/month", "synthetic_assumption", None), ("labor_monthly_cents", "Instructors and front desk", 1_400_000, "cents/month", "synthetic_assumption", None),
                        ("utilities_monthly_cents", "Utilities", 150_000, "cents/month", "synthetic_assumption", None), ("marketing_monthly_cents", "Marketing", 200_000, "cents/month", "synthetic_assumption", None),
                        ("insurance_monthly_cents", "Insurance", 90_000, "cents/month", "synthetic_assumption", None), ("other_fixed_monthly_cents", "Other fixed costs", 120_000, "cents/month", "synthetic_assumption", None),
                        ("startup_capex_cents", "Fit-out and equipment", 9_500_000, "cents", "synthetic_assumption", "Placeholder; no quote exists.")]
MERIDIAN_MILESTONES = [("Confirm demand from the waiting list", "research", date(2026, 12, 1), "doing"), ("Compare equipment and cleaning-service suppliers", "sourcing", date(2027, 1, 20), "todo"), ("Review the financial plan", "financial_plan", date(2027, 2, 15), "todo"), ("Launch roadmap", "roadmap", date(2027, 4, 1), "todo")]
MERIDIAN_SUPPLIERS = [("Synthetic Studio Equipment Supplier", "Fitness equipment", [("Spin bike", "each", 98000, 1, 14, 0), ("Rubber flooring (per m2)", "m2", 4200, 10, 7, 30000)]), ("Synthetic Linen and Towel Service", "Laundry service", [("Towel service (per pickup)", "pickup", 25000, 1, 3, 0)])]


def seed_nasha_launch(svc):
    pid = svc.create_project(**NASHA_PROJECT, basis="synthetic")
    for k, label, v, unit, basis, note in NASHA_ASSUMPTIONS:
        svc.set_assumption(pid, k, label, v, unit, basis, note)
    for title, phase, due, st in NASHA_MILESTONES:
        m = svc.add_milestone(pid, title, phase, due)
        if st != "todo":
            svc.set_milestone_status(m, st)
    for topic, finding, kind, conf, limit, url in NASHA_FINDINGS:
        svc.add_finding(pid, topic, finding, kind, conf, limit, url, SEARCHED if kind == "search_result" else None)
    master = RM.load_master(); q = SUPQ.load(); sid = {}; kinds = {"goat and lamb": "specialty meats"}
    for s in q["suppliers"]:
        sid[s["supplier_id"]] = svc.add_supplier(f"{s['name']} ({kinds.get(s['kind'], s['kind'])})", kinds.get(s["kind"], s["kind"]).capitalize(), "Synthetic (no real service area)", "synthetic_fixture", "synthetic_fixture", notes="Fictional supplier from the repository's synthetic quote set.")
    for qt in q["quotes"]:
        ing = master[qt["ingredient_id"]]
        svc.add_supplier_product(sid[qt["supplier_id"]], ing["name"], qt["unit"], "SYNTHETIC_QUOTE", SYNTH_LIMIT, unit_price_cents=round(qt["unit_price"] * 100, 4), ingredient_ref=qt["ingredient_id"], pack_qty=qt["pack_qty"],
                                 lead_days=qt["lead_days"], min_order_cents=int(qt["min_order_usd"] * 100), valid_from=date.fromisoformat(qt["valid_from"]), valid_to=date.fromisoformat(qt["valid_to"]))
    leads = {}
    for name, cat, area, url, note in REAL_LEADS:
        leads[name] = svc.add_supplier(name, cat, area, "lead_unverified", "search_result", source_url=url, verified_on=None, notes=note)
        svc.add_supplier_product(leads[name], "Wholesale catalogue (no published prices)", "n/a", "NONE_PUBLISHED", NO_PRICE, source_url=url)
        svc.set_project_supplier(pid, leads[name], "shortlisted", "Candidate to ask for a quote later. No contact has been made.")
    for fx in ("S03", "S04", "FS01"):
        svc.set_project_supplier(pid, sid[fx], "shortlisted", "Synthetic fixture used to exercise the comparison.")
    svc.set_project_stage(pid, "sourcing")
    return dict(project=pid, suppliers=sid, leads=leads)


def seed_meridian_launch(svc):
    pid = svc.create_project(**MERIDIAN_PROJECT, basis="synthetic")
    for k, label, v, unit, basis, note in MERIDIAN_ASSUMPTIONS:
        svc.set_assumption(pid, k, label, v, unit, basis, note)
    for title, phase, due, st in MERIDIAN_MILESTONES:
        m = svc.add_milestone(pid, title, phase, due)
        if st != "todo":
            svc.set_milestone_status(m, st)
    svc.add_finding(pid, "Demand", "The first studio has a waiting list of 140 people (synthetic figure).", "synthetic_fixture", 0.4, "Synthetic planning input; not a real waiting list.", None, None)
    sids = {}
    for name, cat, prods in MERIDIAN_SUPPLIERS:
        s = svc.add_supplier(name, cat, "Synthetic (no real service area)", "synthetic_fixture", "synthetic_fixture", notes="Fictional supplier.")
        sids[name] = s
        for pn, unit, cents, pack, lead, mn in prods:
            svc.add_supplier_product(s, pn, unit, "SYNTHETIC_QUOTE", SYNTH_LIMIT, unit_price_cents=cents, pack_qty=pack, lead_days=lead, min_order_cents=mn, valid_from=date(2026, 10, 22), valid_to=date(2026, 11, 21))
        svc.set_project_supplier(pid, s, "shortlisted", "Synthetic fixture.")
    svc.set_project_stage(pid, "financial_plan")
    return dict(project=pid, suppliers=sids)
