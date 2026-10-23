"""Supplier intelligence (Milestone 4): independent evaluation of duplicate detection, classification, service-area matching and quote-category separation (labelled cases + mutants), and the database/API behaviour
around structured, dated supplier sources, the duplicate guard, tenant isolation and honest verification status. SYNTHETIC tenants; the three real supplier leads carry only public-search provenance; nobody is contacted."""
import re
from datetime import date

import pytest

from nasha_lab.growth import supplier_eval as E, supplier_intel as SI

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, demo as DM

A, B = "tenant-nasha", "tenant-fit"
AS_OF = date(2026, 10, 23)


# ---------------------------------------------------------------- pure evaluation
def test_the_labelled_evaluation_meets_its_thresholds_with_no_failures_on_the_real_rules():
    r = E.run_eval()
    assert r["dedupe"]["false_positive"] == 0 and r["dedupe"]["false_negative"] == 0 and r["dedupe"]["cases"] >= 20
    assert r["classification"]["accuracy"] == 1.0 and r["classification"]["cases"] >= 15
    assert r["service_area"]["accuracy"] == 1.0 and r["service_area"]["cases"] >= 12
    assert r["quote_provenance"]["failed"] == []


def test_each_supplier_intelligence_mutant_is_caught_by_the_probe_aimed_at_it():
    m = E.run_mutants()
    assert set(m["baseline_failures"].values()) == {0}, "the probes must all pass on the unmutated rules"
    assert len(m["mutants"]) >= 11 and all(x["killed"] for x in m["mutants"]), [x["name"] for x in m["mutants"] if not x["killed"]]


def test_mutants_are_restored_after_use_and_leave_no_residue():
    before = (SI.duplicate_score, SI.quote_matrix, SI.classify, SI.area_match, SI.DUPLICATE_THRESHOLD, SI.LEGAL_SUFFIXES.copy())
    E.run_mutants()
    after = (SI.duplicate_score, SI.quote_matrix, SI.classify, SI.area_match, SI.DUPLICATE_THRESHOLD, SI.LEGAL_SUFFIXES.copy())
    assert before == after


def test_duplicate_rules_on_named_cases_and_domains_are_normalised_not_guessed():
    f = lambda a, b, u=None, v=None: SI.duplicate_score(dict(name=a, website_url=u), dict(name=b, website_url=v))[0] >= SI.DUPLICATE_THRESHOLD
    assert f("Brothers Produce", "Brothers Produce Inc.") and f("Farm to Table LLC", "Farm To Table, L.L.C.")
    assert not f("Austin Fresh Produce", "Austin Fresh Seafood") and not f("Synthetic Supplier 01", "Synthetic Supplier 02")
    assert f("A Co", "Totally Different", "https://www.same.test/x", "https://same.test/y") and not f("A Co", "Totally Different", "https://a.test", "https://b.test")
    assert SI.domain("https://WWW.Example.com:8443/p?q=1") == "example.com" and SI.domain("not a url") is None and SI.domain(None) is None


def test_quote_matrix_never_ranks_categories_together_and_reports_every_exclusion():
    c = E.quote_cases()
    assert all(c.values()), [k for k, v in c.items() if not v]


