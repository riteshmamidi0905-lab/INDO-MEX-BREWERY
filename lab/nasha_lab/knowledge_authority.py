"""Knowledge authority rules v2 (wrapper; knowledge.py and tools.py are NOT edited). SYNTHETIC / OFFLINE.

v1 = the existing behaviour, passed through unchanged (`AuthorityKB(kb, "v1").ask(q) is kb.ask(q)`).
v2 adds, around the same `ask`:
  (a) EXCLUDED SOURCES SURFACED. The knowledge layer ranks authoritative chunks first and truncates the candidate list, so superseded / unverified / other
      non-authoritative sources that match the question are usually dropped before they can be reported. v2 re-scans a wide candidate list and lists every
      relevant excluded source (cover >= SURFACE_COVER) in `non_authoritative_matches` with kind="excluded_source".
  (b) STATUS AND AUTHORITY PRESERVED per source: document_id, source_path, effective_status, verification_status, decision_status (the registry class),
      authority_rank, tier (AUTHORITATIVE | CAVEATED | EXCLUDED), superseded_by, cover.
  (c) CONFLICT DETECTION by explicit rules (below) between sources that are relevant to the same question (cover >= CONFLICT_COVER).
  (d) ABSTAIN / ESCALATE: a conflict between two sources of the SAME tier that are both usable as authority (two AUTHORITATIVE, or two CAVEATED with no
      authoritative one) cannot be resolved by the status rules, so the answer is ABSTAIN with reason AUTHORITY_CONFLICT, no citation, both sources listed. A conflict
      across tiers is resolved by the existing status rule (authoritative > caveated > excluded) and is reported as resolved; the answer is unchanged.
  (e) TELEMETRY. Unresolved conflicts are entries kind="authority_conflict" in `non_authoritative_matches` (the one list that survives the tool's output schema); the
      ops layer counts them (retrieval.authority_conflicts) and alert rule AR-26 / class AUTHORITY_CONFLICT fires.

CONFLICT RULES (explicit, documented in docs/KNOWLEDGE-AUTHORITY.md; thresholds were fixed BEFORE any v2 trial was run and not changed afterwards)
  R1 polarity: two sentences from different documents conflict when one has PERMIT polarity and the other PROHIBIT polarity and they share >= 2 question
     terms (the same policy question). Polarity comes from regular expressions; a sentence matching both is MIXED and ignored.
  R2 numeric (ADVISORY, never blocks): two sentences from different documents that share >= 3 question terms and carry different sets of QUANTITIES (currency, percent, number + unit)
     are reported as conflict_type NUMERIC_DISAGREEMENT_ADVISORY with blocking=False. It is a heuristic with a high false-positive rate and must not abstain an answer.
"""
import re

from . import knowledge as K

RULES_VERSION = "authority-rules-v2"
REVISION = "v2.1"          # v2.0 (first run) had R2 on any numeral and no "do not serve" prohibition; see docs/KNOWLEDGE-AUTHORITY.md for the measured false conflicts that forced both changes
SURFACE_COVER = 0.20       # lower bar than the answer bar: listing an excluded source is informational, citing it is not
CONFLICT_COVER = K.MIN_COVER
MAX_SURFACED = 10
WIDE = 200

PROHIBIT_RE = re.compile(r"\b(?:not|never|no longer|cannot|can't|isn't|aren't)\s+(?:be\s+|been\s+)?(?:permitted|allowed|approved|acceptable|used|served|ok|okay)\b|\b(?:prohibit\w*|forbidden|banned|barred|disallow\w*|must not|may not|do not use|"
                         r"restrict\w*|excluded|rejected|(?:do|does|did|will|would|shall)\s+not\s+(?:serve|use|contain|include|add|allow|permit)|(?:don't|doesn't)\s+(?:serve|use|contain|include|add|allow))\b|\b(?:beef|pork)[\s-]+free\b|\bno\s+(?:commercial\s+|added\s+)?(?:beef|pork|lard|tallow|bacon|bases?|stock|bouillon|gelatin|derivatives?)\b", re.I)
