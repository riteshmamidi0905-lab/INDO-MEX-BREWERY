"""Read-only Operations HTTP, evidence and fail-closed regression coverage."""
import hashlib
import pytest
from test_headquarters import app,web,datasets,request,login
from showcase.operations import explain

@pytest.mark.parametrize('scenario,expected',[('count-gap',60),('budget-risk',80),('no-gap',0),('missing-count',None)])
def test_explanation_is_bounded(scenario,expected):
    result=explain('nasha-brewery',scenario)
    assert result['difference']==expected
    assert result['live_model'] is False
    assert result['status']==('ABSTAINED' if expected is None else 'EXPLAINED')
    assert all(r['classification']=='SYNTHETIC_SCENARIO_ASSUMPTION' for r in result['records'])
    assert len(result['snapshot_sha256'])==64


def test_operations_auth_selectors_and_tenant_binding(app,datasets):
    assert request(app,'GET','/api/view/operations?scenario=count-gap')[0]==401
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in datasets.values() if hasattr(p,'read_bytes')}
    cookie,csrf=login(app)
    first=request(app,'GET','/api/view/operations?scenario=count-gap',cookie=cookie)[1]
    assert first['gateway']['chain_valid'] and first['gateway']['read_decisions']
    assert first['operations_explanation']['difference']==60
    for query in ['scenario=unknown','scenario=count-gap&scenario=no-gap','tenant=meridian-fitness','scenario=../../secret']:
        assert request(app,'GET','/api/view/operations?'+query,cookie=cookie)[0]==400
    assert request(app,'GET','/api/view/finance?scenario=count-gap',cookie=cookie)[0]==400
    assert request(app,'POST','/api/select',{'business':'meridian-fitness'},cookie,csrf)[0]==200
    second=request(app,'GET','/api/view/operations?scenario=count-gap',cookie=cookie)[1]
    assert second['operations_explanation']['tenant']=='meridian-fitness'
    assert second['operations_explanation']['snapshot_sha256']!=first['operations_explanation']['snapshot_sha256']
    assert all(r['id'].startswith('meridian-fitness:') for r in second['operations_explanation']['records'])
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in datasets.values() if hasattr(p,'read_bytes')}


def test_gateway_failure_never_substitutes_explanation(app,monkeypatch):
    cookie,_=login(app)
    def unavailable(*args,**kwargs):raise RuntimeError('Unavailable source')
    monkeypatch.setattr(app[0],'view',unavailable)
    status,body,_=request(app,'GET','/api/view/operations',cookie=cookie)
    assert status==503 and 'operations_explanation' not in body
    assert 'no data was substituted' in body['error']


def test_invalid_gateway_audit_refuses_explanation(app,monkeypatch):
    from mcp_weir.store import Store
    cookie,_=login(app)
    monkeypatch.setattr(Store,'verify_chain',lambda self:(False,'test corruption'))
    status,body,_=request(app,'GET','/api/view/operations',cookie=cookie)
    assert status==401
    assert 'audit integrity failed' in body['error']
    assert 'operations_explanation' not in body
