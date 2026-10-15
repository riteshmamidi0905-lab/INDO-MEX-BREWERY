"""Status-aware NASHA knowledge retrieval.

INGESTION POLICY (not "index the repo"):
  * Decisions: one chunk per D-n, status/classification taken from tools/decision_register.py (reused, not re-implemented).
  * Documents: only paths with a known authority class: docs/company/data/document-map.csv (generated dashboards are EXCLUDED:
    they are derived from CSV sources), the D-54 dietary policy, docs/company/*.md, docs/decisions/*.md, research/*.md,
    vision/*.md. Excluded with a recorded reason: website/ (build output), visuals/prompts, send-packs, node_modules, CSV data.
  * Every chunk carries document_id, source_path, title, document_type, decision_status, verification_status,
    effective_status, authority_rank, updated_at (git commit date) and, where known, superseded_by.
RETRIEVAL: BM25 (A1), TF-IDF from rag-doc-qa (A0, reused), dense hashing vectors adapted from production-ai-agent-platform (B1),
dense LSA vectors (B2), hybrid RRF (C), status-aware re-rank (D). Neural embeddings were NOT available in the sandbox (model host returned 403).
ANSWERING: extractive, from AUTHORITATIVE current chunks only; otherwise abstain with "INSUFFICIENT VERIFIED EVIDENCE".
"""
import csv
import hashlib
import importlib.util
import math
import os
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ABSTAIN = "INSUFFICIENT VERIFIED EVIDENCE"

# effective_status values and how they may be used
CURRENT, FROZEN, PROVISIONAL = "CURRENT", "FROZEN", "PROVISIONAL"
PENDING, SUPERSEDED, HISTORICAL, VISION, UNVERIFIED, INTERNAL, SUPPORTING = "PENDING", "SUPERSEDED", "HISTORICAL", "VISION", "UNVERIFIED", "INTERNAL", "SUPPORTING"
AUTHORITATIVE = {CURRENT, FROZEN}                      # may support a policy answer
USABLE_WITH_CAVEAT = {PROVISIONAL, SUPPORTING}          # may be cited, always labelled
NOT_AUTHORITATIVE = {PENDING, SUPERSEDED, HISTORICAL, VISION, UNVERIFIED, INTERNAL}
AUTH_RANK = {CURRENT: 1, FROZEN: 1, PROVISIONAL: 3, SUPPORTING: 3, PENDING: 6, UNVERIFIED: 6, VISION: 7, HISTORICAL: 8, INTERNAL: 8, SUPERSEDED: 9}

MIN_COVER = 0.35   # minimum IDF-weighted question-term coverage for an authoritative chunk to support an answer (chosen on the dev split)
OOV_SHARE = 0.25   # abstain when this share of the question IDF mass is about terms the corpus never mentions (dev split)
DOMINANCE = 0.15
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9-])[$]?\d[\d,.]*(?![A-Za-z0-9-])")   # a real numeral, not an id such as H1 or V-26
DATE_ID_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\b[A-Za-z]-\d+\b|\bQ-?\d+\b")
QUANTITY_RE = re.compile(r"\bhow (many|much)\b|\b(price|cost|salary|revenue|number|percent|percentage)\b", re.I)
INJECTION_RE = re.compile(r"ignore (all |any )?(previous|prior|above)|disregard (the )?(policy|instructions)|system prompt|you (must|should) (now )?(approve|call|send|order|email)|as the (assistant|agent)|<\s*/?\s*(system|tool)|override (the )?(policy|rules)|new instructions", re.I)
STOP = set("a an and are as at be by for from has have in is it its of on or that the this to was were will with what which who whose how do does did can could should would we our us not no".split())
TOK_RE = re.compile(r"d-\d+|[a-z0-9]+")


def tokenize(text):
    out = []
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()   # consommé == consomme
    for t in TOK_RE.findall(text.lower()):
        if t in STOP: continue
        if not t.startswith("d-"):
            for suf in ("ing", "ly", "ed", "es", "s"):
                if len(t) > len(suf) + 3 and t.endswith(suf): t = t[:-len(suf)]; break
        out.append(t)
    return out


