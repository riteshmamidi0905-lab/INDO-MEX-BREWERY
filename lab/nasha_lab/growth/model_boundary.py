"""The boundary every agent or model output must cross before Growth OS uses a word of it. Provider-independent: it validates the structured REPORT and the TOOL CALLS that come back from the Production AI Agent Platform
engine, whether the provider is the offline heuristic, a local model (Ollama) or any OpenAI-compatible endpoint. It never trusts the output and never lets it decide anything:
  * the recommendation (suppliers, quantities, costs) is computed from stored quotes and re-derived by `procurement.check_plan`; the model contributes cited research text only;
  * a report is `accepted` only if it is well-formed AND every claim is grounded; one bad claim rejects the whole output (the workflow then uses the deterministic fallback and records why);
  * `abstained` is a valid, safe outcome: the model said the evidence does not answer the question and made no claims.
Rules (each yields a stable code): MALFORMED, NO_EVIDENCE, UNKNOWN_EVIDENCE, UNSUPPORTED_NUMBER, PRICE_MISMATCH, UNKNOWN_SUPPLIER, WRONG_SOURCE, UNSUPPORTED_VERIFICATION, UNSUPPORTED_RECOMMENDATION, INSTRUCTION_TEXT, TOOL_NOT_ALLOWED,
the comparative-claim codes COMPARATIVE_FALSE, COMPARATIVE_UNVERIFIABLE (a lowest/highest claim is checked against the FULL stored quote set of the tenant, never inferred from what retrieval happened to return, and fails closed when the set cannot be compared),
the absence-claim codes ABSENCE_OVERGENERAL, ABSENCE_CONTRADICTED ("no supplier has published a price" needs authoritative stored evidence; "no matching price was found in the searched records" is the scoped form), UNTRUSTED_SOURCE (a claim that rests on a passage containing instructions to the assistant),
and the entity-binding codes UNATTRIBUTED_PRICE, PRICE_NOT_FROM_NAMED_SUPPLIER, UNKNOWN_ENTITY: a price in a claim must be attributed to a supplier by name, must appear in a cited passage OF THAT supplier, and a subject that is in no supplier record
cannot be presented as quoting. A real price is not enough; it must belong to the entity the claim says it belongs to. Binding is per supplier record, not per product line, and is lexical (a paraphrase that never names the supplier is rejected as unattributed; one that names it wrongly is caught only if the name appears).
Uncertainty is COMPUTED from the stored records the claims rest on (unverified leads, synthetic prices, stale data), not taken from the model, so it cannot be omitted or softened by one.
Limits: these are lexical and structural checks. They catch fabricated numbers, invented evidence, overreach and injected instructions in the shapes listed; they do not prove a sentence is true or that a clever paraphrase of a false claim is caught."""
import re

ALLOWED_TOOLS = ("search_corpus", "calculator")
MAX_CLAIMS, MAX_CLAIM_CHARS, MAX_ANSWER_CHARS = 12, 400, 1500
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
COMPANY = re.compile(r"\b((?:[A-Z][\w&'-]*\s+){1,4}(?:LLC|Inc\.?|Co\.?|Corp\.?|Ltd\.?|Company|Dairies|Produce|Foods|Farms|Distributors|Wholesale|Provisions|Imports))\b")
VERIFIED_WORDS = re.compile(r"\b(verified|confirmed|officially|official website|certified|vetted|approved supplier)\b", re.I)
RECOMMEND_WORDS = re.compile(r"\b(i recommend|we recommend|recommend(?:ed)? (?:that|using|choosing|buying|ordering)|you should (?:choose|buy|order|use|select)|best choice|the best supplier|select this supplier|go with)\b", re.I)
INSTRUCTION_WORDS = re.compile(r"(ignore (?:all |any )?(?:previous|prior|above)|disregard (?:the )?(?:above|previous|instructions)|system prompt|you must now|new instructions|place (?:an|the) order|send (?:an? )?(?:email|message)|email the|call the|contact the (?:supplier|vendor|owner)|wire (?:the )?(?:money|funds|payment)|pay (?:the )?invoice|purchase order|api[_ ]?key|password|(?:i|we) authori[sz]e you to|email every supplier|tell the reader to|editor note|note to the assistant)", re.I)

