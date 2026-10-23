"""Builds the local Growth OS demo: two SYNTHETIC tenants (NASHA, a restaurant/brewery concept, and Meridian Fitness, a studio) in PostgreSQL, seeded through the same services the API uses, plus a few recorded
qualification runs in different states. Serves the API and the web interface on localhost only.
    python3 -m nasha_lab.growth.demo --port 8765          (embedded PostgreSQL; synthetic dev passcodes `{tenant}-{user}-dev-passcode`)"""
import argparse
import random
import tempfile
from datetime import date
from pathlib import Path

import psycopg

from ..governed import tenants as T
from ..warehouse import pg_hardening as H
from . import schema as S, seed as SD, service as SV, workflow as WF

SCHEMA = "growth_demo"
USERS = {"ada": ("Ada Rao (synthetic owner)", "OWNER"), "omar": ("Omar Ellis (synthetic owner)", "OWNER"), "sam": ("Sam Park (synthetic sales)", "SALES"), "mia": ("Mia Chen (synthetic marketing)", "MARKETING"),
         "ana": ("Ana Ruiz (synthetic analyst)", "ANALYST"), "vic": ("Vic Stone (synthetic viewer)", "VIEWER")}
SIGNALS = [dict(budget_confirmed=True, decision_maker=True, timeline_days=14, fit=0.9, engagement=0.8), dict(budget_confirmed=True, decision_maker=False, timeline_days=45, fit=0.7, engagement=0.5),
           dict(budget_confirmed=False, decision_maker=False, timeline_days=None, fit=0.2, engagement=0.1), dict(budget_confirmed=True, decision_maker=True, timeline_days=60, fit=0.6, engagement=0.9),
           dict(budget_confirmed=False, decision_maker=True, timeline_days=120, fit=0.4, engagement=0.3)]


def build(root, dsn, schema=SCHEMA, with_warehouse=True):
    root = Path(root)
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'); c.execute(f'CREATE SCHEMA "{schema}"')
    H.migrate(dsn, schema, specs=S.migrations(schema))
    envs = {"tenant-nasha": WF.provision_env(root, dsn, schema, "tenant-nasha", "NASHA (synthetic restaurant and brewery concept)", "restaurant", USERS),
            "tenant-fit": WF.provision_env(root, dsn, schema, "tenant-fit", "Meridian Fitness (synthetic studio)", "fitness", USERS)}
    owner = {t: SV.GrowthService(dsn, schema, t, "ada") for t in envs}
    wh = T.default_pair(root / "wh")[0].warehouse if with_warehouse else None
    nasha = SD.seed_nasha(owner["tenant-nasha"], wh) if wh else None
    fit = SD.seed_fitness(owner["tenant-fit"])
    rnd = random.Random(3)
    by_i = {}
    for t, svc in owner.items():
        sales = SV.GrowthService(dsn, schema, t, "sam")
        for i in range(10):
            a = sales.create_account(f"{'Harbor' if t == 'tenant-nasha' else 'Summit'} Group {i}", "business" if t == "tenant-nasha" else "household")
            c = sales.create_contact(a, f"Synthetic Contact {i}", f"{t[7:]}.contact{i}@example.invalid")
            if i % 4 != 3:
                sales.set_consent(c, "opt_in")
            lead = sales.create_lead(c, rnd.choice(["synthetic-referral", "synthetic-website-form", "synthetic-event-fair"]), SIGNALS[i % len(SIGNALS)])
            by_i[(t, i)] = lead
            if i == 7:
                sales.suppress(f"{t[7:]}.contact{i}@example.invalid", "asked not to be contacted (synthetic)")
            if i in (0, 1, 2, 3, 5, 6):          # direct qualification + conversion so the pipeline has records beyond the workflow
                sales.qualify_lead(lead, SIGNALS[0]); opp = sales.convert_lead(lead, f"{'Catering' if t == 'tenant-nasha' else 'Corporate pack'} {i}", 120000 + 35000 * i)
                for stage in ({1: ["qualified"], 2: ["qualified", "proposal"], 3: ["qualified", "proposal", "negotiation"], 5: ["qualified", "proposal", "negotiation", "won"], 6: ["lost"]}.get(i, [])):
                    sales.advance(opp, stage)
        sales.close()
    # recorded governed qualification runs in four different states (NASHA tenant)
    env = envs["tenant-nasha"]
    wf = WF.GovernedLeadQualification(env)
    tok = lambda u: wf.login(u, f"{env.tenant_id}-{u}-dev-passcode")
    leads = [by_i[("tenant-nasha", i)] for i in (4, 8, 9, 8)]
    r1 = wf.run(tok("sam"), leads[0], idempotency_key="demo-run-1"); wf.decide(r1["corr_id"], tok("ada"), True, "evidence reviewed")
    r2 = wf.run(tok("sam"), leads[1], idempotency_key="demo-run-2"); wf.decide(r2["corr_id"], tok("omar"), False, "decision maker not confirmed")
    wf.run(tok("sam"), leads[2], idempotency_key="demo-run-3")                                         # left awaiting approval
    wf.run(tok("mia"), leads[3], idempotency_key="demo-run-4")                                         # denied by THE WEIR (marketing has no write tool)
    wf.close()
    for s in owner.values():
        s.close()
    return envs


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8765); ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args(argv)
    import pixeltable_pgserver as pg
    import uvicorn
    from .api import create_growth_app
    root = Path(tempfile.mkdtemp(prefix="growth-demo-"))
    srv = pg.get_server(str(root / "pg"), cleanup_mode="stop")
    envs = build(root / "data", srv.get_uri())
    print(f"Growth OS demo (SYNTHETIC data) on http://{a.host}:{a.port}/app   users: ada/omar (owner), sam (sales), mia (marketing), ana (analyst), vic (viewer); passcode = <tenant>-<user>-dev-passcode")
    uvicorn.run(create_growth_app(envs), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