def _load_decision_register():
    spec = importlib.util.spec_from_file_location("decision_register", os.path.join(ROOT, "tools", "decision_register.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _git_date(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def decision_status(reg_status, classification):
    s, c = reg_status.upper(), classification.upper()
    if s.startswith("SUPERSEDED") or c.startswith("SUPERSEDED"): return SUPERSEDED, "SUPERSEDED"
    if c.startswith("FINDING") or s.startswith("FINDING"): return PENDING, "FINDING (not a decision)"
    if c.startswith("AGENT PROPOSED") and not s.startswith("PROVISIONALLY CONFIRMED"): return PENDING, "AGENT-PROPOSED"
    if s.startswith("PROVISIONALLY CONFIRMED") or "PROVISIONAL" in s or "PROVISIONAL" in c: return PROVISIONAL, "FOUNDER-PROVISIONAL"
    if s.startswith("FROZEN"): return FROZEN, "FOUNDER-CONFIRMED" if c.startswith("FOUNDER") else "FROZEN (threshold confirmation pending)"
    if c.startswith("FOUNDER"): return CURRENT, "FOUNDER-CONFIRMED"
    return CURRENT, "PROJECT-RECORDED (founder confirmation not stated)"


def doc_status(cls, path):
    c = cls.upper()
    if c.startswith("SUPERSEDED"): return SUPERSEDED, "SUPERSEDED"
    if c.startswith("HISTORICAL") or c.startswith("ARCHIVE"): return HISTORICAL, "HISTORICAL"
    if c.startswith("VISION") or "VISION LAYER" in c: return VISION, "VISION (not evidence)"
    if c.startswith("INTERNAL"): return INTERNAL, "INTERNAL"
    if c.startswith("CANONICAL"): return CURRENT, "CANONICAL per document map"
    if c.startswith("SUPPORTING"): return SUPPORTING, "SUPPORTING"
    return SUPPORTING, "SUPPORTING"


def chunk_markdown(text, title, max_chars=900):
    """Split at headings, then paragraphs; every chunk keeps its heading path."""
    chunks, path, buf = [], [], []
    def flush():
        body = "\n".join(buf).strip()
        if body:
            for i in range(0, len(body), max_chars * 2):
                part = body[i:i + max_chars * 2]
                # keep near-boundary sentences together: cut at the last paragraph/sentence break
                if i + max_chars * 2 < len(body):
                    cut = max(part.rfind("\n"), part.rfind(". "))
                    if cut > max_chars // 2: part = part[:cut + 1]
                chunks.append((" > ".join(path), part.strip()))
        buf.clear()
    for line in text.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            flush(); lvl = len(m.group(1)); path[:] = path[:lvl - 1] + [m.group(2).strip()]
        else:
            buf.append(line)
    flush()
    return chunks


def build_corpus(root=ROOT, extra_docs=None):
    """Return (chunks, manifest). extra_docs: list of dicts for tests (inject adversarial documents)."""
    reg = _load_decision_register()
    dec_text = open(os.path.join(root, "docs/decisions/DECISIONS.md"), encoding="utf-8").read()
    reg_rows = {r["id"]: r for r in reg.parse(dec_text)}
    chunks, manifest = [], {"included": [], "excluded": []}
    for line in dec_text.splitlines():
        m = reg.ROW.match(line)
        if not m or m.group(1) not in reg_rows: continue
        did, r = m.group(1), reg_rows[m.group(1)]
        eff, ver = decision_status(r["status"], r["classification"])
        text = re.sub(r"\*\*", "", " ".join(c.strip() for c in m.group(3).split("|") if c.strip()))
        chunks.append(dict(chunk_id=did, document_id=did, source_path="docs/decisions/DECISIONS.md", title=f"Decision {did}", document_type="DECISION", decision_status=r["status"], verification_status=ver,
                           effective_status=eff, authority_rank=AUTH_RANK[eff], updated_at=r["date"], supersedes=r["supersedes"], superseded_by=r["superseded_by"], heading="", text=f"{did} ({r['date']}). {text}"))
    manifest["included"].append(("docs/decisions/DECISIONS.md", "DECISION", len(reg_rows)))
    # supersession declared by a LATER decision ("supersedes": D-62 -> D-59) must demote the earlier one, even though the register still lists it ACTIVE
    byid = {c["document_id"]: c for c in chunks}
    for c in list(chunks):
        for old in filter(None, c["supersedes"].split("|")):
            if old in byid and old != c["document_id"]:
                byid[old].update(effective_status=SUPERSEDED, authority_rank=AUTH_RANK[SUPERSEDED], superseded_by=c["document_id"], verification_status="SUPERSEDED (derived from " + c["document_id"] + ")")

    docs = {}
    for r in csv.DictReader(open(os.path.join(root, "docs/company/data/document-map.csv"), encoding="utf-8")):
        p = r["path"]
        if "(generated)" in r["class"].lower():
            manifest["excluded"].append((p, "generated from CSV sources; index the sources instead")); continue
        if p.endswith("/") or "*" in p or not p.endswith(".md") or p == "docs/decisions/DECISIONS.md":
            manifest["excluded"].append((p, "not a single markdown file / indexed separately")); continue
        docs[p] = (r["class"], r["read_instead"])
    def add_glob(prefix_dir, cls):
        d = os.path.join(root, prefix_dir)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            p = f"{prefix_dir}/{f}"
            if f.endswith(".md") and p not in docs and p != "docs/decisions/DECISIONS.md": docs[p] = (cls, "")
    docs.setdefault("food/DIETARY-POLICY-AND-INGREDIENT-SPEC.md", ("CANONICAL", ""))      # the binding D-54 specification
    add_glob("docs/company", "SUPPORTING"); add_glob("docs/decisions", "SUPPORTING"); add_glob("food", "SUPPORTING")
    for p in ("research/CORE5-PRODUCT-SYSTEM.md",): docs[p] = ("CANONICAL", "")
    for f in sorted(os.listdir(os.path.join(root, "research"))):
        p = f"research/{f}"
        if f.endswith(".md") and p not in docs: docs[p] = ("UNVERIFIED RESEARCH", "")
    for f in sorted(os.listdir(os.path.join(root, "vision"))):
        p = f"vision/{f}"
        if f.endswith(".md") and p not in docs: docs[p] = ("VISION (not evidence)", "")
    rows = list(docs.items()) + [(d["source_path"], (d["class"], d.get("read_instead", ""))) for d in (extra_docs or [])]
    extra = {d["source_path"]: d["text"] for d in (extra_docs or [])}
    for p, (cls, read_instead) in rows:
        if p in extra: text = extra[p]
        else:
            fp = os.path.join(root, p)
            if not os.path.isfile(fp): manifest["excluded"].append((p, "listed but file missing")); continue
            text = open(fp, encoding="utf-8", errors="replace").read()
        if cls.upper().startswith("UNVERIFIED"): eff, ver = UNVERIFIED, "UNVERIFIED RESEARCH"
        else: eff, ver = doc_status(cls, p)
        t = re.search(r"^#\s+(.*)", text, re.M); title = t.group(1).strip() if t else os.path.basename(p)
        upd = _git_date(p) if p not in extra else "test"
        n = 0
        for i, (head, body) in enumerate(chunk_markdown(text, title)):
            if len(body) < 40: continue
            n += 1
            chunks.append(dict(chunk_id=f"{p}#{i}", document_id=p, source_path=p, title=title, document_type="DOCUMENT", decision_status=cls, verification_status=ver, effective_status=eff,
                               authority_rank=AUTH_RANK[eff], updated_at=upd, supersedes="", superseded_by=read_instead, heading=head, text=body))
        manifest["included"].append((p, cls, n))
    return chunks, manifest


# ---------------------------------------------------------------- retrievers
class BM25:
    name = "bm25"
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.ids = [c["chunk_id"] for c in chunks]
        self.docs = [tokenize(self._text(c)) for c in chunks]
        self.k1, self.b = k1, b
        self.avg = sum(map(len, self.docs)) / max(1, len(self.docs))
        df = Counter(t for d in self.docs for t in set(d)); n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + .5) / (f + .5)) for t, f in df.items()}
        self.tf = [Counter(d) for d in self.docs]
    @staticmethod
    def _text(c): return f'{c["title"]} {c.get("heading","")} {c["text"]}'
    def search(self, query, k=10):
        q = tokenize(query); sc = []
        for i, tf in enumerate(self.tf):
            s = 0.0; L = len(self.docs[i])
            for t in q:
                f = tf.get(t, 0)
                if f: s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * L / self.avg))
            sc.append(s)
        order = sorted(range(len(sc)), key=lambda i: -sc[i])[:k]
        return [(self.ids[i], sc[i]) for i in order if sc[i] > 0]


