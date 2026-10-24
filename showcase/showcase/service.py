"""Read-only domain tools. Trusted host binds a principal; arguments cannot choose identity.
This is a local adapter, not an authentication service or another agent runtime.
"""
import json
from pathlib import Path
import sqlite3
from nasha_lab.warehouse.tenancy import TenantPrincipal
from .scenario import summary

VIEWS={'summary','finance','organization','projects','operations','stakeholders','evidence'}

class Service:
    def __init__(self, registry, grants):
        # registry and grants are server configuration, never tool arguments.
        self.registry={k:Path(v).resolve() for k,v in registry.items()}
        if len(set(self.registry.values()))!=len(self.registry):
            raise ValueError('tenants must not share database files')
        self.grants=dict(grants)
        self.audit=[]

    def read(self, who: TenantPrincipal, view, arguments=None):
        try:
            if arguments or view not in VIEWS:
                raise PermissionError('unknown view or forbidden arguments')
            if self.grants.get(who.user)!=(who.tenant,who.role) or who.tenant not in self.registry:
                raise PermissionError('principal not granted')
            uri=self.registry[who.tenant].as_uri()+'?mode=ro'
            with sqlite3.connect(uri,uri=True) as con:
                con.row_factory=sqlite3.Row
                if [r[0] for r in con.execute('SELECT tenant_id FROM businesses')]!=[who.tenant]:
                    raise PermissionError('tenant database binding mismatch')
                row=con.execute('SELECT permissions_json FROM agents WHERE tenant_id=? AND id=?',(who.tenant,who.role)).fetchone()
                if not row or view not in json.loads(row[0]):
                    raise PermissionError('agent permission denied')
                if view in ('summary','finance'):
                    result=summary(con,who.tenant)
                else:
                    table={'organization':'agents','projects':'tasks','operations':'transactions','stakeholders':'stakeholders','evidence':'engineering_evidence'}[view]
                    # All identifiers come from this constant mapping; users provide no SQL.
                    result=[dict(r) for r in con.execute(f'SELECT * FROM {table} WHERE tenant_id=? ORDER BY 2 LIMIT 100',(who.tenant,))]
                self.audit.append(dict(user=who.user,tenant=who.tenant,agent=who.role,view=view,decision='allow'))
                return dict(synthetic=True,tenant=who.tenant,view=view,data=result,source='showcase-v1/'+view,limit=100 if isinstance(result,list) else None)
        except PermissionError:
            self.audit.append(dict(user=who.user,tenant=who.tenant,agent=who.role,view=view,decision='deny'))
            raise

class ShowcaseUpstream:
    """THE WEIR Upstream protocol, bound to ONE principal by the trusted host."""
    name='showcase'
    def __init__(self, service, principal):
        self.service,self.principal=service,principal
    async def start(self): pass
    async def close(self): pass
    async def list_tools(self):
        return [dict(name='read',description='Read synthetic showcase records for the bound business and agent.',inputSchema={'type':'object','properties':{'view':{'type':'string','enum':sorted(VIEWS)}},'required':['view'],'additionalProperties':False})]
    async def call_tool(self,name,arguments,timeout):
        try:
            if name!='read' or set(arguments)!={'view'}:
                raise PermissionError('unknown tool or arguments')
            result=self.service.read(self.principal,arguments['view'])
            return {'content':[{'type':'text','text':json.dumps(result)}],'isError':False}
        except PermissionError as e:
            return {'content':[{'type':'text','text':'denied: '+str(e)}],'isError':True}

def weir_policy():
    # Reuse the existing gateway policy defaults; no write or egress tools registered.
    from nasha_lab.warehouse.ops_ai_weir import policy
    p=policy()
    p['policy']['name']='nasha-showcase-read-only'
    p['tools']={'showcase__read':{'effect':'read','result':{'conf':'internal'}}}
    p['upstreams']={'showcase':{'command':['python','-c','pass']}}
    return p

def platform_tool(gateway,session):
    """Real agentplatform Tool -> real THE WEIR Gateway -> scoped Service.
    No alternate orchestrator, planner, approval engine, or LLM provider is added.
    Gateway/session must be dedicated to the bound principal and business.
    """
    from typing import Literal
    from pydantic import BaseModel,ConfigDict
    from agentplatform.tools.base import Tool,ToolResult,ToolError,Risk
    class Args(BaseModel):
        model_config=ConfigDict(extra='forbid')
        view: Literal['summary','finance','organization','projects','operations','stakeholders','evidence']
    class ShowcaseRead(Tool):
        name='showcase_read'
        description='Read synthetic enterprise source records through THE WEIR; no external actions.'
        args_model=Args
        risk=Risk.READ
        async def run(self,args,ctx):
            result=await gateway.call_tool_detailed(session,'showcase__read',args.model_dump())
            if not result.forwarded or result.result.get('isError'):
                raise ToolError('showcase read denied')
            data=json.loads(result.result['content'][0]['text'])
            return ToolResult(text='Synthetic showcase '+args.view,data=data)
    return ShowcaseRead()