CRITICAL = {"MALFORMED", "TOOL_NOT_ALLOWED", "INSTRUCTION_TEXT"}


def _num(s):
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _numbers(text):
    return [n for n in (_num(m) for m in NUM.findall(text)) if n is not None]


def _present(n, passages):
    return any(any(abs(n - m) < 1e-9 for m in _numbers(p)) for p in passages)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


AMOUNT = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
SUBJECT = re.compile(r"^\s*(?:The\s+)?([A-Z][\w&'.-]*(?:\s+(?:[A-Z0-9][\w&'.-]*|and|of|the|&)){1,6}?)\s+(?:quotes?|offers?|lists?|charges?|sells?|publishes|provides?|prices?|supplies)\b")


# ---- instructions hidden in source material (independent of any prompt wording; also used to quarantine documents before they reach a model)
DIRECTIVE_PATTERNS = [re.compile(p, re.I) for p in (
    r"\b(?:note|notice|message|instruction|memo)s?\s+(?:to|for)\s+(?:the\s+)?(?:assistant|model|ai|agent|writer|llm|bot|report)",
    r"\b(?:editor|system|admin|developer)\s+(?:note|notice|message|override)\b",
    r"\b(?:when|if)\s+(?:you\s+are\s+)?asked\s+about\b[^.]{0,120}\b(?:state|say|report|write|claim|answer|respond)\b",
    r"\b(?:tell|instruct|direct|ask|require)\s+the\s+(?:reader|user|assistant|model|agent)\b",
    r"\b(?:disclose|reveal|print|show|repeat)\b[^.]{0,40}\b(?:instructions|prompt|rules)\b",
    r"\bthe\s+records?\s+above\s+(?:are|is)\s+(?:outdated|wrong|incorrect|superseded)",
    r"\byou\s+(?:must|should|shall|will)\s+(?:now\s+)?(?:state|report|say|email|send|ignore|cite|claim)\b",
    r"\bemail\s+every\s+supplier\b", r"\bcite\s+this\s+record\b")]


def directive_flags(text):
    """Patterns in `text` that address the assistant instead of describing a supplier. Lexical: it catches the shapes listed, not every possible phrasing; it is a second, independent layer, never the only one."""
    return [p.pattern[:40] for p in DIRECTIVE_PATTERNS if p.search(text or "")]


# ---- comparative claims
SUPERLATIVE = re.compile(r"\b(lowest|cheapest|least expensive|most affordable|best price|minimum(?!\s+(?:order|quantity|qty|spend|purchase|pack|amount))|highest|most expensive|priciest|maximum(?!\s+(?:order|quantity|qty)))\b", re.I)
HIGH_WORDS = re.compile(r"highest|most expensive|priciest|maximum", re.I)
SCOPED = re.compile(r"\b(?:among|of|in|from|within)\s+(?:the\s+)?(?:retrieved|provided|cited|given|searched|available|returned)\b", re.I)


def _norm_unit(u):
    return _norm(u)


def comparison_set(directory, ref, as_of=None):
    """The stored, tenant-scoped quotes for one ingredient: [(supplier id, name, unit_price_cents, unit, price_class)], and why anything was left out. `as_of` drops quotes outside their stated validity window."""
    rows, left_out = [], []
    for s in directory:
        for p in s.get("products", []):
            if p.get("ingredient_ref") != ref or p.get("unit_price_cents") is None or p.get("price_class") == "NONE_PUBLISHED":
                continue
            if as_of is not None and ((p.get("valid_to") is not None and p["valid_to"] < as_of) or (p.get("valid_from") is not None and p["valid_from"] > as_of)):
                left_out.append(dict(supplier=s["name"], reason="outside its validity window")); continue
            rows.append((s["id"], s["name"], float(p["unit_price_cents"]), p.get("unit"), p.get("price_class"), p.get("currency")))
    return rows, left_out


