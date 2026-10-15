# Case study: a human-supervised operations agent for synthetic business exceptions

> I built a human-supervised operations agent that investigates synthetic business exceptions using structured operational data and status-aware enterprise knowledge, then stops for approval before consequential action.

**Disclosure.** SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED. NASHA is an independent founder concept: there is no restaurant, no customer, no supplier and no sale. All numbers below come from deterministic synthetic scenarios and an author-written golden set, with the same person writing the system and the tests.

## Problem
An operations assistant that can read inventory, orders and policy is useful only if it (1) does not act on bad data, (2) does not treat a draft, superseded or unverified document as policy, (3) says "insufficient verified evidence" when that is true, and (4) cannot spend money or message a supplier. The domain adds a hard constraint: a founder's no-beef/no-pork rule (D-54) where "probably fine" is the wrong answer.

## What was built
Synthetic operations platform (block 1) -> status-aware knowledge layer over the real project documents (decision register, authority classes, supersession) -> 18 typed tools with five permission classes -> FastAPI and MCP surfaces -> LangGraph agent that proposes, interrupts for a human, resumes from a checkpoint, and records a full trace. Architecture and diagram: [AGENT.md](AGENT.md), [ARCHITECTURE.md](ARCHITECTURE.md). Reuse of earlier projects: [REUSE-AND-PROVENANCE.md](REUSE-AND-PROVENANCE.md).

## Results (reproducible: `python -m pytest`, `python -m nasha_lab.eval_*`)
- **133 tests pass, 2 documented expected failures**; CI runs the suite, re-computes the evaluations and builds the Docker image.
- **Retrieval, 6 methods compared** on 55 labelled questions: hybrid BM25+LSA best (Recall@5 0.88, MRR 0.79); hashing vectors rejected (MRR 0.43). Status filtering removes the 31-40% of top-5 results that were superseded, unverified, vision or historical (0 remain). Details: [RAG-EVALUATION.md](RAG-EVALUATION.md).
- **Agent, 18 scenario runs:** correct action and abstention 18/18; 0 unsupported claims of 48; 0 external actions; nothing consequential before approval 18/18.
- **Failure injection, 22 cases:** 20 passed first time; 2 failed (1 real defect, 1 wrong test expectation); 22/22 after the fix.

## The failure that mattered
With goat cover at 2.6 days against a 5-day supplier lead time, I injected a failure into the supplier-status tool. The agent's answer was `NO_ACTION`. It had not decided that nothing was wrong; its drafting branch simply needed a supplier list, did not get one, and fell through to the default. A silent all-clear on partial evidence is the dangerous failure of an operations agent, and the happy-path evaluation scored 18/18 without ever touching it. Fix: short cover with an unconfirmed supplier now escalates as `INSUFFICIENT VERIFIED EVIDENCE`, and `NO_ACTION` is impossible when any tool failed. Regression test: `test_supplier_lookup_failure_never_becomes_no_action`. Full log: [results/FAILURE-LOG.md](../results/FAILURE-LOG.md).

## Other decisions backed by measurement
- The decision register still listed D-59 ("NASHA is a candidate") as ACTIVE after D-62 selected the name. A retrieval layer that trusted the register would present a superseded decision as current; supersession is now derived from the `supersedes` field.
- A first answer layer responded to 7 of 10 unanswerable questions. Thresholds were tuned on a dev split only and checked on a held-out split; the remaining gap (5 of 10) is documented, pinned as expected-failure tests, and not hidden.
- The planner is deterministic, not a model, on purpose: it makes the approval boundary and evidence discipline measurable for free. A model can sit behind the same schema.
- SQLite instead of PostgreSQL/pgvector, and no Kubernetes/Kafka/multi-agent: 758 chunks and ~4,000 orders do not justify them. The storage boundary is kept so pgvector can replace the dense leg.

## Limitations (stated up front)
Synthetic data and same-author evaluation; the golden set is small (n=55); lexical abstention still answers some unanswerable questions; the injection detector is a regex; no neural embeddings (model download blocked in the authoring sandbox); no authentication on the API; Docker is verified in CI, not in the authoring sandbox (no daemon); the agent is rule-based and handles nine event shapes. None of this is evidence of results in a real business.

## Reproduce
`cd lab && pip install -r requirements.txt && python -m pytest -q tests` (verified in a clean virtualenv) and see the README for the evaluation, API, MCP and Docker commands.
