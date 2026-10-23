"""Independent evaluation of supplier intelligence: labelled cases written BEFORE the rules were run against them (labels are human judgements about the names and categories below, not outputs of the code), the
metrics computed from them, and MUTANTS: copies of the rules with exactly one control removed, each of which must be caught by at least one probe. Pure; shared by the tests and the evidence exporter.
Limits: the sets are small and written by the author; they measure whether the stated rules do what they say on representative cases, not accuracy on the real supplier market."""
import contextlib
from datetime import date

from . import supplier_intel as SI

# (name a, website a, name b, website b, same business?)
DEDUPE = [
    ("Brothers Produce", None, "Brothers Produce Inc.", None, True), ("Green Grocer Foods", None, "Green Grocer", None, True), ("Sunrise Dairy Farms", None, "Sunrize Dairy Farms", None, True), ("Farm to Table LLC", None, "Farm To Table, L.L.C.", None, True), ("The Green Grocer Co.", None, "Green Grocer", None, True),
    ("Lone Star Meats & Provisions", None, "Lone Star Meats and Provisions LLC", None, True), ("Austin Fresh Produce", None, "Austin Fresh Produce Inc", None, True), ("Sunrise Dairy Farms", None, "Sunrise Dairy Farm", None, True),
    ("Hill Country Dairies", "https://www.hcd-example.test", "HCD Foods", "https://hcd-example.test/about", True), ("Delta Foods", "https://delta-foods.test", "Delta Foods", "https://deltafoods-other.test", True),
    ("Capital City Wholesale", "https://capcity.test/a", "Cap City Foods", "https://www.capcity.test", True),
    ("Synthetic Supplier 01", None, "Synthetic Supplier 02", None, False), ("Broadline Distributor A", None, "Broadline Distributor B", None, False), ("Hill Country Dairies", None, "Hill Country Feed and Supply", None, False),
    ("Austin Fresh Produce", None, "Austin Fresh Seafood", None, False), ("Brothers Produce", None, "Brothers Seafood", None, False), ("Farm to Table LLC", None, "Farm Table Linens", None, False),
    ("North Star Foods", "https://northstar-a.test", "South Star Foods", "https://southstar-b.test", False), ("Sunrise Dairy Farms", None, "Sunset Dairy Farms", None, False), ("Valley Produce Co", None, "Valley Packaging Co", None, False),
    ("Rio Grande Spices", "https://rgspices.test", "Rio Grande Linen Service", "https://rglinen.test", False), ("Metro Wholesale Foods", None, "Metro Wholesale Produce", None, False)]

# (category, name, products, classes that must be among the matches, expected primary or None when the record legitimately spans classes)
CLASSIFY = [
    ("Produce distribution", "Brothers Produce", [], ["produce"], "produce"), ("Dairy distribution", "Hill Country Dairies", [], ["dairy"], "dairy"), ("Produce, eggs and dairy wholesale", "Farm to Table LLC", [], ["produce", "dairy"], None),
    ("Fitness equipment", "Studio Equipment Supplier", ["Spin bike"], ["fitness_equipment"], "fitness_equipment"), ("Laundry service", "Linen and Towel Service", [], ["laundry_and_linen"], "laundry_and_linen"),
    ("Specialty meats", "Prime Cuts", [], ["meat_and_seafood"], "meat_and_seafood"), ("Poultry", "Supplier 01", ["Chicken thigh"], ["meat_and_seafood"], "meat_and_seafood"),
    ("Dry goods", "Pantry Supply", ["Masa harina", "Rice"], ["dry_goods_and_grocery"], "dry_goods_and_grocery"), ("Packaging", "Box Co", ["Takeout container"], ["packaging_and_disposables"], "packaging_and_disposables"),
    ("Brewing ingredients", "Malt House", ["Malt", "Hops"], ["beverage_ingredients"], None), ("Wholesale cheese importer", "Fromage Imports", [], ["dairy"], "dairy"), ("Seafood", "Gulf Catch", ["Shrimp"], ["meat_and_seafood"], "meat_and_seafood"),
    ("Catering consulting", "Advisory Partners", [], [], "unclassified"), ("Cleaning service", "Shine Co", [], ["cleaning_and_facility_services"], "cleaning_and_facility_services"), ("Fresh vegetables", "Green Acres", [], ["produce"], "produce"),
    ("Grocery", "Corner Grocer", [], ["dry_goods_and_grocery"], "dry_goods_and_grocery")]

