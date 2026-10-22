"""Configurable, deterministic SYNTHETIC multi-location enterprise simulation.

SYNTHETIC DATA / SIMULATED OPERATION. The business does not exist: no restaurant, brewery, customer, employee, sale or merchandise has ever
been real. Locations, people and loyalty profiles are fictional identifiers (no names, emails or addresses). Prices, wages and volumes are
PLACEHOLDER planning inputs, UNCALIBRATED against public industry benchmarks (see docs/ENTERPRISE-SIMULATION.md). Scenario dates are not
real time. Simulated performance says nothing about a real business.

This module ADDS a larger, configurable simulation. It does not change nasha_lab.generator (the three-site, 56-day baseline with injected
defects), which stays the byte-for-byte reproducible fixture for the existing evaluations.

    python -m nasha_lab.enterprise_sim --profile dev  --out /tmp/sim-dev      # 2 minutes of laptop time or less
    python -m nasha_lab.enterprise_sim --profile full --out /tmp/sim-full     # 14 sites, 24 months, ~2.5 M orders

Determinism: one integer seed drives numpy's PCG64 per (table, month) stream; output files are gzip CSV with a zero mtime, and manifest.json
carries a sha256 per file, so the same (profile, seed) yields identical hashes on the same numpy major version.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import generator

SIM_VERSION = "1"
FORBIDDEN_TERMS = ("pork", "beef", "bacon", "lard")


@dataclass(frozen=True)
class SimConfig:
    seed: int = 20261022
    start: str = "2024-01-01"                 # SCENARIO calendar
    months: int = 24
    fast_casual: int = 12
    beer_gardens: int = 2
    target_orders: int = 2_500_000
    loyalty_profiles: int = 150_000
    employees: int = 450
    loyalty_order_share: float = 0.38
    merch_order_share: float = 0.012          # of orders at merch-selling sites
    open_at_start: int = 8                    # others open over the first 18 months (a growing business)
    price_step_date: str = "2025-01-01"
    price_step: float = 1.04
    name: str = "custom"


PROFILES = {
    "dev": SimConfig(name="dev", months=2, fast_casual=2, beer_gardens=1, target_orders=6_000, loyalty_profiles=1_500, employees=40, open_at_start=3),
    "full": SimConfig(name="full"),
}

# ---------------------------------------------------------------- catalog (placeholders; concept SKUs are NOT products)
CATALOG = [  # item_id, name, category, price_cents, ingredients, status
    *[(m[0], m[1], m[2], m[3], m[4], "baseline catalog; placeholder price") for m in generator.MENU_V2],
    ("B04", "Amba Haze mango hazy IPA (working name, experimental concept)", "beer", 900, "water;malt;hops;yeast;mango", "experimental concept SKU, never brewed; working name; placeholder price"),
    ("G01", "Hoodie 01 The Courtyard (concept)", "merch", 8800, "", "concept merchandise, never made or sold; placeholder price"),
    ("G02", "Hoodie 02 Two Worlds (concept)", "merch", 8800, "", "concept merchandise, never made or sold; placeholder price"),
    ("G03", "Graphic tee (concept)", "merch", 3200, "", "concept merchandise, never made or sold; placeholder price"),
]
ITEM_IDS = [c[0] for c in CATALOG]
ITEM_CAT = np.array([c[2] for c in CATALOG])
ITEM_PRICE = np.array([c[3] for c in CATALOG], dtype=np.int64)
MERCH_IDX = np.where(ITEM_CAT == "merch")[0]
CORE_IDX = np.where(ITEM_CAT != "merch")[0]
# base popularity per item for a fast-casual site and a beer garden (row-normalised later)
POP_FAST = {"M01": 5, "M02": 4, "M03": 3, "M04": 3, "M05": 4, "B01": 1.5, "B02": 1.2, "B03": 1.2, "B04": 1.5, "N01": 3, "N02": 2.5}
POP_GARDEN = {"M01": 3, "M02": 2, "M03": 2, "M04": 3, "M05": 2, "B01": 5, "B02": 4, "B03": 4, "B04": 4, "N01": 1.5, "N02": 1.2}
HOUR_FAST = np.array([4, 7, 6, 3, 2, 3, 5, 8, 8, 6, 3, 1], dtype=float)            # hours 11..22
HOUR_GARDEN = np.array([1, 2, 2, 3, 4, 5, 7, 9, 10, 9, 6, 3], dtype=float)
ROLES = [("cook", .30), ("server", .27), ("bartender", .13), ("cashier", .13), ("shift lead", .08), ("manager", .05), ("brewer", .04)]
SUPPLIERS = [(f"S{i:02d}", f"Synthetic Supplier {i:02d}", cat) for i, cat in enumerate(
    ["poultry", "goat and lamb", "produce", "dairy", "dry goods and malt", "hops and yeast", "packaging", "beverage syrups"], 1)]
PROMOS = [  # promo_id, name, start_offset_days, length_days, discount fraction (loyalty orders only)
    ("P01", "Synthetic launch week reward", 0, 14, .10), ("P02", "Synthetic happy-hour bonus", 90, 30, .08),
    ("P03", "Synthetic summer double points", 150, 45, .12), ("P04", "Synthetic anniversary offer", 365, 21, .10),
    ("P05", "Synthetic winter appetizer promo", 400, 30, .06), ("P06", "Synthetic app reorder nudge", 540, 60, .08),
]
INGREDIENT_UNIT = generator.INGREDIENT_UNIT


def _rng(seed, *tags):
    h = hashlib.sha256(("|".join(map(str, (seed, SIM_VERSION) + tags))).encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(h[:8], "big")))


def _writer(path):
    """gzip CSV writer with a fixed mtime so identical content gives identical bytes."""
    raw = open(path, "wb")
    gz = gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, compresslevel=6)
    return raw, io.TextIOWrapper(gz, encoding="utf-8", newline="")


class _Table:
    def __init__(self, out, name):
        self.name, self.path, self.rows, self.first = name, Path(out) / f"{name}.csv.gz", 0, True
        self.raw, self.txt = _writer(self.path)

    def write(self, df):
        df.to_csv(self.txt, index=False, header=self.first, lineterminator="\n")
        self.first = False
        self.rows += len(df)

    def close(self):
        self.txt.close()
        self.raw.close()
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.bytes = self.path.stat().st_size


def _month_starts(cfg):
    s = dt.date.fromisoformat(cfg.start)
    return [dt.date(s.year + (s.month - 1 + k) // 12, (s.month - 1 + k) % 12 + 1, 1) for k in range(cfg.months)]


def _locations(cfg, rng):
    locs = []
    n = cfg.fast_casual + cfg.beer_gardens
    kinds = ["beer garden"] * cfg.beer_gardens + ["fast casual"] * cfg.fast_casual
    open_at_start = min(cfg.open_at_start, n)
    days = (dt.date.fromisoformat(cfg.start).replace(year=dt.date.fromisoformat(cfg.start).year + cfg.months // 12))
    horizon = int(cfg.months * 30.4)
    late = sorted(int(x) for x in rng.integers(30, max(31, int(horizon * 0.75)), size=n - open_at_start)) if n > open_at_start else []
    for i, kind in enumerate(kinds):
        open_day = 0 if i < open_at_start else late[i - open_at_start]
        locs.append({"location_id": f"L{i + 1:02d}", "name": f"Scenario Site {i + 1:02d} (synthetic)", "format": kind,
                     "size_factor": round(float(rng.uniform(0.75, 1.3)), 3), "open_day": open_day,
                     "sells_merch": int(kind == "beer garden" or i % 5 == 0), "capacity_orders_per_hour": 70 if kind == "beer garden" else 55})
    return locs


def _expected_daily(cfg, locs, n_days, start):
    """Expected orders per (day, location) before scaling; weekday, season, growth, new-site ramp."""
    d = np.arange(n_days)
    dow = np.array([(start + dt.timedelta(days=int(k))).weekday() for k in d])
    month = np.array([(start + dt.timedelta(days=int(k))).month for k in d])
    dow_f = np.array([.82, .85, .9, 1.0, 1.25, 1.4, 1.1])[dow]
    season = 1 + .12 * np.sin((month - 3) / 12 * 2 * np.pi)
    growth = 1 + .35 * d / max(1, n_days)
    E = np.zeros((n_days, len(locs)))
    for j, L in enumerate(locs):
        since = d - L["open_day"]
        ramp = np.where(since < 0, 0.0, np.minimum(1.0, 0.55 + 0.45 * since / 60))
        fmt = 1.15 if L["format"] == "beer garden" else 1.0
        E[:, j] = ramp * dow_f * season * growth * L["size_factor"] * fmt
    return E * (cfg.target_orders / E.sum())


def generate(cfg, out, progress=False):
    """Write the tables to `out`. Returns the manifest dict."""
    t0 = time.perf_counter()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    start = dt.date.fromisoformat(cfg.start)
    ms = _month_starts(cfg)
    end = (ms[-1].replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    n_days = (end - start).days
    base = _rng(cfg.seed, "world")
    locs = _locations(cfg, base)
    nl = len(locs)
    E = _expected_daily(cfg, locs, n_days, start)
    tables = {}

    def tbl(name):
        tables[name] = _Table(out, name)
        return tables[name]

    # -- dimensions
    t = tbl("locations"); t.write(pd.DataFrame(locs).assign(open_date=lambda d: [(start + dt.timedelta(days=int(x))).isoformat() for x in d.open_day]).drop(columns="open_day")); t.close()
    t = tbl("menu_items"); t.write(pd.DataFrame([{"item_id": c[0], "name": c[1], "category": c[2], "price_cents": c[3], "ingredients": c[4], "status": c[5]} for c in CATALOG])); t.close()
    t = tbl("suppliers"); t.write(pd.DataFrame(SUPPLIERS, columns=["supplier_id", "name", "category"])); t.close()
    t = tbl("promotions")
    t.write(pd.DataFrame([{"promo_id": p[0], "name": p[1], "start_date": (start + dt.timedelta(days=p[2])).isoformat(), "end_date": (start + dt.timedelta(days=p[2] + p[3] - 1)).isoformat(), "discount_fraction": p[4]} for p in PROMOS if p[2] < n_days]))
    t.close()
    # loyalty profiles: join dates follow a growth curve; fictional ids only
    r = _rng(cfg.seed, "loyalty")
    N = cfg.loyalty_profiles
    join_day = np.floor(n_days * (np.arange(N) / N) ** (1 / 0.8)).astype(int)
    home = r.integers(0, nl, size=N)
    ok = np.array([locs[h]["open_day"] for h in home]) <= join_day            # a member joins at a site that is open
    home = np.where(ok, home, 0)
    t = tbl("loyalty_profiles")
    t.write(pd.DataFrame({"member_id": [f"M{i + 1:06d}" for i in range(N)], "join_date": [(start + dt.timedelta(days=int(x))).isoformat() for x in join_day],
                          "home_location_id": [locs[h]["location_id"] for h in home], "signup_channel": r.choice(["in-store", "app", "event"], size=N, p=[.55, .35, .10])}))
    t.close()
    # employees: fictional ids, no personal data
    r = _rng(cfg.seed, "employees")
    w = np.array([max(1, 1.0 if L["format"] == "fast casual" else 1.7) * L["size_factor"] for L in locs])
    corporate = max(2, cfg.employees // 40)
    per_site = r.multinomial(cfg.employees - corporate, w / w.sum())
    rows, k = [], 0
    role_names, role_p = zip(*ROLES)
    for j, L in enumerate(locs):
        for _ in range(per_site[j]):
            k += 1
            role = r.choice(role_names, p=np.array(role_p) / sum(role_p))
            if role == "brewer" and L["format"] != "beer garden":
                role = "cook"
            hire = L["open_day"] - int(r.integers(7, 45)) if r.random() < .6 else L["open_day"] + int(r.integers(0, max(1, n_days - L["open_day"])))
            wage = {"cook": 1700, "server": 1100, "bartender": 1300, "cashier": 1500, "shift lead": 1900, "manager": 2600, "brewer": 2400}[role] + int(r.integers(-100, 150))
            rows.append({"employee_id": f"E{k:04d}", "location_id": L["location_id"], "role": role, "hire_date": (start + dt.timedelta(days=max(0, hire))).isoformat(), "hourly_rate_cents_placeholder": wage})
    for _ in range(corporate):
        k += 1
        rows.append({"employee_id": f"E{k:04d}", "location_id": "HQ", "role": "support", "hire_date": start.isoformat(), "hourly_rate_cents_placeholder": 3200})
    t = tbl("employees"); t.write(pd.DataFrame(rows)); t.close()

    # -- facts, one month at a time (bounded memory)
    to, tl, tr, tb, tw, tq, ts, tin = (tbl(n) for n in ("orders", "order_lines", "returns", "brew_batches", "waste_events", "quality_events", "shifts", "inventory_counts"))
    pop = {"fast casual": np.array([POP_FAST.get(i, 0.0) for i in ITEM_IDS]), "beer garden": np.array([POP_GARDEN.get(i, 0.0) for i in ITEM_IDS])}
    hours = {"fast casual": HOUR_FAST / HOUR_FAST.sum(), "beer garden": HOUR_GARDEN / HOUR_GARDEN.sum()}
    step_day = (dt.date.fromisoformat(cfg.price_step_date) - start).days
    order_no = 0
    n_join_by_day = np.searchsorted(join_day, np.arange(n_days), side="right")
    promo_by_day = {}
    for p in PROMOS:
        for dd in range(p[2], min(n_days, p[2] + p[3])):
            promo_by_day[dd] = (p[0], p[4])
    totals = {"revenue_cents": 0, "discount_cents": 0, "orders_over_capacity": 0}
    for mi, m0 in enumerate(ms):
        d0 = (m0 - start).days
        d1 = (ms[mi + 1] - start).days if mi + 1 < len(ms) else n_days
        r = _rng(cfg.seed, "orders", mi)
        counts = r.poisson(E[d0:d1])                                          # (days, locations)
        dayi, loci = np.nonzero(counts)
        reps = counts[dayi, loci]
        day = np.repeat(dayi, reps) + d0
        loc = np.repeat(loci, reps)
        n = len(day)
        if n == 0:
            continue
        fmt_garden = np.array([L["format"] == "beer garden" for L in locs])[loc]
        hr = np.where(fmt_garden, r.choice(12, size=n, p=hours["beer garden"]), r.choice(12, size=n, p=hours["fast casual"])) + 11
        # site capacity (orders per hour): orders above it queue into the next hour, up to three passes; what still exceeds capacity is counted
        cap = np.array([L["capacity_orders_per_hour"] for L in locs])[loc]
        for _ in range(3):
            key = day.astype(np.int64) * 10_000 + loc * 100 + hr
            o_idx = np.argsort(key, kind="stable")
            sk = key[o_idx]
            first = np.r_[True, sk[1:] != sk[:-1]]
            start_pos = np.maximum.accumulate(np.where(first, np.arange(n), 0))
            ordinal = np.empty(n, dtype=np.int64)
            ordinal[o_idx] = np.arange(n) - start_pos
            over = (ordinal >= cap) & (hr < 22)
            if not over.any():
                break
            hr = np.where(over, hr + 1, hr)
        key = day.astype(np.int64) * 10_000 + loc * 100 + hr
        _, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        totals["orders_over_capacity"] += int((cnt[inv] > cap).sum())
        sec = hr.astype(np.int64) * 3600 + r.integers(0, 3600, size=n)
        order = np.lexsort((sec, day))
        day, loc, hr, sec, fmt_garden = day[order], loc[order], hr[order], sec[order], fmt_garden[order]
        ts_ = (np.datetime64(start, "s") + day.astype("timedelta64[D]") + sec.astype("timedelta64[s]")).astype(str)
        oid = np.array([f"O{x:08d}" for x in range(order_no + 1, order_no + n + 1)])
        order_no += n
        channel = np.where(fmt_garden, r.choice(["dine-in", "bar", "takeout"], size=n, p=[.55, .35, .10]), r.choice(["dine-in", "takeout", "app", "bar"], size=n, p=[.4, .3, .25, .05]))
        # loyalty member (older members are more active)
        is_loyal = r.random(n) < cfg.loyalty_order_share
        joined = np.maximum(1, n_join_by_day[day])
        member = np.floor(joined * r.random(n) ** 1.6).astype(int)
        member_id = np.where(is_loyal, np.array([f"M{x + 1:06d}" for x in member]), "")
        # lines: Gumbel top-k picks distinct items per order
        site_merch = np.array([L["sells_merch"] for L in locs])[loc].astype(bool)
        buys_merch = site_merch & (r.random(n) < cfg.merch_order_share * 12)    # merch-only baskets are rare; scaled so ~1.2% of all orders at merch sites carry merch
        buys_merch &= r.random(n) < 1 / 12
        p_mat = np.where(fmt_garden[:, None], pop["beer garden"][None, :], pop["fast casual"][None, :])
        keys = np.log(np.maximum(p_mat, 1e-9)) + r.gumbel(size=p_mat.shape).astype(np.float32)
        keys[:, MERCH_IDX] = -np.inf
        rank = np.argsort(-keys, axis=1)
        k_lines = np.minimum(1 + r.poisson(1.3, size=n), 6)
        sel = np.arange(rank.shape[1])[None, :] < k_lines[:, None]
        oi, ci = np.nonzero(sel)
        item = rank[oi, ci]
        qty = 1 + r.choice(3, size=len(oi), p=[.7, .22, .08]) * (r.random(len(oi)) < .5)
        qty = np.maximum(1, qty)
        # merch baskets: one extra merch line
        mo = np.nonzero(buys_merch)[0]
        if len(mo):
            oi = np.concatenate([oi, mo]); item = np.concatenate([item, r.choice(MERCH_IDX, size=len(mo), p=[.35, .35, .30])]); qty = np.concatenate([qty, np.ones(len(mo), dtype=int)])
        o2 = np.argsort(oi, kind="stable")
        oi, item, qty = oi[o2], item[o2], qty[o2]
        line_no = np.arange(len(oi)) - np.searchsorted(oi, oi) + 1
        price = ITEM_PRICE[item] * np.where(day[oi] >= step_day, cfg.price_step, 1.0)
        happy = (hr[oi] >= 15) & (hr[oi] < 17) & (ITEM_CAT[item] == "beer")
        price = np.rint(np.where(happy, price * 0.9, price)).astype(np.int64)
        line_total = qty * price
        subtotal = np.bincount(oi, weights=line_total, minlength=n).astype(np.int64)
        promo_id = np.full(n, "", dtype=object)
        disc = np.zeros(n, dtype=np.int64)
        for dd, (pid, frac) in promo_by_day.items():
            if d0 <= dd < d1:
                sel_o = np.nonzero((day == dd) & is_loyal & (r.random(n) < 0.3))[0]
                promo_id[sel_o] = pid
                disc[sel_o] = np.rint(subtotal[sel_o] * frac).astype(np.int64)
        total = subtotal - disc
        totals["revenue_cents"] += int(total.sum()); totals["discount_cents"] += int(disc.sum())
        to.write(pd.DataFrame({"order_id": oid, "location_id": [locs[x]["location_id"] for x in loc], "ts": ts_, "channel": channel, "member_id": member_id,
                               "promo_id": promo_id, "subtotal_cents": subtotal, "discount_cents": disc, "total_cents": total}))
        tl.write(pd.DataFrame({"order_id": oid[oi], "line_no": line_no, "item_id": np.array(ITEM_IDS)[item], "qty": qty, "unit_price_cents": price}))
        # merch returns (~8% of merch lines)
        mr = np.nonzero((ITEM_CAT[item] == "merch") & (r.random(len(oi)) < 0.08))[0]
        if len(mr):
            tr.write(pd.DataFrame({"order_id": oid[oi[mr]], "line_no": line_no[mr], "return_reason": r.choice(["size", "fit", "changed mind", "defect (synthetic)"], size=len(mr), p=[.45, .25, .2, .1]),
                                   "refund_cents": (qty[mr] * price[mr])}))
        # daily operational facts for this month
        dd = np.arange(d0, d1)
        sc = counts
        for j, L in enumerate(locs):
            vol = sc[:, j].astype(float)
            opened = np.arange(d0, d1) >= L["open_day"]
            if not opened.any():
                continue
            hrs = np.where(opened, np.rint(vol * 0.07 + (14 * 8 if L["format"] == "fast casual" else 14 * 10) * opened), 0)
            ts.write(pd.DataFrame({"date": [(start + dt.timedelta(days=int(x))).isoformat() for x in dd[opened]], "location_id": L["location_id"],
                                   "scheduled_labor_hours": hrs[opened].astype(int), "actual_labor_hours": np.rint(hrs[opened] * r.normal(1.02, 0.05, size=opened.sum())).astype(int)}))
            wmask = opened & (r.random(len(dd)) < .45)
            if wmask.any():
                wi = r.choice(len(INGREDIENT_UNIT), size=wmask.sum())
                ings = list(INGREDIENT_UNIT)
                tw.write(pd.DataFrame({"date": [(start + dt.timedelta(days=int(x))).isoformat() for x in dd[wmask]], "location_id": L["location_id"],
                                       "ingredient": [ings[i] for i in wi], "qty_kg": np.round(r.gamma(2.0, 0.6, size=wmask.sum()) * (1 + vol[wmask] / 250), 2),
                                       "reason": r.choice(["spoilage", "prep loss", "overproduction", "dropped"], size=wmask.sum(), p=[.4, .3, .2, .1])}))
            qmask = opened & (r.random(len(dd)) < 0.012)
            if qmask.any():
                tq.write(pd.DataFrame({"date": [(start + dt.timedelta(days=int(x))).isoformat() for x in dd[qmask]], "location_id": L["location_id"],
                                       "event_type": r.choice(["temperature log gap", "late delivery", "customer complaint (synthetic)", "equipment fault", "cleaning checklist miss"], size=qmask.sum()),
                                       "severity": r.choice(["low", "medium", "high"], size=qmask.sum(), p=[.6, .3, .1])}))
            if L["format"] == "beer garden":
                for x in dd[opened]:
                    if (start + dt.timedelta(days=int(x))).weekday() in (0, 3):
                        beer = r.choice(["B01", "B02", "B03", "B04", "B05"])
                        plan = float(r.choice([800, 1200, 1600]))
                        tb.write(pd.DataFrame([{"batch_id": f"BB{L['location_id']}-{int(x):04d}", "location_id": L["location_id"], "brew_date": (start + dt.timedelta(days=int(x))).isoformat(), "beer_id": beer,
                                                "planned_liters": plan, "yield_liters": round(plan * float(r.normal(.94, .03)), 1), "status": "simulated batch (never brewed)"}]))
    # weekly inventory counts per location x ingredient, correlated with that site's volume
    r = _rng(cfg.seed, "inventory")
    weekly = np.add.reduceat(E, np.arange(0, n_days, 7), axis=0)
    rows = []
    for wk in range(weekly.shape[0]):
        for j, L in enumerate(locs):
            if wk * 7 < L["open_day"]:
                continue
            for ing, unit in INGREDIENT_UNIT.items():
                rows.append({"location_id": L["location_id"], "count_date": (start + dt.timedelta(days=wk * 7)).isoformat(), "ingredient": ing,
                             "qty": round(float(r.uniform(0.5, 1.5)) * weekly[wk, j] * 0.09, 1), "unit": unit})
    tin.write(pd.DataFrame(rows))
    for t in tables.values():
        if t.txt.closed is False:
            t.close()
    secs = time.perf_counter() - t0
    manifest = {
        "synthetic": True, "disclaimer": "SYNTHETIC DATA / SIMULATED OPERATION. No real business, customer, employee, sale or product exists. Prices and wages are placeholders; volumes are UNCALIBRATED.",
        "sim_version": SIM_VERSION, "config": asdict(cfg), "scenario_start": cfg.start, "scenario_days": n_days, "locations": nl,
        "tables": {n: {"rows": t.rows, "bytes": t.bytes, "sha256": t.sha} for n, t in sorted(tables.items())},
        "summary": {"orders": tables["orders"].rows, "order_lines": tables["order_lines"].rows, "revenue_cents_placeholder": totals["revenue_cents"], "discount_cents": totals["discount_cents"],
                    "orders_still_above_site_hourly_capacity_after_queueing": totals["orders_over_capacity"]},
        "generation_seconds": round(secs, 1), "numpy": np.__version__, "pandas": pd.__version__,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    return manifest


def check(out):
    """Referential and arithmetic checks on a generated directory. Returns a list of problems (empty = clean)."""
    out = Path(out)
    rd = lambda n, **k: pd.read_csv(out / f"{n}.csv.gz", **k)
    problems = []
    orders, lines, menu, locs = rd("orders", keep_default_na=False), rd("order_lines"), rd("menu_items"), rd("locations")
    emp, loy = rd("employees"), rd("loyalty_profiles")
    if orders.order_id.duplicated().any():
        problems.append("duplicate order_id")
    if not lines.order_id.isin(orders.order_id).all():
        problems.append("order line without an order")
    if not orders.location_id.isin(locs.location_id).all():
        problems.append("order at an unknown location")
    if not lines.item_id.isin(menu.item_id).all():
        problems.append("order line with an unknown item")
    if (lines.qty <= 0).any() or (lines.unit_price_cents <= 0).any():
        problems.append("non-positive qty or price")
    st = (lines.qty * lines.unit_price_cents).groupby(lines.order_id).sum()
    o = orders.set_index("order_id")
    if not (o.subtotal_cents == st.reindex(o.index).fillna(0)).all():
        problems.append("subtotal differs from line sum")
    if not (o.total_cents == o.subtotal_cents - o.discount_cents).all():
        problems.append("total differs from subtotal minus discount")
    mem = orders.member_id[orders.member_id != ""]
    if not mem.isin(loy.member_id).all():
        problems.append("order by an unknown loyalty member")
    joined = loy.set_index("member_id").join_date
    chk = orders[orders.member_id != ""]
    if (chk.ts.str[:10].values < joined.reindex(chk.member_id).values).any():
        problems.append("order placed before the member joined")
    if not emp.location_id.isin(set(locs.location_id) | {"HQ"}).all():
        problems.append("employee at an unknown location")
    for col in ("ingredients",):
        if menu[col].fillna("").str.lower().str.contains("|".join(FORBIDDEN_TERMS)).any():
            problems.append("forbidden protein in the catalog")
    opened = locs.set_index("location_id").open_date
    if (orders.ts.str[:10].values < opened.reindex(orders.location_id).values).any():
        problems.append("order before the site opened")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=sorted(PROFILES), default="dev")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cfg = PROFILES[a.profile]
    if a.seed is not None:
        cfg = SimConfig(**{**asdict(cfg), "seed": a.seed})
    m = generate(cfg, a.out)
    probs = check(a.out)
    print(json.dumps({"profile": a.profile, "seconds": m["generation_seconds"], "summary": m["summary"], "problems": probs}, indent=1))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
