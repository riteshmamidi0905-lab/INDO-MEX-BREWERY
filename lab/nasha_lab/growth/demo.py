"""Builds the local Growth OS demo: two SYNTHETIC tenants (NASHA — The Courtyard, the flagship hospitality launch case study, and Meridian Fitness, a studio) in PostgreSQL, seeded through the same services the API uses, plus a few recorded
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
from . import agent_research as AR, launch_seed as LS, launch_workflow as LW, scenarios as SC, schema as S, seed as SD, service as SV, workflow as WF

SCHEMA = "growth_demo"
USERS = {"ada": ("Ada Rao (synthetic owner)", "OWNER"), "omar": ("Omar Ellis (synthetic owner)", "OWNER"), "sam": ("Sam Park (synthetic sales)", "SALES"), "mia": ("Mia Chen (synthetic marketing)", "MARKETING"),
         "ana": ("Ana Ruiz (synthetic analyst)", "ANALYST"), "vic": ("Vic Stone (synthetic viewer)", "VIEWER")}
SIGNALS = [dict(budget_confirmed=True, decision_maker=True, timeline_days=14, fit=0.9, engagement=0.8), dict(budget_confirmed=True, decision_maker=False, timeline_days=45, fit=0.7, engagement=0.5),
           dict(budget_confirmed=False, decision_maker=False, timeline_days=None, fit=0.2, engagement=0.1), dict(budget_confirmed=True, decision_maker=True, timeline_days=60, fit=0.6, engagement=0.9),
           dict(budget_confirmed=False, decision_maker=True, timeline_days=120, fit=0.4, engagement=0.3)]


def build(root, dsn, schema=SCHEMA, with_warehouse=True, today=None):
    """`today` is the date the synthetic quotes' 30-day validity window starts from (default: the real today). Tests that run the app with a FIXED as_of pass the same date, otherwise the quotes fall outside the window as soon as the calendar moves past it."""
    root = Path(root)
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'); c.execute(f'CREATE SCHEMA "{schema}"')
    H.migrate(dsn, schema, specs=S.migrations(schema))
    envs = {"tenant-nasha": WF.provision_env(root, dsn, schema, "tenant-nasha", "NASHA — The Courtyard (synthetic hospitality brand)", "hospitality", USERS),
            "tenant-fit": WF.provision_env(root, dsn, schema, "tenant-fit", "Meridian Fitness (synthetic studio)", "fitness", USERS)}
    owner = {t: SV.GrowthService(dsn, schema, t, "ada") for t in envs}
    wh = T.default_pair(root / "wh")[0].warehouse if with_warehouse else None
    nasha = SD.seed_nasha(owner["tenant-nasha"], wh, with_accounts=False)
    fit = SD.seed_fitness(owner["tenant-fit"], with_accounts=False)
    plans = {"tenant-nasha": (SC.NASHA, SC.NASHA_HISTORY), "tenant-fit": (SC.MERIDIAN, SC.MERIDIAN_HISTORY)}
    comments = {"executed": "Evidence reviewed; the qualification follows from the recorded facts.", "rejected": "Not enough confirmed information yet; revisit after a budget conversation."}
    for t, (plan, history) in plans.items():
        sales = SV.GrowthService(dsn, schema, t, "sam")
        ids, prices = SC.seed(sales, owner[t], plan, history)
        wf = WF.GovernedLeadQualification(envs[t])
        tok = lambda u, wf=wf, t=t: wf.login(u, f"{t}-{u}-dev-passcode")
        for sc in plan:
            lead, disp = ids[sc["key"]], sc["disposition"]
            requester = sc["owner"] if sc["owner"] in ("sam", "ada") else "sam"
            approver = "omar" if requester == "ada" else "ada"
            if disp == "denied":
                wf.run(tok("mia"), lead, idempotency_key=f"demo-{t}-{sc['key']}")
            elif disp in ("suppressed", "abstain", "awaiting"):
                wf.run(tok(requester), lead, idempotency_key=f"demo-{t}-{sc['key']}")
            elif disp in ("executed", "rejected"):
                r = wf.run(tok(requester), lead, idempotency_key=f"demo-{t}-{sc['key']}")
                wf.decide(r["corr_id"], tok(approver), disp == "executed", comments[disp])
                if disp == "executed" and sc["basket"] and sales.get_lead_context(lead)["status"] == "qualified":
                    sales.convert_lead(lead, sc["opp"], SC.basket_cents(prices, sc["basket"]))      # a new opportunity starts in the 'new' stage
        wf.close(); sales.close()
    # business-launch workspace: a project per tenant (stored assumptions, milestones, research, suppliers) and recorded procurement runs for the flagship case study
    launch_ids = {"tenant-nasha": LS.seed_nasha_launch(owner["tenant-nasha"], today=today), "tenant-fit": LS.seed_meridian_launch(owner["tenant-fit"], today=today)}
    agent = None
    try:
        import agentplatform  # noqa: F401
        agent = AR.SupplierResearchAgent(dsn, "tenant-nasha", root / "agent-demo")
    except ImportError:
        pass                                           # without the platform package the runs below use the deterministic fallback and say so
    lw = LW.LaunchProcurement(envs["tenant-nasha"], agent=agent)
    ltok = lambda u: lw.login(u, f"tenant-nasha-{u}-dev-passcode")
    pid = launch_ids["tenant-nasha"]["project"]
    r1 = lw.run(ltok("ana"), pid, 4, idempotency_key="demo-proc-1"); lw.decide(r1["corr_id"], ltok("ada"), True, "Quotes are synthetic fixtures; recorded for the planning exercise.")
    r2 = lw.run(ltok("ana"), pid, 1, idempotency_key="demo-proc-2"); lw.decide(r2["corr_id"], ltok("omar"), False, "Wait for real supplier quotes before recording anything.")
    lw.run(ltok("ana"), pid, 2, idempotency_key="demo-proc-3")                                         # left awaiting approval
    lw.run(ltok("sam"), pid, 4, idempotency_key="demo-proc-4")                                         # sales: THE WEIR has no write tool for the role
    lw.close()
    # the second industry on the SAME code: a fitness studio's launch (equipment and service requirements, no recipes), recorded through the same governed workflow
    agent_fit = None
    try:
        import agentplatform  # noqa: F401
        agent_fit = AR.SupplierResearchAgent(dsn, "tenant-fit", root / "agent-demo-fit")
    except ImportError:
        pass
    lf = LW.LaunchProcurement(envs["tenant-fit"], agent=agent_fit)
    ftok = lambda u: lf.login(u, f"tenant-fit-{u}-dev-passcode")
    fpid = launch_ids["tenant-fit"]["project"]
    owner["tenant-fit"].save_scenario(fpid, "Base plan")
    f1 = lf.run(ftok("ana"), fpid, 4, idempotency_key="demo-fit-proc-1"); lf.decide(f1["corr_id"], ftok("ada"), True, "Quotes are synthetic fixtures; recorded for the planning exercise.")
    lf.run(ftok("ana"), fpid, 2, idempotency_key="demo-fit-proc-2")                                    # left awaiting approval
    lf.close()
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
    uvicorn.run(create_growth_app(envs, agent_dsn=srv.get_uri()), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
