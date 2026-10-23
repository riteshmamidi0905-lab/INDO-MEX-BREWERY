# Model-runtime test environment: investigation (D-90)

**Status: still BLOCKED / UNVERIFIED.** `lab/tests/test_llm_planner.py::test_real_local_model_integration_smoke` has not executed in this environment, so the release gate verdict stays `REQUIRES_REVIEW`. The gate was not weakened.

## What the test needs
A reachable Ollama-compatible endpoint (`NASHA_LLM_ENDPOINT`, `NASHA_LLM_MODEL`) that answers structured-output requests. The test is guarded by `llm.OllamaClient().available()`.

## Probes run from this session's container (2026-10-23)
| Target | Result |
|---|---|
| huggingface.co | no connection (000) |
| registry.ollama.ai, ollama.com | no connection (000) |
| github.com (anonymous) | HTTP 400 |
| pypi.org | HTTP 200 (package metadata reachable) |
| `pip download llama-cpp-python` | succeeded (source tarball only) |
| `ollama` or `llama-server` binary on PATH | not installed |

## Why this does not unblock the test
A runtime without weights cannot answer. Model weights are hosted on the blocked model hosts; no PyPI package I know of bundles a usable instruction-following model, and building `llama-cpp-python` from source would still need a model file. Substituting a stub or the repository's scripted client would make the test pass without testing a real model, which is exactly what the guard and the gate exist to prevent. The scripted-client tests (`test_ollama_client_over_http_and_full_run_through_it`, schema-retry and unavailable-model tests) keep running and are reported as what they are: client-protocol and failure-handling tests, not real-model evidence.

## Supported ways to execute it (any one clears the skip)
1. **GitHub Actions:** `.github/workflows/model-eval.yml` and `model-probe.yml` exist for a runner that can pull a small model. They have never run remotely; remote CI stays marked unverified until they do.
2. **A local machine with Ollama:** `ollama pull <small model>`, then `NASHA_LLM_ENDPOINT=http://127.0.0.1:11434 NASHA_LLM_MODEL=<model> python3 -m pytest lab/tests/test_llm_planner.py -k real_local -q`.
3. **An allow-listed network path** from this container to a model host, after which the same command works.

When it executes and passes, re-run `python3 lab/tools/release_gate.py collect` and `check`: the `integration_tests` gate moves from REQUIRES_REVIEW to PASS on its own, and the website's gate panel updates from the new report. Until then nothing in the repository or website claims a real-model result.
