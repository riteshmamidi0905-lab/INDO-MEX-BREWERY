#!/usr/bin/env python3
"""Export RECORDED Growth OS evidence for the portfolio: the capability tracker, a stage-transition matrix and cross-tenant probes actually executed against PostgreSQL, and the control-mutation results.
Nothing is hand-written; the script exits non-zero if any recorded expectation fails. Output: lab/portfolio/growth-os-evidence.json.   cd lab && python3 tools/export_growth_evidence.py"""
import importlib.util
import itertools
import json
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
import psycopg  # noqa: E402
from nasha_lab.governed import tenants as T  # noqa: E402
from nasha_lab.growth import schema as S, seed as SD, service as SV  # noqa: E402
from nasha_lab.warehouse import pg_hardening as H  # noqa: E402

SCHEMA = "growth_export"
ORACLE = {("new", "qualified"), ("new", "lost"), ("qualified", "proposal"), ("qualified", "lost"), ("proposal", "negotiation"), ("proposal", "lost"), ("negotiation", "won"), ("negotiation", "lost"), ("negotiation", "proposal")}


def main():
    import pixeltable_pgserver as pg
    tmp = Path(tempfile.mkdtemp(prefix="growth-evidence-"))
    srv = pg.get_server(str(tmp / "pg"), cleanup_mode="stop"); dsn = srv.get_uri()
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'CREATE SCHEMA "{SCHEMA}"')
    H.migrate(dsn, SCHEMA, specs=S.migrations(SCHEMA))
    users = [("ada", "Ada (synthetic owner)", "OWNER"), ("sam", "Sam (synthetic sales)", "SALES"), ("mia", "Mia (synthetic marketing)", "MARKETING"), ("vic", "Vic (synthetic viewer)", "VIEWER")]
    SV.provision(dsn, SCHEMA, "tenant-nasha", "NASHA (synthetic restaurant and brewery concept)", "restaurant", users)
    SV.provision(dsn, SCHEMA, "tenant-fit", "Meridian Fitness (synthetic studio)", "fitness", users)
    a_env, _ = T.default_pair(tmp / "wh")
    a, b = SV.GrowthService(dsn, SCHEMA, "tenant-nasha", "ada"), SV.GrowthService(dsn, SCHEMA, "tenant-fit", "ada")
    SD.seed_nasha(a, a_env.warehouse); SD.seed_fitness(b)
    # ---- stage matrix (each pair attempted on a fresh opportunity)
    acc = a.read("SELECT id FROM accounts LIMIT 1")[0][0]
    stages = ["new", "qualified", "proposal", "negotiation", "won", "lost"]
    matrix, ok_all = [], True
    for frm, to in itertools.product(stages, stages):
        if frm == to:
            continue
        oid = a._id("opp")
        a.con.execute("INSERT INTO opportunities (tenant_id,id,account_id,name,stage,amount_cents) VALUES (%s,%s,%s,'probe',%s,1)", (a.tenant, oid, acc, frm))
        try:
            a.con.execute("UPDATE opportunities SET stage=%s WHERE tenant_id=%s AND id=%s", (to, a.tenant, oid)); allowed, msg = True, ""
        except psycopg.errors.CheckViolation as e:
            allowed, msg = False, str(e).splitlines()[0]
        matrix.append(dict(frm=frm, to=to, allowed=allowed, database_message=msg, oracle_allowed=((frm, to) in ORACLE)))
        ok_all &= allowed == ((frm, to) in ORACLE)
    # ---- isolation probes
    tables = ["accounts", "contacts", "leads", "segments", "products", "prices", "audit_log", "entity_versions"]
    probes = []
    nosetting = psycopg.connect(SV.app_dsn(dsn), autocommit=True); nosetting.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
    for t in tables:
        own_a = a.con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        own_b = b.con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        key = "seq" if t == "audit_log" else "id" if t != "entity_versions" else "entity_id"
        ids_b = [r[0] for r in b.con.execute(f"SELECT {key} FROM {t}")]
        a_sees_b = a.con.execute(f"SELECT count(*) FROM {t} WHERE tenant_id=%s", ("tenant-fit",)).fetchone()[0]
        a_sees_b_ids = a.con.execute(f"SELECT count(*) FROM {t} WHERE {key} = ANY(%s) AND tenant_id <> %s", (ids_b, "tenant-nasha")).fetchone()[0]
        none = nosetting.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        probes.append(dict(table=t, tenant_a_rows=own_a, tenant_b_rows=own_b, a_sees_b_rows=a_sees_b, a_sees_b_by_id=a_sees_b_ids, no_tenant_setting_rows=none))
        ok_all &= a_sees_b == 0 and a_sees_b_ids == 0 and none == 0 and own_a > 0 and own_b > 0
    attempts = []
    for label, sql, params, exc in [
        ("insert a row for the other tenant", "INSERT INTO accounts (tenant_id,id,name,kind) VALUES ('tenant-fit','acc-forged','forged','business')", (), psycopg.errors.InsufficientPrivilege),
        ("reference the other tenant's account in a contact", "INSERT INTO contacts (tenant_id,id,account_id,full_name,email) VALUES ('tenant-nasha','con-x',%s,'x','x@example.invalid')", (b.read("SELECT id FROM accounts LIMIT 1")[0][0],), psycopg.errors.ForeignKeyViolation),
        ("create a tenant from the application role", "INSERT INTO tenants (tenant_id,name,vertical) VALUES ('tenant-evil','x','y')", (), psycopg.errors.InsufficientPrivilege),
        ("delete from the audit log", "DELETE FROM audit_log", (), psycopg.errors.InsufficientPrivilege)]:
        try:
            a.con.execute(sql, params); res = "ALLOWED (failure)"; ok_all = False
        except exc as e:
            res = f"refused: {type(e).__name__}"
        attempts.append(dict(attempt=label, result=res))
    # ---- control mutants (the same probes/mutants the test suite runs)
    spec = importlib.util.spec_from_file_location("gmut", LAB / "tests/test_growth_mutations.py")
    gm = importlib.util.module_from_spec(spec); sys.modules["gmut"] = gm; spec.loader.exec_module(gm)
    mutants = []
    for i, (name, probe, sql, patch) in enumerate(gm.MUTANTS):
        sc = f"growth_exp_m{i}"; gm.build(dsn, sc)
        for st in (sql.split("; ") if sql else []):
            gm.admin(dsn, sc, st)
        if patch:
            with patch():
                held = probe(dsn, sc)
        else:
            held = probe(dsn, sc)
        mutants.append(dict(mutant=name, probe=probe.__name__, killed=(held is False)))
        ok_all &= held is False
    caps = json.loads((LAB / "nasha_lab/growth/capabilities.json").read_text())
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=LAB).stdout.strip()
    ver = a.verify_audit(), b.verify_audit()
    out = dict(schema="growth-os-evidence/1", commit=commit, synthetic=True, pushed=False, notice="Synthetic tenants and data. NASHA Growth OS is a working name; this is a foundation, not a commercial product. Recorded from probes executed against PostgreSQL when exported.",
               postgres=a.con.execute("SHOW server_version").fetchone()[0], tenants=[dict(id="tenant-nasha", vertical="restaurant"), dict(id="tenant-fit", vertical="fitness")],
               tables=S.ALL_TENANT_TABLES, stage_matrix=matrix, isolation_probes=probes, privilege_attempts=attempts, mutants=mutants, audit_chains_valid=dict(nasha=ver[0][0], fit=ver[1][0]),
               capabilities=caps["capabilities"], status_rules=caps["rules"], all_expectations_met=ok_all)
    (LAB / "portfolio/growth-os-evidence.json").write_text(json.dumps(out, indent=1, default=str))
    a.close(); b.close(); nosetting.close(); srv.cleanup()
    print("written; all expectations met:", ok_all, f"{len(matrix)} stage pairs, {len(probes)} tables probed, {sum(m['killed'] for m in mutants)}/{len(mutants)} mutants killed")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
