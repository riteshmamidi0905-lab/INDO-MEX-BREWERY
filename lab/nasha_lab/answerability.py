"""Abstention as an engineering problem: features of (question, retrieval) -> answerable?  Strategies compared on the dev split, reported on held-out.
Labels: should_answer = not must_abstain (questions whose correct behaviour is to answer from an authoritative source). Not tuned per question."""
import math
import re
from collections import defaultdict

import numpy as np

from . import knowledge as K

FEATURES = ["top1_cover", "rare_cover", "oov_share", "bm25_norm", "margin", "dense_top", "auth_top", "nonauth_gap", "n_support", "qlen", "has_id", "id_unknown", "quant", "num_support"]


def features(kb, q):
    qt = [t for t in dict.fromkeys(K.tokenize(q))]; idf = kb.bm25.idf; oov = max(idf.values())
    w = {t: idf.get(t, oov) for t in qt}; tot = sum(w.values()) or 1.0
    med = float(np.median(list(idf.values()))); rare = {t for t in qt if w[t] >= med}; rare_tot = sum(w[t] for t in rare) or 1.0
    hits = kb.bm25.search(q, 12); top = hits[0][1] if hits else 0.0; second = hits[1][1] if len(hits) > 1 else 0.0
    in_vocab = sum(idf[t] for t in qt if t in idf) or 1.0
    ids = re.findall(r"\bD-\d+\b", q)
    best_auth = best_non = 0.0; nsup = 0; num = 0
    for cid, _ in hits:
        c = kb.chunks[cid]; ct = set(K.tokenize(K.BM25._text(c))); cov = sum(w[t] for t in qt if t in ct) / tot
        if c["effective_status"] in K.AUTHORITATIVE | K.USABLE_WITH_CAVEAT:
            best_auth = max(best_auth, cov); nsup += cov >= 0.5
        else: best_non = max(best_non, cov)
    cov_top = 0.0; rare_cov = 0.0
    if hits:
        c = kb.chunks[hits[0][0]]; ct = set(K.tokenize(K.BM25._text(c))); cov_top = sum(w[t] for t in qt if t in ct) / tot; rare_cov = sum(w[t] for t in rare if t in ct) / rare_tot
    qty = bool(K.QUANTITY_RE.search(q))
    if qty:
        for cid, _ in hits[:6]:
            for sent in re.split(r"(?<=[.!?])\s+", kb.chunks[cid]["text"].replace("\n", " ")):
                if len(set(K.tokenize(q)) & set(K.tokenize(sent))) >= 2 and K.NUMBER_RE.search(K.DATE_ID_RE.sub("", sent)): num = 1
    dense = kb.lsa.search(q, 1); dense_top = dense[0][1] if dense else 0.0
    return dict(top1_cover=cov_top, rare_cover=rare_cov, oov_share=sum(w[t] for t in qt if t not in idf) / tot, bm25_norm=top / in_vocab, margin=(top - second) / in_vocab, dense_top=dense_top,
                auth_top=best_auth, nonauth_gap=best_non - best_auth, n_support=float(nsup), qlen=float(len(qt)), has_id=float(bool(ids)), id_unknown=float(any(i not in kb.chunks for i in ids)), quant=float(qty), num_support=float(num))


def vec(f): return [f[k] for k in FEATURES]


def best_threshold(scores, labels, fp_cost=2.0):
    """Pick tau maximising (TPR - fp_cost*FPR-weighted) on dev: answers when score >= tau. Cost-weighted because answering an unanswerable question is worse than refusing."""
    best = (-9, 0.0)
    cand = sorted(set(scores))
    pos = sum(labels); neg = len(labels) - pos
    for t in cand + [max(cand) + 1e-9]:
        tp = sum(1 for s, y in zip(scores, labels) if s >= t and y); fp = sum(1 for s, y in zip(scores, labels) if s >= t and not y)
        u = tp / max(1, pos) - fp_cost * fp / max(1, neg)
        if u > best[0]: best = (u, t)
    return best[1]


class Strategy:
    name = ""
    def fit(self, X, y, rows): return self
    def predict(self, f, kb=None, q=None): raise NotImplementedError


class Builtin(Strategy):
    name = "S0 built-in rules (coverage + OOV + numeric)"
    def predict(self, f, kb=None, q=None): return not kb.ask(q, use_gate=False)["abstained"]


class Threshold(Strategy):
    def __init__(self, key, label): self.key, self.name = key, label
    def fit(self, X, y, rows): self.tau = best_threshold([x[self.key] for x in X], y); return self
    def predict(self, f, kb=None, q=None): return f[self.key] >= self.tau


class AuthorityOnly(Strategy):
    name = "S4 authority rule (authoritative evidence present, no dominating non-authoritative match)"
    def fit(self, X, y, rows): self.tau = best_threshold([x["auth_top"] - max(0, x["nonauth_gap"]) for x in X], y); return self
    def predict(self, f, kb=None, q=None): return f["auth_top"] - max(0, f["nonauth_gap"]) >= self.tau


class RuleCombo(Strategy):
    name = "S5 combined rule (OOV, rare-term coverage, authority; thresholds grid-searched on dev)"
    def fit(self, X, y, rows):
        best = (-9, None)
        for o in (0.05, 0.15, 0.3, 0.5):
            for r in (0.3, 0.5, 0.7, 0.9):
                for a in (0.2, 0.35, 0.5):
                    pred = [x["oov_share"] < o and x["rare_cover"] >= r and x["auth_top"] >= a for x in X]
                    tp = sum(p and t for p, t in zip(pred, y)); fp = sum(p and not t for p, t in zip(pred, y)); pos = sum(y); neg = len(y) - pos
                    u = tp / max(1, pos) - 2.0 * fp / max(1, neg)
                    if u > best[0]: best = (u, (o, r, a))
        self.o, self.r, self.a = best[1]; return self
    def predict(self, f, kb=None, q=None): return f["oov_share"] < self.o and f["rare_cover"] >= self.r and f["auth_top"] >= self.a