class TfidfBaseline:
    """A0: the TF-IDF index from the existing rag-doc-qa project, reused unmodified."""
    name = "tfidf_ragqa"
    def __init__(self, chunks):
        from ragqa.index import TfidfIndex
        self.ix = TfidfIndex()
        for c in chunks: self.ix.add(c["chunk_id"], BM25._text(c))
    def search(self, query, k=10): return [(i, s) for i, s in self.ix.search(query, top_k=k)]


class HashingDense:
    """B1: signed feature-hashing vectors (words + bigrams + char trigrams); adapted from production-ai-agent-platform/retrieval/embeddings.py."""
    name = "dense_hashing"
    def __init__(self, chunks, dim=512):
        self.dim = dim; self.ids = [c["chunk_id"] for c in chunks]
        self.m = [self._v(BM25._text(c)) for c in chunks]
    def _v(self, text):
        toks = tokenize(text); feats = list(toks) + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        low = text.lower(); feats += ["#" + low[i:i + 3] for i in range(max(0, len(low) - 2))]
        v = [0.0] * self.dim
        for f in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "little")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]
    def search(self, query, k=10):
        q = self._v(query)
        sc = [sum(a * b for a, b in zip(q, row)) for row in self.m]
        order = sorted(range(len(sc)), key=lambda i: -sc[i])[:k]
        return [(self.ids[i], sc[i]) for i in order if sc[i] > 0]