# ---------------------------------------------------------------- database and HTTP
@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import pixeltable_pgserver as pg
    root = tmp_path_factory.mktemp("gsi")
    try:
        srv = pg.get_server(str(root / "pg"), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    dsn = srv.get_uri()
    envs = DM.build(root / "d", dsn, schema="growth_si", with_warehouse=False)
    yield TestClient(GA.create_growth_app(envs, as_of=AS_OF)), envs, dsn
    srv.cleanup()


def H(envs, t, u, **x):
    return {"Authorization": "Bearer " + envs[t].authority.login(u, f"{t}-{u}-dev-passcode"), **x}


def intel(world, t=A, u="vic", project=True):
    c, envs, _ = world
    p = c.get(f"/v1/tenants/{t}/projects", headers=H(envs, t, "ada")).json()["items"][0]["id"] if project else None
    return c.get(f"/v1/tenants/{t}/supplier-intelligence" + (f"?project_id={p}" if p else ""), headers=H(envs, t, u))


def sql(world, q, params=()):
    _, _, dsn = world
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute('SET search_path TO "growth_si", pg_catalog, public')
        return c.execute(q, params).fetchall()


def test_real_leads_are_never_verified_have_no_price_no_contact_and_only_dated_search_snippet_sources(world):
    cards = {x["name"]: x for x in intel(world).json()["cards"]}
    for n in ("Brothers Produce", "Hill Country Dairies", "Farm to Table LLC"):
        x = cards[n]
        assert x["information_category"] == "unverified_public_lead" and x["official_website_verified"] is False and x["official_website"] is None and x["public_channels"] == []
        assert x["price_categories"] == {"none_published": 1} and x["area"]["level"] == "explicit" and x["freshness"] == "unverified"
        assert len(x["sources"]) >= 2 and all(s["access"] == "search_snippet" and str(s["observed_on"]) == "2026-10-23" and s["url"].startswith("https://") for s in x["sources"])
        assert not [s for s in x["sources"] if s["kind"] in ("official_site", "contact_page")], "no official site or contact page was found, so none may be recorded"
    assert not [x for x in cards.values() if x["information_category"] == "verified_supplier_information"], "nothing in the directory is verified"
    syn = [x for x in cards.values() if x["information_category"] == "synthetic_fixture"]
    assert len(syn) == 8 and all(x["area"]["level"] == "not_applicable" and "synthetic_quotation" in x["price_categories"] for x in syn)


def test_the_quote_matrix_over_http_labels_every_price_and_ranks_nothing_across_categories(world):
    q = intel(world).json()["quotes"]
    assert q["as_of"] == "2026-10-23" and "never compared" in q["rule"] and q["rows"]
    for r in q["rows"]:
        assert r["cross_category_ranking"] is None and set(r["categories"]) <= {"synthetic_quotation"}, "only synthetic quotations exist in this data"
        flagged = [e for e in r["categories"]["synthetic_quotation"] if e.get("cheapest_in_category")]
        assert len(flagged) == 1 and flagged[0]["unit_price_cents"] == min(e["unit_price_cents"] for e in r["categories"]["synthetic_quotation"])
    assert intel(world).json()["duplicates"] == []


def test_the_schema_refuses_unsafe_or_malformed_source_records_whoever_writes_them(world):
    c, envs, _ = world
    sid = next(x["id"] for x in intel(world).json()["cards"] if x["name"] == "Brothers Produce")
    base = f"/v1/tenants/{A}/suppliers/{sid}/sources"
    ok = dict(kind="press", url="https://example.test/news", claim="Trade press mentions the business.", access="search_snippet", observed_on="2026-10-23")
    assert c.post(base, json={**ok, "url": "http://insecure.test/x"}, headers=H(envs, A, "ada")).status_code == 422
    assert c.post(base, json={**ok, "kind": "rumour"}, headers=H(envs, A, "ada")).status_code == 422
    assert c.post(base, json={**ok, "access": "phoned"}, headers=H(envs, A, "ada")).status_code == 422
    assert c.post(base, json={**ok, "tenant_id": B}, headers=H(envs, A, "ada")).status_code == 422
    for bad in ("Call the owner on 512-555-0123 for a quote.", "Email buyer@example.test for prices."):
        r = c.post(base, json={**ok, "claim": bad}, headers=H(envs, A, "ada"))
        assert r.status_code in (409, 422) and "512-555" not in r.text, "a contact detail cannot be stored in a source claim"
    assert sql(world, "SELECT count(*) FROM supplier_sources WHERE claim ~ '@' OR claim ~ '[0-9]{3}[-. ]?[0-9]{3,4}'")[0][0] == 0


def test_adding_a_source_is_role_checked_audited_and_visible_with_its_provenance(world):
    c, envs, _ = world
    sid = next(x["id"] for x in intel(world).json()["cards"] if x["name"] == "Hill Country Dairies")
    body = dict(kind="trade_directory", url="https://example.test/directory/hcd", claim="Listed in a trade directory as a dairy distributor.", access="search_snippet", observed_on="2026-10-23")
    assert c.post(f"/v1/tenants/{A}/suppliers/{sid}/sources", json=body, headers=H(envs, A, "vic")).status_code == 403
    r = c.post(f"/v1/tenants/{A}/suppliers/{sid}/sources", json=body, headers=H(envs, A, "ana"))
    assert r.status_code == 201
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='supplier.add' AND decision='allow' AND entity='supplier_sources' AND entity_id=%s", (A, r.json()["id"]))[0][0] == 1
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='supplier.add' AND decision='deny' AND actor='vic'", (A,))[0][0] >= 1
    assert any(s["url"] == body["url"] for x in intel(world).json()["cards"] if x["id"] == sid for s in x["sources"])
    assert c.post(f"/v1/tenants/{A}/suppliers/{sid}/sources", json=body, headers=H(envs, A, "ana")).status_code in (409, 422), "the same claim from the same URL is not stored twice"


def test_supplier_data_and_sources_never_cross_tenants(world):
    c, envs, _ = world
    nasha = {x["id"]: x["name"] for x in intel(world).json()["cards"]}
    fit = {x["id"]: x["name"] for x in intel(world, B, "ada").json()["cards"]}
    assert not set(nasha) & set(fit) and not any("Brothers" in n for n in fit.values())
    sid = next(i for i, n in nasha.items() if n == "Brothers Produce")
    body = dict(kind="press", url="https://example.test/x", claim="A claim about someone else's supplier.", access="search_snippet", observed_on="2026-10-23")
    r = c.post(f"/v1/tenants/{B}/suppliers/{sid}/sources", json=body, headers=H(envs, B, "ada"))
    assert r.status_code in (404, 409, 422) and r.status_code != 201
    assert c.get(f"/v1/tenants/{A}/supplier-intelligence", headers=H(envs, B, "ada")).status_code in (401, 403)
    assert sql(world, "SELECT count(*) FROM supplier_sources WHERE tenant_id=%s AND url='https://example.test/x'", (B,))[0][0] == 0


def test_a_probable_duplicate_supplier_is_refused_and_recorded_unless_a_person_confirms_it_is_distinct(world):
    c, envs, _ = world
    new = dict(name="Brothers Produce, Inc.", category="Produce distribution", service_area="Texas", verification_status="lead_unverified", source_kind="search_result", source_url="https://example.test/b")
    n0 = sql(world, "SELECT count(*) FROM suppliers WHERE tenant_id=%s", (A,))[0][0]
    r = c.post(f"/v1/tenants/{A}/suppliers", json=new, headers=H(envs, A, "ada"))
    assert r.status_code in (409, 422) and "duplicate" in r.text.lower()
    assert sql(world, "SELECT count(*) FROM suppliers WHERE tenant_id=%s", (A,))[0][0] == n0
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='supplier.add' AND decision='deny' AND detail->>'why' LIKE 'possible duplicate%%'", (A,))[0][0] >= 1
    r2 = c.post(f"/v1/tenants/{A}/suppliers", json={**new, "confirm_distinct": True}, headers=H(envs, A, "ada"))
    assert r2.status_code == 201 and sql(world, "SELECT count(*) FROM suppliers WHERE tenant_id=%s", (A,))[0][0] == n0 + 1
    assert any(d["a_name"].startswith("Brothers") and d["b_name"].startswith("Brothers") for d in intel(world).json()["duplicates"]), "the confirmed pair is still reported so a person can merge or retire one"
    assert c.post(f"/v1/tenants/{A}/suppliers", json={**new, "name": "Entirely Different Name Co", "source_url": "https://example.test/c"}, headers=H(envs, A, "sam")).status_code == 403


def test_verified_status_still_requires_a_website_a_source_and_a_date_in_the_database(world):
    _, _, dsn = world
    with psycopg.connect(dsn, autocommit=True) as con:
        con.execute('SET search_path TO "growth_si", pg_catalog, public')
        con.execute("SELECT set_config('app.tenant_id', %s, false)", (A,))
        with pytest.raises(psycopg.errors.IntegrityError):
            con.execute("INSERT INTO suppliers (tenant_id,id,name,category,service_area,verification_status,source_kind) VALUES (%s,'sup-forged01','Forged Co','Produce','Austin','verified_public','search_result')", (A,))
    assert re.fullmatch(r"\d+", str(sql(world, "SELECT count(*) FROM suppliers WHERE name='Forged Co'")[0][0]))
    assert sql(world, "SELECT count(*) FROM suppliers WHERE name='Forged Co'")[0][0] == 0
