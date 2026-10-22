"""NASHA AI Operations Control Center (P1) and reliability evidence (P2).

SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.
Everything in this package observes, evaluates or perturbs the synthetic NASHA lab. It is additive: no frozen Block 3 file is touched, and the
only way it changes agent behaviour is by wrapping `tools.execute` (context manager) and by wrapping the knowledge base / model client / world
connection in proxies that the caller passes in explicitly."""
LABEL = "SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED"
SCHEMA_VERSION = "ops-1"
