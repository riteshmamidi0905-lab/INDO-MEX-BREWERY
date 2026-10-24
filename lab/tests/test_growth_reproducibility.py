"""Reproducibility of evidence. Identical BUSINESS inputs must give identical business decisions in two independently initialised databases (whose generated ids differ), while the records that describe THIS execution
(ids, times, hashes computed over ids) stay truthful and different. The checks are pure where they can be; the integration checks build two worlds in two schemas with different random ids, and two agent databases holding
identical documents. Each rule has a negative test: a deliberately introduced ordering or identifier instability must be DETECTED by the same check."""
import hashlib
import inspect
import asyncio
import json
import re
import textwrap
from datetime import date

import pytest

from nasha_lab.growth import evidence_canon as EC, industry_eval as IE, procurement as PRC, supplier_intel as SI

AS_OF = date(2026, 10, 23)


# ------------------------------------------------------------------------------------------------ canonical view
DOC = {"commit": "abc1234", "generated_at": "2026-10-24T00:00:00", "run": {"corr_id": "run-0123456789", "total_cost_cents": 425000, "ts": "2026-10-24T00:00:01", "call_hash": "deadbeefdeadbeef",
       "suppliers": [{"supplier": "Alpha", "id": "sup-aaaaaaaaaa", "cost_cents": 100}, {"supplier": "Beta", "id": "sup-bbbbbbbbbb", "cost_cents": 200}]}}


def test_canonical_view_removes_only_identifiers_and_volatile_keys():
    v = EC.canonical_view(DOC)
    assert v == {"run": {"corr_id": "<id>", "total_cost_cents": 425000, "suppliers": [{"supplier": "Alpha", "id": "<id>", "cost_cents": 100}, {"supplier": "Beta", "id": "<id>", "cost_cents": 200}]}}
    assert set(EC.VOLATILE_KEYS) >= {"ts", "generated_at", "commit", "call_hash", "proposal_hash"} and all(isinstance(r, str) and len(r) >= 6 for r in EC.VOLATILE_KEYS.values()), "every removed key states why"


def _fresh_ids(doc, seed):
    s = json.dumps(doc)
    for old in set(re.findall(r"(?:sup|run)-[0-9a-f]{10}", s)):
        s = s.replace(old, old[:4] + hashlib.sha1((old + seed).encode()).hexdigest()[:10])
    return json.loads(s)


def test_two_executions_that_differ_only_in_ids_times_and_id_hashes_have_the_same_canonical_hash():
    other = _fresh_ids(DOC, "x"); other["generated_at"] = "2027-01-01T00:00:00"; other["run"]["ts"] = "2027-01-01"; other["run"]["call_hash"] = "0123456789abcdef"; other["commit"] = "fff9999"
    assert other != DOC and EC.canonical_sha256(other) == EC.canonical_sha256(DOC)


@pytest.mark.parametrize("name,mutate", [
    ("a changed business number", lambda d: d["run"].update(total_cost_cents=425001)),
    ("a changed supplier name", lambda d: d["run"]["suppliers"][0].update(supplier="Alpha Two")),
    ("an unstable ordering", lambda d: d["run"]["suppliers"].reverse()),
    ("a changed cost inside a list", lambda d: d["run"]["suppliers"][1].update(cost_cents=201)),
    ("a business field that carries a random id", lambda d: d["run"]["suppliers"][0].update(note="ticket 7"))])
def test_the_canonical_hash_detects_every_kind_of_real_instability(name, mutate):
    other = json.loads(json.dumps(DOC)); mutate(other)
    assert EC.canonical_sha256(other) != EC.canonical_sha256(DOC), name


def test_ids_hidden_inside_free_text_are_masked_but_a_look_alike_word_is_not():
    assert EC.canonical_view({"t": "see sup-0123abcdef and acc-aaaaaaaa"}) == {"t": "see <id> and <id>"}
    assert EC.canonical_view({"t": "a super-fresh supply"}) == {"t": "a super-fresh supply"}