PERMIT_RE = re.compile(r"\b(?:is|are|be|always|remains?|stays?)\s+(?:always\s+)?(?:permitted|allowed|approved|acceptable|fine|ok|okay)\b|\b(?:permitted|allowed)\b", re.I)
NUM_RE = re.compile(r"\$\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:%|percent\b|kg\b|lbs?\b|days?\b|weeks?\b|hours?\b|months?\b|usd\b|dollars?\b)", re.I)       # quantities only: currency, percent, number + unit. Enumerators, sprint/section numbers and ids are not quantities
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\bD-\d+\b|\b[A-Z]-\d+\b")


def polarity(sentence):
    p = bool(PROHIBIT_RE.search(sentence)); a = bool(PERMIT_RE.search(PROHIBIT_RE.sub(" ", sentence)))          # "not allowed" is a prohibition, not a permit plus a prohibition
    if p and a: return "MIXED"
    return "PROHIBIT" if p else ("PERMIT" if a else None)


def numerals(sentence): return set(x.lower().replace(" ", "").rstrip(".,") for x in NUM_RE.findall(DATE_RE.sub("", sentence)))


def tier(status):
    return "AUTHORITATIVE" if status in K.AUTHORITATIVE else ("CAVEATED" if status in K.USABLE_WITH_CAVEAT else "EXCLUDED")


def sentences(text): return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+|\|", text.replace("\n", " \n ")) if len(s.strip()) > 15]


_SENT = {}


def _analyse(text):
    """Per-chunk sentence analysis, independent of the question (cached: chunk text is immutable for a built corpus)."""
    r = _SENT.get(text)
    if r is None:
        r = _SENT[text] = [(s, set(K.tokenize(s)), polarity(s), numerals(s)) for s in sentences(text)]
        if len(_SENT) > 5000: _SENT.pop(next(iter(_SENT)))
    return r


def pair_conflicts(qt, a, b):
    """Rules R1/R2 between two chunks of DIFFERENT documents. Returns a list of {rule, a_sentence, b_sentence, shared}."""
    out = []
    for s1, k1, p1, n1 in _analyse(a["text"]):
        t1 = k1 & qt
        if not t1: continue
        for s2, k2, p2, n2 in _analyse(b["text"]):
            shared = t1 & k2
            if p1 and p2 and {p1, p2} == {"PERMIT", "PROHIBIT"} and len(shared) >= 2: out.append(dict(rule="R1_POLARITY", a_sentence=s1[:200], b_sentence=s2[:200], shared=sorted(shared)))
            elif len(shared) >= 3 and n1 and n2 and n1 != n2 and not (n1 & n2): out.append(dict(rule="R2_NUMERIC", a_sentence=s1[:200], b_sentence=s2[:200], shared=sorted(shared)))
    return out


def _src(h, cover):
    return dict(document_id=h["document_id"], chunk_id=h["chunk_id"], source_path=h["source_path"], effective_status=h["effective_status"], verification_status=h["verification_status"],
                decision_status=h["decision_status"], authority_rank=h["authority_rank"], tier=tier(h["effective_status"]), superseded_by=h.get("superseded_by") or "", cover=round(cover, 3))


