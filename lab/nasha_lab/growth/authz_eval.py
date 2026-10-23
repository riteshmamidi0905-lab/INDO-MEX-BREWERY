"""Independent authorisation evaluation: every (user, operation) in both businesses, over HTTP, against an EXPECTED table written from the intended policy (who is supposed to be able to do what), not read back from the code.
An operation a role may not do must return 403 and leave an audit denial; one it may do must succeed (2xx). Mutants widen the policy in the service and the matrix must notice. Shared by the tests and the evidence exporter."""
import contextlib
import uuid

from . import service as SV

USERS = {"ada": "OWNER", "omar": "OWNER", "ana": "ANALYST", "sam": "SALES", "mia": "MARKETING", "vic": "VIEWER"}
OWNER, ANALYST = {"OWNER"}, {"OWNER", "ANALYST"}
EXPECTED = {"create a project": OWNER, "set an assumption": ANALYST, "add a milestone": OWNER, "add a research finding": ANALYST, "add a supplier record": ANALYST, "add a requirement": ANALYST,
            "shortlist a supplier": ANALYST, "save a scenario": ANALYST, "request a recommendation": ANALYST}


def _ops(c, base, pid, sid, H):
    u = lambda: uuid.uuid4().hex[:8]
    return {
        "create a project": lambda user: c.post(f"{base}/projects", json=dict(name=f"Matrix {u()}", industry="Hospitality", location="Austin, TX", concept="A throwaway project used only by the authorisation matrix.", budget_cents=100_000), headers=H(user)),
        "set an assumption": lambda user: c.put(f"{base}/projects/{pid}/assumptions/weekly_orders", json=dict(label="Orders per week", value=10, unit="orders", basis="synthetic_assumption"), headers=H(user)),
        "add a milestone": lambda user: c.post(f"{base}/projects/{pid}/milestones", json=dict(title=f"Matrix milestone {u()}", phase="idea"), headers=H(user)),
        "add a research finding": lambda user: c.post(f"{base}/projects/{pid}/findings", json=dict(topic="Matrix", finding=f"A finding recorded by the matrix {u()}.", source_kind="founder_note", confidence=0.5, limitation="Test data."), headers=H(user)),
        "add a supplier record": lambda user: c.post(f"{base}/suppliers", json=dict(name=f"Matrix Supplier {u()} Zebra", category="Test", service_area="Nowhere", verification_status="synthetic_fixture", source_kind="synthetic_fixture", confirm_distinct=True), headers=H(user)),
        "add a requirement": lambda user: c.post(f"{base}/projects/{pid}/requirements", json=dict(ref=f"matrix.{u()}", name="Matrix item", kind="equipment", qty=1, unit="each", recurrence="one_time"), headers=H(user)),
        "shortlist a supplier": lambda user: c.put(f"{base}/projects/{pid}/suppliers/{sid}", json=dict(status="shortlisted"), headers=H(user)),
        "save a scenario": lambda user: c.post(f"{base}/projects/{pid}/scenarios", json=dict(name=f"Matrix {u()}", overrides={}), headers=H(user)),
        "request a recommendation": lambda user: c.post(f"{base}/projects/{pid}/procurement", json={"period_weeks": 1}, headers=H(user))}


def run(c, envs, tenant, project_id, supplier_id):
    base = f"/v1/tenants/{tenant}"
    H = lambda user: {"Authorization": "Bearer " + envs[tenant].authority.login(user, f"{tenant}-{user}-dev-passcode"), "Idempotency-Key": uuid.uuid4().hex}
    ops, rows = _ops(c, base, project_id, supplier_id, H), []
    for op, allowed in EXPECTED.items():
        for user, role in USERS.items():
            r = ops[op](user)
            should = role in allowed
            ok = (200 <= r.status_code < 300) if should else r.status_code == 403
            rows.append(dict(tenant=tenant, operation=op, user=user, role=role, expected="allow" if should else "deny", status=r.status_code, ok=ok))
    return rows


def summary(rows):
    return dict(checks=len(rows), correct=sum(r["ok"] for r in rows), wrong=[f"{r['tenant']}/{r['operation']}/{r['role']}: expected {r['expected']}, got {r['status']}" for r in rows if not r["ok"]],
                allowed_checked=sum(r["expected"] == "allow" for r in rows), denied_checked=sum(r["expected"] == "deny" for r in rows))


@contextlib.contextmanager
def widened(action, role):
    """Mutant: quietly let one more role do an action."""
    old = SV.POLICY[action]
    SV.POLICY[action] = set(old) | {role}
    try:
        yield
    finally:
        SV.POLICY[action] = old


MUTANTS = {"analyst_may_create_projects": ("project.create", "ANALYST"), "viewer_may_write_requirements": ("requirement.write", "VIEWER"), "sales_may_shortlist_suppliers": ("supplier.shortlist", "SALES"),
           "analyst_may_write_milestones": ("milestone.write", "ANALYST"), "marketing_may_save_scenarios": ("scenario.save", "MARKETING"), "viewer_may_set_assumptions": ("project.assumption", "VIEWER")}