# ------------------------------------------------------------------------------------------------ deterministic tie-breaks
def _directory(ids):
    """Two suppliers with IDENTICAL quotes (a genuine tie on cost and lead time) and a third that is dearer; `ids` assigns the generated ids."""
    a, b, c = ids
    return [dict(id=a, name="Zeta Supply", verification_status="synthetic_fixture", priced_products=1, products=[IE._p("equip.bike", "Bike", "each", 94_500), IE._p("svc.towel", "Towel service", "pickup", 23_500)]),
            dict(id=b, name="Alpha Supply", verification_status="synthetic_fixture", priced_products=1, products=[IE._p("equip.bike", "Bike", "each", 94_500), IE._p("svc.towel", "Towel service", "pickup", 23_500)]),
            dict(id=c, name="Mid Supply", verification_status="synthetic_fixture", priced_products=1, products=[IE._p("equip.bike", "Bike", "each", 99_000)])]


def _digest(ids, compare=None):
    d = _directory(ids)
    plan = PRC.plan(d, None, 4, AS_OF, IE.REQ, False) if compare is None else _with(compare, d)
    return EC.business_digest(plan), [t["supplier"] for t in plan["supplier_totals"]], [i["chosen"]["supplier"] for i in plan["items"]]


def _with(compare, d):
    old = PRC.compare
    PRC.compare = compare
    try:
        return PRC.plan(d, None, 4, AS_OF, IE.REQ, False)
    finally:
        PRC.compare = old


IDS_1, IDS_2 = ("sup-0000000001", "sup-0000000002", "sup-0000000003"), ("sup-ffffffff03", "sup-ffffffff02", "sup-ffffffff01")        # opposite id orders


def test_a_tie_between_suppliers_is_broken_by_name_so_the_recommendation_does_not_depend_on_generated_ids():
    d1, t1, c1 = _digest(IDS_1)
    d2, t2, c2 = _digest(IDS_2)
    assert (d1, t1, c1) == (d2, t2, c2) and set(c1) == {"Alpha Supply"} and t1 == ["Alpha Supply"], (c1, t1)


def _id_first_compare():
    src = textwrap.dedent(inspect.getsource(PRC.compare)).replace('c["supplier"], c["supplier_id"]))', 'c["supplier_id"], c["supplier"]))')
    assert src != textwrap.dedent(inspect.getsource(PRC.compare)), "the mutant must differ from the source"
    ns = dict(vars(PRC)); exec(src, ns)
    return ns["compare"]


def test_negative_an_id_first_tie_break_is_detected_by_the_same_check():
    mutant = _id_first_compare()
    assert _digest(IDS_1, mutant)[0] != _digest(IDS_2, mutant)[0], "the digest must expose a tie-break that follows generated ids"


def test_quote_comparison_rows_order_ties_by_name_not_by_id():
    def rows(ids):
        sup = [dict(id=i, name=n, verification_status="synthetic_fixture", products=[IE._p("equip.bike", "Bike", "each", 94_500)]) for i, n in zip(ids, ("Zeta Supply", "Alpha Supply"))]
        q = SI.quote_matrix(sup, AS_OF)
        return [e["supplier"] for r in q["rows"] for cat in r["categories"].values() for e in cat]
    assert rows(("sup-0000000001", "sup-0000000002")) == rows(("sup-ffffffff02", "sup-ffffffff01")) == ["Alpha Supply", "Zeta Supply"]


def test_the_operational_proposal_hash_is_bound_to_ids_and_so_legitimately_differs_while_the_business_digest_does_not():
    p1 = PRC.plan(_directory(IDS_1), None, 4, AS_OF, IE.REQ, False); p2 = PRC.plan(_directory(IDS_2), None, 4, AS_OF, IE.REQ, False)
    assert PRC.digest(p1) != PRC.digest(p2), "what THE WEIR binds an approval to includes the supplier ids and must not be rewritten to look identical"
    assert EC.business_digest(p1) == EC.business_digest(p2)


