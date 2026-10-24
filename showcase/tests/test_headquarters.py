"""Phase 3 read-model, authentication, isolation and frontend-build regression tests."""
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import sqlite3
import threading

import pytest
from test_foundation import datasets
from showcase.hq import Headquarters,make_server
from showcase.hq_data import read_model

@pytest.fixture(scope='module')
def web(tmp_path_factory):
    spec=importlib.util.spec_from_file_location('hq_build',Path(__file__).resolve().parents[1]/'headquarters/build.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    path=tmp_path_factory.mktemp('hq-assets')/'web'
    files=module.build(path)
    assert len(files)==9
    with pytest.raises(FileExistsError):module.build(path)
    return path

@pytest.fixture(scope='module')
def app(datasets,web,tmp_path_factory):
    host=Headquarters({'nasha-brewery':datasets['nasha'],'meridian-fitness':datasets['meridian']},web,tmp_path_factory.mktemp('hq-runtime'))
    server=make_server(host,0)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    yield host,server.server_port
    server.shutdown();server.server_close();worker.join()

def request(app,method,path,body=None,cookie=None,csrf=None,origin=None,host=None):
    _,port=app
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=20)
    headers={'Content-Type':'application/json','X-Nasha-Request':'1'}
    if cookie:headers['Cookie']=cookie
    if csrf:headers['X-CSRF-Token']=csrf
    if origin:headers['Origin']=origin
    if host:headers['Host']=host
    conn.request(method,path,json.dumps(body) if body is not None else None,headers)
    response=conn.getresponse();raw=response.read();h=dict(response.getheaders());status=response.status;conn.close()
    return status,json.loads(raw) if h.get('Content-Type')=='application/json' else raw,h

def login(app):
    status,data,headers=request(app,'POST','/api/login',{'code':app[0].access_code})
    assert status==200
    assert 'HttpOnly' in headers['Set-Cookie'] and 'SameSite=Strict' in headers['Set-Cookie']
    return headers['Set-Cookie'].split(';')[0],data['csrf']

@pytest.mark.parametrize('path',['/api/session','/api/view/finance','/api/view/people','/api/view/data'])
def test_unauthenticated_data_refused(app,path):
    status,data,_=request(app,'GET',path)
    assert status==401 and 'businesses' not in data

def test_unauthenticated_business_selection_refused(app):
    assert request(app,'POST','/api/select',{'business':'meridian-fitness'})[0]==401

def test_invalid_login_origin_csrf_and_host(app):
    assert request(app,'POST','/api/login',{'code':'invalid-code'})[0]==401
    assert request(app,'POST','/api/login',{'code':app[0].access_code},origin='https://attacker.invalid')[0]==403
    assert request(app,'GET','/',host='attacker.invalid')[0]==403
    cookie,_=login(app)
    assert request(app,'POST','/api/select',{'business':'meridian-fitness'},cookie)[0]==403

def test_business_switching_and_independent_sessions(app):
    cookie,csrf=login(app);other,_=login(app)
    first=request(app,'GET','/api/view/finance',cookie=cookie)[1]
    assert first['tenant']=='nasha-brewery'
    assert request(app,'POST','/api/select',{'business':'unknown'},cookie,csrf)[0]==403
    assert request(app,'POST','/api/select',{'business':'meridian-fitness'},cookie,csrf)[0]==200
    second=request(app,'GET','/api/view/finance',cookie=cookie)[1]
    assert second['tenant']=='meridian-fitness'
    assert first['summary']['net_revenue_cents']!=second['summary']['net_revenue_cents']
    assert request(app,'GET','/api/view/finance',cookie=other)[1]['tenant']=='nasha-brewery'
    assert all(r['source_ref'].startswith(('fitness-fixture:','assumption:')) for r in second['transactions'])

@pytest.mark.parametrize('query',['tenant=meridian-fitness','path=/etc/passwd','month=2026-13','page=-1','kind=wire-payment','q=a&q=b','source=../../secret'])
def test_override_and_invalid_filters_refused(app,query):
    cookie,_=login(app)
    assert request(app,'GET','/api/view/finance?'+query,cookie=cookie)[0]==400

def test_record_search_pagination_and_source_provenance(app):
    cookie,_=login(app)
    status,data,_=request(app,'GET','/api/view/finance?kind=sale&page=0',cookie=cookie)
    assert status==200 and len(data['transactions'])==20 and data['matching']>20
    assert all(r['kind']=='sale' and len(r['event_hash'])==64 for r in data['transactions'])
    nextpage=request(app,'GET','/api/view/finance?kind=sale&page=1',cookie=cookie)[1]
    assert {t['id'] for t in data['transactions']}.isdisjoint(t['id'] for t in nextpage['transactions'])
    target=data['transactions'][0]['id']
    filtered=request(app,'GET','/api/view/finance?q='+target,cookie=cookie)[1]
    assert filtered['matching']==1 and filtered['transactions'][0]['id']==target
    no_sql=request(app,'GET',"/api/view/finance?q=%27%20OR%201%3D1--",cookie=cookie)[1]
    assert no_sql['matching']==0

def test_read_model_totals_reconcile_and_no_fixture_mutation(app,datasets):
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (datasets['nasha'],datasets['meridian'])}
    cookie,_=login(app)
    for view in ('headquarters','executive','engineering','data','finance','operations','product','crm','people','creation','playbook'):
        status,d,_=request(app,'GET','/api/view/'+view,cookie=cookie)
        assert status==200 and d['tenant']=='nasha-brewery' and d['gateway']['chain_valid']
        assert d['gateway']['consequential_actions']==0
    d=request(app,'GET','/api/view/finance',cookie=cookie)[1]
    assert sum(m['revenue'] for m in d['monthly'])==d['summary']['net_revenue_cents']
    assert sum(m['expense'] for m in d['monthly'])==d['summary']['expense_cents']
    assert sum(m['cash_change'] for m in d['monthly'])==d['summary']['cash_cents']
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in before.items())

def test_evidence_whitelist_and_no_claim_for_missing_reports(app):
    cookie,_=login(app)
    status,d,_=request(app,'GET','/api/view/engineering?source=schema',cookie=cookie)
    assert status==200 and d['document']['path']=='showcase/showcase/schema.sql'
    assert 'CREATE TABLE' in d['document']['text'] and '/6c177d7' in d['document']['github']
    assert not d['reports']

def test_logout_and_expiry(app):
    cookie,csrf=login(app)
    assert request(app,'POST','/api/logout',{},cookie,csrf)[0]==200
    assert request(app,'GET','/api/view/finance',cookie=cookie)[0]==401
    cookie,_=login(app);sid=cookie.split('=',1)[1];app[0].sessions[sid].expires=0
    assert request(app,'GET','/api/session',cookie=cookie)[0]==401

def test_static_headers_and_no_directory_or_runtime_access(app):
    status,html,headers=request(app,'GET','/')
    assert status==200 and b'NASHA AI' in html
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    assert headers['Cache-Control']=='no-store'
    for path in ('/../access-code','/access-code','/build-manifest.json','/fonts/'):
        assert request(app,'GET',path)[0]==404
    assert (app[0].state/'access-code').stat().st_mode & 0o777==0o600
