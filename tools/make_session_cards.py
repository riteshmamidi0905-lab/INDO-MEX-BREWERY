#!/usr/bin/env python3
"""Generate the Core 5 SESSION CARDS (food/sessions/S2..S5-*.md) and the R&D book index (food/sessions/README.md) from the single source of truth
food/sessions/sessions.json (frozen at D-76). Regenerating never changes a gate: edit the JSON (a new decision, before tasting) and rerun.
  python3 tools/make_session_cards.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from session_record import spec, gates_hash
def esc(x): return str(x).replace("|", "/")
def card(key, ss, meta, h):
    L = [f"# SESSION {ss['session']} CARD: {ss['dish']}", "",
         f"**Status:** {ss['state']}. NOTHING HAS BEEN COOKED. Generated from `food/sessions/sessions.json` (gates hash `{h[:12]}`). Open this card, shop, cook, record. You do not need the rest of the repository.", "",
         f"**Primary question:** {ss['question']}", "", f"**Hypothesis (analysis, not evidence):** {ss['hypothesis']}", "",
         "## What you are comparing"] + [f"- **{k}:** {v}" for k, v in ss["constructions"].items()] + [f"- {c}" for c in ss["controls"]] + ["", f"**Test variable:** {ss['test_variable']}", "", "**Keep identical (controlled):**"] + [f"- {c}" for c in ss["controlled"]] + ["",
         "## Shopping (separate: required, screening substitutes, never-acceptable, verify)"]
    for k, items in ss["shopping"].items(): L += [f"**{k}**"] + [f"- [ ] {i}" for i in items] + [""]
    L += [f"**Quantity audit:** {ss['quantity_audit']}", "", f"**Labels:** {ss['verify_labels']}", "", "## Day plan"] + [f"{i}. {x}" for i, x in enumerate(ss["day_plan"], 1)] + ["", "## Equipment"] + [f"- [ ] {e}" for e in ss["equipment_required"]] + ["", f"## {ss['baseline']['label']}"]
    for k, v in ss["baseline"].items():
        if k == "label": continue
        if isinstance(v, dict): L += [f"- **{k.replace('_', ' ')}:**"] + [f"  - {a}: {b}" for a, b in v.items()]
        else: L.append(f"- **{k.replace('_', ' ')}:** {v}")
    L += ["", "## Variables and how well each is supported", "| Variable | Class | Note |", "|---|---|---|"] + [f"| {esc(x['v'])} | {esc(x['class'])} | {esc(x['note'])} |" for x in ss["variables"]]
    L += ["", "## Measure (write down; never estimate later)"] + [f"- [ ] {m}" for m in ss["measurements"]] + ["", "## Photograph (same device, place, light, position; originals untouched; crop/exposure/white balance/rotation only; no generative edits)"] + [f"- [ ] {p}" for p in ss["photos"]]
    L += ["", f"## FROZEN GATES ({meta['thresholds_label']})", "Score each gate at its time (1-5, panel mean). Do not re-crisp or repair plates before scoring. Hold times: " + ", ".join(f"T+{t}" for t in ss["times"]) + ".", "", "| Gate | Minimum | Score at | Note |", "|---|---|---|---|"]
    for g, v in ss["gates"].items(): L.append(f"| {g} | {v['min']} | T+{v['at']} | {esc(ss.get('gate_notes', {}).get(g, ''))} |")
    L += ["", "**Failure gates (any one fails the iteration):**"] + [f"- `{k}`: {v}" for k, v in ss["failure_gates"].items()]
    L += ["", f"**Decision rule:** {meta['thresholds_label']} NONE WINS is a valid result. Thresholds are never changed after tasting.", "", "## Safety, D-54, allergens"] + [f"- {x}" for x in ss["safety"]] + [f"- **Panel:** {ss['panel']}", f"- {meta['d54']}", f"- {meta['mustard_oil']}", "- Allergens: see `food/ALLERGEN-MATRIX.csv`; cross-contact is a process issue; no allergen-free claim.", "",
          "## After the cook", f"- {ss['after_cook']}", "- Scores go in `food/sessions/results.csv` (one row per gate, time, construction, iteration; `real_cook` only; photo IDs and panel size required). Ingest photos with `python3 tools/photo_ingest.py ingest ...`.", "- Anything not measured is `NOT MEASURED`. Never fill from memory."]
    return "\n".join(L) + "\n"
def main():
    s = spec(); h = gates_hash(s); idx = ["# Core 5 R&D book (index)", "", "**What this is:** the one navigable entry point for the five physical sessions. **Status:** NO SESSION HAS BEEN PERFORMED; Chicken 65 Totopos is NOT PERFORMED. Cards below are generated from `sessions.json` (gates frozen at D-76; hash recorded there). The founder can open a card and cook; a brewer, cultural advisor or architect can open their own pack (listed below).", "", "| Session | Dish | Card | Frozen rule | State |", "|---|---|---|---|---|",
           "| 1 | Chicken 65 Totopos | [cook card, shopping and sequence](../t1-test-sheets/13-session-1-quantity-audit-shopping-cook-card.md) | [protocol, D-74](../t1-test-sheets/11-chicken-65-totopos-prototype-protocol-FROZEN.md) | NOT PERFORMED (run `python3 tools/t1_record.py` after cooking) |"]
    for key, ss in s["sessions"].items():
        fn = f"S{ss['session']}-{key}.md"; open(f"food/sessions/{fn}", "w", encoding="utf-8").write(card(key, ss, s["_meta"], h))
        idx.append(f"| {ss['session']} | {ss['dish']} | [{fn}]({fn}) | gates in the card (D-76) | {ss['state']} |")
    idx += ["", "## Other packs", "- Brewer: `beer/pilot-briefs/00-BREWER-HANDOFF.md` (start here).", "- Cultural advisor: `docs/CULTURAL-REVIEW-PACK.md`.", "- Architect / operations: `docs/OPERATIONAL-REQUIREMENTS-CORE5.md`.", "- Fastest project view: `docs/PROTOTYPE-READINESS.md` (generated: `python3 tools/dashboard.py`).", "", "## Order of the sessions", "Founder default 1 to 5. Start goat SOURCING now (long lead) while keeping the goat cook at Session 5; Session 2 does not depend on a tandoor. A better order may emerge after Session 1; the founder decides.", "", f"Frozen gates hash: `{h}`"]
    open("food/sessions/README.md", "w", encoding="utf-8").write("\n".join(idx) + "\n"); print("cards written:", len(s["sessions"]) + 1, "files")
if __name__ == "__main__": main()
