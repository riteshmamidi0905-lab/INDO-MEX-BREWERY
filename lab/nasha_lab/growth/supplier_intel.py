"""Supplier intelligence: pure, deterministic functions over STORED supplier records. No network access, no scraping, no contact with any supplier, no model. Every output says which rule produced it.

What this module does and does not claim:
  * `information_category` says how much a supplier RECORD can be trusted (verified public information, unverified public-search lead, synthetic fixture, stale). It is derived from the stored verification
    status; nothing here upgrades a status.
  * `price_category` says what a PRICE is (published price, supplier quote, synthetic quotation, none). Prices of different categories are never ranked against each other.
  * duplicate detection, category classification and service-area matching are RULE-BASED heuristics with stated rules and thresholds; they suggest, a person decides.
Founder assumptions are not supplier data: they live in project assumptions and are shown beside, never mixed into, supplier comparisons."""
import re
from datetime import date
from difflib import SequenceMatcher

INFO_CATEGORY = {"verified_public": "verified_supplier_information", "lead_unverified": "unverified_public_lead", "synthetic_fixture": "synthetic_fixture", "stale": "stale_information"}
INFO_LABEL = {"verified_supplier_information": "Verified from public sources", "unverified_public_lead": "Unverified public-search lead", "synthetic_fixture": "Synthetic fixture", "stale_information": "Stale: re-verify before use"}
PRICE_CATEGORY = {"PUBLIC_REFERENCE": "published_price", "SUPPLIER_QUOTE": "supplier_quote", "SYNTHETIC_QUOTE": "synthetic_quotation", "NONE_PUBLISHED": "none_published"}
PRICE_LABEL = {"published_price": "Published price", "supplier_quote": "Supplier quote", "synthetic_quotation": "Synthetic quotation", "none_published": "No published price"}
RANKABLE = ("published_price", "supplier_quote", "synthetic_quotation")        # categories that carry a price at all

GENERIC_WORDS = {"supplier", "suppliers", "supply", "foods", "food", "distribution", "distributors", "distributor", "wholesale", "services", "service", "group", "products", "market", "fresh", "synthetic", "and"}
LEGAL_SUFFIXES = {"llc", "inc", "incorporated", "co", "corp", "corporation", "company", "ltd", "limited", "lp", "llp", "the"}
DUPLICATE_THRESHOLD = 0.82


# ------------------------------------------------------------------ names and domains
def normalize_name(name):
    s = re.sub(r"\(.*?\)", " ", (name or "").lower()).replace("&", " and ").replace(".", "")
    toks = [t for t in re.findall(r"[a-z0-9]+", s) if t not in LEGAL_SUFFIXES]
    return " ".join(toks)


def domain(url):
    if not url:
        return None
    m = re.match(r"^https?://([^/:?#]+)", url.strip().lower())
    return re.sub(r"^www\.", "", m.group(1)) if m else None


DUP_RULES = frozenset({"domain", "plural", "generic", "typo"})


def _tokens(name, rules):
    toks = normalize_name(name).split()
    if "plural" in rules:
        toks = [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in toks]
    return toks


def duplicate_score(a, b, rules=None):
    """(score 0..1, reasons). Certain: same official domain, or the same distinctive words (so 'Supplier 01' and 'Supplier 02', 'Distributor A' and 'B', are different suppliers). Otherwise the names must differ only by near-identical words (typos): a differing word with no close counterpart
    (Produce / Seafood, Sunrise / Sunset) means a different business. `rules` lets the evaluation switch a single rule off; production uses all of them."""
    rules = DUP_RULES if rules is None else rules
    da, db = domain(a.get("website_url")), domain(b.get("website_url"))
    if "domain" in rules and da and db and da == db:
        return 1.0, [f"same official website domain ({da})"]
    ta, tb = _tokens(a["name"], rules), _tokens(b["name"], rules)
    drop = GENERIC_WORDS if "generic" in rules else set()
    sa, sb = {t for t in ta if t not in drop}, {t for t in tb if t not in drop}
    if not sa or not sb:
        return 0.0, []                                                       # nothing distinctive to compare
    if sa == sb:
        return 1.0, [f"same distinctive words ({' '.join(sorted(sa))}) once legal suffixes, plurals and generic words are ignored"]
    if "typo" not in rules:
        return 0.0, []
    only_a, only_b = sa - sb, sb - sa
    close = lambda x, ys: any(SequenceMatcher(None, x, y).ratio() >= 0.85 for y in ys)
    if all(close(x, only_b) for x in only_a) and all(close(y, only_a) for y in only_b) and (sa & sb):
        sim = round(SequenceMatcher(None, " ".join(sorted(sa)), " ".join(sorted(sb))).ratio(), 4)
        return sim, [f"names differ only by near-identical words ({', '.join(sorted(only_a))} / {', '.join(sorted(only_b))})"]
    return 0.0, []


