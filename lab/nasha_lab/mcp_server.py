"""MCP server: a SMALL read/analyze/draft tool surface over the NASHA lab. No SQL, no filesystem, no shell, no mutation, no external action.
Mutating tools exist only behind the agent's human-approval gate and are NOT exposed here. Every call runs through tools.execute (typed
validation, permission check, timeout, output validation) and is traced."""
import uuid
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from . import tools as T

MCP_TOOLS = ("query_inventory", "assess_inventory_risk", "get_quality_finding", "get_lineage", "get_open_purchase_orders", "get_supplier_status",
             "search_nasha_knowledge", "get_current_policy", "draft_purchase_recommendation")


def build_server(world, kb, store=None):
    srv = MCPServer("nasha-lab")

    def run(name, **args):
        run_id = "mcp-" + uuid.uuid4().hex[:8]
        ctx = T.ToolContext(run_id=run_id, request_id=run_id, kb=kb, trace=store.trace(run_id, run_id) if store else None)
        return T.execute(world, name, {k: v for k, v in args.items() if v is not None}, ctx)

    def desc(n): return f"[{T.TOOLS[n].permission}] {T.TOOLS[n].description} SYNTHETIC DATA."

    @srv.tool(name="query_inventory", description=desc("query_inventory"))
    def query_inventory(location_id: str, ingredient: str) -> dict[str, Any]: return run("query_inventory", location_id=location_id, ingredient=ingredient)

    @srv.tool(name="assess_inventory_risk", description=desc("assess_inventory_risk"))
    def assess_inventory_risk(location_id: str, ingredient: str) -> dict[str, Any]: return run("assess_inventory_risk", location_id=location_id, ingredient=ingredient)

    @srv.tool(name="get_quality_finding", description=desc("get_quality_finding"))
    def get_quality_finding(finding_id: int) -> dict[str, Any]: return run("get_quality_finding", finding_id=finding_id)

    @srv.tool(name="get_lineage", description=desc("get_lineage"))
    def get_lineage(table: str, key: str) -> dict[str, Any]: return run("get_lineage", table=table, key=key)

    @srv.tool(name="get_open_purchase_orders", description=desc("get_open_purchase_orders"))
    def get_open_purchase_orders(ingredient: Optional[str] = None) -> dict[str, Any]: return run("get_open_purchase_orders", ingredient=ingredient)

    @srv.tool(name="get_supplier_status", description=desc("get_supplier_status"))
    def get_supplier_status(supplier_id: Optional[str] = None, ingredient: Optional[str] = None) -> dict[str, Any]: return run("get_supplier_status", supplier_id=supplier_id, ingredient=ingredient)

    @srv.tool(name="search_nasha_knowledge", description=desc("search_nasha_knowledge"))
    def search_nasha_knowledge(query: str, k: int = 4, include_nonauthoritative: bool = False) -> dict[str, Any]: return run("search_nasha_knowledge", query=query, k=k, include_nonauthoritative=include_nonauthoritative)

    @srv.tool(name="get_current_policy", description=desc("get_current_policy"))
    def get_current_policy(question: str) -> dict[str, Any]: return run("get_current_policy", question=question)

    @srv.tool(name="draft_purchase_recommendation", description=desc("draft_purchase_recommendation") + " Creates a draft only; no purchase order exists.")
    def draft_purchase_recommendation(location_id: str, ingredient: str, qty_kg: float, supplier_id: str, rationale: str, evidence_ids: list[str]) -> dict[str, Any]:
        return run("draft_purchase_recommendation", location_id=location_id, ingredient=ingredient, qty_kg=qty_kg, supplier_id=supplier_id, rationale=rationale, evidence_ids=evidence_ids)

    return srv


if __name__ == "__main__":      # python -m nasha_lab.mcp_server  (stdio)
    from . import generator, knowledge, world
    w, _, _ = world.build_world(1, menu_version=generator.CURRENT_MENU_VERSION)
    build_server(w, knowledge.default_kb()).run()
