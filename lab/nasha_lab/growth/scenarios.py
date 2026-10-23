"""Coherent SYNTHETIC business scenarios for the two demo tenants. Every organisation and person is fictional (emails use the reserved example.invalid domain). Nothing here is a real customer,
partnership, quote or sale. NASHA is a proposed concept: the scenarios below are PROPOSED USE CASES the platform is being tested against, not services NASHA provides today.
Pipeline values are computed from the tenant's own stored concept prices (products x prices), not typed in. Each lead carries the information a sales person would have (who, what they asked, when,
who owns it) and signals consistent with that story, so qualification explanations read as business reasoning."""
from datetime import date

# --- NASHA (restaurant and brewery concept) -------------------------------------------------------------------------------------------------------------------------------------------------------
# disposition: what the demo does with the lead (executed / awaiting / rejected / denied / suppressed / abstain / none)
NASHA = [
    dict(key="catering", scenario="Corporate catering inquiry", org="Larkspur Analytics", kind="business", person="Dana Whitfield", title="Office Manager", slug="dana.whitfield", source="synthetic-website-form",
         received=date(2026, 10, 12), owner="sam", consent="opt_in", disposition="awaiting",
         inquiry="Friday team lunch for about 40 people in mid-November. Needs vegetarian options. Finance has approved the budget; the operations director signs off on the menu.",
         signals=dict(budget_confirmed=True, decision_maker=False, timeline_days=24, fit=0.9, engagement=0.8), basket=[("Chicken Tikka Tacos", 20), ("Paneer Tikka Taco", 20), ("Chaat Elote", 20)], opp="Larkspur team lunch (40 guests)"),
    dict(key="event", scenario="Private event booking", org="Oyelaran Family", kind="household", person="Marcus Oyelaran", title=None, slug="marcus.oyelaran", source="synthetic-referral",
         received=date(2026, 10, 9), owner="ada", consent="opt_in", disposition="executed",
         inquiry="60th birthday dinner for 25 guests, five weeks out. Wants a shared-plates menu and a beer pairing. Marcus makes the decision and has a budget in mind.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=35, fit=0.8, engagement=0.9), basket=[("Nawaabi Enchiladas", 10), ("Goan Peri-Peri Wings", 12), ("Chaat Elote", 12)], opp="Oyelaran 60th birthday (25 guests)"),
    dict(key="hotel", scenario="Hospitality partnership", org="Juniper Row Hotel", kind="business", person="Tomas Reyes", title="Concierge Manager", slug="tomas.reyes", source="synthetic-event-fair",
         received=date(2026, 10, 2), owner="sam", consent="opt_in", disposition="rejected",
         inquiry="Exploring a welcome-drink and dinner-voucher partnership for hotel guests. No budget has been set and the general manager has not been involved yet.",
         signals=dict(budget_confirmed=False, decision_maker=False, timeline_days=120, fit=0.5, engagement=0.3), basket=[], opp=None),
    dict(key="market", scenario="Local community event", org="Eastside Makers Market", kind="business", person="Lila Brandt", title="Market Organiser", slug="lila.brandt", source="synthetic-event-fair",
         received=date(2026, 10, 14), owner="sam", consent="opt_in", disposition="executed",
         inquiry="Street fair in six weeks. Asking whether a beer-garden vendor slot would be possible. Lila decides, but there is no vendor budget; vendors pay a stall fee.",
         signals=dict(budget_confirmed=False, decision_maker=True, timeline_days=42, fit=0.6, engagement=0.7), basket=[], opp=None),
    dict(key="merch", scenario="Merchandise partnership", org="Copperline Print Co.", kind="business", person="Ines Calder", title="Account Executive", slug="ines.calder", source="synthetic-referral",
         received=date(2026, 10, 6), owner="sam", consent="opt_in", disposition="suppressed", suppress_reason="Asked not to be contacted again (synthetic)",
         inquiry="Proposed co-branded glassware. Asked us to stop contacting them after the first call.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=20, fit=0.7, engagement=0.6), basket=[], opp=None),
    dict(key="legal", scenario="Corporate catering inquiry", org="Redwood Legal Group", kind="business", person="Hana Petrov", title="Front Desk Lead", slug="hana.petrov", source="synthetic-website-form",
         received=date(2026, 10, 15), owner="sam", consent="none", disposition="executed",
         inquiry="Monthly working lunches for a 15-person firm. No consent for marketing contact has been recorded yet, so only the qualification can be recorded, not outreach.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=60, fit=0.6, engagement=0.9), basket=[("Paneer Makhani Pizza", 5), ("Chaat Elote", 5)], opp="Redwood monthly working lunches (15 people)"),
    dict(key="dental", scenario="Corporate catering inquiry", org="Hartley Dental", kind="business", person="Priyanka Hartley", title="Practice Owner", slug="priyanka.hartley", source="synthetic-referral",
         received=date(2026, 10, 18), owner="sam", consent="opt_in", disposition="abstain",
         inquiry="Referral from a past guest; the practice owner mentioned a staff lunch. No qualification details were captured yet, so the system should abstain rather than guess.",
         signals=None, basket=[], opp=None),
    dict(key="retention", scenario="Restaurant customer retention", org="Moreno Household", kind="household", person="Sofia Moreno", title=None, slug="sofia.moreno", source="synthetic-referral",
         received=date(2026, 10, 19), owner="sam", consent="opt_in", disposition="denied",
         inquiry="Regular guest in the simulated order history who has not visited in 70 days. Candidate for a win-back conversation after consent is confirmed.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=14, fit=0.7, engagement=0.4), basket=[], opp=None),
]
# Completed (simulated) deals that populate the pipeline with stage history: (org, person, slug, opp name, basket, final stage path)
NASHA_HISTORY = [
    dict(org="Fernhill Co-working", person="Gil Amato", slug="gil.amato", opp="Fernhill launch-party catering", basket=[("Chicken Tikka Tacos", 30), ("Chaat Elote", 25)], path=["qualified", "proposal", "negotiation", "won"]),
    dict(org="Pell Street Gallery", person="Wren Okada", slug="wren.okada", opp="Pell Street opening night", basket=[("Goan Peri-Peri Wings", 40)], path=["qualified", "proposal"]),
    dict(org="Marlowe & Finch Design", person="Ravi Marlowe", slug="ravi.marlowe", opp="Marlowe & Finch client dinner", basket=[("Nawaabi Enchiladas", 12), ("Paneer Makhani Pizza", 6)], path=["qualified", "proposal", "negotiation"]),
    dict(org="Tern Running Club", person="Odile Tern", slug="odile.tern", opp="Tern club post-race social", basket=[("Crispy Aloo Chaat Nachos", 30)], path=["qualified", "lost"]),
]

# --- Meridian Fitness (a separate synthetic studio) -----------------------------------------------------------------------------------------------------------------------------------------------
MERIDIAN = [
    dict(key="wellness", scenario="Corporate wellness programme", org="Kestrel Logistics", kind="business", person="Renata Voss", title="HR Director", slug="renata.voss", source="synthetic-referral",
         received=date(2026, 10, 8), owner="sam", consent="opt_in", disposition="awaiting",
         inquiry="Wants memberships for 25 employees for three months as a wellness benefit. Budget approved by finance; Renata signs the agreement.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=21, fit=0.9, engagement=0.8), basket=[("Monthly membership", 75)], opp="Kestrel wellness benefit (25 staff, 3 months)"),
    dict(key="trial", scenario="Trial class follow-up", org="Okafor Household", kind="household", person="Jamal Okafor", title=None, slug="jamal.okafor", source="synthetic-trial-class",
         received=date(2026, 10, 16), owner="sam", consent="opt_in", disposition="executed",
         inquiry="Attended a free trial class on Saturday and asked about a 10-class pack. Wants to start within two weeks.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=14, fit=0.8, engagement=0.9), basket=[("10-class pack", 1)], opp="Okafor 10-class pack"),
    dict(key="winback", scenario="Lapsed member win-back", org="Marsh Household", kind="household", person="Elena Marsh", title=None, slug="elena.marsh", source="synthetic-referral",
         received=date(2026, 10, 11), owner="ada", consent="opt_in", disposition="rejected",
         inquiry="Member who paused six months ago. Replied to a referral message but has not said whether a budget exists or when she would return.",
         signals=dict(budget_confirmed=False, decision_maker=True, timeline_days=100, fit=0.5, engagement=0.4), basket=[], opp=None),
    dict(key="pt", scenario="Personal training package", org="Calderon Household", kind="household", person="Bruno Calderon", title=None, slug="bruno.calderon", source="synthetic-trial-class",
         received=date(2026, 10, 13), owner="sam", consent="opt_in", disposition="denied",
         inquiry="Interested in ten personal-training sessions. Contact came through the studio newsletter form.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=30, fit=0.7, engagement=0.6), basket=[("Personal training session", 10)], opp=None),
    dict(key="optout", scenario="Trial class follow-up", org="Hollis Household", kind="household", person="Cam Hollis", title=None, slug="cam.hollis", source="synthetic-trial-class",
         received=date(2026, 10, 5), owner="sam", consent="opt_in", disposition="suppressed", suppress_reason="Unsubscribed after the trial class (synthetic)",
         inquiry="Attended a trial class, then unsubscribed from all contact.",
         signals=dict(budget_confirmed=True, decision_maker=True, timeline_days=20, fit=0.6, engagement=0.5), basket=[], opp=None),
]
MERIDIAN_HISTORY = [
    dict(org="Birchwood Dental Staff", person="Mara Birchwood", slug="mara.birchwood", opp="Birchwood staff class pack", basket=[("10-class pack", 8)], path=["qualified", "proposal", "negotiation", "won"]),
    dict(org="Linden Apartments", person="Kofi Linden", slug="kofi.linden", opp="Linden residents' monthly memberships", basket=[("Monthly membership", 20)], path=["qualified", "proposal"]),
]


def price_map(svc):
    """name -> current price in cents, read from the tenant's own stored prices."""
    return {n: int(c) for n, c in svc.read("SELECT p.name, pr.amount_cents FROM products p JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id WHERE p.tenant_id=%s AND pr.status='current'", (svc.tenant,))}


def basket_cents(prices, basket):
    return sum(prices[name] * qty for name, qty in basket)


def seed(svc_sales, svc_owner, plan, history):
    """Create accounts, contacts, consent, leads (with inquiry, owner, scenario) and the history deals. Returns {key: lead_id}. Runs with the tenant's own users: sales creates records, owner suppresses where the scenario says so."""
    prices = price_map(svc_owner)
    ids = {}
    for sc in plan:
        a = svc_sales.create_account(sc["org"], sc["kind"])
        c = svc_sales.create_contact(a, sc["person"], f"{sc['slug']}@example.invalid", sc["title"])
        if sc["consent"] != "none":
            svc_sales.set_consent(c, sc["consent"])
        ids[sc["key"]] = svc_sales.create_lead(c, sc["source"], sc["signals"], sc["inquiry"], sc["owner"], sc["scenario"], sc["received"])
        if sc["disposition"] == "suppressed":
            svc_sales.suppress(f"{sc['slug']}@example.invalid", sc["suppress_reason"])
    for h in history:
        a = svc_sales.create_account(h["org"], "business")
        c = svc_sales.create_contact(a, h["person"], f"{h['slug']}@example.invalid")
        svc_sales.set_consent(c, "opt_in")
        lead = svc_sales.create_lead(c, "synthetic-referral", dict(budget_confirmed=True, decision_maker=True, timeline_days=25, fit=0.8, engagement=0.8), f"Completed simulated deal: {h['opp']}.", "sam", "Simulated history", date(2026, 9, 1))
        svc_sales.qualify_lead(lead, dict(budget_confirmed=True, decision_maker=True, timeline_days=25, fit=0.8, engagement=0.8))
        opp = svc_sales.convert_lead(lead, h["opp"], basket_cents(prices, h["basket"]))
        for st in h["path"]:
            svc_sales.advance(opp, st)
    return ids, prices