class LSADense:
    """B2: latent semantic analysis (TF-IDF -> truncated SVD). A dense vector model, NOT a neural embedding."""
    name = "dense_lsa"
    def __init__(self, chunks, dim=128):
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np
        self.np = np; self.ids = [c["chunk_id"] for c in chunks]
        self.vec = TfidfVectorizer(tokenizer=tokenize, lowercase=False, token_pattern=None, sublinear_tf=True)
        X = self.vec.fit_transform([BM25._text(c) for c in chunks])
        self.svd = TruncatedSVD(n_components=min(dim, X.shape[1] - 1, X.shape[0] - 1), random_state=0)
        Z = self.svd.fit_transform(X); n = np.linalg.norm(Z, axis=1, keepdims=True); n[n == 0] = 1
        self.Z = Z / n
    def search(self, query, k=10):
        q = self.svd.transform(self.vec.transform([query])); n = self.np.linalg.norm(q) or 1
        sc = self.Z @ (q[0] / n); order = self.np.argsort(-sc)[:k]
        return [(self.ids[i], float(sc[i])) for i in order if sc[i] > 0]


class Hybrid:
    """C: reciprocal-rank fusion (same fusion as production-ai-agent-platform) of BM25 and a dense retriever."""
    RRF_K = 60
    def __init__(self, a, b, name="hybrid_rrf"): self.a, self.b, self.name = a, b, name
    def search(self, query, k=10):
        f = defaultdict(float)
        for r in (self.a.search(query, 30), self.b.search(query, 30)):
            for rank, (cid, _s) in enumerate(r): f[cid] += 1 / (self.RRF_K + rank + 1)
        return sorted(f.items(), key=lambda x: -x[1])[:k]


