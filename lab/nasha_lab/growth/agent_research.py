"""Agent-assisted supplier research on the Production AI Agent Platform's REAL engine (planner -> hybrid retrieval over pgvector -> structured report with citations -> verification).

What is reused (installed package `agentplatform`, pin f8ba373): Container/AgentEngine, hybrid retrieval, the Report/Claim/Verification models, the provider abstraction, the tool registry (restricted here to the
READ tools search_corpus and calculator: no consequential tool exists in this registry, so the platform's own approval broker is never needed and there is no second approval path).
What it does NOT do: it never writes to Growth OS, never contacts anyone, and its output is research evidence, not a decision. Authorization for the one consequential write stays with THE WEIR.

Isolation: one agent database PER TENANT (physically separate corpora), created on demand through an administrative DSN that only the server configuration holds.
Honesty about models: the default provider is the platform's OFFLINE HEURISTIC (deterministic, extractive, NOT a language model). A real model provider is selectable by configuration but has NOT been exercised
in this repository's tests; the result's `mode` says which one ran. If the engine is unavailable or fails, callers fall back to a deterministic stored-data summary and the mode says so."""
import asyncio
import os
import re
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from . import model_boundary as MB

MODE_OFFLINE, MODE_MODEL, MODE_FALLBACK = "engine_offline_heuristic", "engine_model", "deterministic_fallback"
DOLLAR = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")


def env_seconds(name, default, lo=1.0, hi=3600.0):
    """A timeout in seconds from the environment, default unchanged when unset. A value that is not a number or lies outside [lo, hi] is an error, not a silent fallback: a timeout must never be changed (or ignored) by accident.
    The timeouts exist so a slow LOCAL model (a CPU-served 7B model can need minutes per call) is given the time it needs; they are never raised to hide a failure, and every run records which values applied."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        v = float(raw)
    except ValueError:
        raise AgentUnavailable(f"{name}={raw!r} is not a number of seconds", "bad_configuration") from None
    if not lo <= v <= hi:
        raise AgentUnavailable(f"{name}={v} is outside the allowed range {lo}..{hi} seconds", "bad_configuration")
    return v


class AgentUnavailable(Exception):
    def __init__(self, reason, failure_class="unavailable"):
        super().__init__(reason); self.reason, self.failure_class = reason, failure_class


def money(cents):
    return f"${cents / 100:,.2f}"


def supplier_documents(directory):
    """One markdown document per supplier, built from the tenant's stored supplier records: facts, verification status, freshness, products and prices WITH their price class and limitations."""
    docs = {}
    for s in directory:
        lines = [f"# {s['name']}", f"Category: {s['category']}. Service area: {s['service_area']}.",
                 f"Verification status: {s['verification_status'].replace('_', ' ')}. Data freshness: {s['freshness']}. Source kind: {s['source_kind'].replace('_', ' ')}."]
        if s.get("website_url"):
            lines.append(f"Official website: {s['website_url']}.")
        if s.get("notes"):
            lines.append(s["notes"])
        for p in s["products"]:
            if p["price_class"] == "NONE_PUBLISHED":
                lines.append(f"- {p['name']}: no published price. {p['limitation']}")
            else:
                lines.append(f"- {p['name']} ({p['ingredient_ref'] or 'item'}): {money(float(p['unit_price_cents']))} per {p['unit']}, {p['price_class'].replace('_', ' ').lower()}, lead time {p['lead_days']} days, minimum order {money(p['min_order_cents'] or 0)}. {p['limitation']}")
        docs[f"supplier-{s['id']}"] = (s["name"], "\n".join(lines) + "\n")
    return docs


def verify_claims(report, evidence, directory):
    """Independent check (separate from the platform's own verification): every cited evidence id exists, and every dollar amount in a claim appears in the cited passages AND equals a stored supplier price."""
    stored = set()
    for s in directory:
        for p in s["products"]:
            if p["unit_price_cents"] is not None:
                stored.add(f"{float(p['unit_price_cents']) / 100:,.2f}")
            if p.get("min_order_cents") is not None:
                stored.add(f"{float(p['min_order_cents']) / 100:,.2f}")
    problems = []
    if not isinstance(report, dict) or not isinstance(report.get("claims", []), list):
        return ["malformed report: not an object with a list of claims"]
    for c in report.get("claims", []):
        if not isinstance(c, dict) or not isinstance(c.get("text"), str) or not isinstance(c.get("evidence_ids", []), list):
            problems.append("malformed claim: not {text, evidence_ids[]}"); continue
        cited = [evidence[e]["text"] for e in c.get("evidence_ids", []) if e in evidence]
        if len(cited) != len(c.get("evidence_ids", [])):
            problems.append(f"claim cites an evidence id that does not exist: {c['text'][:60]}")
        for amt in DOLLAR.findall(c["text"]):
            norm = f"{float(amt.replace(',', '')):,.2f}"
            if not any(norm in t.replace("$ ", "$") or f"${norm}" in t for t in cited):
                problems.append(f"amount ${norm} is not in the cited passage")
            elif norm not in stored:
                problems.append(f"amount ${norm} does not match a stored supplier price")
    return problems


# The platform's retrieval uses a pgvector HNSW index (approximate; its graph is built with random level draws) and a GIN full-text index, and breaks score ties by whatever order the index returns. On this corpus (tens of
# short supplier records) that made the retrieved evidence, and so the agent's cited claims, differ between two independently built databases holding IDENTICAL documents (measured: 11, 12 and 13 passages over four
# fresh databases). Index scans are switched off for this agent database only, so the same query is answered by an exact scan; ties then follow the (deterministic) ingestion order. An exact scan is the right
# trade at this corpus size; a large corpus would need the index back, and with it a canonical re-ranking step.
EXACT_SEARCH = "-c enable_indexscan=off -c enable_bitmapscan=off -c enable_indexonlyscan=off"


