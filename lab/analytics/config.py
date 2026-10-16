"""The ONE place where assumptions live. Every value below is an ASSUMPTION or a simulation parameter, NOT a NASHA fact.

Menu prices come from the lab generator (placeholder inputs, see nasha_lab/generator.py). Ingredient costs, overheads and the
supplier-reliability profile do not exist anywhere in the repository; they are invented here, labelled, and changeable.
Changing a value changes the downstream numbers; results files record the config hash.
"""
import hashlib
import json

SEED = 1                      # default build seed (the lab generator seed)
MENU_VERSION_SOURCE = "v2"    # lab menu version used as the order source (orders are identical across v1/v2; only M04 differs)
DEFECTS_PER_TYPE = 8          # lab generator default: injected defects per type (labelled in the generator's truth set)

# --- SCD2 menu change (ASSUMPTION): the v1 -> v2 switch of M04 is given a synthetic effective date INSIDE the 56-day window so that
# orders exist on both sides. The lab itself models menu versions as whole-world alternatives, not as a dated change.
MENU_CHANGE_DATE = "2026-04-13"       # first date on which M04 is 'Mango Habanero Gobi' (v2). v1 'Gobi Taco' is valid before it.
HIGH_DATE = "9999-12-31"

# --- ASSUMED food cost per kg (USD). NOT real. Used only for contribution-margin illustrations.
COST_PER_KG = {"chicken thigh": 6.0, "paneer": 9.0, "goat": 14.0, "cauliflower": 2.5, "corn masa": 1.8, "cheese": 8.0, "malt": 2.0, "hops": 25.0}
OTHER_COST_PCT_OF_PRICE = {"food": 0.10, "beer": 0.0, "na": 0.0}   # untracked ingredients/packaging as a share of price (ASSUMPTION)
FIXED_UNIT_COST_USD = {"beer": 1.50, "na": 0.90}                     # per unit: brewing overhead / drink inputs (ASSUMPTION); makes beer COGS non-trivial
COGS_SENSITIVITY = (0.75, 1.0, 1.25)                                 # cost multipliers used to test ranking robustness

# --- Inventory re-simulation (analytics layer). Mirrors the lab world's weekly-count / replenish-to-par design but applies the
# SCD2-effective recipe, logged waste and a labelled unlogged-shrink injection.
COUNT_NOISE = (0.97, 1.03)
PAR_WEEKS = 1.6
PERISHABLE = {"chicken thigh", "paneer", "goat", "cauliflower", "cheese"}
WASTE_EVENT_PROB = {"perishable": 0.45, "dry": 0.10}                 # per site-ingredient-week
WASTE_FRACTION_OF_WEEKLY_USAGE = (0.02, 0.08)
WASTE_REASONS = {"perishable": ["SPOILAGE", "PREP_TRIM", "SPILL"], "dry": ["SPILL", "EXPIRED"]}
INJECTED_SHRINK = [("L03", "goat", 0.06)]                            # unlogged shrink: 6% of weekly usage disappears with no waste entry (truth label)
SHORT_SHIP_PROB = 0.05                                               # fraction of PO lines received short
SHORT_SHIP_RANGE = (0.10, 0.30)

# --- Supplier delivery reliability profile (ASSUMPTION; injected, so the reliability queries have a known answer)
SUPPLIER_LATE_PROB = {"S01": 0.05, "S02": 0.10, "S03": 0.40, "S04": 0.05, "S05": 0.25}
SUPPLIER_LATE_DAYS = {"S01": (1, 1), "S02": (1, 2), "S03": (1, 3), "S04": (1, 1), "S05": (1, 2)}

# --- Synthetic guest layer (NASHA has no guests; this exists only to exercise cohort/retention/experiment techniques)
GUEST_ID_COVERAGE = 0.40      # share of orders carrying a synthetic guest id (like a loyalty scan rate)
GUEST_NEW_PROB_START = 0.35   # probability an identified order comes from a NEW guest in week 1 ...
GUEST_NEW_PROB_END = 0.08     # ... decaying linearly to this by the last week
GUEST_FREQ_GAMMA = (2.0, 0.5) # shape, scale of a guest's latent visit propensity
GUEST_CHURN_HALF_LIFE_WEEKS = 6.0

# --- Synthetic exception workflow (event -> exception -> approval -> resolution), for the funnel query only
EXC_APPROVAL_PROB = 0.75
EXC_RESOLUTION_PROB = 0.80    # conditional on approval
EXC_MAX_APPROVAL_HOURS = 72
EXC_MAX_RESOLUTION_HOURS = 120

AS_OF = "2026-05-01"          # same scenario as-of as nasha_lab.generator.AS_OF
FRESHNESS_MAX_AGE_DAYS = 7


def config_hash():
    blob = {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in sorted(globals().items()) if k.isupper() and not k.startswith("_")}
    return hashlib.sha256(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()[:12]
