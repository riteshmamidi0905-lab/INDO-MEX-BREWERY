import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import pytest

from showcase.config import BusinessConfig, WORKFORCE
from showcase.scenario import build, canonical, digest, export, summary, validate
from showcase.service import Service, TenantPrincipal, ShowcaseUpstream, weir_policy, platform_tool

@pytest.fixture(scope='module')
def datasets(tmp_path_factory):
    root=tmp_path_factory.mktemp('showcase')
    cfg=BusinessConfig(start='2026-10-01',end='2026-10-24',target_orders=120,seed=17)
    paths={}
    for name,c in [('nasha',cfg),('replay',cfg),('changed',replace(cfg,seed=18)),('meridian',replace(cfg,tenant='meridian-fitness',industry='fitness',name='Meridian Fitness (fictional)'))]:
        paths[name]=root/(name+'.db')
        build(c,paths[name])
    return paths

def snapshot(p,tenant='nasha-brewery'):
    with sqlite3.connect(p) as c:
        validate(c)
        return export(c,tenant)

def test_deterministic_replay_and_seed_sensitivity(datasets):
    assert canonical(snapshot(datasets['nasha']))==canonical(snapshot(datasets['replay']))
    assert digest(snapshot(datasets['nasha']))!=digest(snapshot(datasets['changed']))

def test_finances_and_workforce(datasets):
    s=snapshot(datasets['nasha'])
    assert len(s['tables']['agents'])==15
    assert all(a['fictional']==1 for a in s['tables']['agents'])
    assert all(t['status']=='queued' for t in s['tables']['tasks'])
    assert s['summary']['cash_cents']==s['summary']['capital_cents']+s['summary']['net_income_cents']
    dates=[e['occurred'] for e in s['tables']['business_events']]
    assert min(dates)>='2026-10-01' and max(dates)<='2026-10-24'
    assert s['summary']['net_revenue_cents']>0

def test_no_overwrite(datasets):
    before=datasets['nasha'].read_bytes()
    with pytest.raises(FileExistsError): build(BusinessConfig(),datasets['nasha'])
    assert datasets['nasha'].read_bytes()==before

@pytest.mark.parametrize('field,value',[('tenant','../escape'),('start','2027-01-01'),('target_orders',0),('industry','banking')])
def test_invalid_profile(tmp_path,field,value):
    with pytest.raises(ValueError): build(replace(BusinessConfig(),**{field:value}),tmp_path/'bad.db')
    assert not (tmp_path/'bad.db').exists()

@pytest.mark.parametrize('mutation',[
 "UPDATE business_events SET payload_json='{}' WHERE seq=2",
 "UPDATE financial_records SET debit_cents=debit_cents+1 WHERE debit_cents>0 AND transaction_id='CAPITAL'",
 "UPDATE transaction_lines SET qty=qty+1 WHERE transaction_id=(SELECT id FROM transactions WHERE kind='sale' LIMIT 1)",
 "DELETE FROM financial_records WHERE transaction_id='CAPITAL'",
 "UPDATE transactions SET amount_cents=amount_cents+1 WHERE id='CAPITAL'",
 "UPDATE financial_records SET account='revenue' WHERE account='capital'",
])
def test_tampering_fails(datasets,tmp_path,mutation):
    p=tmp_path/'mutant.db'; p.write_bytes(datasets['nasha'].read_bytes())
    with sqlite3.connect(p) as c:
        c.execute(mutation)
        with pytest.raises(ValueError): validate(c)

def service(datasets):
    return Service({'nasha-brewery':datasets['nasha'],'meridian-fitness':datasets['meridian']},{'finance':('nasha-brewery','maya'),'hr':('nasha-brewery','olivia'),'meridian':('meridian-fitness','maya')})

def test_tenant_isolation_role_grants_and_no_argument_overrides(datasets):
    svc=service(datasets)
    maya=TenantPrincipal('finance','maya','nasha-brewery')
    assert svc.read(maya,'finance')['tenant']=='nasha-brewery'
    assert svc.read(TenantPrincipal('meridian','maya','meridian-fitness'),'finance')['tenant']=='meridian-fitness'
    for who,view,args in [(TenantPrincipal('finance','maya','meridian-fitness'),'finance',{}),(TenantPrincipal('hr','olivia','nasha-brewery'),'finance',{}),(maya,'summary',{'tenant':'meridian-fitness'}),(maya,'drop table transactions',{})]:
        with pytest.raises(PermissionError): svc.read(who,view,args)
    assert len([a for a in svc.audit if a['decision']=='deny'])==4

def test_registry_rejects_shared_paths_and_wrong_binding(datasets):
    with pytest.raises(ValueError): Service({'a':datasets['nasha'],'b':datasets['nasha']},{})
    svc=Service({'meridian-fitness':datasets['nasha']},{'u':('meridian-fitness','maya')})
    with pytest.raises(PermissionError): svc.read(TenantPrincipal('u','maya','meridian-fitness'),'summary')

def test_cross_tenant_foreign_keys(datasets):
    with sqlite3.connect(datasets['nasha']) as c:
        c.execute('PRAGMA foreign_keys=ON')
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO tasks VALUES ('meridian-fitness','bad','foundation','maya','bad','queued')")

def test_real_weir_and_platform_adapter(datasets,tmp_path):
    from mcp_weir.gateway import Gateway
    from mcp_weir.policy import parse_policy
    from mcp_weir.store import Store
    from agentplatform.tools.base import ToolContext, ToolRegistry, ToolError
    from pydantic import ValidationError
    async def check():
        svc=service(datasets)
        upstream=ShowcaseUpstream(svc,TenantPrincipal('finance','maya','nasha-brewery'))
        store=Store(str(tmp_path/'weir.db'))
        gateway=Gateway(parse_policy(weir_policy()),store,{'showcase':upstream})
        await gateway.start()
        try:
            session=gateway.open_session('showcase-bound-finance')
            tool=platform_tool(gateway,session)
            registry=ToolRegistry(); registry.register(tool)
            args=tool.args_model(view='finance')
            result=await registry.get('showcase_read').run(args,ToolContext('fixture',None,None))
            assert result.data['synthetic'] and result.data['tenant']=='nasha-brewery'
            with pytest.raises(ValidationError): tool.args_model(view='finance',tenant='meridian-fitness')
            with pytest.raises(ToolError): await tool.run(tool.args_model(view='organization'),ToolContext('fixture',None,None))
            for action in ('send_email','execute_payment','publish','write'):
                blocked=await gateway.call_tool_detailed(session,'showcase__'+action,{})
                assert not blocked.forwarded
            assert store.verify_chain()[0]
        finally: await gateway.close()
    asyncio.run(check())
