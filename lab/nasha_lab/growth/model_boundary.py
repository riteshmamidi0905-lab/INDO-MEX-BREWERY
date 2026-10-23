"""The boundary every agent or model output must cross before Growth OS uses a word of it. Provider-independent: it validates the structured REPORT and the TOOL CALLS that come back from the Production AI Agent Platform
engine, whether the provider is the offline heuristic, a local model (Ollama) or any OpenAI-compatible endpoint. It never trusts the output and never lets it decide anything:
  * the recommendation (suppliers, quantities, costs) is computed from stored quotes and re-derived by `procurement.check_plan`; the model contributes cited research text only;
  * a report is `accepted` only if it is well-formed AND every claim is grounded; one bad claim rejects the whole output (the workflow then uses the deterministic fallback and records why);
  * `abstained` is a valid, safe outcome: the model said the evidence does not answer the question and made no claims.
Rules (each yields a stable code): MALFORMED, NO_EVIDENCE, UNKNOWN_EVIDENCE, UNSUPPORTED_NUMBER, PRICE_MISMATCH, UNKNOWN_SUPPLIER, WRONG_SOURCE, UNSUPPORTED_VERIFICATION, UNSUPPORTED_RECOMMENDATION, INSTRUCTION_TEXT, TOOL_NOT_ALLOWED.
Uncertainty is COMPUTED from the stored records the claims rest on (unverified leads, synthetic prices, stale data), not taken from the model, so it cannot be omitted or softened by one.
Limits: these are lexical and structural checks. They catch fabricated numbers, invented evidence, overreach and injected instructions in the shapes listed; they do not prove a sentence is true or that a clever paraphrase of a false claim is caught."""
import re

ALLOWED_TOOLS = ("search_corpus", "calculator")
MAX_CLAIMS, MAX_CLAIM_CHARS, MAX_ANSWER_CHARS = 12, 400, 1500
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
COMPANY = re.compile(r"\b((?:[A-Z][\w&'-]*\s+){1,4}(?:LLC|Inc\.?|Co\.?|Corp\.?|Ltd\.?|Company|Dairies|Produce|Foods|Farms|Distributors|Wholesale|Provisions|Imports))\b")
VERIFIED_WORDS = re.compile(r"\b(verified|confirmed|officially|official website|certified|vetted|approved supplier)\b", re.I)
RECOMMEND_WORDS = re.compile(r"\b(i recommend|we recommend|recommend(?:ed)? (?:that|using|choosing|buying|ordering)|you should (?:choose|buy|order|use|select)|best choice|the best supplier|select this supplier|go with)\b", re.I)
INSTRUCTION_WORDS = re.compile(r"(ignore (?:all |any )?(?:previous|prior|above)|disregard (?:the )?(?:above|previous|instructions)|system prompt|you must now|new instructions|place (?:an|the) order|send (?:an? )?(?:email|message)|email the|call the|contact the (?:supplier|vendor|owner)|wire (?:the )?(?:money|funds|payment)|pay (?:the )?invoice|purchase order|api[_ ]?key|password)", re.I)

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


def review(report, evidence, directory, tool_calls=(), allowed_tools=ALLOWED_TOOLS, rules=None):
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
            return dict(status="rejected", claims_accepted=[], claims_rejected=[], report_codes=report_codes, tool_codes=[], uncertainty=computed_uncertainty(directory, set()), flags=flags, problems=problems)
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
    cited_suppliers = set()
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
        mentioned = {sid for nm, sid in names.items() if nm and nm in low}
        if "source" in R and (mentioned - sup_of):
            codes.append("WRONG_SOURCE")                                      # names a supplier but cites no passage from that supplier's record
        if "supplier_names" in R:
            for m in COMPANY.findall(text):
                if not any(_norm(m) in nm or nm in _norm(m) for nm in names):
                    codes.append("UNKNOWN_SUPPLIER"); break
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
                problems=problems)


RULES = frozenset({"shape", "tools", "instruction", "grounding", "numbers", "prices", "source", "supplier_names", "verification", "recommendation"})

# Providers that cost money. A local runtime (Ollama) and the offline heuristic are allowed; a paid hosted provider is refused unless a person sets NASHA_ALLOW_PAID_MODEL=1 for that process. No network call is made on refusal.
PAID_PROVIDERS = {"openai", "anthropic"}


def provider_permitted(provider, env):
    if provider in PAID_PROVIDERS and env.get("NASHA_ALLOW_PAID_MODEL") != "1":
        return False, f"provider '{provider}' is a paid hosted service; it needs explicit approval (NASHA_ALLOW_PAID_MODEL=1) and none was given"
    return True, None
