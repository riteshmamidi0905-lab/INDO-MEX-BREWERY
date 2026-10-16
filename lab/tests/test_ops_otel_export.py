"""Optional OpenTelemetry export (Milestone 4). Skipped when the optional packages are absent. SYNTHETIC / OFFLINE."""
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("opentelemetry.sdk.trace"); pytest.importorskip("opentelemetry.exporter.otlp.proto.http")
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from nasha_lab.ops import faults as F, otel_export as O, runner as R


@pytest.fixture(scope="module")
def runs():
    out = []
    for sc in F.pool()[:3]: rec, ev, env = R.run_scenario(sc); out.append((rec, ev))
    return out


def test_default_is_off_and_imports_nothing():
    code = "import os,sys; os.environ.pop('NASHA_OTEL',None); import nasha_lab.ops.otel_export as o; assert o.maybe_export([]) is None; assert 'opentelemetry' not in sys.modules; print('ok')"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=".", env={**__import__('os').environ, "PYTHONPATH": "."}); assert r.stdout.strip() == "ok", r.stderr


def test_invalid_mode_is_rejected(runs):
    with pytest.raises(ValueError): O.maybe_export(runs, m="grpc")


def test_file_export_is_valid_otlp_json_with_hex_ids_and_parent_links(runs, tmp_path):
    assert O.maybe_export(runs, out_dir=str(tmp_path), m="file") == dict(mode="file", traces=3)
    spans = []
    for line in (tmp_path / "traces.jsonl").read_text().splitlines():
        d = json.loads(line); res = {a["key"]: a["value"]["stringValue"] for a in d["resourceSpans"][0]["resource"]["attributes"]}; assert res["service.name"] == "nasha-ops-lab" and "SYNTHETIC" in res["deployment.environment"]
        spans += d["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert all(len(s["traceId"]) == 32 and len(s["spanId"]) == 16 and int(s["traceId"], 16) for s in spans)          # hex, as OTLP/JSON requires
    roots = [s for s in spans if s["name"] == "agent.run"]; assert len(roots) == 3 and all("parentSpanId" not in s for s in roots)
    by_id = {s["spanId"]: s for s in spans}
    for s in spans:
        if s["name"] != "agent.run": p = by_id[s["parentSpanId"]]; assert p["name"] == "agent.run" and p["traceId"] == s["traceId"] and int(s["startTimeUnixNano"]) >= int(p["startTimeUnixNano"]) - 1_000_000
    assert any(s["name"].startswith("tool.") for s in spans) and any(s["name"].startswith("agent.node.") for s in spans)
    attrs = {a["key"]: a["value"] for a in roots[0]["attributes"]}; assert attrs["nasha.synthetic"]["boolValue"] is True and attrs["nasha.run_id"]["stringValue"].startswith("run-")


def test_export_is_deterministic_for_the_same_records(runs, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"; O.maybe_export(runs, out_dir=str(a), m="file"); O.maybe_export(runs, out_dir=str(b), m="file")
    assert (a / "traces.jsonl").read_text() == (b / "traces.jsonl").read_text()


def test_metrics_replay_the_registry_names_and_values(runs, tmp_path):
    O.maybe_export(runs, out_dir=str(tmp_path), m="file"); d = json.loads((tmp_path / "metrics.jsonl").read_text()); names = {m["name"]: m for sm in d["resourceMetrics"][0]["scopeMetrics"] for m in sm["metrics"]}
    assert {"nasha.agent.run.count", "nasha.agent.run.duration", "nasha.tool.call.count", "gen_ai.client.token.usage"} <= set(names)
    assert sum(int(p["asInt"]) for p in names["nasha.agent.run.count"]["sum"]["dataPoints"]) == 3 and names["nasha.agent.run.duration"]["histogram"]["dataPoints"][0]["count"]


class _Collector(BaseHTTPRequestHandler):
    got = []
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])); _Collector.got.append((self.path, self.headers["Content-Type"], body, self.headers.get("Content-Encoding"))); self.send_response(200); self.send_header("Content-Type", "application/x-protobuf"); self.end_headers(); self.wfile.write(b"")
    def log_message(self, *a): pass


def test_otlp_http_export_reaches_a_local_collector_stub(runs):
    srv = HTTPServer(("127.0.0.1", 0), _Collector); th = threading.Thread(target=srv.serve_forever, daemon=True); th.start(); _Collector.got.clear()
    try: assert O.maybe_export(runs, endpoint=f"http://127.0.0.1:{srv.server_port}", m="otlp")["traces"] == 3
    finally: srv.shutdown()
    paths = {p for p, *_ in _Collector.got}; assert paths == {"/v1/traces", "/v1/metrics"} and all(ct == "application/x-protobuf" for _, ct, _, _ in _Collector.got)
    import gzip
    dec = lambda b, enc: gzip.decompress(b) if enc == "gzip" else b
    tr = ExportTraceServiceRequest(); n = 0
    for p, _, b, enc in _Collector.got:
        if p == "/v1/traces": tr.ParseFromString(dec(b, enc)); n += sum(len(ss.spans) for rs in tr.resource_spans for ss in rs.scope_spans)
    assert n >= 3
    mt = [ExportMetricsServiceRequest.FromString(dec(b, enc)) for p, _, b, enc in _Collector.got if p == "/v1/metrics"]; assert mt and mt[0].resource_metrics


def test_console_export_runs(runs):
    assert O.maybe_export(runs, out_dir="silent", m="console")["traces"] == 3
