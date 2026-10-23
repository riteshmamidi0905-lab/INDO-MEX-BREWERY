# Growth OS ↔ Production AI Agent Platform: minimal integration

Status: IMPLEMENTED and tested (6 tests, `lab/tests/test_growth_agent_tools.py`). Not a full integration.

## What is reused (pin: production-ai-agent-platform f8ba373)
- `Tool`, `ToolRegistry`, `Risk`, `ToolResult`, `ToolExecutor`: argument validation, timeouts, retries, metrics.
- Three **read-only** Growth OS tools: `GetLeadContext`, `PipelineSummary`, `PriceMargin`.
- `build_registry()` asserts every registered tool is `Risk.READ`; no consequential tool is registered.
- `RefusingBroker` is wired as the approval broker, so there is no second approval path. Approvals exist only in the Growth OS workflow, enforced by THE WEIR.
- Tools run through `GrowthService`, so tenant binding, RLS and default-deny apply unchanged.

## What is NOT reused (no claim of integration)
Agent engine/planner, LLM providers, storage, retrieval, MCP layer, the platform's approval broker, its evaluation and observability stack. The lead-qualification workflow is deterministic and rule-based; it does not run on the agent platform. There is no second agent runtime.

## Requirement and limits
- Needs an editable install of the platform checkout (`pip install -e <platform> --no-deps`); not vendored here.
- Blocker for deeper integration: the platform's approval broker and engine would need a tenant-aware, WEIR-backed adapter; not built.
- No real model runtime was exercised; the release gate stays REQUIRES_REVIEW.