def verify_comparative(text, directory, mentions_ids, amounts, retrieved_supplier_ids, as_of=None):
    """-> None when the claim has no superlative; else dict(verdict 'verified'|'false'|'unverifiable', reason, product, kind, scope, set, extreme). Fails closed."""
    sm = SUPERLATIVE.search(text)
    if not sm:
        return None
    kind = "high" if HIGH_WORDS.search(sm.group(1)) else "low"
    low = _norm(text)
    refs = {}
    for s in directory:
        for p in s.get("products", []):
            ref = p.get("ingredient_ref")
            if not ref:
                continue
            for nm in {_norm(p["name"]), _norm(re.sub(r"\s*\([^)]*\)\s*$", "", p["name"])), _norm(ref)}:
                if nm and re.search(rf"(?<![a-z0-9]){re.escape(nm)}(?![a-z0-9])", low):
                    refs.setdefault(ref, p["name"])
    out = dict(kind=kind, scope="stored quotes of the tenant", product=None, set=[], extreme=None)
    if len(refs) != 1:
        return dict(out, verdict="unverifiable", reason="no product could be identified in the claim" if not refs else f"{len(refs)} different products are named; a superlative needs exactly one")
    ref = next(iter(refs)); out["product"] = ref
    rows, left_out = comparison_set(directory, ref, as_of)
    out["left_out"] = left_out
    scoped = bool(SCOPED.search(text))
    if scoped:
        rows = [r for r in rows if r[0] in retrieved_supplier_ids]
        out["scope"] = "the retrieved records only (the claim says so); NOT a global statement"
    out["set"] = [dict(supplier=r[1], price=r[2], unit=r[3]) for r in sorted(rows, key=lambda r: (r[2], r[1]))]
    if len({r[1] for r in rows}) < 2:
        return dict(out, verdict="unverifiable", reason="fewer than two suppliers have a comparable quote, so there is nothing to rank")
    if len({_norm_unit(r[3]) for r in rows}) != 1:
        return dict(out, verdict="unverifiable", reason="the quotes are in different units")
    if len({r[4] for r in rows}) != 1:
        return dict(out, verdict="unverifiable", reason="the quotes are of different kinds (e.g. synthetic and supplier quotes) and are not comparable")
    if len({r[5] for r in rows}) != 1:
        return dict(out, verdict="unverifiable", reason="the quotes are in different currencies")
    ext = (max if kind == "high" else min)(r[2] for r in rows)
    winners = {r[0] for r in rows if abs(r[2] - ext) < 1e-9}
    out["extreme"] = dict(price_cents=ext, suppliers=sorted(r[1] for r in rows if r[0] in winners))
    if not mentions_ids and not amounts:
        return dict(out, verdict="unverifiable", reason="the claim names neither a supplier nor a price, so it cannot be checked")
    if mentions_ids and not set(mentions_ids) <= winners:
        return dict(out, verdict="false", reason="a named supplier is not the " + ("highest" if kind == "high" else "lowest") + " quote in the comparison set")
    if amounts and any(round(a, 2) != round(ext / 100, 2) for a in amounts):
        return dict(out, verdict="false", reason="the stated price is not the " + ("highest" if kind == "high" else "lowest") + " in the comparison set")
    return dict(out, verdict="verified", reason="matches the extreme of the comparison set")


# ---- absence claims
ABSENCE = re.compile(r"\b(?:no|not any|none of|never|neither|zero)\b[^.]{0,60}\b(?:price|prices|pricing|quote|quotes|prices list|price list)\b|\b(?:does not|do not|doesn't|don't|has not|have not|did not|didn't|cannot|can't)\b[^.]{0,30}\b(?:publish|publishes|provide|list|offer|quote|state)\b[^.]{0,30}\b(?:price|prices|quote|quotes)\b|\bno published price", re.I)
UNIVERSAL = re.compile(r"\b(?:any|all|every|each)\s+(?:of\s+the\s+)?suppliers?\b|\bno\s+suppliers?\b|\bnone\s+of\s+the\s+suppliers\b|\bnone\s+of\s+them\b|\bany\s+supplier\b|\bsuppliers\s+(?:do|have|did)\s+not\b", re.I)
EVIDENCE_SCOPE = re.compile(r"\b(?:in|from|within)\s+(?:the\s+)?(?:retrieved|provided|cited|available|searched|given|returned)\s+(?:records?|evidence|passages?|sources?|documents?)\b|\b(?:the\s+)?(?:evidence|passages?|retrieved records?)\s+(?:does|do)\s+not\b|\bnot\s+(?:directly\s+)?(?:provided|found|stated|included|present)\s+in\s+the\s+(?:evidence|records?|passages?)\b", re.I)


