# Pinned offline Operations component

Source commit: `0f9149ad13c7e870ff309814345c338e797c345e` from this repository's Claude engineering branch. The two Python source files and eight upstream contract artifacts are copied unchanged; see `UPSTREAM.json` for hashes. Namespace/package marker files are local. No provider path is enabled or exposed by the adapter.

This is reuse of the existing pure M-OPS-1 checker/renderer, not another agent framework. See `showcase/docs/AMARA_OFFLINE_ADAPTER.md` for provenance, API, limitations and test coverage. Never update pins or vendored contracts silently.

Renderer pin: `ops-renderer-v2.0-tenant-scoped-labels`. The host adapter always supplies authorized scope and its own immutable display table. Historical v1 fixtures remain unchanged; generic/historical callback pipelines are not used.
