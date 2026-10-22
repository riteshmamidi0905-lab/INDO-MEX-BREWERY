"""NASHA synthetic enterprise warehouse (SQLite): contracts, incremental ingestion, SQL models with lineage, quality gates, monitoring.

SYNTHETIC DATA / SIMULATED OPERATION. Built over the output of nasha_lab.enterprise_sim. Nothing here describes a real business.
No framework beyond the standard library, pandas and SQLite: model files are plain SQL with `-- depends:` headers (dbt-style ideas, no dbt).
"""