NOT_PROVIDED = re.compile(r"\bnot\s+(?:directly\s+)?(?:provided|found|stated|published|available|included|present)\b", re.I)


def classify_absence(text, directory, passages=(), mentions_ids=()):
    """-> None if `text` is not an absence claim; else dict(kind 'named'|'evidence_scoped'|'universal'|'quotation', verdict 'supported'|'contradicted'|'overgeneral', reason, suggestion).
    A claim that quotes a cited passage word for word keeps its provenance and is not re-judged. A named supplier is checked against its stored products; an evidence-scoped claim against the cited passages; a universal claim only
    against the authoritative stored set: "no supplier has published a price" is accepted only if no stored supplier has one."""
    if "$" in text or not (ABSENCE.search(text) or (NOT_PROVIDED.search(text) and re.search(r"\b(?:price|prices|quote|quotes|pricing)\b", text, re.I))):
        return None
    nt = _norm(text)
    if nt and any(nt in _norm(p) for p in passages):
        return dict(kind="quotation", verdict="supported", reason="the claim is a word-for-word quotation of a cited passage", suggestion=None)
    suggestion = "No matching price was found in the searched records."
    priced = [s["name"] for s in directory if any(p.get("unit_price_cents") is not None and p.get("price_class") != "NONE_PUBLISHED" for p in s.get("products", []))]
    if mentions_ids and not UNIVERSAL.search(text):
        byid = {s["id"]: s for s in directory}
        pr = [byid[i]["name"] for i in mentions_ids if i in byid and any(p.get("unit_price_cents") is not None and p.get("price_class") != "NONE_PUBLISHED" for p in byid[i].get("products", []))]
        if pr:
            return dict(kind="named", verdict="contradicted", reason=f"the stored record of {', '.join(pr)} contains published prices", suggestion=suggestion)
        return dict(kind="named", verdict="supported", reason="every stored product of the named supplier(s) has no published price", suggestion=None)
    if EVIDENCE_SCOPE.search(text) and not UNIVERSAL.search(text):
        if any("$" in p for p in passages):
            return dict(kind="evidence_scoped", verdict="contradicted", reason="a cited passage does state a price", suggestion=suggestion)
        return dict(kind="evidence_scoped", verdict="supported", reason="no cited passage states a price", suggestion=None)
    if priced:
        return dict(kind="universal", verdict="overgeneral", reason=f"a universal absence claim is contradicted by the stored records ({len(priced)} supplier(s) have published prices, e.g. {priced[0]}); a search that returned only some records cannot establish it", suggestion=suggestion)
    return dict(kind="universal", verdict="supported", reason="the authoritative stored set contains no published price at all", suggestion=None)


def _aliases(directory):
    """normalised name -> {supplier ids}. A supplier answers to its full name and to the name without a trailing parenthetical category ('Synthetic Supplier 04 (dairy)' is also 'Synthetic Supplier 04')."""
    out = {}
    for s in directory:
        for nm in {_norm(s["name"]), _norm(re.sub(r"\s*\([^)]*\)\s*$", "", s["name"]))}:
            if nm:
                out.setdefault(nm, set()).add(s["id"])
    return out


def _mentions(text, aliases):
    """[(position, supplier ids)] for every whole-word occurrence of a supplier name in the claim; the longest alias wins where names overlap."""
    low = _norm(text)
    found = []
    for nm, ids in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(nm)}(?![a-z0-9])", low):
            if not any(a < m.end() and m.start() < b for a, b, _ in found):
                found.append((m.start(), m.end(), ids))
    return sorted(found)


