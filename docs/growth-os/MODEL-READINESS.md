# Real-model readiness: options, the smallest viable run, and the decision needed

Status: **no language model has run in this project.** This page prepares the first genuine run; it does not make one. Facts below were checked on 2026-10-24.

## What is checked in this sandbox
* 4 CPU cores, 15 GB RAM, no GPU, about 4.5 GB free disk. No Ollama or llama.cpp runtime; `localhost:11434` refuses.
* Outbound network: `huggingface.co`, `ollama.com`, `registry.ollama.ai` are refused by the environment's network policy; PyPI and GitHub are reachable. No weights can be downloaded here.
* Credentials: none for any model provider are configured; none were used. Paid providers are refused in code (`model_boundary.provider_permitted`) unless a person sets `NASHA_ALLOW_PAID_MODEL=1`.

## What the platform needs from a model (read from the pinned Production AI Agent Platform `f8ba373`)
* The `ollama` provider speaks the OpenAI-compatible `/chat/completions` API at `AP_OLLAMA_BASE_URL` (default `http://localhost:11434/v1`) with model `AP_OLLAMA_MODEL`, temperature 0 and `response_format: json_object`; the reply must validate as the platform's `Plan` and `Report` schemas, with one repair round-trip. Any server offering that API qualifies (Ollama, llama.cpp server, vLLM).
* Two structured calls per run (plan, then report over up to ~12 retrieved supplier passages): roughly 3-5k prompt tokens and under 1k completion tokens each.
* **One required code change before the first run:** `agent_research.SupplierResearchAgent` fixes `provider_timeout_s=60`. A CPU-served 7B model can need longer per call, and a timeout is recorded as a fallback, not as a model result. The change is to read the timeout from an environment variable; it touches gated source, so it belongs to the authorised step, not to this preparation.
* The model's output is never trusted: it crosses `model_boundary.review` (10 rules), the recommendation is recomputed from stored quotes, and an approval by a different person through THE WEIR is still required. A rejected or abstained output is a valid, recorded result.

## Options
| Option | Needs | Cost | Smallest model | Verdict |
|---|---|---|---|---|
| A. Ollama inside this sandbox | founder allows `ollama.com`, `registry.ollama.ai` (and its blob CDN) in the environment's network policy | free | `qwen2.5:3b-instruct` (~2 GB, ~2-6 tokens/s on 4 CPU cores) | possible but slow and disk-tight (4.5 GB free) |
| B. Approved remote Ollama / OpenAI-compatible endpoint | an endpoint URL, a model name and (if any) a key supplied by the founder; the sandbox must be allowed to reach it | whatever the endpoint costs; none if it is yours | any that returns valid JSON | fastest to try if you already run one |
| **C. Ollama on a GitHub-hosted runner** | **AUTHORISED (Phase 2).** One manual, read-only workflow, `.github/workflows/model-live.yml`, started by hand | free for public repositories (standard runner: 4 vCPU, 16 GB) | `qwen2.5:7b-instruct` (~4.7 GB; the 1.5B/7B/14B experiments in this repo ran on the same runner class) | **recommended**: no sandbox network change, no key, no paid usage, precedent in `model-eval.yml` |
| D. Paid hosted OpenAI-compatible API | a capped key and `NASHA_ALLOW_PAID_MODEL=1` set by a person | by token: about 100k prompt + 15k completion tokens for ~10 runs; at the platform's own editable estimate for `gpt-4o-mini` ($0.15 / $0.60 per 1M) that is about $0.02. Check current prices first. | n/a | only with explicit approval; not needed for a first run |
| E. Hugging Face Inference through the connected account | the founder's explicit approval to use that account's quota | account-dependent | n/a | not used; listed so it is not used by accident |

Smallest viable model: 1.5B models were measured in this repository on a different task (planner experiments) and are likely to miss the `Report` schema often; use 7B for the first run and report the schema-failure rate honestly. A 3B model is the floor for option A on this hardware.

## Validation procedure (what must be shown, unchanged from `MODEL-VALIDATION-PLAN.md`)
Real inference recorded (`live.json.executed = true`, mode `engine_model`, model id, latency, tokens, cost 0 for a local runtime); structured output through the boundary; every claim grounded in cited supplier passages; abstention on an unanswerable question; a prompt-injection note in a supplier record ignored; the recommendation hash equal to the deterministic one; approval only by a different person through THE WEIR; trace and audit rows recorded; tenant isolation between NASHA and Meridian; comparison with the deterministic fallback.

## Exact commands
* Option C: after the workflow is installed, `Actions -> model-live -> Run workflow` (model `qwen2.5:7b-instruct`). The workflow has `contents: read` only, so nothing is pushed: results are printed in the job log between `MODEL_LIVE_RESULT_BEGIN/END` and uploaded as the `model-live-evidence` artifact (battery result, Ollama version/tags/show, Ollama request log). The battery is `lab/tools/live_model_battery.py`; its output is separate from the scripted evaluation.
* Options A/B (any machine with a runtime): `NASHA_LIVE_MODEL_PROVIDER=ollama AP_OLLAMA_BASE_URL=<endpoint>/v1 AP_OLLAMA_MODEL=<model> python lab/tools/live_model_validation.py`.
* The release gate stays `REQUIRES_REVIEW` until `tests/test_growth_model_live.py` itself passes with a real model.

## Founder decision needed
Choose one: **C** (authorise adding and starting the manual workflow; free), **A** (allow the Ollama registry hosts for this environment), **B** (provide an endpoint), or **D** (approve a capped key). Nothing paid, and no network or workflow change, happens before that choice.