class Logistic(Strategy):
    """Hyper-parameters chosen by 5-fold CROSS-VALIDATION ON THE DEV SPLIT ONLY, maximising the mean of per-source accuracy (hand-written paraphrases weigh 3x because
    the generated templates are lexically close to their sources and a gate trained on them alone over-refuses paraphrases: see docs/RETRIEVAL-EVALUATION.md)."""
    name = "S6 logistic regression on retrieval features (fit on dev)"
    W_HAND, FP_COST = 3.0, 1.0
    def fit(self, X, y, rows):
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        M = np.array([vec(x) for x in X]); self.sc = StandardScaler().fit(M)
        w = np.array([self.W_HAND if r.get("source") == "handwritten" else 1.0 for r in rows])
        self.clf = LogisticRegression(C=1.0, class_weight={0: self.FP_COST, 1: 1.0}, max_iter=2000).fit(self.sc.transform(M), y, sample_weight=w)
        p = self.clf.predict_proba(self.sc.transform(M))[:, 1]; self.tau = best_threshold(list(p), y, fp_cost=self.FP_COST); return self
    def predict(self, f, kb=None, q=None): return self.clf.predict_proba(self.sc.transform([vec(f)]))[0, 1] >= self.tau


class Ensemble(Strategy):
    name = "S7 ensemble: S0 AND S6 (answer only if both agree)"
    def __init__(self, a, b): self.a, self.b = a, b
    def predict(self, f, kb=None, q=None): return self.a.predict(f, kb, q) and self.b.predict(f, kb, q)


def evaluate(kb, rows, strategies):
    dev = [r for r in rows if r["split"] == "dev"]; held = [r for r in rows if r["split"] == "heldout"]
    F = {r["id"]: features(kb, r["question"]) for r in rows}
    y = lambda rs: [not r["must_abstain"] for r in rs]
    for s in strategies:
        if not isinstance(s, Ensemble): s.fit([F[r["id"]] for r in dev], y(dev), dev)
    out = {}
    for s in strategies:
        out[s.name] = {}
        for label, rs in (("dev", dev), ("heldout", held), ("all", rows)):
            pred = {r["id"]: bool(s.predict(F[r["id"]], kb, r["question"])) for r in rs}
            ans = [r for r in rs if not r["must_abstain"]]; una = [r for r in rs if r["must_abstain"]]
            fa = sum(pred[r["id"]] for r in una); miss = sum(not pred[r["id"]] for r in ans)
            cats = defaultdict(lambda: [0, 0])
            for r in rs: cats[r["category"]][0] += pred[r["id"]] != (not r["must_abstain"]); cats[r["category"]][1] += 1
            out[s.name][label] = dict(n=len(rs), accuracy=round(1 - (fa + miss) / len(rs), 3), false_answer_rate=round(fa / max(1, len(una)), 3), false_answer=f"{fa}/{len(una)}", false_abstain_rate=round(miss / max(1, len(ans)), 3), false_abstain=f"{miss}/{len(ans)}",
                                      error_by_category={c: f"{v[0]}/{v[1]}" for c, v in sorted(cats.items()) if v[0]})
    return out


def default_strategies():
    s6 = Logistic()
    return [Builtin(), Threshold("bm25_norm", "S1 BM25 score threshold (normalised)"), Threshold("top1_cover", "S2 evidence coverage threshold"), Threshold("rare_cover", "S3 rare-term coverage threshold"), AuthorityOnly(), RuleCombo(), s6, Ensemble(Builtin(), s6)]


class GateModel:
    """The shipped answerability gate: S6 logistic regression, trained on the DEV split only, stored as plain JSON (no pickle)."""
    PATH = None

    def __init__(self, mean, scale, coef, intercept, tau, trained_on):
        self.mean, self.scale, self.coef = (np.array(x) for x in (mean, scale, coef)); self.intercept, self.tau, self.trained_on = intercept, tau, trained_on

    @classmethod
    def from_strategy(cls, s, n): return cls(s.sc.mean_.tolist(), s.sc.scale_.tolist(), s.clf.coef_[0].tolist(), float(s.clf.intercept_[0]), float(s.tau), n)

    def prob(self, f):
        z = (np.array(vec(f)) - self.mean) / np.where(self.scale == 0, 1, self.scale); return float(1 / (1 + math.exp(-(float(z @ self.coef) + self.intercept))))

    def predict(self, kb, q):
        p = self.prob(features(kb, q)); return p >= self.tau, p

    def save(self, path):
        import json
        json.dump(dict(features=FEATURES, mean=self.mean.tolist(), scale=self.scale.tolist(), coef=self.coef.tolist(), intercept=self.intercept, tau=self.tau, trained_on=self.trained_on, note="S6 logistic regression, fit on dev split only"), open(path, "w"), indent=1)

    @classmethod
    def load(cls, path):
        import json
        d = json.load(open(path)); assert d["features"] == FEATURES, "feature list changed: retrain the gate"
        return cls(d["mean"], d["scale"], d["coef"], d["intercept"], d["tau"], d["trained_on"])


def train_and_save(kb, rows, path):
    dev = [r for r in rows if r["split"] == "dev"]; s = Logistic().fit([features(kb, r["question"]) for r in dev], [not r["must_abstain"] for r in dev], dev)
    g = GateModel.from_strategy(s, f"dev split, n={len(dev)}"); g.save(path); return g
