"""Seeded analytics-layer simulations. SYNTHETIC. Everything here is an invention of this package, labelled as such in the mart.

The lab generator provides sites, menu, orders and order lines. It does NOT provide: dated menu changes, guests, receipts with timing,
purchase-order history, logged waste or an exception workflow. Those are simulated below with parameters from config.py, and every
injected property (late suppliers, unlogged shrink, short shipments) is recorded in a truth dict so analyses can be scored against it.
"""
import datetime as dt
import random

from nasha_lab import generator, world

from . import config as C

D = dt.date.fromisoformat
START = generator.START
N_USAGE_DAYS = generator.DAYS            # 56 days of orders: days 0..55
SNAP_DAYS = list(range(0, 57, 7))        # weekly start-of-day counts, day 56 = the day after the last order day
LEAD = {ing: lt for (_s, ing, lt, _spec, _moq) in world.SUPPLIER_INGREDIENTS}
SUPPLIER_OF = {ing: s for (s, ing, *_r) in world.SUPPLIER_INGREDIENTS}
MOQ = {ing: moq for (_s, ing, _lt, _spec, moq) in world.SUPPLIER_INGREDIENTS}


def recipe_at(item_id, date_iso):
    """Recipe in force for an item on a date (SCD2-consistent): M04 changes from v1 to v2 on MENU_CHANGE_DATE."""
    if item_id == "M04" and date_iso >= C.MENU_CHANGE_DATE:
        return world.RECIPES_V2["M04"]
    return world.RECIPES.get(item_id, {})


def usage_by_day(order_rows):
    """order_rows: iterable of (site_id, order_date, item_id, qty). Returns {(site, ingredient, day_index): kg} using the dated recipe."""
    use = {}
    for site, d, item, qty in order_rows:
        di = (D(d) - START).days
        for ing, kg in recipe_at(item, d).items():
            use[(site, ing, di)] = use.get((site, ing, di), 0.0) + qty * kg
    return use


def simulate_inventory(use, seed):
    """Day-by-day stock simulation per site x ingredient with weekly counts and a base-stock reorder policy.

    Returns dict(snapshots, receipts, pos, waste, truth).
      snapshots: (site, ingredient, day, counted_qty)
      receipts : (site, ingredient, day, qty_received)        physical arrivals (used by the stock balance)
      pos      : PO line dicts (order day, expected day, received day or None, qty_ordered, qty_received)
      waste    : (site, ingredient, day, reason, qty)         the LOGGED waste events
    """
    rng = random.Random(seed * 6607 + 11)
    snaps, receipts, pos, waste = [], [], [], []
    truth = {"late_prob": dict(C.SUPPLIER_LATE_PROB), "unlogged_shrink": [list(x) for x in C.INJECTED_SHRINK], "short_ship_prob": C.SHORT_SHIP_PROB}
    shrink = {(s, i): r for s, i, r in C.INJECTED_SHRINK}
    sites = [l[0] for l in generator.LOCATIONS]
    for site in sites:
        for ing in generator.INGREDIENT_UNIT:
            u = [use.get((site, ing, d), 0.0) for d in range(N_USAGE_DAYS + 1)]       # day 56 has no orders: usage 0
            lead = LEAD[ing]; sup = SUPPLIER_OF[ing]
            run_rate = sum(u[:N_USAGE_DAYS]) / N_USAGE_DAYS
            kind = "perishable" if ing in C.PERISHABLE else "dry"
            # logged waste plan: at most one event per week
            wplan = {}
            for w in range(8):
                if rng.random() < C.WASTE_EVENT_PROB[kind]:
                    day = 7 * w + rng.randrange(7)
                    qty = round(max(0.2, sum(u[7 * w:7 * w + 7]) * rng.uniform(*C.WASTE_FRACTION_OF_WEEKLY_USAGE)), 2)
                    wplan[day] = (rng.choice(C.WASTE_REASONS[kind]), qty)
            stock = max(run_rate * (7 + lead + 2), 5.0)
            pending = []                                  # (arrive_day, qty, po_index)
            for d in range(0, 57):
                for p in [p for p in pending if p[0] == d]:
                    stock += p[1]; receipts.append((site, ing, d, round(p[1], 2)))
                    pos[p[2]]["received_day"] = d; pos[p[2]]["qty_received"] = round(p[1], 2)
                pending = [p for p in pending if p[0] != d]
                if d % 7 == 0:
                    counted = round(stock * rng.uniform(*C.COUNT_NOISE), 2)
                    snaps.append((site, ing, d, counted))
                    hist = u[max(0, d - 14):d] if d >= 7 else u[:N_USAGE_DAYS]
                    avg = sum(hist) / len(hist)
                    position = counted + sum(p[1] for p in pending)
                    target = avg * (7 + lead + 2)
                    need = target - position
                    if need > 0:
                        qty = max(round(need, 1), float(MOQ[ing]))
                        late = rng.random() < C.SUPPLIER_LATE_PROB[sup]
                        delay = rng.randint(*C.SUPPLIER_LATE_DAYS[sup]) if late else 0
                        short = rng.random() < C.SHORT_SHIP_PROB
                        rec_qty = round(qty * (1 - rng.uniform(*C.SHORT_SHIP_RANGE)), 2) if short else qty
                        pos.append({"site": site, "ingredient": ing, "supplier": sup, "order_day": d, "expected_day": d + lead, "delay": delay,
                                    "received_day": None, "qty_ordered": qty, "qty_received": 0.0, "planned_receive": rec_qty})
                        pending.append((d + lead + delay, rec_qty, len(pos) - 1))
                if d < N_USAGE_DAYS:
                    out = u[d]
                    if d in wplan:
                        waste.append((site, ing, d, wplan[d][0], wplan[d][1])); out += wplan[d][1]
                    out += shrink.get((site, ing), 0.0) * u[d]
                    stock = max(0.0, stock - out)
    return {"snapshots": snaps, "receipts": receipts, "pos": pos, "waste": waste, "truth": truth}


