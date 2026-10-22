# OpenTelemetry export (optional)

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.**

## Decision

The rule was: add OpenTelemetry only if it gives a real export or backend path, never for resume keywords. Investigation here: `pip` works through the proxy, and `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http` (1.45.1 installed here) install and run offline. That gives a genuine path, so a **small, optional, default-off** exporter was added: `nasha_lab/ops/otel_export.py`. The existing in-process `MetricsRegistry` is unchanged and remains the default; no new hard dependency (`requirements.txt` untouched; optional pins in `requirements-otel.txt`). Tests skip when the packages are absent.

## What it does

* Gate `NASHA_OTEL`: `off` (default; imports nothing), `console`, `file`, `otlp`.
* **Traces** from the existing run records plus their trace events: one trace per run (`agent.run`, with run id, family, outcome, action, planner, approval state, mutation and external-action counts), a child span per graph node (`agent.node.*`) and per tool call or tool error (`tool.*`, error status with the code). Trace and span ids are derived from the run id, so the same records export byte-identically.
* **Metrics** by replaying the existing `telemetry.observe` over the records through an OpenTelemetry-backed registry (`OtelRegistry`), so metric names match the in-process ones (`nasha.agent.run.count`, `nasha.agent.run.duration`, `nasha.tool.call.count`, `gen_ai.client.token.usage`, ...).
* `file` writes OTLP/JSON lines (`traces.jsonl`, `metrics.jsonl`, default dir `results/ops/otel`, not committed) in the format the OpenTelemetry Collector `otlpjsonfile` receiver reads; ids are converted to hex as OTLP/JSON requires. `otlp` posts OTLP/HTTP protobuf to `OTEL_EXPORTER_OTLP_ENDPOINT` (`/v1/traces`, `/v1/metrics`).

Use: `NASHA_OTEL=file python -c "from nasha_lab.ops import otel_export as O; ..."` with `runs = [(record, events), ...]` from `runner.run_scenario`.

## Verified and not verified

Verified by tests: default-off imports nothing; OTLP/JSON file has valid structure, hex ids, parent links, resource attributes; deterministic output; metrics replay run counts; OTLP/HTTP delivery to a local stub HTTP server that parses the protobuf (`ExportTraceServiceRequest` / `ExportMetricsServiceRequest`); console exporters run.

**Not verified**: ingestion by a real Collector, Jaeger, Tempo or any vendor backend (none is available here); the exact `otlpjsonfile` compatibility is by format, not by running a collector. Timing comes from the stored trace timestamps, so spans describe post-hoc records, not a live instrumented service. The lab's service itself is not instrumented and does not call this module.
