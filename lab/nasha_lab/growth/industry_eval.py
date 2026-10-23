"""Independent check of the industry generalisation in procurement planning: hand-worked needs and totals for requirement-driven projects, the rule that an industry without recipes never reads a recipe, and one mutant per rule.
Expected numbers were worked out by hand from the fixture below, not produced by the code. Pure; shared by the tests and the evidence exporter."""
import contextlib
from datetime import date

from . import procurement as PRC

AS_OF = date(2026, 10, 23)


def _p(ref, name, unit, cents, pack=1, lead=3, mn=0):
    return dict(name=name, ingredient_ref=ref, unit=unit, unit_price_cents=cents, pack_qty=pack, lead_days=lead, min_order_cents=mn, price_class="SYNTHETIC_QUOTE", valid_from=date(2026, 1, 1), valid_to=date(2027, 1, 1), source_url=None, limitation="x")


DIRECTORY = [dict(id="s1", name="Studio Supply One", verification_status="synthetic_fixture", priced_products=2, products=[_p("equip.bike", "Bike", "each", 98_000), _p("svc.towel", "Towel service", "pickup", 25_000)]),
             dict(id="s2", name="Studio Supply Two", verification_status="synthetic_fixture", priced_products=2, products=[_p("equip.bike", "Bike", "each", 94_500), _p("svc.towel", "Towel service", "pickup", 23_500)])]
REQ = [dict(ref="equip.bike", name="Bike", kind="equipment", qty=4, unit="each", recurrence="one_time"), dict(ref="svc.towel", name="Towel service", kind="service", qty=1, unit="pickup", recurrence="per_week")]
SCENARIO = dict(lines=[dict(name="Unmapped membership", units_per_month=100.0)])      # a product with no recipe


def _plan(weeks, req=REQ, scen=None, use_recipes=False):
    return PRC.plan(DIRECTORY, scen, weeks, AS_OF, req, use_recipes)


def cases():
    """name -> bool. Hand work: 2 weeks = 4 bikes once (4 x 94,500) + 2 towel pickups (2 x 23,500) = 425,000; 4 weeks = 378,000 + 4 x 23,500 = 472,000 (the one-time bikes do not grow with the period)."""
    p2, p4 = _plan(2), _plan(4)
    f = _plan(2, scen=SCENARIO, use_recipes=False)
    h = _plan(2, req=[], scen=SCENARIO, use_recipes=True)
    return {
        "two weeks of needs total 425,000 at the cheapest quotes": p2["total_cost_cents"] == 425_000,
        "four weeks total 472,000: recurring needs scale with the period": p4["total_cost_cents"] == 472_000,
        "one-time equipment is the same quantity in any period": [i["need_qty"] for i in p2["items"] if i["ingredient_ref"] == "equip.bike"] == [i["need_qty"] for i in p4["items"] if i["ingredient_ref"] == "equip.bike"] == [4.0],
        "recurring service need is weeks x quantity": [i["need_qty"] for i in p4["items"] if i["ingredient_ref"] == "svc.towel"] == [4.0],
        "the independent re-derivation agrees with the plan": PRC.check_plan(DIRECTORY, p2, AS_OF) == [] and PRC.check_plan(DIRECTORY, p4, AS_OF) == [],
        "only recurring needs get a reorder point": [r["ingredient"] for r in p2["replenishment"]] == ["Towel service"],
        "an industry without recipes never reads a recipe": f["needs_from"] == ["requirements"] and f["portions"] == {} and not [x for x in f["flags"] if x["kind"] == "unmapped_products"],
        "an industry with recipes still flags a product that has none": h["needs_from"] == ["recipes"] and any(x["kind"] == "unmapped_products" for x in h["flags"]),
        "a project with no needs plans nothing": _plan(2, req=[])["total_cost_cents"] == 0}


@contextlib.contextmanager
def _patched(**kv):
    old = {k: getattr(PRC, k) for k in kv}
    try:
        for k, v in kv.items():
            setattr(PRC, k, v)
        yield
    finally:
        for k, v in old.items():
            setattr(PRC, k, v)


def _needs(scale_recurring=True, scale_one_time=False, ignore=False):
    def f(requirements, period_weeks):
        out = {}
        for r in ([] if ignore else requirements or []):
            mult = (period_weeks if (r["recurrence"] == "per_week" and scale_recurring) or (r["recurrence"] == "one_time" and scale_one_time) else 1)
            out[r["ref"]] = dict(ingredient_ref=r["ref"], ingredient=r["name"], unit=r["unit"], qty=float(r["qty"]) * mult, recurrence=r["recurrence"], kind=r["kind"])
        return out
    return f


def _force_recipes():
    real = PRC.plan
    return lambda directory, scen, weeks, as_of, requirements=(), use_recipes=True: real(directory, scen, weeks, as_of, requirements, True)


def _all_recurring():
    real = PRC.replenishment
    def f(items, period_weeks, safety_pct=20.0):
        return real([dict(i, recurrence="per_week") for i in items], period_weeks, safety_pct)
    return f


MUTANTS = {
    "requirements_ignored": ("explicit requirements are part of what a project needs", lambda: _patched(needs_from_requirements=_needs(ignore=True))),
    "recurring_not_scaled_by_period": ("a recurring need is needed every week of the period", lambda: _patched(needs_from_requirements=_needs(scale_recurring=False))),
    "one_time_scaled_by_period": ("a one-time purchase is bought once however long the period", lambda: _patched(needs_from_requirements=_needs(scale_one_time=True))),
    "recipes_forced_for_every_industry": ("an industry without recipes never reads a recipe", lambda: _patched(plan=_force_recipes())),
    "equipment_given_a_reorder_point": ("only recurring needs get a reorder point", lambda: _patched(replenishment=_all_recurring()))}


def run_cases():
    return cases()


def run_mutants():
    base = sum(not v for v in cases().values())
    out = []
    for name, (removes, patch) in MUTANTS.items():
        with patch():
            bad = [k for k, v in cases().items() if not v]
        out.append(dict(name=name, removes=removes, failures_on_mutant=len(bad), killed=len(bad) > base, caught_by=bad[:3]))
    return dict(baseline_failures=base, mutants=out)
