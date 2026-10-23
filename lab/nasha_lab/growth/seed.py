"""Deterministic SYNTHETIC seed data for two different simulated businesses (tenants). Names are invented, emails use the reserved example.invalid domain, amounts are assumptions.
NASHA (restaurant/brewery concept) draws products and costs from the existing recipe-costing module and segments from the synthetic order history; Meridian Fitness (a studio) has its own products, prices,
customers, accounts and pipeline. Neither is a real business."""
import random
from datetime import date

from . import pricing as GP, segments as GS

FIRST = ["Asha", "Ben", "Cleo", "Dev", "Esme", "Finn", "Gita", "Hugo", "Iris", "Jon", "Kira", "Leo", "Maya", "Nico", "Opal", "Pablo", "Quin", "Rhea", "Sol", "Tara"]
LAST = ["Alder", "Birch", "Cedar", "Dunn", "Elm", "Fir", "Grove", "Hazel", "Ivey", "Juniper", "Knoll", "Laurel", "Maple", "Nettle", "Oakes", "Pine"]


def _people(rnd, tag, n):
    return [(f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", f"{tag}{i:03d}@example.invalid") for i in range(n)]


def seed_nasha(svc, warehouse_path, seed=1):
    """Owner-run seed: segments from RFM, products + current prices from the existing costing, B2B event/catering accounts, leads and opportunities."""
    rnd = random.Random(seed)
    seg, _ = GS.segment(warehouse_path)
    seg_ids = {name: svc.create_segment(f"nasha-{name}", "behavioral", s["criteria"], "synthetic_data_derived", round(s["confidence"], 4), s["est_value_cents"]) for name, s in seg.items() if s["n"]}
    icp = svc.create_segment("nasha-corporate-lunch-organisers", "icp", {"description": "offices ordering team lunches and private events", "basis": "assumption"}, "synthetic_assumption", 0.3)
    prods = {}
    for rid, it in GP.nasha_items().items():
        pid = svc.create_product(it["name"], "dish", round(it["cost_cents"]), "planning_assumption")
        svc.set_price(pid, it["price_cents"], date(2026, 10, 23), "current", "founder-approved concept price (D-88)")
        prods[rid] = pid
    accounts = []
    for i, (name, email) in enumerate(_people(rnd, "nasha", 8)):
        a = svc.create_account(f"{name.split()[1]} Events {i}", "business", icp)
        c = svc.create_contact(a, name, email)
        l = svc.create_lead(c, rnd.choice(["synthetic-referral", "synthetic-website-form", "synthetic-event-fair"]))
        accounts.append((a, c, l))
    return dict(segments={**seg_ids, "icp": icp}, products=prods, accounts=accounts)


def seed_fitness(svc, seed=2):
    """A different business: studio memberships, class packs and personal training, with its own accounts, leads and prices."""
    rnd = random.Random(seed)
    icp = svc.create_segment("fit-busy-professionals", "icp", {"description": "working adults wanting 2-3 sessions a week", "basis": "assumption"}, "synthetic_assumption", 0.25)
    prods = {}
    for name, kind, cost, price in [("Monthly membership", "membership", 1800, 7900), ("10-class pack", "pack", 2500, 14900), ("Personal training session", "service", 3500, 8500)]:
        pid = svc.create_product(name, kind, cost); svc.set_price(pid, price, date(2026, 10, 23), "current", "synthetic assumption"); prods[name] = pid
    accounts = []
    for i, (name, email) in enumerate(_people(rnd, "fit", 6)):
        a = svc.create_account(f"{name} (household {i})", "household", icp)
        c = svc.create_contact(a, name, email)
        l = svc.create_lead(c, rnd.choice(["synthetic-trial-class", "synthetic-referral"]))
        accounts.append((a, c, l))
    return dict(segments={"icp": icp}, products=prods, accounts=accounts)
