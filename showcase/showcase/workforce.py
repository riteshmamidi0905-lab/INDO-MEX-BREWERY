"""Fixed procurement demonstration over existing ToolExecutor, THE WEIR and Ledger.
DETERMINISTIC_REPLAY, not LLM inference. No financial fixture writes or transmission.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time

from pydantic import BaseModel,ConfigDict,Field
from agentplatform.config import Settings
from agentplatform.tools.base import Tool,ToolRegistry,ToolContext,ToolResult,ToolError,Risk
from agentplatform.orchestrator.executor import ToolExecutor,ToolFailure
from agentplatform.telemetry import Tracer
from mcp_weir.gateway import Gateway
from mcp_weir.policy import parse_policy
from mcp_weir.store import Store as WeirStore
from nasha_lab.identity import Authority,Identity
from nasha_lab.governed.ledger import Ledger
from nasha_lab.trace import Store as TraceStore
from nasha_lab.governed.weir_bridge import policy_for,PROC_TOOL
from .scenario import canonical,digest,summary

MODE='DETERMINISTIC_REPLAY'
GRANT_TOOL='create_draft_purchase_order'
SCENARIOS={
 'count-gap':{'title':'Count discrepancy / replenishment','expected':100,'counted':40,'target':120,'unit_cost_cents':350,'budget_cents':50000},
 'budget-risk':{'title':'Count discrepancy / budget exceeded','expected':100,'counted':20,'target':120,'unit_cost_cents':750,'budget_cents':20000},
 'no-gap':{'title':'Balanced count / no action','expected':100,'counted':100,'target':120,'unit_cost_cents':350,'budget_cents':50000},
 'missing-count':{'title':'Missing count / fail closed','expected':100,'counted':None,'target':120,'unit_cost_cents':350,'budget_cents':50000},
}
AGENTS={'operations':('amara','Operations','analyze_inventory'),'procurement':('arjun','Procurement','prepare_replenishment'),'finance':('maya','Finance','assess_finance')}

class WorkflowDenied(PermissionError):pass

class OpsOutput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    discrepancy:int=Field(ge=0)
    counted:int=Field(ge=0)
    need:int=Field(ge=0)
    status:str

class ProposalOutput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    quantity:int=Field(gt=0)
    amount_cents:int=Field(gt=0)
    unit_cost_cents:int=Field(gt=0)
    supplier_id:str
    price_class:str

class FinanceOutput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    proposed_cents:int=Field(gt=0)
    budget_cents:int=Field(ge=0)
    modeled_cash_cents:int
    cash_after_hypothetical_cents:int
    recommendation:str

class CallArgs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    run_id:str
    inputs:dict

class GatewayRead(Tool):
    risk=Risk.READ
    args_model=CallArgs
    def __init__(self,name,gateway,session,decision_callback=None):
        self.name,self.gateway,self.session=name,gateway,session
        self.decision_callback=decision_callback
        self.description='Bound deterministic scenario read through THE WEIR; no LLM inference.'
    async def run(self,args,ctx):
        result=await self.gateway.call_tool_detailed(self.session,'workforce__'+self.name,args.model_dump())
        if self.decision_callback:self.decision_callback(result)
        if not result.forwarded or result.result.get('isError'):
            raise ToolError('Gateway read refused or malformed')
        data=json.loads(result.result['content'][0]['text'])
        return ToolResult(text='Deterministic '+self.name,data=data)

class StageUpstream:
    name='workforce'
    def __init__(self,tenant,run_id,role,compute,expected,fault=None):
        self.tenant,self.run_id,self.role=tenant,run_id,role
        self.compute,self.expected,self.fault=compute,expected,fault
    async def start(self):pass
    async def close(self):pass
    async def list_tools(self):
        return [{'name':AGENTS[self.role][2],'description':'Deterministic role-bound synthetic analysis','inputSchema':CallArgs.model_json_schema()}]
    async def call_tool(self,name,args,timeout):
        if name!=AGENTS[self.role][2] or args!={'run_id':self.run_id,'inputs':self.expected}:
            return {'content':[{'type':'text','text':'denied: role, inputs or workflow binding mismatch'}],'isError':True}
        if self.fault:await self.fault(self.role)
        data=self.compute(self.expected)
        return {'content':[{'type':'text','text':json.dumps(data)}],'isError':False}

class DraftUpstream:
    """Only a signed, exact, unexpired, reviewer-bound WEIR call can reach the ledger."""
    name='procurement'
    def __init__(self,engine,run_id,action,context=None):
        self.engine,self.run_id,self.action,self.context=engine,run_id,action,context
    async def start(self):pass
    async def close(self):pass
    async def list_tools(self):
        return [{'name':GRANT_TOOL,'description':'Record a SIMULATED DRAFT_NOT_SENT action only; never purchases or changes inventory.','inputSchema':{'type':'object','additionalProperties':True}}]
    async def call_tool(self,name,args,timeout):
        try:
            if name!=GRANT_TOOL or args!=self.action or not self.context:raise WorkflowDenied('NO_BOUND_APPROVAL')
            e=self.engine;run=e.ledger.run(self.run_id)
            if not run or run['state']!='APPROVED':raise WorkflowDenied('NOT_APPROVED')
            e.require_integrity(self.run_id,approved=True)
            ctx=self.context
            if ctx['reviewer']!=run['requester'] or args['tenant_id']!=e.tenant:raise WorkflowDenied('APPROVER_OR_TENANT_MISMATCH')
            ok,reason,identity=e.authority.verify_grant(ctx['grant'],self.run_id,GRANT_TOOL,args,digest(args))
            if not ok or identity.id!=ctx['reviewer']:raise WorkflowDenied(reason or 'REVIEWER_MISMATCH')
            approval=e.weir.get_approval(ctx['approval_id'])
            if not approval or approval.session_id!=self.run_id or approval.resolved_by!=ctx['reviewer'] or approval.expires<e.clock():raise WorkflowDenied('WEIR_APPROVAL_MISMATCH')
            draft,duplicate=e.ledger.create_po_draft(run['proposal_id'],ctx['approval_id'],identity.id,args['idempotency_key'],self.run_id)
            return {'content':[{'type':'text','text':json.dumps({'draft_id':draft,'state':'DRAFT_NOT_SENT','simulated':True,'duplicate':duplicate})}],'isError':False}
        except WorkflowDenied as error:
            return {'content':[{'type':'text','text':'denied: '+str(error)}],'isError':True}

class TenantWorkforce:
    def __init__(self,tenant,fixture,state,clock=time.time,ttl=300,timeout=3.0,fault=None,reports=()):
        self.tenant,self.fixture,self.clock,self.ttl=tenant,Path(fixture),clock,ttl
        self.timeout,self.fault=timeout,fault
        self.reports=tuple(reports)
        self.state=Path(state);self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.lock=threading.RLock()
        self.ledger=Ledger(self.state/'procurement-ledger.db',tenant,clock)
        self.weir=WeirStore(str(self.state/'workforce-weir.db'),clock)
        self.trace=TraceStore(str(self.state/'workforce-trace.db'))
        self.authority=Authority({},grant_ttl=ttl,clock=clock)
    def close(self):
        self.ledger.close();self.weir.close();self.trace.con.close()
    def context(self,run_id):
        for row in self.ledger.audit_rows(run_id):
            if row['action']=='phase4.context':return json.loads(row['detail'])
        raise WorkflowDenied('MISSING_CONTEXT_AUDIT')
    def owned(self,run_id,reviewer):
        run=self.ledger.run(run_id)
        if not run or run['requester']!=reviewer:
            self.ledger.audit(reviewer,None,'phase4.access_denied',None,run_id,'Unknown or ungranted workflow')
            raise WorkflowDenied('WORKFLOW_NOT_GRANTED')
        return run
    def event(self,run_id,kind,actor='system',**data):
        body={'tenant_id':self.tenant,'workflow_id':run_id,'correlation_id':run_id,'mode':MODE,**data}
        self.ledger.audit(actor,None,'phase4.'+kind,run_id,'',canonical(body))
        self.trace.trace(run_id).event(kind,actor=actor,**body)
    def cash(self):
        with sqlite3.connect(self.fixture.resolve().as_uri()+'?mode=ro',uri=True) as con:return summary(con,self.tenant)['cash_cents']
    def action(self,run_id):
        run=self.ledger.run(run_id);p=self.ledger.proposal(run['proposal_id'])
        return {'tenant_id':self.tenant,'run_id':run_id,'proposal_id':p['proposal_id'],'quantity':int(p['qty']),'amount_cents':round(p['est_cost_usd']*100),'supplier_id':p['supplier_id'],'effect':'DRAFT_NOT_SENT','idempotency_key':'phase4:'+run_id,'inputs_hash':p['inputs_hash']}
    def require_integrity(self,run_id,approved=False):
        if not self.ledger.verify_audit()[0] or not self.weir.verify_chain()[0]:raise WorkflowDenied('AUDIT_CHAIN_INVALID')
        audits=self.ledger.audit_rows(run_id)
        required={'phase4.context','phase4.agent_completed','proposal_created','phase4.approval_requested'}
        if approved:required.add('phase4.human_approved')
        if not required<={r['action'] for r in audits}:raise WorkflowDenied('MISSING_AUDIT_RECORDS')
        completed=[json.loads(r['detail']) for r in audits if r['action']=='phase4.agent_completed']
        if [r['agent'] for r in completed]!=['amara','arjun','maya']:raise WorkflowDenied('INCOMPLETE_AGENT_AUDIT')
        requested=[json.loads(r['detail']) for r in audits if r['action']=='phase4.approval_requested']
        if len(requested)!=1 or requested[0]['action']!=self.action(run_id) or requested[0]['action_hash']!=digest(self.action(run_id)):
            raise WorkflowDenied('ACTION_DIFFERS_FROM_HELD_PROPOSAL')
        if requested[0]['approval_id']!=self.ledger.run(run_id)['approval_id']:
            raise WorkflowDenied('APPROVAL_AUDIT_MISMATCH')
        context=self.context(run_id)
        if self.cash()!=context['cash_cents']:raise WorkflowDenied('STALE_FINANCIAL_CONTEXT')
        p=self.ledger.proposal(self.ledger.run(run_id)['proposal_id'])
        proposal=completed[1]['output'];finance=completed[2]['output']
        if finance['recommendation']!='REVIEW_REQUIRED' or round(p['est_cost_usd']*100)!=proposal['amount_cents'] or int(p['qty'])!=proposal['quantity']:
            raise WorkflowDenied('MODIFIED_PROPOSAL')
        traces=self.trace.events(run_id)
        if len([r for r in traces if r['kind']=='agent_completed'])!=3:raise WorkflowDenied('MISSING_EXECUTION_TRACE')
    async def step(self,run_id,role,inputs,compute,output_model):
        agent,_,tool_name=AGENTS[role]
        self.event(run_id,'agent_started',actor=agent,agent=agent,role=role,inputs=inputs)
        upstream=StageUpstream(self.tenant,run_id,role,compute,inputs,self.fault)
        policy=policy_for('QUALITY_LEAD',self.ttl)
        policy['tools']={'workforce__'+tool_name:{'effect':'read','result':{'conf':'internal'}}}
        policy['upstreams']={'workforce':{'command':['python','-c','pass']}}
        gateway=Gateway(parse_policy(policy),self.weir,{'workforce':upstream},clock=self.clock)
        await gateway.start()
        try:
            session=gateway.open_session(run_id+':'+role)
            registry=ToolRegistry()
            def record_policy(result):
                self.event(run_id,'policy_decision',actor=agent,agent=agent,tool='workforce__'+tool_name,call_id=result.call_id,forwarded=result.forwarded,codes=result.codes,approval_id=result.approval_id)
            registry.register(GatewayRead(tool_name,gateway,session,record_policy))
            executor=ToolExecutor(registry,Settings(tool_timeout_s=self.timeout,tool_retries=1),None)
            async def emit(kind,**data):self.event(run_id,'tool_call',actor=agent,event=kind,**data)
            started=time.perf_counter()
            result,record=await executor.call(tool_name,{'run_id':run_id,'inputs':inputs},ToolContext(run_id,None,None),emit=emit,tracer=Tracer(),approval_mode='consequential')
            output=output_model.model_validate(result.data).model_dump()
            self.event(run_id,'agent_completed',actor=agent,agent=agent,role=role,inputs=inputs,output=output,tool=tool_name,call=record.model_dump(),duration_ms=round((time.perf_counter()-started)*1000,2))
            return output
        finally:await gateway.close()
    def start(self,reviewer,scenario_id,key):
        if scenario_id not in SCENARIOS or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',key):raise ValueError('Invalid scenario or idempotency key')
        with self.lock:
            existing=self.ledger.con.execute('SELECT corr_id FROM runs WHERE tenant_id=? AND idem_key=?',(self.tenant,key)).fetchone()
            if existing:
                run=self.owned(existing[0],reviewer)
                if self.context(run['corr_id'])['scenario_id']!=scenario_id:raise ValueError('Idempotency key belongs to different inputs')
                return self.snapshot(run['corr_id'],reviewer)
            corr=self.trace.create_run('phase4:'+scenario_id,request_id=key)
            self.ledger.start_run(corr,reviewer,'FOUNDER','SYNTHETIC-SITE','SYNTHETIC-STOCK',key)
            scenario=dict(SCENARIOS[scenario_id])
            scenario['item']='Fictional packaging units' if self.tenant=='nasha-brewery' else 'Fictional towel units'
            context={'scenario_id':scenario_id,'scenario':scenario,'cash_cents':self.cash(),'assumption':'Injected inventory snapshot; unit cost and budget are hypothetical, not foundation inventory observations or supplier quotes.'}
            self.event(corr,'context',**context)
            try:asyncio.run(self._prepare(corr,context))
            except Exception as error:
                code='TOOL_TIMEOUT' if isinstance(error,ToolFailure) and 'TIMEOUT' in str(error.failure).upper() else type(error).__name__
                self.event(corr,'failure',error=code,detail='Execution stopped. No fixture mutation or supplier transmission occurred.')
                self.ledger.set_state(corr,'FAILED',failure=code)
                self.trace.set_status(corr,'FAILED',code,True)
            return self.snapshot(corr,reviewer)
    async def _prepare(self,corr,context):
        scenario=context['scenario']
        def analyze(data):
            if data['counted'] is None:raise ValueError('Missing count requires verification')
            discrepancy=max(0,data['expected']-data['counted'])
            return OpsOutput(discrepancy=discrepancy,counted=data['counted'],need=max(0,data['target']-data['counted']),status='DISCREPANCY' if discrepancy else 'NO_ACTION').model_dump()
        ops=await self.step(corr,'operations',scenario,analyze,OpsOutput)
        self.ledger.set_state(corr,'EVIDENCE_COLLECTED')
        if not ops['discrepancy']:
            self.ledger.set_state(corr,'ABSTAINED');self.trace.set_status(corr,'COMPLETED','NO_ACTION',True);return
        procurement=await self.step(corr,'procurement',{'need':ops['need'],'unit_cost_cents':scenario['unit_cost_cents']},lambda d:ProposalOutput(quantity=d['need'],amount_cents=d['need']*d['unit_cost_cents'],unit_cost_cents=d['unit_cost_cents'],supplier_id='SYN-WORKFLOW-SUPPLIER',price_class='PLANNING_ASSUMPTION').model_dump(),ProposalOutput)
        finance=await self.step(corr,'finance',{'proposed_cents':procurement['amount_cents'],'budget_cents':scenario['budget_cents'],'modeled_cash_cents':context['cash_cents']},lambda d:FinanceOutput(**d,cash_after_hypothetical_cents=d['modeled_cash_cents']-d['proposed_cents'],recommendation='REVIEW_REQUIRED' if d['proposed_cents']<=min(d['budget_cents'],d['modeled_cash_cents']) else 'BLOCK').model_dump(),FinanceOutput)
        if finance['recommendation']=='BLOCK':
            self.ledger.set_state(corr,'BLOCKED',failure='FINANCE_POLICY');self.trace.set_status(corr,'COMPLETED','BLOCKED',True);return
        p=dict(reco_id='wf:'+corr,ingredient_id='SYNTHETIC-STOCK',location_id='SYNTHETIC-SITE',supplier_id=procurement['supplier_id'],quote_id='SYNTHETIC-ASSUMPTION',qty=procurement['quantity'],unit='units',est_cost_usd=procurement['amount_cents']/100,price_class='PLANNING_ASSUMPTION',inputs_hash=digest(context))
        pid=self.ledger.add_proposal(corr,p,{'mode':MODE,'finance':finance},['scenario:'+context['scenario_id'],'foundation:finance_summary'],'arjun','Procurement')
        self.ledger.set_state(corr,'PROPOSED',proposal_id=pid)
        action=self.action(corr)
        gateway=self.write_gateway(corr,action)
        await gateway.start()
        try:
            outcome=await asyncio.wait_for(gateway.call_tool_detailed(gateway.open_session(corr),PROC_TOOL,action),self.timeout)
            if outcome.forwarded or not outcome.approval_id:raise WorkflowDenied('WRITE_NOT_HELD')
            self.ledger.set_state(corr,'AWAITING_APPROVAL',approval_id=outcome.approval_id)
            self.event(corr,'approval_requested',approval_id=outcome.approval_id,action=action,action_hash=digest(action),policy_codes=outcome.codes)
            self.trace.set_status(corr,'AWAITING_APPROVAL','HUMAN_REVIEW_REQUIRED')
        finally:await gateway.close()
    def write_gateway(self,corr,action,context=None):
        policy=policy_for('FOUNDER',self.ttl)
        policy['tools']={PROC_TOOL:policy['tools'][PROC_TOOL]}
        policy['upstreams']={'procurement':{'command':['python','-c','pass']}}
        return Gateway(parse_policy(policy),self.weir,{'procurement':DraftUpstream(self,corr,action,context)},clock=self.clock)
    def decide(self,reviewer,run_id,approval_id,action_hash,decision,role='FOUNDER'):
        if decision not in ('approve','reject'):raise ValueError('Invalid decision')
        with self.lock:
            run=self.owned(run_id,reviewer)
            try:
                if role!='FOUNDER' or run['state']!='AWAITING_APPROVAL':raise WorkflowDenied('REPLAY_OR_ROLE_DENIED')
                action=self.action(run_id)
                if approval_id!=run['approval_id'] or not secrets.compare_digest(action_hash,digest(action)):raise WorkflowDenied('MODIFIED_ACTION_OR_APPROVAL')
                self.require_integrity(run_id)
                approval=self.weir.get_approval(approval_id)
                if not approval or approval.session_id!=run_id or approval.tool!=PROC_TOOL:raise WorkflowDenied('APPROVAL_BINDING_MISMATCH')
                if approval.expires<self.clock():
                    self.weir.resolve_approval(approval_id,False,by=reviewer)
                    self.ledger.set_state(run_id,'FAILED',failure='APPROVAL_EXPIRED');self.event(run_id,'failure',error='APPROVAL_EXPIRED')
                    raise WorkflowDenied('APPROVAL_EXPIRED')
                outcome=self.weir.resolve_approval(approval_id,decision=='approve',by=reviewer)
                if outcome!=('approved' if decision=='approve' else 'denied'):raise WorkflowDenied('APPROVAL_REPLAY')
                if decision=='reject':
                    self.ledger.set_proposal_state(run['proposal_id'],'REJECTED',reviewer,role,run_id)
                    self.ledger.set_state(run_id,'REJECTED',reviewer,role)
                    self.event(run_id,'human_rejected',actor=reviewer,approval_id=approval_id)
                    self.trace.set_status(run_id,'COMPLETED','REJECTED',True)
                else:
                    self.event(run_id,'human_approved',actor=reviewer,approval_id=approval_id,action_hash=action_hash)
                    self.ledger.set_state(run_id,'APPROVED',reviewer,role)
                    grant=self.authority.issue_grant(Identity(reviewer,role),run_id,[{'tool':GRANT_TOOL,'args':action,'args_hash':digest(action)}])
                    asyncio.run(self._execute(run_id,action,{'reviewer':reviewer,'approval_id':approval_id,'grant':grant}))
            except WorkflowDenied as error:
                self.event(run_id,'decision_denied',actor=reviewer,error=str(error))
                raise
            return self.snapshot(run_id,reviewer)
    async def _execute(self,corr,action,context):
        gateway=self.write_gateway(corr,action,context)
        await gateway.start()
        try:
            outcome=await asyncio.wait_for(gateway.call_tool_detailed(gateway.open_session(corr),PROC_TOOL,action),self.timeout)
            if not outcome.forwarded or outcome.result.get('isError'):raise WorkflowDenied('GATEWAY_EXECUTION_DENIED')
            result=json.loads(outcome.result['content'][0]['text'])
            self.ledger.set_state(corr,'EXECUTED',context['reviewer'],'FOUNDER')
            self.event(corr,'simulated_execution',actor=context['reviewer'],result=result,approval_id=context['approval_id'],policy_codes=outcome.codes)
            self.trace.set_status(corr,'COMPLETED','SIMULATED_DRAFT_NOT_SENT',True)
        except Exception:
            existing=self.ledger.con.execute('SELECT po_id FROM po_drafts WHERE proposal_id=?',(action['proposal_id'],)).fetchone()
            if existing:
                self.ledger.set_state(corr,'EXECUTED');self.event(corr,'recovery',result='RECONCILED_EXISTING_DRAFT',draft_id=existing[0])
                self.trace.set_status(corr,'COMPLETED','RECOVERED_EXISTING_SIMULATED_DRAFT',True)
                return
            else:
                self.ledger.set_state(corr,'FAILED',failure='EXECUTION_FAILED_REAPPROVAL_REQUIRED');self.event(corr,'failure',error='EXECUTION_FAILED_REAPPROVAL_REQUIRED')
                self.trace.set_status(corr,'FAILED','EXECUTION_FAILED_REAPPROVAL_REQUIRED',True)
            raise WorkflowDenied('EXECUTION_FAILED_REAPPROVAL_REQUIRED') from None
        finally:await gateway.close()
    def snapshot(self,run_id,reviewer):
        run=self.owned(run_id,reviewer)
        events=self.trace.events(run_id)
        action=self.action(run_id) if run['proposal_id'] else None
        approval=self.weir.get_approval(run['approval_id']) if run['approval_id'] else None
        return {'tenant':self.tenant,'mode':MODE,'live_model':False,'workflow':run,'context':self.context(run_id),'events':events,'audit':self.ledger.audit_rows(run_id),'audit_valid':self.ledger.verify_audit()[0] and self.weir.verify_chain()[0],'action':action,'action_hash':digest(action) if action else None,'approval':{'id':approval.id,'state':approval.state,'expires':approval.expires,'reviewer':reviewer,'effect':'DRAFT_NOT_SENT'} if approval else None,'drafts':[dict(zip(('id','proposal_id','supplier_id','amount_usd','state','approved_by'),r)) for r in self.ledger.po_drafts() if r[1]==run['proposal_id']],'external_actions':0,'financial_fixture_mutated':False}
    def catalog(self,reviewer):
        with self.lock:
            runs=self.ledger.con.execute('SELECT corr_id,state,created FROM runs WHERE tenant_id=? AND requester=? ORDER BY created DESC LIMIT 30',(self.tenant,reviewer)).fetchall()
            from .hq_data import report
            return {'evaluation':[report(p) for p in self.reports],'tenant':self.tenant,'mode':MODE,'live_model':False,'scenarios':[{'id':k,**v} for k,v in SCENARIOS.items()],'runs':[{'id':r[0],'state':r[1],'created':r[2]} for r in runs],'agents':[{'id':a[0],'role':a[1],'tool':a[2]} for a in AGENTS.values()],'limitation':'No approved model/provider is configured. These are actual tool executions with deterministic analysis, not live LLM inference.'}

class Workforce:
    def __init__(self,registry,state,**kw):
        self.engines={tenant:TenantWorkforce(tenant,path,Path(state)/tenant,**kw) for tenant,path in registry.items()}
    def tenant(self,tenant):
        if tenant not in self.engines:raise WorkflowDenied('TENANT_NOT_GRANTED')
        return self.engines[tenant]
    def close(self):
        for engine in self.engines.values():engine.close()