# ------------------------------------------------------------------------------------------------ the retrieval setting that removed the evidence variance
def test_the_agent_database_is_opened_with_exact_scans_only():
    from nasha_lab.growth import agent_research as AR
    assert "enable_indexscan=off" in AR.EXACT_SEARCH and "enable_bitmapscan=off" in AR.EXACT_SEARCH and "enable_indexonlyscan=off" in AR.EXACT_SEARCH
    assert "EXACT_SEARCH" in inspect.getsource(AR._tenant_dsn), "the setting must actually be applied to the agent DSN"


# ------------------------------------------------------------------------------------------------ two independently initialised environments
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
from test_growth_launch import USERS, dsn  # noqa: E402,F401  (fixture reuse: honours NASHA_PG_DSN, else the embedded server)

from nasha_lab.growth import launch_seed as LS, launch_workflow as LW, schema as S, seed as SD, service as SV, workflow as WF  # noqa: E402
from nasha_lab.warehouse import pg_hardening as H  # noqa: E402


def build_world(dsn, tmp, schema):
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'); c.execute(f'CREATE SCHEMA "{schema}"')
    H.migrate(dsn, schema, specs=S.migrations(schema))
    out = {"dsn": dsn, "schema": schema}
    for t in ("tenant-nasha", "tenant-fit"):
        env = WF.provision_env(tmp, dsn, schema, t, t, "hospitality", USERS)
        s = SV.GrowthService(dsn, schema, t, "ada")
        (SD.seed_nasha(s, None, with_accounts=False) if t == "tenant-nasha" else SD.seed_fitness(s, with_accounts=False))
        out[t] = dict(env=env, ids=(LS.seed_nasha_launch(s, today=AS_OF) if t == "tenant-nasha" else LS.seed_meridian_launch(s, today=AS_OF))); s.close()
    return out


@pytest.fixture(scope="module")
def worlds(dsn, tmp_path_factory):
    return build_world(dsn, tmp_path_factory.mktemp("rep_a"), "repro_a"), build_world(dsn, tmp_path_factory.mktemp("rep_b"), "repro_b")


def svc(w, tenant, user="ana"):
    return SV.GrowthService(w["dsn"], w["schema"], tenant, user)


def decisions(w, tenant):
    s = svc(w, tenant); pid = w[tenant]["ids"]["project"]
    d = s.supplier_directory(AS_OF, pid); ctx = s.procurement_context(pid)
    plan = PRC.plan(d, ctx["scenario"], 4, AS_OF, ctx["requirements"], ctx["use_recipes"])
    cards = {c["name"]: (c["classification"]["primary"], c["evidence_tier"], (c["area"] or {}).get("level")) for c in s.supplier_intelligence(pid, AS_OF)["cards"]}
    fin = s.preview_scenario(pid)["results"]
    ids = {x["id"] for x in d}; s.close()
    return dict(digest=EC.business_digest(plan), total=plan["total_cost_cents"], cards=cards, fin_sha=EC.canonical_sha256(fin), fin=fin, ids=ids, names=sorted(x["name"] for x in d))


@pytest.mark.parametrize("tenant", ["tenant-nasha", "tenant-fit"])
def test_two_independently_initialised_databases_make_the_same_business_decisions(worlds, tenant):
    a, b = decisions(worlds[0], tenant), decisions(worlds[1], tenant)
    assert a["ids"].isdisjoint(b["ids"]) and a["ids"] and b["ids"], "the two worlds really have different generated ids"
    assert a["names"] == b["names"] and a["cards"] == b["cards"], "supplier classification, evidence tier and service-area match do not depend on ids"
    assert a["digest"] == b["digest"] and a["total"] == b["total"], "same needs and quotes give the same recommendation"
    assert a["fin_sha"] == b["fin_sha"] and a["fin"]["startup"]["total_requirement_cents"] == b["fin"]["startup"]["total_requirement_cents"], "financial calculations are unchanged"


