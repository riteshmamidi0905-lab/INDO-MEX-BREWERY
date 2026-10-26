"""Offline adapter conformance. No vector verifier, provider or external service used."""
import ast
from dataclasses import replace
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
import pytest
from jsonschema import Draft202012Validator,FormatChecker
from showcase import operations_adapter as adapter
from showcase.operations_adapter import OfflineConfig,AdapterRefused
from test_workforce import engine,Clock,start,approve,datasets

FIXTURES=Path(__file__).parent/'fixtures/ops_vectors_v2'
NOW='2026-10-25T00:00:00Z'
ANALYSIS='00000000-0000-4000-8000-000000000001'
RUN='run-0000000001'
def vector(name):return json.loads((FIXTURES/(name+'.json')).read_text())
SCOPES=vector('identifiers')['tenants']  # Deterministic OFFLINE fixtures; never installed in host identities.

@pytest.fixture
def config():return OfflineConfig(SCOPES,NOW)

def ref_canonical(v):
    # Independent reference calculations, not the adapter's canonical/record helpers.
    return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def ref_sha(v):return hashlib.sha256(ref_canonical(v)).hexdigest()

def ref_record(scope,f):
    return {'profile':'record-hash.v1','tenant_scope_id':scope,**{k:f['provenance'][k] for k in ('source_kind','source_ref','record_id','source_revision')},**{k:f[k] for k in ('subject_id','inventory_item_id','field','availability','value','unit','as_of')}}

@pytest.mark.parametrize('case',vector('amara_adapter')['items'],ids=lambda c:c['tenant']+':'+c['scenario'])
def test_eight_cases_independent_hashes_renderer_and_contract(config,case):
    source=adapter.retain_scenario(config,case['tenant'],case['scenario'])
    result=adapter.replay(config,source,tenant=case['tenant'],analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)
    mi=result['model_input'];env=result['envelope']
    assert mi==case['expected_model_input']
    assert env['rendered_explanation']==case['shared_renderer_text']
    assert result['verification_status']==('ABSTAIN_VERIFIED' if case['scenario']=='missing-count' else 'ANSWER_VERIFIED')
    assert env['status']=='AUDIT_PENDING' and env['audit_complete'] is False
    assert env['provider'] is None and env['mode']=='DETERMINISTIC_REPLAY'
    assert not result['live_model'] and result['provider_calls']==0 and 'no model call' in result['label']
    assert not adapter.contract.result_invariants(env)
    assert ref_sha({k:mi[k] for k in ('as_of','entities','facts','comparison_groups','completeness')})==mi['snapshot_sha256']
    for f in mi['facts']:
        assert ref_sha(ref_record(SCOPES[case['tenant']],f))==f['provenance']['record_sha256']
        assert f['provenance']['source_revision']==case['scenario']+':v1'
    schema=adapter.contract.SCHEMAS['model-input.schema.json']
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(mi)
    Draft202012Validator(adapter.contract.SCHEMAS['model-output.schema.json'],format_checker=FormatChecker()).validate(env['model_output'])
    if env['model_output']['status']=='ANSWER':
        sealed=dict(schema_version='ops-explanation-output.v1',analysis_id=ANALYSIS,snapshot_sha256=mi['snapshot_sha256'],claims=env['model_output']['claims'],rendered_explanation=env['rendered_explanation'],validator_revision=result['validator_revision'],renderer_revision=result['renderer_revision'])
        assert env['accepted_result_sha256']==ref_sha(sealed)

@pytest.mark.parametrize('case',vector('canonical_json')['positive'],ids=lambda c:c['name'])
def test_canonical_json_independent(case):
    value=json.loads(case['input_json_text']);raw=adapter.canonical(value)
    assert raw==ref_canonical(value)==bytes.fromhex(case['canonical_hex'])
    assert hashlib.sha256(raw).hexdigest()==case['sha256']

@pytest.mark.parametrize('value',[1.0,float('nan'),float('inf'),{'x':60.0},{1:'bad'},'\ud800'])
def test_canonical_refuses_invalid_values(value):
    with pytest.raises((ValueError,UnicodeError)):adapter.canonical(value)

@pytest.mark.parametrize('profile',['record-hash.v0','record-hash.v9','ops-record-hash.v1',''])
def test_config_rejects_unapproved_profile(profile):
    with pytest.raises(AdapterRefused) as e:OfflineConfig(SCOPES,NOW,record_hash_profile=profile)
    assert e.value.status=='FAILED' and e.value.codes==('record_hash_profile_unsupported',)

@pytest.mark.parametrize('profile',['record-hash.v0','record-hash.v9'])
def test_snapshot_metadata_cannot_choose_profile(config,profile):
    s=replace(adapter.retain_scenario(config,'nasha-brewery','count-gap'),record_hash_profile=profile)
    with pytest.raises(AdapterRefused,match='record_hash_profile_unsupported'):adapter.model_input(config,s,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)

