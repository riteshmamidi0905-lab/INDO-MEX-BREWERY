"""Real tool/WEIR/approval integration and security-negative tests; no model inference."""
import asyncio
import hashlib
import json
from pathlib import Path
import pytest
from test_foundation import datasets
from showcase.workforce import TenantWorkforce,WorkflowDenied,DraftUpstream,StageUpstream,GRANT_TOOL
from nasha_lab.identity import Identity
from showcase.scenario import digest

class Clock:
    def __init__(self):self.now=2000000000.0
    def __call__(self):return self.now

@pytest.fixture
def engine(datasets,tmp_path):
    e=TenantWorkforce('nasha-brewery',datasets['nasha'],tmp_path/'workforce',clock=Clock())
    yield e
    e.close()

def start(e,scenario='count-gap',key='request-001'):
    return e.start('reviewer-a',scenario,key)

def approve(e,r,**overrides):
    data=dict(reviewer='reviewer-a',run_id=r['workflow']['corr_id'],approval_id=r['approval']['id'],action_hash=r['action_hash'],decision='approve')
    data.update(overrides)
    return e.decide(**data)

def test_real_platform_tools_and_weir_hold_write(engine):
    r=start(engine)
    assert r['workflow']['state']=='AWAITING_APPROVAL'
    assert r['mode']=='DETERMINISTIC_REPLAY' and not r['live_model']
    assert r['approval']['state']=='pending' and r['drafts']==[] and r['audit_valid']
    completed=[e for e in r['events'] if e['kind']=='agent_completed']
    assert [e['agent'] for e in completed]==['amara','arjun','maya']
    assert completed[1]['output']['amount_cents']==28000
    assert completed[2]['output']['recommendation']=='REVIEW_REQUIRED'
    policy=[e for e in r['events'] if e['kind']=='policy_decision']
    assert len(policy)==3 and all(e['forwarded'] and e['call_id'] for e in policy)
    assert all(e['call']['status']=='ok' and e['duration_ms']>=0 for e in completed)
    decisions=[e for e in engine.weir.events() if e['kind']=='call.decision']
    assert len(decisions)>=4

def test_valid_approval_creates_only_one_simulated_draft_and_no_financial_mutation(engine):
    before=hashlib.sha256(engine.fixture.read_bytes()).hexdigest()
    r=approve(engine,start(engine))
    assert r['workflow']['state']=='EXECUTED' and r['audit_valid']
    assert len(r['drafts'])==1 and r['drafts'][0]['state']=='DRAFT_NOT_SENT'
    assert r['drafts'][0]['approved_by']=='reviewer-a'
    assert not r['financial_fixture_mutated'] and r['external_actions']==0
    assert hashlib.sha256(engine.fixture.read_bytes()).hexdigest()==before
    assert 'grant' not in json.dumps(r['events']).lower()

def test_rejection_never_creates_effect(engine):
    r=approve(engine,start(engine),decision='reject')
    assert r['workflow']['state']=='REJECTED' and not r['drafts']

@pytest.mark.parametrize('scenario,state,agents',[('no-gap','ABSTAINED',1),('budget-risk','BLOCKED',3),('missing-count','FAILED',0)])
def test_safe_no_action_budget_and_missing_data_outcomes(engine,scenario,state,agents):
    r=start(engine,scenario)
    assert r['workflow']['state']==state and not r['drafts'] and r['approval'] is None
    assert len([e for e in r['events'] if e['kind']=='agent_completed'])==agents

def test_deterministic_outputs_replay(engine):
    a=start(engine,key='repeat-001');b=start(engine,key='repeat-002')
    outputs=lambda r:[(e['agent'],e['inputs'],e['output']) for e in r['events'] if e['kind']=='agent_completed']
    assert outputs(a)==outputs(b)

def test_start_is_idempotent_and_key_is_bound_to_inputs(engine):
    a=start(engine);b=start(engine)
    assert a['workflow']['corr_id']==b['workflow']['corr_id']
    assert len(engine.catalog('reviewer-a')['runs'])==1
    with pytest.raises(ValueError):start(engine,'budget-risk')

def test_repeated_approval_is_refused_no_duplicate_execution(engine):
    r=start(engine);approve(engine,r)
    with pytest.raises(WorkflowDenied):approve(engine,r)
    assert len(engine.ledger.po_drafts())==1

