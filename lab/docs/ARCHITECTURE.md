# Architecture and tradeoffs (SYNTHETIC / NOT PRODUCTION DEPLOYED)

```
generator.py  seeded synthetic raw tables (all strings, like CSV) + ground-truth labels of injected defects
      |  raw CSV
pipeline.stage    typing; rows that cannot be typed are REJECTED WITH A REASON, never dropped silently
dq.run_rules      pure functions over staged data; never imports labels (tested by AST)
pipeline.run      severities: ERROR -> quarantine (+ cascade to parents/children), WARN -> flag and keep, BLOCKER -> publish gate
      |
SQLite star schema: dim_location, dim_menu_item, fact_order, fact_order_line, fact_inventory_count
                    dq_finding, quarantine, lineage;  views v_daily_sales, v_item_mix
evaluate.py       scores findings against injected truth: precision/recall per rule, clean-run false positives
```
**Invariants (tested):** every raw row is either modeled or quarantined (`raw = modeled + quarantined`); modeled facts contain no orphan lines, non-positive quantities, future timestamps, mismatched totals or `lb` units; the analytics view reconciles to the fact table; the D-54 term list is a superset of `tools/diet_audit.py` (one policy, enforced).

**Decisions and tradeoffs**
- *SQLite + stdlib, not PostgreSQL/dbt/Kafka.* $0, no services, deterministic CI. The layer contract (staging/validated/modeled) maps to dbt models later; that migration is **not claimed**. Postgres/pgvector will be justified only when the RAG block needs vectors (the existing `production-ai-agent-platform` already does this; reuse, not rebuild).
- *Rules independent of the generator.* Otherwise the evaluation would be circular.
- *Severity design.* Price drift is a WARN: a real price change must not delete revenue. A D-54 violation is a BLOCKER that fails the publish gate but keeps the record visible and flagged, so a compliance defect is surfaced instead of silently shrinking the menu.
- *Cascade quarantine* keeps facts self-consistent (an order with a bad line is removed whole) at the cost of discarding good lines; cascades are counted separately and never scored as findings.
- *Not built on purpose:* streaming, orchestration, microservices, a vector DB, an agent. None is needed for this block.
