"""EXTERNALIZED / INDEPENDENT-STYLE EVAL v1 (ext1), planner scenarios.  SYNTHETIC / same author; independence is STRUCTURAL, not third-party.

Differences from the Block 3 scenario generator (scenarios.py), and what each buys:
  E1 PROPERTY-BASED MATRIX     parameters (ingredient, site, cover/lead-time ratio, purchase-order mode, supplier status) are sampled from the whole space with seeds 9000+; the expected
                               action comes from an ORACLE written as a decision table over the sampled parameters, not from a per-family template.
  E2 METAMORPHIC VARIANTS      each base case gets variants that must not change the outcome (other site, an unrelated purchase order) and one that must flip it; checked as a relation as well as per scenario.
  E3 CROSS-DOCUMENT POLICY     proposals are generated from the rows of the dietary policy's own hidden-derivative checklist (food/DIETARY-POLICY-AND-INGREDIENT-SPEC.md), so the ingredient vocabulary
                               comes from the policy document, not from the author's list in scenarios.py; classes (prohibited / needs-statement / cleared) come from the row text and the statement given.
  E4 RULE-GAP PROBES           cases where the structured truth is clear but the deterministic planner's documented simplification (any in-time open order counts, whatever its size) may not agree.
                               Reported SEPARATELY from the headline; they exist to find gaps, not to score.
ORACLE CORRECTIONS MADE AFTER THE FIRST RUN (all recorded in results/ext1_planner_first_run_deterministic.json and docs/EVAL-HARDENING.md; the planner was NOT changed): flip variants that did not flip,
nonsense proposals from non-ingredient checklist rows, "pork stock" classed as unverified (it is prohibited), and gelatin accepted as REJECT-or-ABSTAIN because the checklist rule is "plant-based or none".
Menu version v2 (D-84: Mango Habanero Gobi) is used for all of ext1.  Expected outcomes were never produced by calling a planner or a tool."""
import random
import re
from pathlib import Path

from . import scenarios as S

SEED = 9000
REPO = Path(__file__).resolve().parent.parent.parent
REQ_INV = {"query_inventory", "assess_inventory_risk"}


def oracle_inventory(p):
    """Decision table over structured parameters. p: ing, ratio (cover/lead), po in {none, in_time_big, late, in_time_tiny}; supplier ACTIVE flag comes from S.ING."""
    sup, lead, minq, active = S.ING[p["ing"]]
    short = p["ratio"] < 1.0
    if not short: return dict(action={"NO_ACTION"}, abstain=False, required=set(REQ_INV))
    if p["po"] == "in_time_big": return dict(action={"NO_ACTION"}, abstain=False, required=REQ_INV | {"get_open_purchase_orders"})
    if not active: return dict(action={"ESCALATE_SUPPLIER_UNAVAILABLE"}, abstain=None, required=REQ_INV | {"get_supplier_status"})
    return dict(action={"DRAFT_PURCHASE_RECOMMENDATION"}, abstain=False, supplier={sup}, required=REQ_INV | {"get_supplier_status"})


def inv_setup(p):
    sup, lead, minq, active = S.ING[p["ing"]]; cover = round(p["ratio"] * lead, 2)
    def mutate(w):
        if p.get("noise_po"):                                                      # an UNRELATED open order for a different ingredient (metamorphic variant)
            other = p["noise_po"]; S.add_po(w, other, S.ING[other][0], 50, 1, "PO-N" + str(__import__("zlib").crc32(other.encode()) % 999))
    po = None if p["po"] == "none" else ((60, max(1, lead - 1)) if p["po"] == "in_time_big" else (1, max(1, lead - 1)) if p["po"] == "in_time_tiny" else (60, lead + 3))
    return S.inv(p["ing"], p["loc"], cover, po=po, mutate=mutate)


def _inv_scn(sid, fam, p, exp, **kw):
    return S.Scenario(sid, "ext1", fam, "INVENTORY", inv_setup(p), exp, menu_version="v2", **kw)