def _tenant_dsn(admin_dsn, tenant):
    dbname = "agent_" + re.sub(r"[^a-z0-9]", "_", tenant.lower())[:40]
    with psycopg.connect(admin_dsn, autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,)).fetchone():
            c.execute(f'CREATE DATABASE "{dbname}"')
    d = conninfo_to_dict(admin_dsn); d["dbname"] = dbname
    d["options"] = EXACT_SEARCH
    return make_conninfo(**d)


class SupplierResearchAgent:
    """Per-tenant runner. `provider` is the platform provider name ('offline' by default). Build lazily; close() releases the pools."""

    def __init__(self, admin_dsn, tenant, work_dir, provider="offline"):
        self.admin_dsn, self.tenant, self.work_dir, self.provider = admin_dsn, tenant, Path(work_dir), provider
        self._c, self._ingested = None, None

    async def _container(self):
        if self._c is None:
            allowed, why = MB.provider_permitted(self.provider, os.environ)
            if not allowed:
                raise AgentUnavailable(why, "provider_not_permitted")        # refused before any settings, container or network call exists
            try:
                from agentplatform.config import Settings
                from agentplatform.container import Container
                from agentplatform.tools.base import ToolRegistry
                from agentplatform.tools.builtin import Calculator, SearchCorpus
            except ImportError as e:
                raise AgentUnavailable(f"the Production AI Agent Platform package is not installed ({e.name})") from e
            reg = ToolRegistry()
            for t in (SearchCorpus(), Calculator()):                  # READ tools only
                reg.register(t)
            self.work_dir.mkdir(parents=True, exist_ok=True)
            s = Settings(database_url=_tenant_dsn(self.admin_dsn, self.tenant), reports_dir=str(self.work_dir), default_provider=self.provider, provider_fallbacks=[] if self.provider != "offline" else ["offline"],
                         approval_timeout_s=5, tool_timeout_s=10, provider_timeout_s=env_seconds("NASHA_AGENT_PROVIDER_TIMEOUT_S", 60.0))
            self._c = await Container.build(s, registry=reg)
        return self._c

    async def run(self, docs, query, corpus_version):
        """One platform run. Returns (RunRecord, [events]) whatever the outcome, so a caller measuring a real model can inspect failures too.
        docs: {doc_id: (title, markdown)}."""
        from agentplatform.models import RunConstraints, RunRequest
        c = await self._container()
        if self._ingested != corpus_version:
            for doc_id, (title, text) in docs.items():
                await c.ingestor.ingest_text(doc_id, title, text, meta={"tenant": self.tenant})
            self._ingested = corpus_version
        rec = await c.engine.submit(RunRequest(query=query, provider=self.provider, constraints=RunConstraints(max_steps=4, require_approval_for="consequential")))
        await c.engine.wait(rec.id)
        return await c.repo.get_run(rec.id), list(await c.repo.events_after(rec.id, 0))

    async def research(self, docs, query, corpus_version):
        """Returns dict(mode, provider, run_id, report, verification, evidence{id: {...}}, tool_calls, usage, event_counts, models, failure_class). Raises AgentUnavailable unless the run completed."""
        from agentplatform.models import RunState
        rec, events = await self.run(docs, query, corpus_version)
        if rec.state is not RunState.COMPLETED or rec.report is None:
            raise AgentUnavailable(f"the agent run ended {rec.state.value}: {rec.error}", getattr(rec.failure_class, "value", "unknown"))
        evs, counts, models = {}, {}, []
        for e in events:
            counts[e.type] = counts.get(e.type, 0) + 1
            if e.type == "evidence.added":
                evs[e.data["id"]] = dict(doc_id=e.data["doc_id"], title=e.data["title"], text=e.data["text"])
            elif e.type == "usage.updated" and e.data.get("model") and e.data["model"] not in models:
                models.append(e.data["model"])
        return dict(mode=MODE_OFFLINE if self.provider == "offline" else MODE_MODEL, provider=rec.provider, run_id=rec.id, report=rec.report.model_dump(), verification=rec.verification.model_dump() if rec.verification else None,
                    evidence=evs, tool_calls=[dict(tool=t.tool, status=t.status) for t in rec.tool_calls], usage=rec.usage.model_dump(), event_counts=counts, models=models, failure_class=None)

    async def documents(self):
        """Doc ids currently indexed in THIS tenant's agent database (used to prove corpora are not shared)."""
        c = await self._container()
        return sorted(d["id"] if "id" in d else d["doc_id"] for d in await c.repo.list_documents())

    async def close(self):
        if self._c is not None:
            await self._c.close(); self._c = None


def deterministic_summary(directory, ingredient_names):
    """The fallback when no engine is available: a plain extraction of stored facts (no retrieval, no model), clearly labelled."""
    claims = []
    for s in directory:
        for p in s["products"]:
            if p["unit_price_cents"] is not None and p.get("ingredient_ref") in ingredient_names:
                claims.append(dict(text=f"{s['name']} quotes {p['name']} at {money(float(p['unit_price_cents']))} per {p['unit']} ({p['price_class']}).", evidence_ids=[]))
    return dict(mode=MODE_FALLBACK, provider="none", run_id=None, report=dict(title="Stored supplier data summary (no agent run)", answer=f"{len(claims)} quoted items were read directly from stored supplier records.", claims=claims,
                limitations=["No agent or model was used; this is a direct read of stored supplier data."]), verification=None, evidence={}, tool_calls=[], usage=None, event_counts={}, models=[], failure_class="fallback")