class AuthorityKB:
    """Wrap a KnowledgeBase. rules="v1": pass-through. rules="v2": see module docstring. All other attributes delegate to the wrapped base."""
    def __init__(self, kb, rules="v2"):
        if rules not in ("v1", "v2"): raise ValueError("rules must be v1 or v2")
        self._kb, self.rules = kb, rules

    def __getattr__(self, name): return getattr(self._kb, name)

    def search(self, query, **kw): return self._kb.search(query, **kw)

    def _cover_fn(self, question):
        kb = self._kb; qt = set(K.tokenize(question)); idf = kb.bm25.idf; oov = max(idf.values()); weight = {t: idf.get(t, oov) for t in qt}; total = sum(weight.values()) or 1.0
        def cover(h):
            ct = set(K.tokenize(K.BM25._text(h))); return sum(w for t, w in weight.items() if t in ct) / total
        return qt, cover

    def scan(self, question, retriever=None):
        """Wide candidate scan -> (surfaced excluded sources, conflicts, sources considered). Pure function of the corpus and the question."""
        kb = self._kb; qt, cover = self._cover_fn(question)
        raw = kb.search(question, k=WIDE, retriever=retriever, include_nonauthoritative=True, candidates=WIDE)
        rel = [(h, cover(h)) for h in raw if not h["injection_suspected"]]
        surf = sorted([(h, c) for h, c in rel if tier(h["effective_status"]) == "EXCLUDED" and c >= SURFACE_COVER], key=lambda x: -x[1])
        seen, excluded = set(), []
        for h, c in surf:
            if h["document_id"] in seen: continue
            seen.add(h["document_id"]); excluded.append(dict(_src(h, c), kind="excluded_source"))
        pool = [(h, c) for h, c in rel if c >= (SURFACE_COVER if tier(h["effective_status"]) == "EXCLUDED" else CONFLICT_COVER)]
        conflicts = []
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                (a, ca), (b, cb) = pool[i], pool[j]
                if a["document_id"] == b["document_id"]: continue
                ta, tb = tier(a["effective_status"]), tier(b["effective_status"])
                if ta == "EXCLUDED" and tb == "EXCLUDED": continue
                hits = sorted(pair_conflicts(qt, a, b), key=lambda x: x["rule"])          # R1 before R2: a blocking finding is never masked by an advisory one
                if not hits: continue
                resolved = ta != tb
                advisory = hits[0]["rule"] == "R2_NUMERIC"
                winner = None if (not resolved or advisory) else (a if ["AUTHORITATIVE", "CAVEATED", "EXCLUDED"].index(ta) < ["AUTHORITATIVE", "CAVEATED", "EXCLUDED"].index(tb) else b)["document_id"]
                kind = ("NUMERIC_DISAGREEMENT_ADVISORY" if advisory else "SUPERSEDED_CONTRADICTS_CURRENT" if "SUPERSEDED" in (a["effective_status"], b["effective_status"]) and resolved else
                        "EXCLUDED_CONTRADICTS_CURRENT" if resolved and "EXCLUDED" in (ta, tb) else "LOWER_AUTHORITY_CONTRADICTS_HIGHER" if resolved else "UNRESOLVED_AUTHORITY_CONFLICT")
                conflicts.append(dict(kind="authority_conflict", conflict_type=kind, resolved=resolved or advisory, blocking=not (resolved or advisory), resolution=("ADVISORY_ONLY" if advisory else ("STATUS_RULE_" + winner) if resolved else "ABSTAIN_ESCALATE"), winner=winner, rule=hits[0]["rule"],
                                      sources=[_src(a, ca), _src(b, cb)], evidence=hits[0], effective_status="AUTHORITY_CONFLICT" if not (resolved or advisory) else "RESOLVED_CONFLICT", chunk_id=a["chunk_id"] + " <> " + b["chunk_id"]))
        return excluded[:MAX_SURFACED], conflicts

    def ask(self, question, **kw):
        base = self._kb.ask(question, **kw)
        if self.rules == "v1": return base
        excluded, conflicts = self.scan(question, kw.get("retriever"))
        res = dict(base, authority_rules=RULES_VERSION)
        unresolved = [c for c in conflicts if c["blocking"]]
        resolved = [c for c in conflicts if not c["blocking"]]
        # keep v1's own entries (id/status) only where v2 did not already list that document
        listed = {e["document_id"] for e in excluded}
        legacy = [dict(m, kind="excluded_source") for m in base.get("non_authoritative_matches", []) if str(m.get("chunk_id", "")).split("#")[0] not in listed]
        res["non_authoritative_matches"] = excluded + legacy + unresolved + resolved
        notes = list(base.get("status_notes", []))
        for c in [x for x in resolved if x["conflict_type"] != "NUMERIC_DISAGREEMENT_ADVISORY"]: notes.append(f"{c['conflict_type']}: {c['sources'][0]['document_id']} and {c['sources'][1]['document_id']} disagree; {c['winner']} governs by status")
        if unresolved:
            u = unresolved[0]; docs = sorted({s["document_id"] for c in unresolved for s in c["sources"]})
            res.update(answer=K.ABSTAIN, abstained=True, citations=[], answer_sentences=[], authority_escalation=True,
                       reason="AUTHORITY_CONFLICT: " + " vs ".join(s["document_id"] + f" ({s['effective_status']})" for s in u["sources"]) + f" give contradictory answers (rule {u['rule']}); the status rules cannot resolve it. All conflicting sources: {', '.join(docs)}. Escalate to the decision owner.")
        if notes: res["status_notes"] = notes
        return res