def assign_guests(orders, seed):
    """orders: list of (order_id, site_id, order_ts_iso, week_index). Returns {order_id: guest_id}. SYNTHETIC guest layer."""
    rng = random.Random(seed * 104729 + 7)
    pools = {}; out = {}; counter = {}
    for oid, site, ts, wk in sorted(orders, key=lambda r: (r[2], r[0])):
        if rng.random() > C.GUEST_ID_COVERAGE:
            continue
        p_new = C.GUEST_NEW_PROB_START + (C.GUEST_NEW_PROB_END - C.GUEST_NEW_PROB_START) * min(wk, 7) / 7
        pool = pools.setdefault(site, [])
        if not pool or rng.random() < p_new:
            counter[site] = counter.get(site, 0) + 1
            g = {"id": f"G-{site}-{counter[site]:04d}", "lam": rng.gammavariate(*C.GUEST_FREQ_GAMMA), "last": wk}
            pool.append(g)
        else:
            weights = [g["lam"] * 0.5 ** ((wk - g["last"]) / C.GUEST_CHURN_HALF_LIFE_WEEKS) for g in pool]
            g = rng.choices(pool, weights=weights)[0]
        g["last"] = wk
        out[oid] = g["id"]
    return out


def simulate_exception_workflow(exceptions, seed):
    """exceptions: list of (event_id, detected_ts_iso). Returns {event_id: (approved_ts|None, resolved_ts|None)}. SIMULATED process."""
    rng = random.Random(seed * 3571 + 5)
    out = {}
    for eid, ts in exceptions:
        t0 = dt.datetime.fromisoformat(ts)
        appr = res = None
        if rng.random() < C.EXC_APPROVAL_PROB:
            appr = t0 + dt.timedelta(hours=rng.uniform(1, C.EXC_MAX_APPROVAL_HOURS))
            if rng.random() < C.EXC_RESOLUTION_PROB:
                res = appr + dt.timedelta(hours=rng.uniform(1, C.EXC_MAX_RESOLUTION_HOURS))
        out[eid] = (appr.isoformat(timespec="seconds") if appr else None, res.isoformat(timespec="seconds") if res else None)
    return out