def computed_uncertainty(directory, cited_supplier_ids):
    """What a reader must keep in mind, from the stored records themselves (not from the model)."""
    by = {s["id"]: s for s in directory}
    cited = [by[i] for i in sorted(cited_supplier_ids) if i in by]
    out = []
    unv = sorted(s["name"] for s in cited if s["verification_status"] != "verified_public")
    if unv:
        out.append(f"{len(unv)} of {len(cited)} cited supplier records are not verified from an official source: {', '.join(unv)}.")
    syn = sorted(s["name"] for s in cited if any(p["price_class"] == "SYNTHETIC_QUOTE" for p in s["products"]))
    if syn:
        out.append(f"Prices cited for {len(syn)} supplier(s) are synthetic quotations, not real prices.")
    nop = sorted(s["name"] for s in cited if s["products"] and all(p["price_class"] == "NONE_PUBLISHED" for p in s["products"]))
    if nop:
        out.append(f"No published price exists for: {', '.join(nop)}; they cannot be ranked.")
    stale = sorted(s["name"] for s in cited if str(s.get("freshness", "")).startswith(("stale", "aging", "unverified")))
    if stale:
        out.append(f"Data freshness is not 'fresh' for: {', '.join(stale)}.")
    if not cited:
        out.append("No supplier record is cited, so nothing here supports a conclusion about any supplier.")
    else:
        out.append("Nothing here has been confirmed with any supplier; a price applies only within its stated validity dates.")      # standing caveat: uncertainty is never empty when suppliers are cited
    return out