# (project location, stated service area, expected level)
AREA = [("Austin, TX", "Austin and surrounding areas (per the source)", "explicit"), ("Austin, TX", "Austin, TX (per the source)", "explicit"),
        ("Austin, TX", "Greater Houston, Dallas/Fort Worth, Austin, San Antonio and other Texas metros (per the source)", "explicit"), ("Austin, TX", "Houston and the Gulf Coast", "none"),
        ("Austin, TX", "Statewide Texas delivery", "statewide"), ("Austin, TX", "Synthetic (no real service area)", "not_applicable"), ("Austin, TX", "North America", "unknown"), ("Austin, TX", "", "unknown"),
        ("Austin, TX", "Cedar Park and Round Rock", "explicit"), ("Cedar Park, TX", "Austin metro", "explicit"), ("Houston, TX", "Austin and surrounding areas", "none"), ("Dallas, TX", "Dallas/Fort Worth", "explicit"),
        ("San Antonio, TX", "Houston, Austin", "none"), ("Austin, TX", "Travis County", "explicit")]


def _supplier(i, name, status="synthetic_fixture", prods=()):
    return dict(id=i, name=name, category="Produce", service_area="Austin", website_url=None, verification_status=status, verified_on=None, source_kind="synthetic_fixture", source_url=None, notes=None, freshness="x", shortlist_status=None, products=list(prods), sources=[])


def _prod(price, cls="SYNTHETIC_QUOTE", valid_to=date(2027, 1, 1), ref="ING1", lead=2):
    return dict(name="Item", ingredient_ref=ref, unit="kg", unit_price_cents=price, pack_qty=1, lead_days=lead, min_order_cents=0, price_class=cls, valid_from=date(2026, 1, 1), valid_to=valid_to, source_url=None, limitation="x")


def quote_cases(as_of=date(2026, 10, 23)):
    """Constructed directories with a known answer about category separation. Each returns True when the behaviour is right."""
    d = [_supplier("s1", "A", "synthetic_fixture", [_prod(300)]), _supplier("s2", "B", "lead_unverified", [_prod(250, "SUPPLIER_QUOTE")]), _supplier("s3", "C", "synthetic_fixture", [_prod(100, "SYNTHETIC_QUOTE", valid_to=date(2026, 1, 2))]),
         _supplier("s4", "D", "lead_unverified", [_prod(None, "NONE_PUBLISHED")]), _supplier("s5", "E", "synthetic_fixture", [_prod(200)])]
    row = SI.quote_matrix(d, as_of)["rows"][0]
    cats = row["categories"]
    return {
        "categories are kept apart": set(cats) == {"synthetic_quotation", "supplier_quote"},
        "cheapest is chosen inside the category only": cats["synthetic_quotation"][0]["supplier"] == "E" and cats["synthetic_quotation"][0].get("cheapest_in_category") and not cats["synthetic_quotation"][1].get("cheapest_in_category"),
        "no cross-category ranking is produced": row["cross_category_ranking"] is None and row["mixed_categories"] is True,
        "an expired quote is listed as expired and not compared": [e["supplier"] for e in row["expired"]] == ["C"] and all(e["supplier"] != "C" for es in cats.values() for e in es),
        "a supplier with no published price is listed as unpriced and never ranked": [e["supplier"] for e in row["unpriced"]] == ["D"] and all(e["supplier"] != "D" for es in cats.values() for e in es)}


def run_eval():
    dd = [(SI.duplicate_score(dict(name=a, website_url=u), dict(name=b, website_url=v))[0] >= SI.DUPLICATE_THRESHOLD, exp) for a, u, b, v, exp in DEDUPE]
    tp = sum(1 for p, e in dd if p and e); fp = sum(1 for p, e in dd if p and not e); fn = sum(1 for p, e in dd if not p and e)
    cl_ok = []
    for cat, name, prods, includes, primary in CLASSIFY:
        r = SI.classify(cat, name, prods)
        cl_ok.append(set(includes) <= {m["cls"] for m in r["matches"]} and (primary is None or r["primary"] == primary) and (bool(includes) or r["primary"] == "unclassified"))
    ar_ok = [SI.area_match(loc, sa)["level"] == exp for loc, sa, exp in AREA]
    qc = quote_cases()
    return dict(dedupe=dict(cases=len(dd), true_positive=tp, false_positive=fp, false_negative=fn, precision=tp / (tp + fp) if tp + fp else 1.0, recall=tp / (tp + fn) if tp + fn else 1.0),
                classification=dict(cases=len(cl_ok), correct=sum(cl_ok), accuracy=sum(cl_ok) / len(cl_ok)), service_area=dict(cases=len(ar_ok), correct=sum(ar_ok), accuracy=sum(ar_ok) / len(ar_ok)),
                quote_provenance=dict(checks=len(qc), passed=sum(qc.values()), failed=[k for k, v in qc.items() if not v]))