def rehash_source(source,data,trusted=None):
    return replace(source,snapshot_bytes=ref_canonical(data),snapshot_sha256=ref_sha(data),trusted_record_hashes=source.trusted_record_hashes if trusted is None else trusted)

@pytest.mark.parametrize('kind',['all-v0','mixed-v0','foreign-tenant','wrong-value'])
def test_recomputed_snapshot_cannot_hide_bad_source_hash(config,kind):
    s=adapter.retain_scenario(config,'nasha-brewery','count-gap');d=json.loads(s.snapshot_bytes)
    foreign=json.loads(adapter.retain_scenario(config,'meridian-fitness','count-gap').snapshot_bytes)
    for i,f in enumerate(d['facts']):
        if kind=='all-v0' or kind=='mixed-v0' and i==0:f['provenance']['record_sha256']=ref_sha({k:f[k] for k in ('subject_id','field','value','unit')})
        if kind=='foreign-tenant':f['provenance']['record_sha256']=foreign['facts'][i]['provenance']['record_sha256']
        if kind=='wrong-value' and i==0:f['value']+=1
    with pytest.raises(AdapterRefused,match='source_hash_mismatch'):adapter.model_input(config,rehash_source(s,d),tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)

def test_scoped_immutable_trusted_map(config):
    a=adapter.retain_scenario(config,'nasha-brewery','count-gap');b=adapter.retain_scenario(config,'meridian-fitness','count-gap')
    assert set(a.trusted_record_hashes)==set(b.trusted_record_hashes)
    assert dict(a.trusted_record_hashes)!=dict(b.trusted_record_hashes)
    with pytest.raises(TypeError):a.trusted_record_hashes['bad']='0'*64
    with pytest.raises(TypeError):config.tenant_scopes['new']='arbitrary'
    detached=dict(a.trusted_record_hashes);c=replace(a,trusted_record_hashes=detached);detached.clear();assert c.trusted_record_hashes
    for source in [replace(a,trusted_record_hashes={}),replace(a,trusted_record_hashes=b.trusted_record_hashes)]:
        with pytest.raises(AdapterRefused):adapter.model_input(config,source,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)
    with pytest.raises(AdapterRefused,match='cross_tenant_reference'):adapter.model_input(config,a,tenant='meridian-fitness',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)
    with pytest.raises(AdapterRefused):adapter.retain_scenario(config,'foreign','count-gap')
    with pytest.raises(AdapterRefused):adapter.retain_scenario(config,'nasha-brewery','foreign')
    changed=OfflineConfig({**SCOPES,'nasha-brewery':'00000000-0000-4000-8000-000000000099'},NOW)
    with pytest.raises(AdapterRefused):adapter.model_input(changed,a,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)

@pytest.mark.parametrize('now',['2026-10-24T00:00:00Z','2026-10-27T00:00:00Z'])
def test_stale_or_future_source_refused(config,now):
    s=adapter.retain_scenario(config,'nasha-brewery','count-gap')
    with pytest.raises(AdapterRefused,match='stale_snapshot'):adapter.replay(config,s,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=now)

@pytest.mark.parametrize('name',['ops_explanation.py','model_boundary.py'])
def test_pinned_upstream_source_and_contracts(name):
    root=Path(adapter.__file__).parent/'_ops_alignment';pins=json.loads((root/'UPSTREAM.json').read_text())
    for file,h in pins['files'].items():assert hashlib.sha256((root/file).read_bytes()).hexdigest()==h
    for line in (FIXTURES/'MANIFEST.sha256').read_text().splitlines():
        h,f=line.split(None,1);assert hashlib.sha256((FIXTURES/f.strip()).read_bytes()).hexdigest()==h

@pytest.mark.parametrize('case',vector('verdicts')['cases'],ids=lambda c:c['id'])
def test_aligned_validator_102_previously_independently_verified_vectors(case):
    vectors=vector('verdicts');mi=vectors['inputs'][case['input']];opts=dict(case['options']);raw=case.get('output_text')
    if 'output_hex'in case:raw=bytes.fromhex(case['output_hex'])
    if 'output_non_text'in case:raw=ast.literal_eval(case['output_non_text'])
    if 'output_recipe'in case:r=case['output_recipe'];raw=' '*r['prefix_spaces']+r['then']
    if 'trusted_record_hashes'in opts:
        option=opts['trusted_record_hashes'];mp={f['provenance']['record_id']+'|'+f['provenance']['source_ref']:f['provenance']['record_sha256'] for f in vectors['inputs']['gap']['facts']}
        if option=='empty':mp={}
        if option=='one-hash-wrong':mp[next(iter(mp))]='0'*64
        opts['trusted_record_hashes']=mp
    result=adapter.contract.validate_output(raw,mi,**opts)
    assert (result['status'],result['codes'],result['flags'])==(case['expected_status'],case['expected_codes'],case['expected_flags'])

