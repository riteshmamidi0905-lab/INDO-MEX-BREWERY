# Growth OS and the Production AI Agent Platform

Pin: `production-ai-agent-platform` f8ba373, installed editable (`pip install -e <repo> --no-deps`). Not vendored.

## What is genuinely integrated (Milestone 3)
`lab/nasha_lab/growth/agent_research.py` runs the platform's REAL engine (`Container` / `AgentEngine`): planner -> hybrid retrieval over pgvector -> structured `Report` with cited `Claim`s -> the platform's own verification. It is used for ONE agent-assisted workflow: **supplier research brief -> evidence -> independent verification -> deterministic recommendation -> THE WEIR hold -> human review** (`launch_workflow.py`).

* Tools: only `search_corpus` and `calculator` (READ). No consequential tool is registered, so the platform's approval broker is never involved and no second approval path exists. Authorization of the one write stays with THE WEIR.
* Corpus: one markdown document per supplier built from the tenant's stored records (status, freshness, products, price class, limitations).
* Isolation: one agent database PER TENANT (physically separate corpora), created through an administrative DSN held by server configuration; a test proves the corpora are disjoint.
* The agent never writes to Growth OS and never decides: every number in the recommendation is computed from stored quotes and re-derived by separate arithmetic; agent claims are checked (cited evidence exists; every dollar figure equals a stored supplier price) and discarded if they fail.
* Fallback: if the engine is unavailable, times out, errors or fails verification, a deterministic stored-data summary is used and the run records `deterministic_fallback` and why. Tested (same recommendation hash with the agent, a scripted agent, or none).

## What ran, and what did not
* Ran in tests: the engine with its **offline heuristic provider** (deterministic, extractive; NOT a language model), real PostgreSQL + pgvector, real THE WEIR.
* Scripted doubles (not models) test failure modes: unavailable agent, fabricated claim.
* **Not run:** any real language-model provider (OpenAI-compatible, Anthropic, Ollama). They are selectable by configuration (`agent_provider`) but untested here; the result's `mode` field says `engine_model` when one is used. No model-backed claim is made. The release gate therefore stays REQUIRES_REVIEW.

## Still not integrated
The platform's evaluation harness, observability stack, MCP layer and its own approval broker are not used by Growth OS. The lead-qualification workflow is deterministic rules and does not run on the engine. Read-only tools from Milestone 2 (`agent_tools.py`) remain.
