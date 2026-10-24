"""Read models for Phase 3. All financial figures come from retained foundation stores.
No business writes, generated metrics, model calls, or external actions.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET
from .scenario import summary

FOUNDATION='6c177d7ac8afa3d5573c46d6298a83bdc09138fd'
REPO=Path(__file__).resolve().parents[2]
SOURCE_FILES={
 'phase4-playbook':('showcase/workforce/PLAYBOOK.md','Phase 4 · governed workforce playbook'),
 'phase4-implementation':('showcase/showcase/workforce.py','Phase 4 · actual deterministic tool and approval adapter'),
 'simulation':('showcase/showcase/scenario.py','Python · deterministic simulation'),
 'schema':('showcase/showcase/schema.sql','SQL · relational records and journals'),
 'tenant':('showcase/showcase/service.py','Python · tenant and persona grants'),
 'postgres':('showcase/showcase/postgres.py','PostgreSQL · forced tenant policies'),
 'tests':('showcase/tests/test_foundation.py','Tests · reconciliation and denied actions'),
 'gateway':('lab/nasha_lab/warehouse/ops_ai_weir.py','THE WEIR · existing gateway bridge'),
 'architecture':('showcase/docs/ARCHITECTURE.md','Architecture · domain boundaries'),
 'audit':('showcase/docs/AUDIT.md','Integrations · evidence and reuse'),
 'playbook':('showcase/docs/PLAYBOOK.md','Engineering playbook · reference plan'),
 'handoff':('showcase/docs/HANDOFF.md','Foundation · verified handoff'),
}

def rows(con,sql,args=()):
    return [dict(r) for r in con.execute(sql,args)]

def report(path):
    path=Path(path)
    if not path.is_file(): return {'available':False,'label':path.name}
    try:
        root=ET.parse(path).getroot()
        cases=root.findall('.//testcase')
        return {'available':True,'label':path.name,'tests':len(cases),'failures':sum(c.find('failure') is not None or c.find('error') is not None for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'timestamp':next((s.get('timestamp') for s in root.iter('testsuite') if s.get('timestamp')),None)}
    except (ET.ParseError,OSError):
        return {'available':False,'label':path.name,'error':'Unreadable report'}

def source(source_id):
    if source_id not in SOURCE_FILES: raise ValueError('Unknown evidence ID')
    relative,title=SOURCE_FILES[source_id]
    text=(REPO/relative).read_text()
    return {'id':source_id,'title':title,'path':relative,'sha256':hashlib.sha256(text.encode()).hexdigest(),'text':text[:20000],'truncated':len(text)>20000,'github':None if source_id.startswith('phase4-') else f'https://github.com/riteshmamidi0905-lab/INDO-MEX-BREWERY/blob/{FOUNDATION}/{relative}'}


def read_model(path,tenant,view,filters,reports,source_id=None):
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        business=dict(con.execute('SELECT tenant_id,name,idea,founded,end_date,config_json FROM businesses WHERE tenant_id=?',(tenant,)).fetchone())
        business['config']=json.loads(business.pop('config_json'))
        result={'tenant':tenant,'synthetic':True,'business':business,'view':view,'summary':summary(con,tenant),'source':'foundation schema v1 · financial_records + transactions + business_events'}
        counts={t:con.execute(f'SELECT count(*) FROM {t} WHERE tenant_id=?',(tenant,)).fetchone()[0] for t in ('agents','departments','tasks','transactions','business_events','financial_records','transaction_lines','stakeholders')}
        result['counts']=counts
        if view in ('headquarters','executive','finance','data'):
            result['monthly']=rows(con,"""SELECT substr(e.occurred,1,7) month,
              SUM(CASE WHEN f.account='revenue' THEN f.credit_cents-f.debit_cents ELSE 0 END) revenue,
              SUM(CASE WHEN f.account IN ('operating_expense','payroll_expense') THEN f.debit_cents-f.credit_cents ELSE 0 END) expense,
              SUM(CASE WHEN f.account='cash' THEN f.debit_cents-f.credit_cents ELSE 0 END) cash_change
              FROM financial_records f JOIN transactions t ON t.tenant_id=f.tenant_id AND t.id=f.transaction_id
              JOIN business_events e ON e.tenant_id=t.tenant_id AND e.id=t.event_id
              WHERE f.tenant_id=? GROUP BY substr(e.occurred,1,7) ORDER BY month""",(tenant,))
        if view in ('finance','operations'):
            where='t.tenant_id=?'; args=[tenant]
            if filters.get('month'): where+=' AND substr(e.occurred,1,7)=?'; args.append(filters['month'])
            if filters.get('kind'): where+=' AND t.kind=?'; args.append(filters['kind'])
            if filters.get('q'):
                where+=' AND (t.id LIKE ? ESCAPE \'\\\' OR e.source_ref LIKE ? ESCAPE \'\\\')'
                query=filters['q'].replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
                args.extend(['%'+query+'%']*2)
            join=' FROM transactions t JOIN business_events e ON e.tenant_id=t.tenant_id AND e.id=t.event_id WHERE '+where
            result['matching']=con.execute('SELECT count(*)'+join,args).fetchone()[0]
            result['page']=filters.get('page',0)
            result['transactions']=rows(con,'SELECT t.id,t.kind,t.amount_cents,e.occurred,e.actor_id,e.source_ref,e.event_hash'+join+' ORDER BY e.seq DESC LIMIT 20 OFFSET ?',(*args,result['page']*20))
            result['tasks']=rows(con,'SELECT t.*,a.name agent_name FROM tasks t JOIN agents a ON a.tenant_id=t.tenant_id AND a.id=t.agent_id WHERE t.tenant_id=? ORDER BY t.id',(tenant,))
        if view in ('executive','people'):
            result['agents']=rows(con,'SELECT a.*,d.name department FROM agents a JOIN departments d ON d.tenant_id=a.tenant_id AND d.id=a.department_id WHERE a.tenant_id=? ORDER BY a.id',(tenant,))
            for agent in result['agents']:
                agent['permissions']=json.loads(agent.pop('permissions_json'))
                agent['task_count']=con.execute('SELECT count(*) FROM tasks WHERE tenant_id=? AND agent_id=?',(tenant,agent['id'])).fetchone()[0]
        if view in ('executive','product'):
            result['projects']=rows(con,'SELECT * FROM projects WHERE tenant_id=? ORDER BY id',(tenant,))
            result['tasks']=rows(con,'SELECT t.*,a.name agent_name FROM tasks t JOIN agents a ON a.tenant_id=t.tenant_id AND a.id=t.agent_id WHERE t.tenant_id=? ORDER BY t.id',(tenant,))
        if view=='crm':
            result['stakeholders']=rows(con,"""SELECT s.*,count(t.id) transaction_count,COALESCE(SUM(t.amount_cents),0) linked_cents
             FROM stakeholders s LEFT JOIN transactions t ON t.tenant_id=s.tenant_id AND t.stakeholder_id=s.id
             WHERE s.tenant_id=? GROUP BY s.tenant_id,s.id ORDER BY s.id""",(tenant,))
            result['relationships']=rows(con,'SELECT kind,count(*) count FROM transactions WHERE tenant_id=? AND stakeholder_id IS NOT NULL GROUP BY kind ORDER BY kind',(tenant,))
        if view in ('data','engineering','playbook'):
            result['evidence']=[{'id':key,'path':value[0],'title':value[1]} for key,value in SOURCE_FILES.items()]
            result['reports']=[report(p) for p in reports]
            result['schema']=[{'table':t,'columns':[dict(r) for r in con.execute(f'PRAGMA table_info({t})')]} for t in ('businesses','departments','agents','projects','tasks','stakeholders','business_events','transactions','transaction_lines','financial_records','engineering_evidence')]
            result['quality']={'foreign_key_violations':len(con.execute('PRAGMA foreign_key_check').fetchall()),'unbalanced_transactions':con.execute('SELECT count(*) FROM (SELECT transaction_id FROM financial_records WHERE tenant_id=? GROUP BY transaction_id HAVING sum(debit_cents)<>sum(credit_cents))',(tenant,)).fetchone()[0],'cash_identity_balanced':result['summary']['cash_cents']==result['summary']['capital_cents']+result['summary']['net_income_cents'],'scope':'Read-time checks only; not a full replay or signature verification'}
        if source_id: result['document']=source(source_id)
        return result