def run_workflow(w, tenant="tenant-fit"):
    wf = LW.LaunchProcurement(w[tenant]["env"], agent=None, as_of=AS_OF)
    tok = lambda u: wf.login(u, f"{tenant}-{u}-dev-passcode")
    pid = w[tenant]["ids"]["project"]
    r = wf.run(tok("ana"), pid, 4)
    run = wf.status(r["corr_id"]); trace = wf.trace(r["corr_id"])
    denied = wf.decide(r["corr_id"], tok("ana"), True)                          # the requester may not approve
    done = wf.decide(r["corr_id"], tok("ada"), True, "reviewed")
    out = dict(corr=r["corr_id"], first=r["status"], proposal_hash=run["proposal_hash"], stages=[(e.get("stage"), e.get("name")) for e in trace if e.get("kind") == "stage"], denied=denied.get("failure"), final=done["status"],
               total=run["items"]["total_cost_cents"], digest=EC.business_digest(run["items"]), ids={t["supplier_id"] for t in run["items"]["supplier_totals"]})
    s = svc(w, tenant, "vic"); out["chain_ok"] = s.verify_audit()[0]; out["history"] = [h["action"] for h in s.project_history(pid)]; s.close(); wf.close()
    return out


def test_the_governed_workflow_behaves_identically_in_two_databases_and_its_run_metadata_stays_truthful(worlds):
    a, b = run_workflow(worlds[0]), run_workflow(worlds[1])
    assert a["first"] == b["first"] == "AWAITING_APPROVAL" and a["denied"] == b["denied"] == "ROLE_DENIED" and a["final"] == b["final"] == "EXECUTED"
    assert a["stages"] == b["stages"] and a["history"] == b["history"], "same stage sequence and same audited history"
    assert a["chain_ok"] is True and b["chain_ok"] is True, "audit chains verify in both"
    assert a["digest"] == b["digest"] and a["total"] == b["total"]
    assert a["corr"] != b["corr"] and a["ids"].isdisjoint(b["ids"]), "run identifiers are genuinely different executions"
    assert a["proposal_hash"] != b["proposal_hash"], "the proposal hash THE WEIR binds an approval to includes supplier ids; it is not rewritten to look identical"


# ------------------------------------------------------------------------------------------------ identical documents, independent agent databases
def test_identical_documents_give_identical_cited_evidence_in_independent_agent_databases(worlds, tmp_path):
    pytest.importorskip("agentplatform", reason="INTEGRATION UNAVAILABLE: the Production AI Agent Platform is not installed")
    from nasha_lab.growth import agent_research as AR
    w = worlds[0]; s = svc(w, "tenant-nasha"); docs = AR.supplier_documents(s.supplier_directory(AS_OF)); s.close()
    q = "Which suppliers quote the lowest published prices for the ingredients needed, and what are the verification status, data freshness and price limitations of each supplier's data? Cite the supplier records."
    loop = asyncio.new_event_loop()
    try:
        def one(i):
            a = AR.SupplierResearchAgent(w["dsn"], f"repro-agent-{i}", tmp_path / f"w{i}")
            r = loop.run_until_complete(a.research(docs, q, "v1")); loop.run_until_complete(a.close())
            return ([(EC.mask(v["doc_id"]), v["title"], hashlib.sha1(v["text"].encode()).hexdigest()[:8]) for v in r["evidence"].values()], [c["text"] for c in r["report"]["claims"]])
        runs = [one(i) for i in range(4)]
    finally:
        loop.close()
    assert all(r == runs[0] for r in runs) and runs[0][0] and runs[0][1], "the same evidence passages in the same order and the same cited claims in all four independent databases"
