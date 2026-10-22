"""P5 hardened service layer around the NASHA lab API. SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.

Additive: `nasha_lab.api.create_app` is untouched. `create_hardened_app` (nasha_lab.service.app) adds typed configuration, signed-token authentication,
role-based authorization, rate limiting, deadlines, idempotency, PostgreSQL persistence, structured errors/logs/metrics and health/readiness endpoints."""
LABEL = "SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED"
VERSION = "1.0.0"
