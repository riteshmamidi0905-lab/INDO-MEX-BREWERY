import threading
import pytest
from test_foundation import datasets
from test_headquarters import web,request,login
from showcase.hq import Headquarters,make_server

@pytest.fixture(scope='module')
def app(datasets,web,tmp_path_factory):
    root=tmp_path_factory.mktemp('governed-host')
    host=Headquarters({'nasha-brewery':datasets['nasha'],'meridian-fitness':datasets['meridian']},web,root/'host',workforce_state=root/'workflow-state')
    server=make_server(host,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield host,server.server_port
    server.shutdown();server.server_close();thread.join();host.workforce.close()

def begin(app,cookie,csrf,key='http-flow-001',scenario='count-gap'):
    status,run,_=request(app,'POST','/api/workflows/start',{'scenario':scenario,'idempotency_key':key},cookie,csrf)
    assert status==200
    return run

def review_body(r,decision='approve'):
    return dict(run=r['workflow']['corr_id'],approval_id=r['approval']['id'],action_hash=r['action_hash'],decision=decision)

@pytest.mark.parametrize('method,path,body',[('GET','/api/workflows',None),('GET','/api/workflows?run=unknown',None),('POST','/api/workflows/start',{'scenario':'count-gap','idempotency_key':'no-auth-001'}),('POST','/api/workflows/review',{})])
def test_workflow_api_requires_authentication(app,method,path,body):
    assert request(app,method,path,body)[0]==401

def test_csrf_and_origin_required_for_start(app):
    cookie,csrf=login(app)
    body={'scenario':'count-gap','idempotency_key':'csrf-start-001'}
    assert request(app,'POST','/api/workflows/start',body,cookie)[0]==403
    assert request(app,'POST','/api/workflows/start',body,cookie,csrf,origin='https://attacker.invalid')[0]==403

def test_http_approve_and_reject_bound_actions(app):
    cookie,csrf=login(app)
    r=begin(app,cookie,csrf,'approve-http-001')
    assert r['workflow']['state']=='AWAITING_APPROVAL' and not r['drafts']
    result=request(app,'POST','/api/workflows/review',review_body(r),cookie,csrf)
    assert result[0]==200 and result[1]['workflow']['state']=='EXECUTED'
    assert len(result[1]['drafts'])==1
    assert request(app,'POST','/api/workflows/review',review_body(r),cookie,csrf)[0]==401
    rejected=begin(app,cookie,csrf,'reject-http-001')
    result=request(app,'POST','/api/workflows/review',review_body(rejected,'reject'),cookie,csrf)
    assert result[0]==200 and result[1]['workflow']['state']=='REJECTED' and not result[1]['drafts']

def test_http_session_and_tenant_isolation(app):
    cookie,csrf=login(app);other,other_csrf=login(app)
    r=begin(app,cookie,csrf,'isolation-http-001')
    assert request(app,'GET','/api/workflows?run='+r['workflow']['corr_id'],cookie=other)[0]==401
    assert request(app,'POST','/api/workflows/review',review_body(r),other,other_csrf)[0]==401
    assert request(app,'POST','/api/select',{'business':'meridian-fitness'},cookie,csrf)[0]==200
    assert request(app,'GET','/api/workflows?run='+r['workflow']['corr_id'],cookie=cookie)[0]==401
    assert request(app,'POST','/api/workflows/review',review_body(r),cookie,csrf)[0]==401
    catalog=request(app,'GET','/api/workflows',cookie=cookie)[1]
    assert catalog['tenant']=='meridian-fitness' and catalog['runs']==[]

def test_http_tenant_role_effect_and_payload_overrides_refused(app):
    cookie,csrf=login(app)
    for extra in ({'tenant':'meridian-fitness'},{'role':'FOUNDER'},{'effect':'SEND_ORDER'},{'amount_cents':1}):
        body={'scenario':'count-gap','idempotency_key':'override-http-001',**extra}
        assert request(app,'POST','/api/workflows/start',body,cookie,csrf)[0]==400
    assert request(app,'GET','/api/workflows?tenant=meridian-fitness',cookie=cookie)[0]==400
    r=begin(app,cookie,csrf,'tamper-http-001')
    bad={**review_body(r),'action_hash':'0'*64}
    assert request(app,'POST','/api/workflows/review',bad,cookie,csrf)[0]==401
    assert request(app,'POST','/api/workflows/review',{**review_body(r),'args':{'amount_cents':1}},cookie,csrf)[0]==400
    snapshot=request(app,'GET','/api/workflows?run='+r['workflow']['corr_id'],cookie=cookie)[1]
    assert snapshot['workflow']['state']=='AWAITING_APPROVAL' and not snapshot['drafts']

def test_workflow_catalog_never_claims_model_execution(app):
    cookie,_=login(app)
    d=request(app,'GET','/api/workflows',cookie=cookie)[1]
    assert not d['live_model'] and d['mode']=='DETERMINISTIC_REPLAY'
    assert len(d['agents'])==3 and len(d['scenarios'])==4
