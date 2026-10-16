"""Optional OpenTelemetry export of the existing run records (Milestone 4). SYNTHETIC / OFFLINE. DEFAULT OFF, no hard dependency.
Gate: NASHA_OTEL = off (default/unset) | console | file | otlp.   file: OTLP/JSON lines under NASHA_OTEL_DIR (default results/ops/otel) that an OpenTelemetry Collector
`otlpjsonfile` receiver (or any OTLP/JSON consumer) can ingest. otlp: OTLP/HTTP protobuf to OTEL_EXPORTER_OTLP_ENDPOINT. console: the SDK console exporters.
Nothing in the lab imports this module unless asked, and `opentelemetry` is imported only when export is requested."""
import base64
import hashlib
import io
import json
import os
import random

from .util import RESULTS_DIR

MODES = ("off", "console", "file", "otlp")
SERVICE = "nasha-ops-lab"


def mode(): return (os.environ.get("NASHA_OTEL") or "off").lower()


def available():
    try:
        import opentelemetry.sdk.trace  # noqa: F401
        import opentelemetry.exporter.otlp.proto.http  # noqa: F401
        return True
    except Exception:
        return False


def _ns(t): return int(round(t * 1e9))


def _resource():
    from opentelemetry.sdk.resources import Resource
    return Resource.create({"service.name": SERVICE, "service.version": "ops-lab", "service.instance.id": "synthetic-lab", "deployment.environment": "SYNTHETIC-OFFLINE-NOT-PRODUCTION"})


class SeededIds:
    """Deterministic trace/span ids derived from the run id, so repeated exports of the same record are identical."""
    def __init__(self): self.rng = random.Random(0)
    def seed(self, key): self.rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))
    def generate_span_id(self): return self.rng.getrandbits(64) or 1
    def generate_trace_id(self): return self.rng.getrandbits(128) or 1


def _gen():
    from opentelemetry.sdk.trace.id_generator import IdGenerator
    class G(SeededIds, IdGenerator): pass
    return G()


class OtlpJsonFileSpanExporter:
    """SpanExporter writing one ExportTraceServiceRequest per line in OTLP/JSON (the collector's otlpjsonfile format)."""
    def __init__(self, path): self.path = path; os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "w").close()
    def export(self, spans):
        from google.protobuf.json_format import MessageToJson
        from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
        from opentelemetry.sdk.trace.export import SpanExportResult
        d = json.loads(MessageToJson(encode_spans(spans)))
        for rs in d["resourceSpans"]:
            for ss in rs["scopeSpans"]:
                for sp in ss["spans"]:
                    for k in ("traceId", "spanId", "parentSpanId"):
                        if k in sp: sp[k] = base64.b64decode(sp[k]).hex()          # OTLP/JSON carries ids as hex, protobuf-JSON as base64
        with open(self.path, "a", encoding="utf-8") as f: f.write(json.dumps(d, separators=(",", ":")) + "\n")
        return SpanExportResult.SUCCESS
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): return True


