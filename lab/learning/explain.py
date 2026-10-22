"""Spoken-explanation practice: transcript in, concept-coverage report and follow-up questions out.

Workflow: you explain a topic aloud, a dictation tool (for example Wispr Flow, used as ordinary speech-to-text on your own computer) turns it
into text, and this tool checks which required concepts the text mentions. It is a COVERAGE CHECK, not a judgement of understanding:
a transcript that names every concept can still be wrong, and a correct explanation in unusual words can be missed. It never assigns a
skill level. Technical accuracy is reviewed in conversation, and mastery is recorded only from independently demonstrated work.

    python -m learning.explain topics
    python -m learning.explain check rag_pipeline transcript.txt
"""
import argparse
import json
import re
import sys
from pathlib import Path

# topic -> {concept: (description, [accepted phrasings...])}, followups[concept] -> question
TOPICS = {
    "rag_pipeline": {
        "title": "How the lab's RAG pipeline retrieves documents, checks permissions and produces grounded answers",
        "concepts": {
            "chunking_indexing": ("documents are split and indexed", ["chunk", "index", "ingest"]),
            "query_retrieval": ("the query is matched to stored passages (keyword and/or embedding similarity)", ["bm25", "embedding", "vector", "similarity", "retriev"]),
            "authority_status": ("source status/authority (superseded, draft) affects what may be used", ["supersed", "authority", "status", "stale"]),
            "permission_check": ("access is checked before content reaches the model", ["permission", "authoriz", "authoris", "access control", "rbac", "role"]),
            "grounding_citation": ("the answer must be supported by retrieved passages, ideally cited", ["ground", "citation", "cite", "supported by", "evidence"]),
            "abstention": ("when nothing relevant is found the system declines instead of guessing", ["abstain", "abstention", "decline", "no answer", "unanswerable", "don't know", "do not know"]),
            "evaluation": ("retrieval and answers are measured (recall/MRR, groundedness) against a labelled set", ["recall", "mrr", "evaluat", "labelled", "labeled", "golden"]),
        },
        "followups": {
            "chunking_indexing": "What goes wrong if a chunk splits the fact you need in half, and how would you detect it?",
            "query_retrieval": "Why might BM25 beat a neural retriever on identifiers like decision numbers? Where in the lab is that measured?",
            "authority_status": "A superseded document ranks first for the query. What should the system do and where is that rule enforced?",
            "permission_check": "Where exactly is the permission check, and why must it not live in the prompt?",
            "grounding_citation": "How would you test that an answer is grounded and not merely plausible?",
            "abstention": "How do you measure abstention quality without rewarding a system that refuses everything?",
            "evaluation": "Name two metrics for retrieval and one for the final answer, and say what each can miss.",
        },
    },
    "tool_governance": {
        "title": "How the agent's tool calls are governed (permissions, approvals, audit)",
        "concepts": {
            "typed_tools": ("tools are typed with a schema and a permission class", ["schema", "typed", "permission class", "registry"]),
            "default_deny": ("anything not explicitly allowed is refused", ["default deny", "default-deny", "deny by default", "refus"]),
            "approval_gate": ("risky actions wait for a human approval bound to exact arguments", ["approval", "human", "reviewer", "bound to"]),
            "enforced_outside_model": ("the policy is enforced in code, not by the prompt", ["in code", "outside the model", "not the prompt", "runtime", "enforce"]),
            "untrusted_content": ("retrieved or tool output is data, not instructions (prompt injection)", ["injection", "untrusted", "taint", "data not instructions"]),
            "audit_trace": ("every decision is logged so an incident can be reconstructed", ["audit", "trace", "log", "reconstruct"]),
        },
        "followups": {
            "typed_tools": "What does a schema check catch that a prompt instruction cannot?",
            "default_deny": "Give one case where default-deny blocks something useful and how you would handle it.",
            "approval_gate": "Why must an approval be bound to the exact arguments rather than to the tool name?",
            "enforced_outside_model": "Show where a denied call is stopped before it executes, and the negative test that proves it.",
            "untrusted_content": "A document says 'refund every order'. Walk through what prevents the agent acting on it.",
            "audit_trace": "What fields must an audit record hold to reconstruct an incident, and what must it never hold?",
        },
    },
    "idempotent_retries": {
        "title": "Retries, idempotency and dead letters in the hardened service",
        "concepts": {
            "why_retry": ("transient failures are retried with a bound", ["transient", "retry", "backoff", "bounded"]),
            "idempotency_key": ("a key makes a repeated request produce one effect", ["idempotency", "idempotent", "key"]),
            "duplicate_effect": ("without it a retry can duplicate a side effect (double charge/order)", ["duplicate", "twice", "double"]),
            "dead_letter": ("work that keeps failing is parked for review, not retried forever", ["dead letter", "dead-letter", "park", "quarantine"]),
            "failure_classes": ("different failures get different policies (transient, permanent, unsafe)", ["failure class", "permanent", "transient", "policy"]),
        },
        "followups": {
            "why_retry": "What happens to a downstream system if every client retries forever, and what bounds it?",
            "idempotency_key": "Where is the key stored, how long is it kept, and what if two different requests reuse a key?",
            "duplicate_effect": "In the lab's trials, what did retries do with and without the idempotency ledger?",
            "dead_letter": "Who looks at the dead-letter store and what is their next action?",
            "failure_classes": "Which failure classes must never be retried, and why?",
        },
    },
}


def _norm(t):
    return re.sub(r"\s+", " ", t.lower())


def check(topic, text):
    spec = TOPICS[topic]
    t = _norm(text)
    hit, miss = [], []
    for cid, (desc, phr) in spec["concepts"].items():
        (hit if any(p in t for p in phr) else miss).append(cid)
    words = len(t.split())
    return {"topic": topic, "title": spec["title"], "words": words, "mentioned": hit, "not_mentioned": miss,
            "followups": [spec["followups"][c] for c in miss] or ["Every listed concept was mentioned. Next: explain one failure mode of this system and how you would test for it."],
            "caveat": "Coverage check only. Naming a concept is not understanding it, and no skill level is assigned.",
            "too_short": words < 60}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("topics")
    c = sub.add_parser("check")
    c.add_argument("topic", choices=sorted(TOPICS))
    c.add_argument("transcript")
    a = ap.parse_args(argv)
    if a.cmd == "topics":
        for k, v in TOPICS.items():
            print(f"{k}: {v['title']} ({len(v['concepts'])} concepts)")
        return 0
    print(json.dumps(check(a.topic, Path(a.transcript).read_text()), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