# ---------------------------------------------------------------------------------------------- mutants
@contextlib.contextmanager
def _patched(**kv):
    old = {k: getattr(SI, k) for k in kv}
    try:
        for k, v in kv.items():
            setattr(SI, k, v)
        yield
    finally:
        for k, v in old.items():
            setattr(SI, k, v)


def _score_without(rule):
    real = SI.duplicate_score
    return lambda a, b, rules=None: real(a, b, SI.DUP_RULES - {rule})


def _quote_without(rule):
    real = SI.quote_matrix
    def f(directory, as_of=None, baseline=None):
        as_of = as_of or date.today()
        if rule == "category_separation":          # rank every priced quote together, whatever its category
            out = real(directory, as_of, baseline)
            for r in out["rows"]:
                allq = sorted((e for es in r["categories"].values() for e in es), key=lambda e: e["unit_price_cents"])
                r["categories"] = {"synthetic_quotation": allq} if allq else {}
                r["mixed_categories"] = False
                r["cross_category_ranking"] = [e["supplier"] for e in allq]
                for e in allq:
                    e.pop("cheapest_in_category", None)
                if allq:
                    allq[0]["cheapest_in_category"] = True
            return out
        if rule == "expiry":                       # ignore validity windows
            d2 = [dict(s, products=[dict(p, valid_to=None) for p in s["products"]]) for s in directory]
            return real(d2, as_of, baseline)
        return real(directory, as_of, baseline)
    return f


MUTANTS = {
    "no_domain_match": dict(removes="same official domain is treated as the same business", patch=lambda: _patched(duplicate_score=_score_without("domain")), kills="dedupe"),
    "no_plural_and_typo_handling": dict(removes="'Farm' / 'Farms' and 'Sunrise' / 'Sunrize' are the same word (plural handling and typo tolerance overlap, so they are removed together; either alone is covered by the other)",
                                        patch=lambda: _patched(duplicate_score=lambda a, b, rules=None, _r=SI.duplicate_score: _r(a, b, SI.DUP_RULES - {"plural", "typo"})), kills="dedupe"),
    "no_typo_tolerance": dict(removes="near-identical words (typos) still match", patch=lambda: _patched(duplicate_score=_score_without("typo")), kills="dedupe"),
    "no_generic_word_guard": dict(removes="sharing only generic words is not evidence of identity", patch=lambda: _patched(duplicate_score=_score_without("generic")), kills="dedupe"),
    "threshold_too_low": dict(removes="the duplicate threshold", patch=lambda: _patched(DUPLICATE_THRESHOLD=0.0), kills="dedupe"),
    "no_legal_suffix_removal": dict(removes="'LLC', 'Inc' and similar are ignored in names", patch=lambda: _patched(LEGAL_SUFFIXES=set()), kills="dedupe"),
    "classification_ignores_category": dict(removes="the stated category is the strongest classification signal", patch=lambda: _patched(classify=lambda category, name="", product_names=(), _r=SI.classify: _r("", name, product_names)), kills="classification"),
    "area_ignores_project_location": dict(removes="a service area must name the project's own metro", patch=lambda: _patched(area_match=lambda loc, sa, _r=SI.area_match: _r("Houston, TX", sa)), kills="service_area"),
    "synthetic_area_treated_as_real": dict(removes="synthetic fixtures have no real service area", patch=lambda: _patched(area_match=lambda loc, sa, _r=SI.area_match: _r(loc, sa.replace("Synthetic", "Austin"))), kills="service_area"),
    "quotes_ranked_across_categories": dict(removes="price categories are never ranked against each other", patch=lambda: _patched(quote_matrix=_quote_without("category_separation")), kills="quote_provenance"),
    "expired_quotes_compared": dict(removes="expired quotes are excluded from comparison", patch=lambda: _patched(quote_matrix=_quote_without("expiry")), kills="quote_provenance"),
}


def _probe_failures(r):
    return dict(dedupe=r["dedupe"]["false_positive"] + r["dedupe"]["false_negative"], classification=r["classification"]["cases"] - r["classification"]["correct"],
                service_area=r["service_area"]["cases"] - r["service_area"]["correct"], quote_provenance=r["quote_provenance"]["checks"] - r["quote_provenance"]["passed"])


def run_mutants():
    base = _probe_failures(run_eval())
    out = []
    for name, m in MUTANTS.items():
        with m["patch"]():
            f = _probe_failures(run_eval())
        out.append(dict(name=name, removes=m["removes"], targeted_probe=m["kills"], failures_on_mutant=f[m["kills"]], killed=f[m["kills"]] > base[m["kills"]]))
    return dict(baseline_failures=base, mutants=out)