def find_duplicates(directory, threshold=DUPLICATE_THRESHOLD):
    """Candidate duplicate pairs, strongest first. Suggestions only: a person confirms or marks them distinct."""
    out = []
    for i, a in enumerate(directory):
        for b in directory[i + 1:]:
            score, why = duplicate_score(a, b)
            if score >= threshold:
                out.append(dict(a=a["id"], a_name=a["name"], b=b["id"], b_name=b["name"], score=score, reasons=why))
    return sorted(out, key=lambda d: (-d["score"], d["a"], d["b"]))


# ------------------------------------------------------------------ category classification
CLASSES = [("produce", ("produce", "vegetable", "fruit", "greens", "herb", "farm")), ("dairy", ("dairy", "milk", "butter", "cream", "cheese", "paneer", "yogurt", "egg")),
           ("meat_and_seafood", ("meat", "lamb", "goat", "chicken", "poultry", "turkey", "sausage", "beef", "pork", "seafood", "fish", "butcher")), ("dry_goods_and_grocery", ("grocery", "dry goods", "flour", "masa", "rice", "spice", "pantry", "grain", "dry")),
           ("beverage_ingredients", ("hops", "malt", "grain", "yeast", "beverage", "brewing")), ("packaging_and_disposables", ("packaging", "disposable", "container", "bag", "box")),
           ("fitness_equipment", ("fitness", "treadmill", "rower", "dumbbell", "kettlebell", "barbell", "squat", "weights", "bike", "bikes", "spin", "reformer")), ("flooring_and_fitout", ("flooring", "floor", "rubber", "mirror", "mirrors", "fit-out", "fitout", "construction", "acoustic")),
           ("equipment", ("equipment", "machine", "furniture", "locker", "lockers")), ("software_and_systems", ("software", "booking", "access", "sound", "audio", "pos", "system", "systems")),
           ("laundry_and_linen", ("laundry", "linen", "towel", "towels")), ("cleaning_and_facility_services", ("cleaning", "janitorial", "sanitation", "pest", "maintenance")), ("broadline_distribution", ("broadline", "cash and carry", "cash-and-carry", "foodservice distribution", "wholesale club")), ("services", ("service", "services"))]


def classify(category, name="", product_names=()):
    """Rule-based: count keyword hits per class in the stated category (weight 3), the name (2) and product names (1). Returns primary class, all matches and the rule used; 'unclassified' if nothing matches."""
    text = [(re.sub(r"[^a-z0-9 ]", " ", (category or "").lower()), 3), (re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()), 2)] + [(re.sub(r"[^a-z0-9 ]", " ", p.lower()), 1) for p in product_names]
    scores = {}
    for cls, kws in CLASSES:
        s = sum(w for t, w in text for k in kws if re.search(rf"\b{re.escape(k)}\w*\b", t))
        if s:
            scores[cls] = s
    if not scores:
        return dict(primary="unclassified", matches=[], rule="no keyword matched the category, name or products", method="rule_based_keywords")
    order = {c: i for i, (c, _) in enumerate(CLASSES)}
    ranked = sorted(scores, key=lambda c: (-scores[c], order[c]))               # ties go to the class listed first (the more specific one)
    return dict(primary=ranked[0], matches=[dict(cls=c, score=scores[c]) for c in ranked], rule="keyword hits weighted category x3, name x2, product x1", method="rule_based_keywords")


# ------------------------------------------------------------------ service-area matching
METROS = {"austin": ("austin", "round rock", "cedar park", "pflugerville", "georgetown", "travis county"), "houston": ("houston", "harris county"), "dallas_fort_worth": ("dallas", "fort worth", "dfw", "dallas/fort worth"),
          "san_antonio": ("san antonio", "bexar"), "corpus_christi": ("corpus christi",), "mcallen": ("mcallen", "rio grande valley")}


def _metro_of(text):
    t = (text or "").lower()
    return sorted(m for m, aliases in METROS.items() if any(re.search(rf"\b{re.escape(a)}\b", t) for a in aliases))


def area_match(project_location, service_area):
    """How well a stated service area covers a project location. Levels: explicit (the project's metro is named), statewide (the area says Texas/statewide without naming metros), none (other metros named),
    unknown (nothing parseable), not_applicable (synthetic fixture). The text is the supplier's own description via its source, never verified coverage."""
    sa = (service_area or "").lower()
    if sa.startswith("synthetic"):
        return dict(level="not_applicable", reason="synthetic fixture has no real service area")
    want = _metro_of(project_location)
    named = _metro_of(service_area)
    if want and set(want) & set(named):
        return dict(level="explicit", reason=f"service area names {', '.join(sorted(set(want) & set(named)))}", metros=named)
    if re.search(r"\b(statewide|all of texas|texas-wide)\b", sa):
        return dict(level="statewide", reason="area says statewide", metros=named)
    if named:
        return dict(level="none", reason=f"service area names {', '.join(named)} but not the project's metro", metros=named)
    return dict(level="unknown", reason="no metro could be parsed from the service area text", metros=[])


