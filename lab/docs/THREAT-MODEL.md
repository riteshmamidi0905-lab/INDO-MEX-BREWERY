# Threat model (prototype; SYNTHETIC; STRIDE-lite)

| Threat | Where | Control | Evidence |
|---|---|---|---|
| Prompt injection inside a retrieved document | knowledge -> agent | instruction-pattern detector withholds the chunk and flags the run; planner is deterministic and takes no instructions from data | `prompt_injection_in_retrieved_document`; limitation: regex misses paraphrase (`test_injection_heuristic_misses_paraphrase...`) |
| Prompt injection inside a tool result | tools -> agent | same detector on tool output; text withheld from claims | `prompt_injection_in_tool_result` |
| Unverified or superseded source overrides a founder decision | knowledge | status-aware filtering; decisions outrank documents; derived supersession | RAG eval: 0 status violations; 0 must-not-cite |
| Forbidden external action | tools | EXTERNAL_ACTION refused unconditionally, not exposed over MCP/HTTP | `forbidden_action_refused_even_if_requested` |
| Approval replay or argument swap after approval | tools | approval hash binds run id, tool and argument SHA-256 | `approval_bound_to_exact_arguments` |
| Unbounded tool surface (SQL, filesystem, shell) | MCP | allowlist of 9 typed tools; no SQL/filesystem/shell exists in the registry | `test_mcp_lists_exactly_the_allowlisted_tools...` |
| Secrets in logs/traces | trace | key-pattern redaction before persistence | `test_trace_redacts_secrets` (no secrets exist in this prototype) |
| Duplicate event causes duplicate side effects | agent | idempotent per event id | `duplicate_event_*` |
| Silent success on partial evidence | agent | NO_ACTION impossible when any non-injection gap exists | regression test (real defect fixed) |
| Impersonated reviewer | API | **NOT mitigated**: no authentication; reviewer is a free-text field | listed limitation |
| Denial of service, rate limiting, TLS, authn/z | API | **not implemented** (prototype, local only) | listed limitation |