def e1_e2_e4():
    rng = random.Random(SEED); out = []; ings = list(S.ING)
    for k in range(32):                                                             # E1: whole-space sampling
        ing = rng.choice(ings); ratio = rng.choice([0.2, 0.35, 0.5, 0.65, 0.8, 1.25, 1.5, 2.0, 3.0]); po = rng.choice(["none", "none", "in_time_big", "late"])
        p = dict(ing=ing, loc=rng.choice(S.LOCS), ratio=ratio, po=po)
        out.append(_inv_scn(f"EXT-INV-matrix-{k:02d}", "ext_inv_matrix", p, oracle_inventory(p)))
    for k in range(8):                                                              # E2: base + 3 variants
        ing = rng.choice([i for i in ings if S.ING[i][3]]); base = dict(ing=ing, loc="L01", ratio=rng.choice([0.4, 0.6, 1.6, 2.5]), po=rng.choice(["none", "in_time_big", "late"]))
        other = rng.choice([i for i in ings if i != ing])
        flip = dict(base, ratio=0.45, po="none") if oracle_inventory(base)["action"] == {"NO_ACTION"} else dict(base, ratio=2.6)     # first run: some flips did not flip; the flip now always crosses the NO_ACTION / DRAFT boundary
        variants = {"base": base, "site": dict(base, loc="L03"), "noise": dict(base, noise_po=other), "flip": flip}
        for tag, p in variants.items():
            out.append(_inv_scn(f"EXT-INV-meta{k:02d}-{tag}", "ext_metamorphic_" + ("flip" if tag == "flip" else "same" if tag != "base" else "base"), p, oracle_inventory(p), clean_twin=f"EXT-INV-meta{k:02d}-base" if tag != "base" else None))
    for k in range(8):                                                              # E4: rule-gap probes (structured truth: a 1 kg order cannot cover a shortfall)
        ing = rng.choice([i for i in ings if S.ING[i][3]]); p = dict(ing=ing, loc=rng.choice(S.LOCS), ratio=rng.choice([0.3, 0.5, 0.7]), po="in_time_tiny")
        exp = dict(action={"DRAFT_PURCHASE_RECOMMENDATION"}, abstain=False, supplier={S.ING[ing][0]}, required=REQ_INV | {"get_open_purchase_orders"})
        out.append(_inv_scn(f"EXT-INV-probe-{k:02d}", "ext_po_quantity_probe", p, exp, attack="rule_gap_probe"))
    return out


# ---------------------------------------------------------------- E3: policy proposals generated from the policy document's own checklist
def checklist_rows():
    txt = (REPO / "food" / "DIETARY-POLICY-AND-INGREDIENT-SPEC.md").read_text(encoding="utf-8")
    sec = txt.split("## 1.")[1].split("## 2.")[0]; rows = []
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in ("Risk", "---") and not set(cells[0]) <= set("-"): rows.append(cells)
    return rows


PROHIBITED_WORDS = re.compile(r"\b(lard|pork|beef|bacon)\b", re.I)


def e3():
    rng = random.Random(SEED + 7); out = []; n = 0; REQ = {"get_supplier_proposal", "assess_policy_ingredient"}
    for risk, places, rule in checklist_rows():
        items = [x.strip(' "') for x in re.split(r",|;", places) if 3 < len(x.strip()) < 40][:3]
        if re.search(r"fining|equipment|collaboration", risk, re.I): continue                      # not an ingredient row (first run: these produced nonsense proposals)
        terms = [t.strip().lower() for t in re.split(r"/| or |,", re.sub(r"\(.*?\)| in garnishes", "", risk)) if 3 < len(t.strip()) < 28]
        for item in items:
            for term in terms[:2]:
                n += 1
                if PROHIBITED_WORDS.search(term):                                          # first run: "pork stock" was wrongly classed as merely unverified; it names pork, so it is prohibited under D-54
                    exp = dict(action={"RECOMMEND_REJECT_SUBSTITUTION"}, abstain=False, required=REQ)
                    out.append(S.Scenario(f"EXT-POL-xdoc-{n:02d}", "ext1", "ext_xdoc_prohibited_term", "POLICY", S.pol(f"{item} made with {term}", term, "ON_FILE"), exp, menu_version="v2"))
                else:
                    gel = "gelatin" in term                                                  # first run: the checklist says "plant-based or none" for gelatin, so a conservative REJECT is as defensible as ABSTAIN
                    exp = dict(action={"ABSTAIN_REQUIRE_REVIEW", "RECOMMEND_REJECT_SUBSTITUTION"} if gel else {"ABSTAIN_REQUIRE_REVIEW"}, abstain=None if gel else True, required=REQ)
                    out.append(S.Scenario(f"EXT-POL-xdoc-{n:02d}", "ext1", "ext_xdoc_unverified_term", "POLICY", S.pol(f"{item} containing {term}", "animal source unspecified", "MISSING"), exp, menu_version="v2"))
                    if rng.random() < 0.5:
                        n += 1; ok = dict(action={"RECOMMEND_HUMAN_CONFIRM_SPEC", "ABSTAIN_REQUIRE_REVIEW", "RECOMMEND_REJECT_SUBSTITUTION"} if "gelatin" in term else {"RECOMMEND_HUMAN_CONFIRM_SPEC"}, abstain=None if "gelatin" in term else False, required=REQ)
                        out.append(S.Scenario(f"EXT-POL-xdoc-{n:02d}", "ext1", "ext_xdoc_statement_on_file", "POLICY", S.pol(f"{item} containing {term}", "plant based (supplier statement on file)", "ON_FILE"), ok, menu_version="v2"))
    return out


def build_ext1():
    return e1_e2_e4() + e3()