def test_provider_callbacks_and_configuration_not_exposed(config,monkeypatch):
    def forbidden(*a,**kw):pytest.fail('Generic candidate/provider pipeline must not run')
    monkeypatch.setattr(adapter.contract,'explain',forbidden)
    monkeypatch.setattr(adapter.contract,'deterministic_replay',forbidden)
    s=adapter.retain_scenario(config,'nasha-brewery','count-gap')
    result=adapter.replay(config,s,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)
    assert result['provider_calls']==0
    for key,value in [('mode','LIVE_LLM'),('provider',forbidden),('record_hash_profile','record-hash.v0'),('rules',[])]:
        with pytest.raises(TypeError):adapter.replay(config,s,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW,**{key:value})

def test_existing_run_state_hashes_authorization_and_audits_unchanged(engine,config,monkeypatch):
    # Pre-existing run created by the original test fixture path, never by adapter code.
    run=start(engine);run_id=run['workflow']['corr_id'];before=engine.snapshot(run_id,'reviewer-a');db=list(engine.ledger.con.iterdump());trace=list(engine.trace.con.iterdump());events=list(engine.weir.events())
    def forbidden(*a,**kw):pytest.fail('Adapter attempted a consequential workflow operation')
    for method in ('start','decide','write_gateway'):monkeypatch.setattr(engine,method,forbidden)
    result=adapter.replay_owned_run(engine,'reviewer-a',run_id,config,analysis_id=ANALYSIS,now=NOW)
    after=engine.snapshot(run_id,'reviewer-a')
    assert result['model_input']['workflow_id']==run_id
    for key in ('action_hash','action','approval','drafts','workflow'):assert before[key]==after[key]
    assert list(engine.ledger.con.iterdump())==db and list(engine.trace.con.iterdump())==trace and list(engine.weir.events())==events
    from showcase.workforce import WorkflowDenied
    with pytest.raises(WorkflowDenied):adapter.replay_owned_run(engine,'reviewer-b',run_id,config,analysis_id=ANALYSIS,now=NOW)
    with pytest.raises(WorkflowDenied):adapter.replay_owned_run(engine,'reviewer-a','run-0000000000',config,analysis_id=ANALYSIS,now=NOW)
    assert engine.action(run_id)==before['action'] and not engine.ledger.po_drafts()


def test_source_bytes_and_config_are_copied_and_input_is_detached(config):
    s=adapter.retain_scenario(config,'nasha-brewery','count-gap');mutable=bytearray(s.snapshot_bytes)
    retained=replace(s,snapshot_bytes=mutable);mutable.clear();assert retained.snapshot_bytes==s.snapshot_bytes
    scopes=dict(SCOPES);cfg=OfflineConfig(scopes,NOW);scopes.clear();assert dict(cfg.tenant_scopes)==SCOPES
    mi=adapter.model_input(config,s,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)
    mi['facts'][0]['value']=999
    assert adapter.model_input(config,s,tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)['facts'][0]['value']==40


def test_malformed_and_profile_smuggling_source_is_refused(config):
    s=adapter.retain_scenario(config,'nasha-brewery','count-gap')
    for data in [[],None,dict(json.loads(s.snapshot_bytes),record_hash_profile='record-hash.v0')]:
        with pytest.raises(AdapterRefused):adapter.model_input(config,rehash_source(s,data),tenant='nasha-brewery',analysis_id=ANALYSIS,workflow_id=RUN,now=NOW)


def test_preexisting_approval_authorization_unchanged_by_replay(engine,config):
    from showcase.workforce import WorkflowDenied
    run=start(engine);run_id=run['workflow']['corr_id']
    def wrong_checker():
        return engine.decide('reviewer-b',run_id,run['approval']['id'],run['action_hash'],'approve')
    with pytest.raises(WorkflowDenied):wrong_checker()
    action=engine.action(run_id)
    adapter.replay_owned_run(engine,'reviewer-a',run_id,config,analysis_id=ANALYSIS,now=NOW)
    with pytest.raises(WorkflowDenied):wrong_checker()
    assert engine.action(run_id)==action and not engine.ledger.po_drafts()
    # Original authorized rejection still resolves the original hold; adapter issued no approval.
    rejected=engine.decide('reviewer-a',run_id,run['approval']['id'],run['action_hash'],'reject')
    assert rejected['workflow']['state']=='REJECTED' and not rejected['drafts']
