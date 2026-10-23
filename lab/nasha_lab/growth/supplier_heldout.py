"""HELD-OUT cases for supplier intelligence. Written AFTER the supplier_intel rules were frozen (engineering commit 168fdb5) and run against them; the labels are human judgements about the names and categories, made
without running the code. The rules must NOT be tuned to these cases: if a rule changes after this file was first run, the cases are no longer held out and the result must say so. Misses are kept and reported. One service-area case that duplicated a development case was removed after the first run (13 -> 12 cases; all correct before and after), found by test_held_out_cases_are_disjoint_from_the_development_cases.
Limits: small, author-labelled, drawn from the supplier names and categories of this project; they say nothing about general accuracy on the supplier market."""
from . import supplier_intel as SI

FROZEN_AT = "168fdb5"
DEDUPE = [  # (name a, website a, name b, website b, same business?)
    ("Masienda", "https://masienda.com", "Masienda Inc.", None, True), ("Austin Homebrew Supply", None, "Austin Home Brew Supply", None, True), ("Ben E. Keith Foods", None, "Ben E Keith Foods LLC", None, True),
    ("Restaurant Depot", None, "Restaurant Depot Austin", None, True), ("WebstaurantStore", None, "Webstaurant Store", None, True), ("Yakima Chief Hops", "https://www.yakimachief.com", "YCH Hops", "https://yakimachief.com/about", True),
    ("Briess Malt and Ingredients", None, "Briess Malt & Ingredients Co.", None, True), ("The Mozzarella Company", None, "Mozzarella Co", None, True), ("Farm to Table LLC", None, "Farm-to-Table Co.", None, True),
    ("Hill Country Dairies", None, "Hill Country Dairy", None, True), ("Delta Spice", None, "Delta Spices", None, True), ("Lone Star Meats", None, "Lone Star Meat Market", None, True),
    ("Rogue Fitness", None, "Rogue Foods", None, False), ("Life Fitness", None, "Life Time Fitness", None, False), ("Texas Brewing Supply", None, "Texas Brewing Equipment", None, False),
    ("Austin Fresh Dairy", None, "Austin Fresh Produce", None, False), ("Gulf Coast Seafood", None, "Gulf Coast Seafood Grill", None, False), ("Keith Brothers Produce", None, "Brothers Produce", None, False),
    ("Meadow Dairy Co", None, "Meadow Creamery", None, False), ("Pioneer Linen Service", None, "Pioneer Laundry Service", None, False), ("Hilltop Foods", None, "Hilltop Farms", None, False),
    ("Atlas Equipment Rental", None, "Atlas Equipment Repair", None, False)]

