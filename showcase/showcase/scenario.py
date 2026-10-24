"""Reuse nasha_lab.enterprise_sim as the source; extend it with showcase domain records.
No provider calls, contacts, payments, external writes, or agent execution.
"""
from dataclasses import asdict
import calendar
import csv
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from . import VERSION
from .config import BusinessConfig, WORKFORCE

TABLES=('businesses','departments','agents','projects','tasks','stakeholders','business_events','transactions','transaction_lines','financial_records','engineering_evidence')

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()

def _rows(root,name):
    with gzip.open(root/f'{name}.csv.gz','rt') as f:
        yield from csv.DictReader(f)

def build(config: BusinessConfig, destination, workforce=None):
    """Create a NEW per-business database. Refuse overwrites, including symlinks.

    Source simulator uses whole months. We explicitly filter orders to the requested
    inclusive window; retained line items, discounts and refunds reconcile unchanged.
    The fixture's sales target is a volume assumption, not a forced revenue total.
    """
    config.validate()
    dest=Path(destination)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb'):
        pass
    con=sqlite3.connect(dest)
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript(Path(__file__).with_name('schema.sql').read_text())
    tenant=config.tenant
    staff=WORKFORCE if workforce is None else workforce
    ids={s[0] for s in staff}
    if len(staff)!=len(ids) or not {'maya','amara'} <= ids:
        con.close()
        raise ValueError('workforce needs unique IDs and finance/operations actors')
    seq=0
    previous='0'*64
    def insert(table,*values):
        con.execute(f'INSERT INTO {table} VALUES ({",".join("?" for _ in values)})',values)
    def event(occurred,kind,actor,source,payload):
        nonlocal seq,previous
        seq+=1
        eid=f'EV{seq:08d}'
        body=dict(tenant_id=tenant,id=eid,seq=seq,occurred=occurred,kind=kind,actor_id=actor,source_ref=source,payload=payload,prev_hash=previous)
        hashed=digest(body)
        insert('business_events',tenant,eid,seq,occurred,kind,actor,source,canonical(payload),previous,hashed)
        previous=hashed
        return eid
    def transaction(tid,date,kind,amount,source,stakeholder=None,details=None):
        actor='amara' if kind=='sale' else 'maya'
        eid=event(date,kind,actor,source,dict(transaction_id=tid,amount_cents=amount,**(details or {})))
        insert('transactions',tenant,tid,eid,stakeholder,kind,amount)
        accounts={'sale':('cash','revenue'),'refund':('revenue','cash'),'expense':('operating_expense','cash'),'payroll':('payroll_expense','cash'),'capital':('cash','capital')}
        debit,credit=accounts[kind]
        insert('financial_records',tenant,tid,1,debit,amount,0)
        insert('financial_records',tenant,tid,2,credit,0,amount)
    try:
        with con:
            insert('businesses',tenant,config.name,config.idea,config.start,config.end,1,canonical({'version':VERSION,**asdict(config),'limitations':['Uncalibrated volume; concept prices','No taxes, accruals or depreciation; cash-basis demonstration','Payroll personas are fictional cost assumptions, not LLM usage costs']}))
            for aid,dept,name,role,salary,permissions in staff:
                insert('departments',tenant,aid,dept)
                insert('agents',tenant,aid,aid,name,role,salary,canonical(permissions),1)
            insert('projects',tenant,'foundation','Business blueprint and operating review','active')
            for aid,dept,*_ in staff:
                insert('tasks',tenant,'review-'+aid,'foundation',aid,f'Review synthetic {dept.lower()} source records and propose next steps','queued')
            insert('stakeholders',tenant,'SYN-CUSTOMERS','customer','Fictional customer cohort',1)
            insert('stakeholders',tenant,'SYN-SUPPLIER','supplier','Fictional operating supplier',1)
            insert('stakeholders',tenant,'SYN-CAPITAL','investor','Fictional capital contributor',1)
            transaction('CAPITAL',config.start,'capital',300000000,'assumption:opening-capital','SYN-CAPITAL')
            if config.industry=='hospitality':
                from nasha_lab.enterprise_sim import SimConfig,generate
                start=dt.date.fromisoformat(config.start); end=dt.date.fromisoformat(config.end)
                months=(end.year-start.year)*12+end.month-start.month+1
                cfg=SimConfig(seed=config.seed,start=start.replace(day=1).isoformat(),months=months,fast_casual=0,beer_gardens=1,target_orders=config.target_orders,loyalty_profiles=100,employees=15,open_at_start=1,price_step=1.0,menu='current',name=VERSION)
                with tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp)
                    generate(cfg,root)
                    orders={o['order_id']:o for o in _rows(root,'orders') if config.start<=o['ts'][:10]<=config.end}
                    for oid,o in sorted(orders.items()):
                        amount=int(o['total_cents'])
                        transaction(oid,o['ts'][:10],'sale',amount,'enterprise_sim:orders/'+oid,'SYN-CUSTOMERS',{'subtotal_cents':int(o['subtotal_cents']),'discount_cents':int(o['discount_cents'])})
                    for line in _rows(root,'order_lines'):
                        if line['order_id'] in orders:
                            insert('transaction_lines',tenant,line['order_id'],int(line['line_no']),line['item_id'],int(line['qty']),int(line['unit_price_cents']))
                    for r in _rows(root,'returns'):
                        oid=r['order_id']
                        if oid in orders:
                            transaction(f'REFUND-{oid}-{r["line_no"]}',orders[oid]['ts'][:10],'refund',int(r['refund_cents']),'enterprise_sim:returns/'+oid+'/'+r['line_no'],'SYN-CUSTOMERS',{'order_id':oid,'line_no':int(r['line_no'])})
            else:
                # Alternate business profile: memberships, not a hospitality catalog.
                start=dt.date.fromisoformat(config.start); end=dt.date.fromisoformat(config.end)
                for i in range(config.target_orders):
                    day=start+dt.timedelta(days=i%((end-start).days+1))
                    oid=f'MEM{i:08d}'
                    transaction(oid,day.isoformat(),'sale',5000,'fitness-fixture:membership/'+oid,'SYN-CUSTOMERS',{'subtotal_cents':5000,'discount_cents':0})
                    insert('transaction_lines',tenant,oid,1,'fitness-membership',1,5000)
            # Monthly compensation is prorated by in-window calendar days. This is
            # a fictional annual salary /12, using exact integer arithmetic.
            day=dt.date.fromisoformat(config.start).replace(day=1)
            end=dt.date.fromisoformat(config.end)
            while day<=end:
                days=calendar.monthrange(day.year,day.month)[1]
                last=day.replace(day=days)
                active=(min(last,end)-max(day,dt.date.fromisoformat(config.start))).days+1
                month=day.isoformat()[:7]
                payroll=sum(s[4]*active//(12*days) for s in staff)
                transaction('PAY-'+month,min(last,end).isoformat(),'payroll',payroll,'assumption:workforce-salary/'+month,details={'active_days':active,'month_days':days})
                # Cost-of-sales proxy explicitly declared; never a supplier quote.
                sales=con.execute("SELECT COALESCE(SUM(t.amount_cents),0) FROM transactions t JOIN business_events e ON e.tenant_id=t.tenant_id AND e.id=t.event_id WHERE t.tenant_id=? AND t.kind='sale' AND substr(e.occurred,1,7)=?",(tenant,month)).fetchone()[0]
                if sales:
                    transaction('COST-'+month,min(last,end).isoformat(),'expense',max(1,sales*35//100),'assumption:operating-cost-35pct/'+month,'SYN-SUPPLIER')
                day=(last+dt.timedelta(days=1)).replace(day=1)
            repo=Path(__file__).resolve().parents[2]
            for i,p in enumerate(('lab/nasha_lab/enterprise_sim.py','lab/nasha_lab/warehouse/ops_ai_weir.py','lab/nasha_lab/governed/tenants.py','showcase/showcase/schema.sql')):
                insert('engineering_evidence',tenant,f'E{i}',p,hashlib.sha256((repo/p).read_bytes()).hexdigest(),'inspected','File inspected; this row does not assert a test passed or reconstruct a historical prompt.')
        validate(con)
        return summary(con,tenant)
    finally:
        con.close()

def summary(con,tenant):
    cur=con.execute('SELECT net_revenue_cents,expense_cents,cash_cents,capital_cents FROM finance_summary WHERE tenant_id=?',(tenant,))
    row=cur.fetchone()
    if row is None:
        raise ValueError('tenant not found')
    result=dict(zip(('net_revenue_cents','expense_cents','cash_cents','capital_cents'),row))
    result['net_income_cents']=row[0]-row[1]
    return dict(tenant=tenant,synthetic=True,version=VERSION,**result)

def validate(con):
    """Fail on broken books, provenance, line reconciliation, or reference integrity."""
    if con.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('foreign key violation')
    for tenant,start,end in con.execute('SELECT tenant_id,founded,end_date FROM businesses'):
        previous='0'*64
        for expected,row in enumerate(con.execute('SELECT id,seq,occurred,kind,actor_id,source_ref,payload_json,prev_hash,event_hash FROM business_events WHERE tenant_id=? ORDER BY seq',(tenant,)),1):
            eid,seq,date,kind,actor,source,payload,prev,h=row
            doc=dict(tenant_id=tenant,id=eid,seq=seq,occurred=date,kind=kind,actor_id=actor,source_ref=source,payload=json.loads(payload),prev_hash=prev)
            if seq!=expected or prev!=previous or digest(doc)!=h or not start<=date<=end:
                raise ValueError('event provenance broken')
            previous=h
        bad=con.execute('SELECT transaction_id FROM financial_records WHERE tenant_id=? GROUP BY transaction_id HAVING SUM(debit_cents)<>SUM(credit_cents) OR COUNT(*)<>2',(tenant,)).fetchall()
        if bad: raise ValueError('unbalanced journal')
        for tid,kind,amount,eid in con.execute('SELECT id,kind,amount_cents,event_id FROM transactions WHERE tenant_id=?',(tenant,)):
            payload=json.loads(con.execute('SELECT payload_json FROM business_events WHERE tenant_id=? AND id=?',(tenant,eid)).fetchone()[0])
            postings=con.execute('SELECT COALESCE(SUM(debit_cents),0),COALESCE(SUM(credit_cents),0) FROM financial_records WHERE tenant_id=? AND transaction_id=?',(tenant,tid)).fetchone()
            accounts={'sale':('cash','revenue'),'refund':('revenue','cash'),'expense':('operating_expense','cash'),'payroll':('payroll_expense','cash'),'capital':('cash','capital')}
            debit,credit=accounts[kind]
            expected_postings={(debit,amount,0),(credit,0,amount)}
            actual_postings=set(con.execute('SELECT account,debit_cents,credit_cents FROM financial_records WHERE tenant_id=? AND transaction_id=?',(tenant,tid)))
            event_kind=con.execute('SELECT kind FROM business_events WHERE tenant_id=? AND id=?',(tenant,eid)).fetchone()[0]
            if actual_postings!=expected_postings or event_kind!=kind:
                raise ValueError('journal account or event kind mismatch')
            if payload.get('transaction_id')!=tid or payload.get('amount_cents')!=amount or postings!=(amount,amount):
                raise ValueError('transaction/event/journal mismatch')
            if kind=='sale':
                total=con.execute('SELECT COALESCE(SUM(qty*unit_price_cents),0) FROM transaction_lines WHERE tenant_id=? AND transaction_id=?',(tenant,tid)).fetchone()[0]
                if total!=payload['subtotal_cents'] or total-payload['discount_cents']!=amount:
                    raise ValueError('sale line reconciliation failed')
        s=summary(con,tenant)
        if s['cash_cents']!=s['capital_cents']+s['net_income_cents']:
            raise ValueError('financial reconciliation failed')

def export(con,tenant):
    """Canonical logical snapshot; no wall clock or SQLite layout dependence."""
    out={}
    for table in TABLES:
        cur=con.execute(f'SELECT * FROM {table} WHERE tenant_id=? ORDER BY 1,2',(tenant,))
        cols=[c[0] for c in cur.description]
        rows=[dict(zip(cols,r)) for r in cur]
        out[table]=sorted(rows,key=canonical)
    return dict(synthetic=True,version=VERSION,tables=out,summary=summary(con,tenant))