# ------------------------------------------------------------------ freshness and the per-supplier card
TIER_LABEL = {"primary_page_read": "Official page read", "official_domain_snippet": "Official-domain search snippet (page not opened)", "secondary_only": "Secondary sources only", "synthetic": "Synthetic fixture (no real source)", "none": "No source recorded"}


def evidence_tier(s):
    """How direct the evidence behind a supplier record is, from its recorded sources (never from a claim): an official page that was READ; a snippet of a page on the supplier's own domain; directory, press or reference
    sources only; or a synthetic fixture. Verified status additionally requires a read official page, a website, a source and a date (enforced by the database), so no tier below the first can verify a supplier."""
    if s["verification_status"] == "synthetic_fixture":
        return "synthetic"
    own = [x for x in s.get("sources", []) if x["kind"] in ("official_site", "contact_page")]
    if any(x["access"] == "page_read" for x in own):
        return "primary_page_read"
    if own:
        return "official_domain_snippet"
    return "secondary_only" if s.get("sources") else "none"


def supplier_card(s, project_location=None, as_of=None):
    """One supplier with its information category, derived classification, area match and counts by price category. Pure: nothing is stored."""
    info = INFO_CATEGORY.get(s["verification_status"], "unverified_public_lead")
    cats = {}
    for p in s["products"]:
        c = PRICE_CATEGORY[p["price_class"]]
        cats[c] = cats.get(c, 0) + 1
    tier = evidence_tier(s)
    return dict(id=s["id"], name=s["name"], evidence_tier=tier, evidence_tier_label=TIER_LABEL[tier], official_domain_seen=sorted({domain(x["url"]) for x in s.get("sources", []) if x["kind"] in ("official_site", "contact_page")}), information_category=info, information_label=INFO_LABEL[info], official_website=s.get("website_url"), official_website_verified=s["verification_status"] == "verified_public",
                verified_on=s.get("verified_on"), freshness=s.get("freshness"), classification=classify(s["category"], s["name"], [p["name"] for p in s["products"]]),
                area=area_match(project_location, s["service_area"]) if project_location else None, price_categories=cats, sources=s.get("sources", []), public_channels=[x for x in s.get("sources", []) if x["kind"] in ("official_site", "contact_page")])


# ------------------------------------------------------------------ quote comparison with explicit data categories
def _valid(p, as_of):
    return p["unit_price_cents"] is not None and p["price_class"] != "NONE_PUBLISHED" and (p["valid_from"] is None or p["valid_from"] <= as_of) and (p["valid_to"] is None or as_of <= p["valid_to"])


def quote_matrix(directory, as_of=None, baseline=None):
    """Per ingredient: every supplier's price, grouped by price CATEGORY. The cheapest is reported only WITHIN a category; categories are never ranked against each other, and a record whose quote has expired
    is listed as expired, not compared. `baseline` (optional {ingredient_ref: unit_price_cents}) is a planning assumption shown separately, never mixed in."""
    as_of = as_of or date.today()
    rows = {}
    for s in directory:
        info = INFO_CATEGORY.get(s["verification_status"], "unverified_public_lead")
        for p in s["products"]:
            ref = p["ingredient_ref"]
            if not ref:
                continue
            cat = PRICE_CATEGORY[p["price_class"]]
            r = rows.setdefault(ref, dict(ingredient_ref=ref, name=p["name"], unit=p["unit"], categories={}, expired=[], unpriced=[]))
            entry = dict(supplier_id=s["id"], supplier=s["name"], information_category=info, unit_price_cents=None if p["unit_price_cents"] is None else float(p["unit_price_cents"]), pack_qty=None if p["pack_qty"] is None else float(p["pack_qty"]),
                         lead_days=p["lead_days"], min_order_cents=p["min_order_cents"], valid_to=str(p["valid_to"]) if p["valid_to"] else None, source_url=p.get("source_url"))
            if cat == "none_published":
                r["unpriced"].append(dict(supplier=s["name"], supplier_id=s["id"])); continue
            if not _valid(p, as_of):
                r["expired"].append(dict(supplier=s["name"], supplier_id=s["id"], valid_to=entry["valid_to"])); continue
            r["categories"].setdefault(cat, []).append(entry)
    out = []
    for ref in sorted(rows):
        r = rows[ref]
        for cat, es in r["categories"].items():
            es.sort(key=lambda e: (e["unit_price_cents"], e["lead_days"] if e["lead_days"] is not None else 999, e["supplier"], e["supplier_id"]))      # name before id: ids are random per database
            es[0]["cheapest_in_category"] = True
        r["categories"] = {c: r["categories"][c] for c in sorted(r["categories"], key=RANKABLE.index)}
        r["cross_category_ranking"] = None
        r["mixed_categories"] = len(r["categories"]) > 1
        if baseline and ref in baseline:
            r["planning_assumption_unit_price_cents"] = baseline[ref]
        out.append(r)
    return dict(as_of=str(as_of), rows=out, rule="The cheapest is reported within one price category only; categories are never compared with each other")
