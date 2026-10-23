"""Seed data for the business-launch workspace of the two SYNTHETIC tenants. NASHA — The Courtyard is the flagship hospitality launch case study (a proposed brand, not an operating business); Meridian Fitness is a
second, unrelated business, so the platform stays industry-agnostic. Everything is labelled by provenance:
  * assumptions: 'synthetic_assumption' (planning inputs I chose, replaceable by the founder), never presented as measured;
  * supplier fixtures: the repository's existing SYNTHETIC supplier quotes (price class SYNTHETIC_QUOTE), reused, not re-invented;
  * three REAL supplier LEADS found through public web search on 2026-10-23: name/category/area and the page that mentions them ONLY. They are 'lead_unverified': no official website verified, no contact, no price;
  * research findings from those pages are 'search_result' with their URL, retrieval date and limitations.
No supplier has been contacted and no price from a real supplier is recorded."""
from datetime import date, timedelta

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
REAL_LEADS = [("Farm to Table LLC", "Produce, eggs and dairy wholesale", "Austin and surrounding areas (per the source)", "https://www.austinchronicle.com/food/food-o-file-11764527/", "Reported by the Austin Chronicle; official website not verified."),
              ("Hill Country Dairies", "Dairy distribution", "Austin, TX (per the source)", "https://www.pnc.com/content/riverarch/us/en/portfolio/hill-country-dairies.html", "Described in a PNC investment profile; official website not verified."),
              ("Brothers Produce", "Produce distribution", "Greater Houston, Dallas/Fort Worth, Austin, San Antonio and other Texas metros (per the source)", "https://www.restaurant365.com/partners/brothers-produce/", "Described in a Restaurant365 partner profile; official website not verified.")]

# Dated public SOURCES for the three real leads, from a public web search run on SEARCHED. Every row is a search-result SNIPPET: the pages themselves could not be opened from this environment, so access='search_snippet'.
# A directory or press mention is evidence that the business exists and what it is described as doing; it is NOT an official website, a price, or a verification. No official website was found for any of the three.
REAL_SOURCES = {
    "Brothers Produce": [("partner_listing", "https://www.restaurant365.com/partners/brothers-produce/", "Listed as a Restaurant365 partner covering Austin among several Texas metros."),
                         ("trade_directory", "https://www.producemarketguide.com/company/113604/brothers-produce-inc", "Listed in the Produce Market Guide trade directory (headquarters entry)."),
                         ("press", "https://www.thepacker.com/news/industry/grubmarket-adds-brothers-produce", "Trade press (July 2024) reports that GrubMarket acquired Brothers Produce, a foodservice produce distributor serving Texas.")],
    "Hill Country Dairies": [("investor_profile", "https://www.pnc.com/content/riverarch/us/en/portfolio/hill-country-dairies.html", "Investor portfolio page describes an Austin-headquartered dairy distributor for foodservice customers."),
                             ("press", "https://www.themiddlemarket.com/latest-news/riverarch-equity-partners-invests-in-hill-country-dairies", "Trade press reports an equity investment in Hill Country Dairies by RiverArch Equity Partners.")],
    "Farm to Table LLC": [("press", "https://www.austinchronicle.com/food/food-o-file-11764527/", "Austin Chronicle describes an Austin distributor of locally grown produce to restaurants and school districts."),
                          ("trade_directory", "https://www.producemarketguide.com/company/549852/farm-to-table-llc", "Listed in the Produce Market Guide as an Austin wholesaler of locally grown farm products; contact details are behind a login and were not recorded."),
                          ("press", "https://refrigeratedfrozenfood.com/articles/91481-farm-to-table-expands-to-houston-market", "Trade press describes an Austin-based produce distributor expanding to Houston (an older article; may be out of date).")]}
OFFICIAL_SITE_FINDING = ("Supplier verification", "A public search on 2026-10-23 found directory listings, press and investor pages for Farm to Table LLC, Hill Country Dairies and Brothers Produce, but no confirmed official website for any of them. All three stay unverified leads.",
                         "search_result", 0.6, "Only search-result snippets were seen; the pages could not be opened here. An official website, public contact channel and published prices would need a person to confirm them.",
                         "https://www.producemarketguide.com/company/549852/farm-to-table-llc")

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
    for name, cat, area, url, note in REAL_LEADS:
        leads[name] = svc.add_supplier(name, cat, area, "lead_unverified", "search_result", source_url=url, verified_on=None, notes=note)
        for kind, url2, claim in REAL_SOURCES[name]:
            svc.add_supplier_source(leads[name], kind, url2, claim, "search_snippet", SEARCHED)
        svc.add_supplier_product(leads[name], "Wholesale catalogue (no published prices)", "n/a", "NONE_PUBLISHED", NO_PRICE, source_url=url)
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
    today = today or date.today()
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
            svc.add_supplier_product(s, pn, unit, "SYNTHETIC_QUOTE", SYNTH_LIMIT, unit_price_cents=cents, pack_qty=pack, lead_days=lead, min_order_cents=mn, valid_from=today - timedelta(days=1), valid_to=today + timedelta(days=29))
        svc.set_project_supplier(pid, s, "shortlisted", "Synthetic fixture.")
    svc.set_project_stage(pid, "financial_plan")
    return dict(project=pid, suppliers=sids)