CLASSIFY = [  # (category, name, products, classes that must be among the matches, expected primary or None)
    ("Specialty grains and masa (wholesale)", "Masienda", [], ["dry_goods_and_grocery"], "dry_goods_and_grocery"), ("Cash-and-carry wholesale foodservice", "Restaurant Depot", [], ["broadline_distribution"], "broadline_distribution"),
    ("Broadline foodservice distribution", "Sysco Central Texas", [], ["broadline_distribution"], "broadline_distribution"), ("Dairy: fresh cheese producer", "The Mozzarella Company", [], ["dairy"], "dairy"),
    ("Brewing ingredients: hops", "Yakima Chief Hops", [], ["beverage_ingredients"], "beverage_ingredients"), ("Brewing ingredients and equipment", "Austin Homebrew Supply", [], ["beverage_ingredients", "equipment"], None),
    ("Restaurant equipment and supplies (online)", "WebstaurantStore", [], ["equipment"], "equipment"), ("Boutique fitness equipment", "Peak Strength Supply", ["Squat rack", "Dumbbell set"], ["fitness_equipment"], "fitness_equipment"),
    ("Studio flooring", "Ironclad Surfaces", ["Rubber flooring tiles"], ["flooring_and_fitout"], "flooring_and_fitout"), ("Towel and laundry service", "Fresh Fold Linen", [], ["laundry_and_linen"], "laundry_and_linen"),
    ("Commercial cleaning", "Sparkle Facility Care", [], ["cleaning_and_facility_services"], "cleaning_and_facility_services"), ("Class booking software", "Bookwell", ["Member access control"], ["software_and_systems"], "software_and_systems"),
    ("Audio systems for studios", "Resonate AV", ["Speaker system"], ["software_and_systems"], "software_and_systems"), ("Poultry processor", "Hill Poultry Co", ["Chicken thighs"], ["meat_and_seafood"], "meat_and_seafood"),
    ("Gulf seafood", "Coastal Catch", ["Shrimp"], ["meat_and_seafood"], "meat_and_seafood"), ("Fresh vegetables and herbs", "Green Valley Farms", [], ["produce"], "produce"),
    ("Takeout packaging", "BoxIt", ["Paper bags"], ["packaging_and_disposables"], "packaging_and_disposables"), ("Business consulting", "Advisory Partners", [], [], "unclassified"),
    ("Spice importer", "Saffron Trading", ["Cumin", "Black pepper"], ["dry_goods_and_grocery"], "dry_goods_and_grocery"), ("Yeast and fermentation supplies", "Lalvin Labs", [], ["beverage_ingredients"], "beverage_ingredients"),
    ("Fitness studio fit-out contractor", "Studio Build", [], ["flooring_and_fitout"], "flooring_and_fitout"), ("Egg and dairy wholesale", "Prairie Eggs", [], ["dairy"], "dairy"),
    ("Janitorial supplies", "Neat Co", [], ["cleaning_and_facility_services"], "cleaning_and_facility_services"), ("Reformer pilates equipment", "Core Studio Gear", ["Reformer"], ["fitness_equipment"], "fitness_equipment")]

AREA = [("Austin, TX", "Austin, TX store; location details conflict between sources", "explicit"), ("Austin, TX", "Central Texas (per a 2012 trade report)", "unknown"), ("Austin, TX", "Dallas, TX (supplies Texas restaurants per press)", "none"),
        ("Austin, TX", "United States, online (per secondary sources)", "unknown"), ("Austin, TX", "Texas and other states; Austin is served from the San Antonio facility", "explicit"), ("Austin, TX", "Round Rock and Georgetown", "explicit"),
        ("Cedar Park, TX", "Austin, TX store", "explicit"), ("Houston, TX", "Greater Houston and Dallas/Fort Worth", "explicit"), ("Dallas, TX", "Houston", "none"), ("Austin, TX", "Statewide delivery in Texas", "statewide"),
        ("San Antonio, TX", "Bexar County and Austin", "explicit"), ("Austin, TX", "Pflugerville", "explicit")]


def run():
    dd = [(SI.duplicate_score(dict(name=a, website_url=u), dict(name=b, website_url=v))[0] >= SI.DUPLICATE_THRESHOLD, exp, f"{a} | {b}") for a, u, b, v, exp in DEDUPE]
    tp = sum(1 for p, e, _ in dd if p and e); fp = sum(1 for p, e, _ in dd if p and not e); fn = sum(1 for p, e, _ in dd if not p and e)
    cl = []
    for cat, name, prods, includes, primary in CLASSIFY:
        r = SI.classify(cat, name, prods)
        cl.append((set(includes) <= {m["cls"] for m in r["matches"]} and (primary is None or r["primary"] == primary) and (bool(includes) or r["primary"] == "unclassified"), f"{cat} -> {r['primary']}"))
    ar = [(SI.area_match(loc, sa)["level"] == exp, f"{loc} | {sa}") for loc, sa, exp in AREA]
    return dict(frozen_at=FROZEN_AT, dedupe=dict(cases=len(dd), true_positive=tp, false_positive=fp, false_negative=fn, precision=tp / (tp + fp) if tp + fp else 1.0, recall=tp / (tp + fn) if tp + fn else 1.0,
                                                  misses=[x[2] for x in dd if x[0] != x[1]]),
                classification=dict(cases=len(cl), correct=sum(c for c, _ in cl), accuracy=sum(c for c, _ in cl) / len(cl), misses=[d for c, d in cl if not c]),
                service_area=dict(cases=len(ar), correct=sum(c for c, _ in ar), accuracy=sum(c for c, _ in ar) / len(ar), misses=[d for c, d in ar if not c]))