def span_exporter(m, out_dir=None, endpoint=None):
    if m == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        return ConsoleSpanExporter(out=io.StringIO()) if out_dir == "silent" else ConsoleSpanExporter()
    if m == "file": return OtlpJsonFileSpanExporter(os.path.join(out_dir or os.environ.get("NASHA_OTEL_DIR") or os.path.join(RESULTS_DIR, "otel"), "traces.jsonl"))
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    return OTLPSpanExporter(endpoint=(endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")).rstrip("/") + "/v1/traces")


def trace_runs(runs, exporter):
    """runs: iterable of (record, events). One trace per run: root `agent.run`, one child per graph node (`agent.node.*`) and one per tool call/error (`tool.*`)."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.trace import Status, StatusCode, set_span_in_context
    ids = _gen(); tp = TracerProvider(resource=_resource(), id_generator=ids); tp.add_span_processor(SimpleSpanProcessor(exporter)); tr = tp.get_tracer("nasha_lab.ops.otel_export")
    n = 0
    for rec, ev in runs:
        if not ev: continue
        ids.seed(rec["run_id"]); t0, t1 = ev[0]["ts"], ev[-1]["ts"]
        root = tr.start_span("agent.run", start_time=_ns(t0), attributes={"nasha.run_id": rec["run_id"], "nasha.event_id": rec["event_id"] or "", "nasha.family": rec["family"] or "", "nasha.outcome_category": rec["outcome_category"],
                                                                         "nasha.action": rec["action"] or "", "nasha.planner": rec["planner"]["type"] or "", "nasha.approval_state": rec["approval"]["state"], "nasha.mutations_executed": rec["safety"]["mutations_executed"],
                                                                         "nasha.external_actions": rec["safety"]["external_actions"], "nasha.synthetic": True})
        ctx = set_span_in_context(root); nodes = [e for e in ev if e["kind"] == "state" and e.get("node")]
        for i, e in enumerate(nodes):
            end = nodes[i + 1]["ts"] if i + 1 < len(nodes) else t1
            tr.start_span("agent.node." + e["node"].lower(), context=ctx, start_time=_ns(e["ts"]), attributes={"nasha.node": e["node"]}).end(end_time=_ns(max(end, e["ts"])))
        for e in ev:
            if e["kind"] not in ("tool_call", "tool_error"): continue
            ms = e.get("ms") or 0.0; ok = e["kind"] == "tool_call"
            sp = tr.start_span("tool." + str(e.get("tool")), context=ctx, start_time=_ns(e["ts"] - ms / 1000.0), attributes={"nasha.tool": str(e.get("tool")), "nasha.permission": str(e.get("permission")), "nasha.tool.ok": ok, **({} if ok else {"nasha.error_code": str(e.get("code"))})})
            if not ok: sp.set_status(Status(StatusCode.ERROR, str(e.get("code"))))
            sp.end(end_time=_ns(e["ts"]))
        if rec["outcome_category"] == "FAILED": root.set_status(Status(StatusCode.ERROR, "run failed"))
        root.end(end_time=_ns(t1)); n += 1
    tp.shutdown(); return n


class OtelRegistry:
    """Same add/set/record interface as telemetry.MetricsRegistry, backed by OpenTelemetry instruments, so `telemetry.observe(OtelRegistry(...), rec)` works unchanged."""
    def __init__(self, meter): self.m, self.i = meter, {}
    def _inst(self, kind, name, unit):
        k = (kind, name)
        if k not in self.i: self.i[k] = {"c": self.m.create_counter, "h": self.m.create_histogram, "g": self.m.create_gauge}[kind](name, unit=unit)
        return self.i[k]
    def add(self, name, value=1, unit="1", **attrs): self._inst("c", name, unit).add(value, {k: str(v) for k, v in attrs.items()})
    def record(self, name, value, unit="ms", **attrs): self._inst("h", name, unit).record(value, {k: str(v) for k, v in attrs.items()})
    def set(self, name, value, unit="1", **attrs): self._inst("g", name, unit).set(value, {k: str(v) for k, v in attrs.items()})


def metrics_from_records(records):
    """Returns OTel MetricsData built by replaying `telemetry.observe` over the run records."""
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from . import telemetry as TM
    rd = InMemoryMetricReader(); mp = MeterProvider(resource=_resource(), metric_readers=[rd]); reg = OtelRegistry(mp.get_meter("nasha_lab.ops.otel_export"))
    for r in records: TM.observe(reg, r)
    data = rd.get_metrics_data(); mp.shutdown(); return data


def export_metrics(data, m, out_dir=None, endpoint=None):
    if m == "file":
        from google.protobuf.json_format import MessageToJson
        from opentelemetry.exporter.otlp.proto.common.metrics_encoder import encode_metrics
        d = out_dir or os.environ.get("NASHA_OTEL_DIR") or os.path.join(RESULTS_DIR, "otel"); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "metrics.jsonl"), "w", encoding="utf-8") as f: f.write(json.dumps(json.loads(MessageToJson(encode_metrics(data))), separators=(",", ":")) + "\n")          # metrics carry no ids
    elif m == "console":
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
        ConsoleMetricExporter(out=io.StringIO() if out_dir == "silent" else __import__("sys").stdout).export(data)
    else:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        OTLPMetricExporter(endpoint=(endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")).rstrip("/") + "/v1/metrics").export(data)


def maybe_export(runs, out_dir=None, endpoint=None, m=None):
    """The one entry point. Returns None (and imports nothing) unless NASHA_OTEL selects a mode. runs: list of (record, events)."""
    m = m or mode()
    if m == "off": return None
    if m not in MODES: raise ValueError(f"NASHA_OTEL must be one of {MODES}")
    if not available(): raise RuntimeError("OpenTelemetry SDK/OTLP exporter not installed; see requirements-otel.txt (optional)")
    runs = list(runs); n = trace_runs(runs, span_exporter(m, out_dir, endpoint)); export_metrics(metrics_from_records([r for r, _ in runs]), m, out_dir, endpoint)
    return dict(mode=m, traces=n)
