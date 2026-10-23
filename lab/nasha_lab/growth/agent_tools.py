"""Growth OS read tools on the Production AI Agent Platform's tool layer (smallest viable integration).

What is REUSED from the separate `agentplatform` package (pinned in docs/growth-os/AGENT-PLATFORM-INTEGRATION.md): its `Tool` / `ToolRegistry` / `Risk` / `ToolResult` contract and its `ToolExecutor`
(typed argument validation, per-call timeout, bounded retries, failure classification, metrics). What is NOT used: its planner/engine, providers, storage, retrieval, MCP server or approval broker.
Consequential actions are never registered here: they run through the governed workflow and THE WEIR (a second approval system would be a second authorization framework), and the executor is given a broker
that refuses to be used, so a tool wrongly registered as consequential would fail loudly instead of being approved somewhere else.
Every tool is tenant-bound: it is built around one GrowthService (one tenant, one authenticated user), so it can only see that tenant's rows (PostgreSQL row-level security applies underneath)."""
import asyncio
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from . import pricing as GP
from .service import Denied, GrowthService

try:
    from agentplatform.config import Settings
    from agentplatform.orchestrator.executor import ToolExecutor, ToolFailure
    from agentplatform.telemetry import Tracer
    from agentplatform.tools.base import Risk, Tool, ToolContext, ToolError, ToolRegistry, ToolResult
    AVAILABLE = True
except ImportError:                                    # pragma: no cover - the integration is optional; tests skip with an explicit reason
    AVAILABLE = False


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeadArgs(_Strict):
    lead_id: str = Field(pattern=r"^lead-[a-f0-9]{8,12}$")


class NoArgs(_Strict):
    pass


class ProductArgs(_Strict):
    product_id: str = Field(pattern=r"^prod-[a-f0-9]{8,12}$")


if AVAILABLE:
    class RefusingBroker:
        """Growth OS has ONE approval path (THE WEIR). If the executor ever asks for an approval here, fail instead of approving."""
        async def request(self, *a, **k):
            raise RuntimeError("approvals are not handled by this tool layer: use the governed workflow (THE WEIR)")

    def _svc(ctx) -> GrowthService:
        return ctx.extras["growth_service"]

    class GetLeadContext(Tool):
        name, description, args_model, risk = "get_lead_context", "Read one lead of the current tenant with consent/suppression status and recorded signals.", LeadArgs, Risk.READ

        async def run(self, args, ctx):
            try:
                c = _svc(ctx).get_lead_context(args.lead_id)
            except Denied as e:
                raise ToolError(str(e)) from e
            if c is None:
                raise ToolError("no such lead in this tenant")
            return ToolResult(text=f"lead {c['lead_id']} status={c['status']} consent={c['consent_status']} suppressed={c['suppressed']}", data=c)

    class PipelineSummary(Tool):
        name, description, args_model, risk = "pipeline_summary", "Count and total value of opportunities per stage for the current tenant.", NoArgs, Risk.READ

        async def run(self, args, ctx):
            rows = _svc(ctx).read("SELECT stage, count(*), coalesce(sum(amount_cents),0) FROM opportunities WHERE tenant_id=%s GROUP BY stage ORDER BY stage", (_svc(ctx).tenant,))
            data = {r[0]: dict(count=r[1], amount_cents=int(r[2])) for r in rows}
            return ToolResult(text="; ".join(f"{k}: {v['count']}" for k, v in data.items()) or "no opportunities", data=data)

    class PriceMargin(Tool):
        name, description, args_model, risk = "price_margin", "Current price, unit cost and gross margin of one product of the current tenant (planning-assumption costs).", ProductArgs, Risk.READ

        async def run(self, args, ctx):
            s = _svc(ctx)
            r = s.read("SELECT p.name, p.unit_cost_cents, pr.amount_cents FROM products p JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id AND pr.status='current' WHERE p.tenant_id=%s AND p.id=%s", (s.tenant, args.product_id))
            if not r:
                raise ToolError("no such product with a current price in this tenant")
            name, cost, price = r[0]
            return ToolResult(text=f"{name}: margin {GP.gross_margin(price, cost):.4f}", data=dict(name=name, price_cents=price, unit_cost_cents=cost, margin=GP.gross_margin(price, cost)))

    def build_registry() -> "ToolRegistry":
        reg = ToolRegistry()
        for t in (GetLeadContext(), PipelineSummary(), PriceMargin()):
            reg.register(t)
        assert all(t.risk is Risk.READ for t in reg._tools.values()), "no consequential tool may be registered on this layer"
        return reg

    class GrowthToolRuntime:
        """Runs Growth OS read tools through the agent platform's ToolExecutor for ONE tenant-bound service."""
        def __init__(self, svc: GrowthService, timeout_s=5.0, retries=0):
            self.svc, self.registry = svc, build_registry()
            self.settings = Settings(tool_timeout_s=timeout_s, tool_retries=retries)
            self.executor = ToolExecutor(self.registry, self.settings, RefusingBroker())
            self.events: list[tuple] = []

        async def _emit(self, kind, **kw):
            self.events.append((kind, kw))

        async def _call(self, name, args, run_id):
            ctx = ToolContext(run_id=run_id, retriever=None, settings=self.settings, extras={"growth_service": self.svc})
            return await self.executor.call(name, args, ctx, emit=self._emit, tracer=Tracer(), approval_mode="none")

        def call(self, name, args: dict, run_id="growth-run"):
            """-> (ToolResult, ToolCallRecord) or raises agentplatform's ToolFailure with a classified failure."""
            return asyncio.run(self._call(name, args, run_id))