def test_another_reviewer_cannot_read_start_replay_or_approve(engine):
    r=start(engine)
    with pytest.raises(WorkflowDenied):engine.snapshot(r['workflow']['corr_id'],'reviewer-b')
    with pytest.raises(WorkflowDenied):approve(engine,r,reviewer='reviewer-b')
    with pytest.raises(WorkflowDenied):engine.start('reviewer-b','count-gap','request-001')
    assert not engine.ledger.po_drafts()

def test_cross_tenant_run_and_approval_refused(engine,datasets,tmp_path):
    r=start(engine)
    other=TenantWorkforce('meridian-fitness',datasets['meridian'],tmp_path/'other',clock=engine.clock)
    try:
        with pytest.raises(WorkflowDenied):approve(other,r)
        own=start(other)
        with pytest.raises(WorkflowDenied):approve(other,own,approval_id=r['approval']['id'])
        assert not other.ledger.po_drafts()
    finally:other.close()

@pytest.mark.parametrize('override',[{'action_hash':'0'*64},{'approval_id':'foreign-approval'},{'role':'VIEWER'}])
def test_modified_action_or_unauthorized_role_denied(engine,override):
    r=start(engine)
    with pytest.raises(WorkflowDenied):approve(engine,r,**override)
    assert not engine.ledger.po_drafts()

def test_expired_approval_fails_closed(engine):
    r=start(engine);engine.clock.now+=301
    with pytest.raises(WorkflowDenied,match='EXPIRED'):approve(engine,r)
    assert engine.ledger.run(r['workflow']['corr_id'])['state']=='FAILED'
    assert not engine.ledger.po_drafts()

def test_action_from_different_workflow_denied(engine):
    a=start(engine,key='flow-001');b=start(engine,key='flow-002')
    with pytest.raises(WorkflowDenied):approve(engine,b,approval_id=a['approval']['id'])
    assert not engine.ledger.po_drafts()

def test_direct_upstream_bypass_denied(engine):
    r=start(engine);up=DraftUpstream(engine,r['workflow']['corr_id'],r['action'])
    result=asyncio.run(up.call_tool(GRANT_TOOL,r['action'],1))
    assert result['isError'] and not engine.ledger.po_drafts()

def test_unknown_role_tool_and_modified_inputs_denied():
    u=StageUpstream('nasha-brewery','run-a','operations',lambda _: {'ok':True},{'counted':1})
    for name,args in [('create_draft_purchase_order',{'run_id':'run-a','inputs':{'counted':1}}),('analyze_inventory',{'run_id':'run-b','inputs':{'counted':1}}),('analyze_inventory',{'run_id':'run-a','inputs':{'counted':999}})]:
        assert asyncio.run(u.call_tool(name,args,1))['isError']

def test_modified_stored_proposal_fails_validation(engine):
    r=start(engine)
    engine.ledger.con.execute('UPDATE proposals SET qty=qty+1 WHERE proposal_id=?',(r['action']['proposal_id'],))
    with pytest.raises(WorkflowDenied):approve(engine,r)
    assert not engine.ledger.po_drafts()

@pytest.mark.parametrize('mutation',["DELETE FROM audit WHERE seq=(SELECT MAX(seq) FROM audit)","UPDATE audit SET detail='corrupt' WHERE seq=1"])
def test_missing_or_modified_audit_fails_closed(engine,mutation):
    r=start(engine);engine.ledger.con.execute(mutation)
    with pytest.raises(WorkflowDenied):approve(engine,r)
    assert not engine.ledger.po_drafts()

def test_missing_execution_records_fail_closed(engine):
    r=start(engine)
    engine.trace.con.execute("DELETE FROM trace_events WHERE run_id=? AND kind='agent_completed'",(r['workflow']['corr_id'],));engine.trace.con.commit()
    with pytest.raises(WorkflowDenied):approve(engine,r)
    assert not engine.ledger.po_drafts()