class KnowledgeBase:
    def __init__(self, chunks, manifest=None, retriever="hybrid"):
        self.chunks = {c["chunk_id"]: c for c in chunks}; self.manifest = manifest or {}
        self.bm25 = BM25(chunks); self.lsa = LSADense(chunks); self._hash = None
        self.retrievers = {"tfidf": None, "hashing": None, "hybrid_hash": None, "bm25": self.bm25, "lsa": self.lsa, "hybrid": Hybrid(self.bm25, self.lsa)}
        self._chunks_list = chunks; self.default = retriever
    def add_retriever(self, name, obj, embedding_model=None):
        self.retrievers[name] = obj
        if embedding_model: self.embedding_model = embedding_model

    embedding_model = None

    def retriever(self, name):
        if name == "tfidf" and self.retrievers["tfidf"] is None: self.retrievers["tfidf"] = TfidfBaseline(self._chunks_list)
        if name in ("hashing", "hybrid_hash") and self._hash is None:
            self._hash = HashingDense(self._chunks_list); self.retrievers["hashing"] = self._hash; self.retrievers["hybrid_hash"] = Hybrid(self.bm25, self._hash)
        return self.retrievers[name]

    def search(self, query, k=5, retriever=None, status_aware=True, include_nonauthoritative=False, candidates=40):
        """status_aware: demote/ exclude by authority. Non-authoritative chunks are excluded unless include_nonauthoritative,
        in which case they are returned AFTER authoritative ones and labelled."""
        hits = self.retriever(retriever or self.default).search(query, candidates)
        out = []
        for cid, s in hits:
            c = self.chunks[cid]
            if status_aware and not include_nonauthoritative and c["effective_status"] in NOT_AUTHORITATIVE: continue
            out.append(dict(c, score=round(float(s), 4), injection_suspected=bool(INJECTION_RE.search(c["text"]))))
        if status_aware:
            out.sort(key=lambda h: (h["authority_rank"] > 3, -h["score"]))      # authoritative / caveated first, relevance second
        return out[:k]

    gate = None            # optional learned answerability gate (answerability.GateModel); None = built-in rules only

    def ask(self, question, k=4, retriever=None, min_score=None, use_gate=True):
        """Extractive, status-aware answer. Abstains when no authoritative chunk supports the question."""
        qt = set(tokenize(question))
        if self.gate is not None and use_gate:
            ok, p = self.gate.predict(self, question)
            if not ok: return dict(answer=ABSTAIN, abstained=True, reason=f"answerability gate: estimated answerability {p:.2f} is below the threshold {self.gate.tau:.2f}", citations=[], non_authoritative_matches=[], injection_flagged=[], gate_p=round(p, 3))
        raw = self.search(question, k=12, retriever=retriever, include_nonauthoritative=True)
        auth = [h for h in raw if h["effective_status"] in AUTHORITATIVE | USABLE_WITH_CAVEAT and not h["injection_suspected"]]
        flagged = [h["chunk_id"] for h in raw if h["injection_suspected"]]
        rejected = [dict(chunk_id=h["chunk_id"], effective_status=h["effective_status"]) for h in raw if h["effective_status"] in NOT_AUTHORITATIVE and h["chunk_id"] not in flagged]

        idf = self.bm25.idf; oov = max(idf.values())            # a question term the corpus has never seen counts as maximally informative
        weight = {t: idf.get(t, oov) for t in qt}; total = sum(weight.values()) or 1.0

        def cover(h):                                       # IDF-weighted fraction of question terms present in the chunk
            ct = set(tokenize(BM25._text(h)))
            return sum(w for t, w in weight.items() if t in ct) / total
        unknown = sorted(t for t in qt if t not in idf)            # terms the corpus has never mentioned
        if unknown and sum(weight[t] for t in unknown) / total >= OOV_SHARE:
            return dict(answer=ABSTAIN, abstained=True, reason="the question refers to terms absent from the NASHA corpus: " + ", ".join(unknown), citations=[], non_authoritative_matches=[], injection_flagged=flagged)
        for did in dict.fromkeys(re.findall(r"\bD-\d+\b", question)):       # an explicitly named decision decides the status answer
            c = self.chunks.get(did)
            if c and c["effective_status"] in NOT_AUTHORITATIVE:
                return dict(answer=ABSTAIN, abstained=True, reason=f"{did} has status {c['effective_status']} ({c['verification_status']}); it is not an authoritative current decision" + (f", superseded by {c['superseded_by']}" if c["superseded_by"] else ""),
                            citations=[], non_authoritative_matches=[dict(chunk_id=did, effective_status=c["effective_status"])], injection_flagged=flagged)
        # a question that is really ABOUT a non-authoritative source (a pending proposal, a superseded decision) must not be answered from a weaker authoritative neighbour
        nonauth = [h for h in raw if h["effective_status"] in NOT_AUTHORITATIVE and not h["injection_suspected"]]
        best_non = max(nonauth, key=cover, default=None)
        auth = [h for h in auth if cover(h) >= (min_score if min_score is not None else MIN_COVER)]
        best_auth_cover = max((cover(h) for h in auth), default=0.0)
        if best_non is not None and cover(best_non) >= MIN_COVER and cover(best_non) - best_auth_cover >= DOMINANCE:
            return dict(answer=ABSTAIN, abstained=True, reason=f"the best match is {best_non['document_id']}, status {best_non['effective_status']} ({best_non['verification_status']}), which is not an authoritative current source",
                        citations=[], non_authoritative_matches=[dict(chunk_id=best_non["chunk_id"], effective_status=best_non["effective_status"])], injection_flagged=flagged)
        if QUANTITY_RE.search(question):          # a "how many / what price" question needs a number in a sentence that actually matches the question
            def numeric_support(h):
                return any(len(qt & set(tokenize(x))) >= 2 and NUMBER_RE.search(DATE_ID_RE.sub("", x)) for x in re.split(r"(?<=[.!?])\s+", h["text"].replace("\n", " ")))
            auth = [h for h in auth if numeric_support(h)]
        auth.sort(key=lambda h: (h["authority_rank"], h["document_type"] != "DECISION", -cover(h), -h["score"]))
        auth = auth[:k]
        if not auth:
            why = "no authoritative current source covers the question"
            if rejected: why += "; only non-authoritative material matched (" + ", ".join(sorted({r["effective_status"] for r in rejected})) + ")"
            return dict(answer=ABSTAIN, abstained=True, reason=why, citations=[], non_authoritative_matches=rejected[:5], injection_flagged=flagged)
        sents = []
        for h in auth:
            for s in re.split(r"(?<=[.!?])\s+", h["text"].replace("\n", " ")):
                ov = len(qt & set(tokenize(s)))
                if ov: sents.append((ov, -h["authority_rank"], s.strip(), h))
        sents.sort(key=lambda x: (-x[0], -x[1]))
        chosen, used = [], set()
        for ov, _r, s, h in sents[:2]:
            if s not in used: used.add(s); chosen.append((s, h))
        answer = " ".join(s for s, _ in chosen) or auth[0]["text"][:300]
        cites = [dict(document_id=h["document_id"], chunk_id=h["chunk_id"], source_path=h["source_path"], effective_status=h["effective_status"], verification_status=h["verification_status"], score=h["score"]) for h in auth]
        notes = []
        if any(h["effective_status"] in USABLE_WITH_CAVEAT for h in auth): notes.append("includes PROVISIONAL or SUPPORTING material; not a final founder decision")
        if any(r["effective_status"] == SUPERSEDED for r in rejected): notes.append("a SUPERSEDED source also matched and was not used")
        return dict(answer=answer, answer_sentences=[s for s, _ in chosen], abstained=False, reason="", citations=cites, status_notes=notes, non_authoritative_matches=rejected[:5], injection_flagged=flagged)


_KB = {}
def default_kb():
    if "kb" not in _KB:
        ch, man = build_corpus(); _KB["kb"] = KnowledgeBase(ch, man)
        gp = os.path.join(ROOT, "lab", "eval", "answerability_gate.json")
        if os.environ.get("NASHA_GATE", "1") == "1" and os.path.exists(gp):
            from .answerability import GateModel
            _KB["kb"].gate = GateModel.load(gp)
    return _KB["kb"]