def review(report, evidence, directory, tool_calls=(), allowed_tools=ALLOWED_TOOLS, rules=None, as_of=None):
    """Validate an agent report. Returns dict(status accepted|abstained|rejected, claims_accepted, claims_rejected[{text, codes}], report_codes, tool_codes, uncertainty, flags, problems[list of readable strings]).
    `rules` (a set of rule names) exists so the evaluation can switch ONE rule off; production uses all."""
    R = rules if rules is not None else RULES
    rejected, accepted, report_codes, flags = [], [], [], []
    def bad(code, why):
        report_codes.append(code); problems.append(f"{code}: {why}")
    problems = []
    # ---- shape
    if "shape" in R:
        if not isinstance(report, dict) or not isinstance(report.get("claims", []), list) or not isinstance(report.get("answer", ""), str):
            bad("MALFORMED", "the report is not an object with a text answer and a list of claims")
            return dict(status="rejected", claims_accepted=[], claims_rejected=[], report_codes=report_codes, tool_codes=[], uncertainty=computed_uncertainty(directory, set()), flags=flags, problems=problems, comparisons=[], absences=[])
        if len(report["claims"]) > MAX_CLAIMS or len(report.get("answer", "")) > MAX_ANSWER_CHARS:
            bad("MALFORMED", f"more than {MAX_CLAIMS} claims or an answer over {MAX_ANSWER_CHARS} characters")
    claims = report.get("claims", []) if isinstance(report, dict) else []
    # ---- tool calls (read-only allowlist)
    tool_codes = []
    if "tools" in R:
        for t in tool_calls or []:
            if not isinstance(t, dict) or t.get("tool") not in allowed_tools:
                tool_codes.append("TOOL_NOT_ALLOWED"); bad("TOOL_NOT_ALLOWED", f"tool {t.get('tool') if isinstance(t, dict) else t!r} is not in the read-only allowlist {list(allowed_tools)}")
    suppliers = {s["id"]: s for s in directory}
    names = {_norm(s["name"]): s["id"] for s in directory}
    aliases = _aliases(directory)
    cited_suppliers, comparisons, absences = set(), [], []
    retrieved_supplier_ids = {sid for sid in suppliers if any(v["doc_id"] == f"supplier-{sid}" or v["doc_id"].startswith((f"supplier-{sid}#", f"supplier-{sid}:")) for v in evidence.values())}
    for c in claims:
        codes, text = [], ""
        if not isinstance(c, dict) or not isinstance(c.get("text"), str) or not isinstance(c.get("evidence_ids", []), list) or not all(isinstance(e, str) for e in c.get("evidence_ids", [])):
            if "shape" in R:
                rejected.append(dict(text=str(c)[:80], codes=["MALFORMED"])); bad("MALFORMED", "a claim is not {text, evidence_ids[]}")
            continue
        text, ids = c["text"], c.get("evidence_ids", [])
        if len(text) > MAX_CLAIM_CHARS and "shape" in R:
            codes.append("MALFORMED")
        if "instruction" in R and INSTRUCTION_WORDS.search(text):
            codes.append("INSTRUCTION_TEXT")
        known = [e for e in ids if e in evidence]
        if "grounding" in R:
            if not ids:
                codes.append("NO_EVIDENCE")
            elif len(known) != len(ids):
                codes.append("UNKNOWN_EVIDENCE")
        passages = [evidence[e]["text"] for e in known]
        docs = {evidence[e]["doc_id"] for e in known}
        sup_of = {sid for sid in suppliers if any(d == f"supplier-{sid}" or d.startswith(f"supplier-{sid}#") or d.startswith(f"supplier-{sid}:") for d in docs)}
        cited_suppliers |= sup_of
        if "numbers" in R:
            for n in _numbers(text):
                if not _present(n, passages):
                    codes.append("UNSUPPORTED_NUMBER"); break
        if "prices" in R:
            stored = {round(float(p["unit_price_cents"]) / 100, 2) for s in directory for p in s["products"] if p["unit_price_cents"] is not None} \
                | {round(float(p["min_order_cents"]) / 100, 2) for s in directory for p in s["products"] if p.get("min_order_cents") is not None}       # a stated minimum order is a stored fact too
            for m in re.findall(r"\$\s?(\d[\d,]*(?:\.\d+)?)", text):
                v = _num(m)
                if v is not None and round(v, 2) not in stored:
                    codes.append("PRICE_MISMATCH"); break
        low = _norm(text)
        mentions = _mentions(text, aliases)
        mentioned = {sid for _, _, ids in mentions for sid in ids} | {sid for nm, sid in names.items() if nm and nm in low}
        if "source" in R and (mentioned - sup_of):
            codes.append("WRONG_SOURCE")                                      # names a supplier but cites no passage from that supplier's record
        if "supplier_names" in R:
            for m in COMPANY.findall(text):
                if not any(_norm(m) in nm or nm in _norm(m) for nm in names):
                    codes.append("UNKNOWN_SUPPLIER"); break
        # ---- entity binding: skipped when an identity code (UNKNOWN_SUPPLIER, WRONG_SOURCE) already rejected the claim, so one defect is not reported twice
        if not ({"UNKNOWN_SUPPLIER", "WRONG_SOURCE"} & set(codes)):
            amounts = [_num(m) for m in AMOUNT.findall(text)]
            amounts = [a for a in amounts if a is not None]
            if "attribution" in R and amounts and not mentioned:
                codes.append("UNATTRIBUTED_PRICE")                            # a price with no supplier named is not a usable fact about any supplier
            if "price_binding" in R and amounts and mentions:
                own = {sid: [evidence[e]["text"] for e in known if evidence[e]["doc_id"] == f"supplier-{sid}" or evidence[e]["doc_id"].startswith((f"supplier-{sid}#", f"supplier-{sid}:"))] for sid in suppliers}
                for m in AMOUNT.finditer(text):
                    v = _num(m.group(1))
                    # the supplier the price belongs to: the closest name BEFORE it in the claim, else the closest after it ("a price of $4.50 from Meadow Dairy Co")
                    pos = len(_norm(text[:m.start()]))
                    before = [t for t in mentions if t[1] <= pos]
                    near = max(before, key=lambda t: t[1]) if before else min(mentions, key=lambda t: t[0])
                    if v is not None and _present(v, passages) and not any(_present(v, own[sid]) for sid in near[2] if sid in own):
                        codes.append("PRICE_NOT_FROM_NAMED_SUPPLIER"); break          # (a price absent from every cited passage is UNSUPPORTED_NUMBER, reported above)
            if "entity" in R and not mentioned:
                sm = SUBJECT.match(text)
                if sm and not any(_norm(sm.group(1)) in nm or nm in _norm(sm.group(1)) for nm in aliases):
                    codes.append("UNKNOWN_ENTITY")
        # ---- comparative, absence and untrusted-source rules (each skipped when an evidence/identity code already rejected the claim, so one defect is reported once)
        if not ({"UNKNOWN_SUPPLIER", "WRONG_SOURCE", "UNKNOWN_EVIDENCE", "NO_EVIDENCE", "MALFORMED"} & set(codes)):
            if "source_directive" in R and any(directive_flags(p) for p in passages):
                codes.append("UNTRUSTED_SOURCE")                                  # the cited passage addresses the assistant; nothing resting on it is accepted
            if "comparative" in R:
                cmp_ = verify_comparative(text, directory, mentioned, [a for a in (_num(m) for m in AMOUNT.findall(text)) if a is not None], retrieved_supplier_ids, as_of)
                if cmp_ is not None:
                    # a price with no supplier is already UNATTRIBUTED_PRICE; the comparative rule speaks only when nothing else names the problem
                    if cmp_["verdict"] == "false":
                        codes.append("COMPARATIVE_FALSE")
                    elif cmp_["verdict"] == "unverifiable" and not ("UNATTRIBUTED_PRICE" in codes):
                        codes.append("COMPARATIVE_UNVERIFIABLE")
                    comparisons.append(dict(claim=text[:200], **cmp_))
            if "absence" in R:
                ab = classify_absence(text, directory, passages, sorted(mentioned))
                if ab is not None:
                    if ab["verdict"] == "contradicted":
                        codes.append("ABSENCE_CONTRADICTED")
                    elif ab["verdict"] == "overgeneral":
                        codes.append("ABSENCE_OVERGENERAL")
                    absences.append(dict(claim=text[:200], **ab))
        if "verification" in R and VERIFIED_WORDS.search(text):
            subjects = (mentioned or sup_of)
            if subjects and any(suppliers[i]["verification_status"] != "verified_public" for i in subjects):
                codes.append("UNSUPPORTED_VERIFICATION")
        if "recommendation" in R and RECOMMEND_WORDS.search(text):
            codes.append("UNSUPPORTED_RECOMMENDATION")
        codes = sorted(set(codes))
        if codes:
            rejected.append(dict(text=text[:120], codes=codes)); problems.extend(f"{k}: {text[:70]}" for k in codes)
            if CRITICAL & set(codes):
                report_codes += [k for k in codes if k in CRITICAL]
        else:
            accepted.append(dict(text=text, evidence_ids=ids))
    answer = report.get("answer", "") if isinstance(report, dict) else ""
    if "instruction" in R and INSTRUCTION_WORDS.search(answer):
        bad("INSTRUCTION_TEXT", "the answer text contains instruction-like content")
    if not report_codes and not rejected and not accepted:
        status = "abstained"                                                    # no claims and nothing wrong: the model declined to conclude, which is allowed
    elif report_codes or rejected:
        status = "rejected"
    else:
        status = "accepted"
    if status == "accepted" and not (report.get("limitations") if isinstance(report, dict) else None):
        flags.append("MODEL_OMITTED_LIMITATIONS")                                # quality flag: the computed uncertainty below is what is shown
    return dict(status=status, claims_accepted=accepted, claims_rejected=rejected, report_codes=sorted(set(report_codes)), tool_codes=sorted(set(tool_codes)), uncertainty=computed_uncertainty(directory, cited_suppliers), flags=flags,
                problems=problems, comparisons=comparisons, absences=absences)


RULES = frozenset({"shape", "tools", "instruction", "grounding", "numbers", "prices", "source", "supplier_names", "verification", "recommendation", "attribution", "price_binding", "entity", "comparative", "absence", "source_directive"})

# Providers that cost money. A local runtime (Ollama) and the offline heuristic are allowed; a paid hosted provider is refused unless a person sets NASHA_ALLOW_PAID_MODEL=1 for that process. No network call is made on refusal.
PAID_PROVIDERS = {"openai", "anthropic"}


def provider_permitted(provider, env):
    if provider in PAID_PROVIDERS and env.get("NASHA_ALLOW_PAID_MODEL") != "1":
        return False, f"provider '{provider}' is a paid hosted service; it needs explicit approval (NASHA_ALLOW_PAID_MODEL=1) and none was given"
    return True, None