def test_signed_grants_bind_tool_run_reviewer_expiry_and_nonce(engine):
    r=start(engine);action=r['action'];corr=r['workflow']['corr_id'];h=digest(action)
    grant=engine.authority.issue_grant(Identity('reviewer-a','FOUNDER'),corr,[{'tool':GRANT_TOOL,'args':action,'args_hash':h}])
    assert not engine.authority.verify_grant(grant,'other-run',GRANT_TOOL,action,h)[0]
    assert not engine.authority.verify_grant(grant,corr,'execute_payment',action,h)[0]
    assert not engine.authority.verify_grant(grant,corr,GRANT_TOOL,{**action,'amount_cents':1},digest({**action,'amount_cents':1}))[0]
    ok,_,who=engine.authority.verify_grant(grant,corr,GRANT_TOOL,action,h)
    assert ok and who.id=='reviewer-a'
    assert not engine.authority.verify_grant(grant,corr,GRANT_TOOL,action,h)[0]
    engine.clock.now+=301
    assert not engine.authority.verify_grant(grant,corr,GRANT_TOOL,action,h)[0]

def test_read_timeouts_are_bounded_and_reported(datasets,tmp_path):
    calls=[]
    async def delay(role):calls.append(role);await asyncio.sleep(.1)
    e=TenantWorkforce('nasha-brewery',datasets['nasha'],tmp_path/'timeout',timeout=.02,fault=delay)
    try:
        r=start(e)
        assert r['workflow']['state']=='FAILED' and not r['drafts']
        assert 1<=len(calls)<=2
        assert any(v.get('event')=='tool.retrying' for v in r['events'])
    finally:e.close()

def test_transient_read_timeout_recovers_with_one_retry(datasets,tmp_path):
    calls=[]
    async def once(role):
        calls.append(role)
        if len(calls)==1:await asyncio.sleep(.1)
    e=TenantWorkforce('nasha-brewery',datasets['nasha'],tmp_path/'retry',timeout=.02,fault=once)
    try:
        r=start(e)
        assert r['workflow']['state']=='AWAITING_APPROVAL'
        assert len(calls)==4 and r['drafts']==[]
    finally:e.close()

@pytest.mark.parametrize('column,value',[('supplier_id','OTHER-SUPPLIER'),('inputs_hash','modified'),('est_cost_usd',1)])
def test_held_action_cannot_be_retargeted_after_prepare(engine,column,value):
    r=start(engine)
    assert column in {'supplier_id','inputs_hash','est_cost_usd'}
    engine.ledger.con.execute(f'UPDATE proposals SET {column}=? WHERE proposal_id=?',(value,r['action']['proposal_id']))
    changed=engine.action(r['workflow']['corr_id'])
    with pytest.raises(WorkflowDenied):approve(engine,r,action_hash=digest(changed))
    assert not engine.ledger.po_drafts()

def test_lost_write_response_reconciles_existing_draft_without_duplicate(engine):
    r=start(engine)
    original=engine.write_gateway
    def wrap(corr,action,context=None):
        gateway=original(corr,action,context)
        if context:
            call=gateway.call_tool_detailed
            async def lost(session,tool,args):
                outcome=await call(session,tool,args)
                if outcome.forwarded and not outcome.result.get('isError'):raise asyncio.TimeoutError()
                return outcome
            gateway.call_tool_detailed=lost
        return gateway
    engine.write_gateway=wrap
    result=approve(engine,r)
    assert result['workflow']['state']=='EXECUTED' and len(result['drafts'])==1
    assert any(e['kind']=='recovery' and e['result']=='RECONCILED_EXISTING_DRAFT' for e in result['events'])
    with pytest.raises(WorkflowDenied):approve(engine,r)
    assert len(engine.ledger.po_drafts())==1

def test_failed_write_never_assumes_success_and_requires_new_approval(engine):
    r=start(engine)
    original=engine.write_gateway
    def wrap(corr,action,context=None):
        gateway=original(corr,action,context)
        if context:
            async def failure(*args):raise asyncio.TimeoutError()
            gateway.call_tool_detailed=failure
        return gateway
    engine.write_gateway=wrap
    with pytest.raises(WorkflowDenied):approve(engine,r)
    assert engine.ledger.run(r['workflow']['corr_id'])['state']=='FAILED'
    assert not engine.ledger.po_drafts()

def test_signed_grant_from_another_tenant_authority_is_invalid(engine):
    from nasha_lab.identity import Authority
    r=start(engine);action=r['action'];corr=r['workflow']['corr_id']
    grant=engine.authority.issue_grant(Identity('reviewer-a','FOUNDER'),corr,[{'tool':GRANT_TOOL,'args':action,'args_hash':digest(action)}])
    other_tenant=Authority({},clock=engine.clock)
    ok,reason,_=other_tenant.verify_grant(grant,corr,GRANT_TOOL,action,digest(action))
    assert not ok and reason=='BAD_SIGNATURE'
