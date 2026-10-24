"""Authenticated loopback-only Headquarters host. Optional governed simulation ledger; no external actions.
Local review identity only: NOT production SSO or a multi-user identity provider.
"""
import argparse
import asyncio
from dataclasses import dataclass,field
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlparse,parse_qs

from .hq_data import read_model,SOURCE_FILES
from .service import Service,TenantPrincipal,ShowcaseUpstream,weir_policy

CAPABILITIES={
 'headquarters':('summary','adrian'),'executive':('organization','adrian'),
 'engineering':('evidence','daniel'),'data':('operations','priya'),
 'finance':('finance','maya'),'operations':('operations','amara'),
 'product':('projects','elena'),'crm':('stakeholders','lucas'),
 'people':('organization','olivia'),'creation':('projects','elena'),
 'playbook':('evidence','daniel'),
}

@dataclass
class Session:
    csrf: str
    expires: float
    tenant: str
    lock: object=field(default_factory=threading.RLock)

class Headquarters:
    def __init__(self,registry,web,state,reports=(),access_code=None,clock=time.monotonic,workforce_state=None):
        self.registry={t:Path(p).resolve() for t,p in registry.items()}
        if not self.registry or any(not re.fullmatch('[a-z][a-z0-9-]{0,47}',t) for t in self.registry):
            raise ValueError('Invalid trusted registry')
        self.web=Path(web).resolve(); self.state=Path(state).resolve()
        self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.reports=tuple(reports); self.clock=clock
        self.names={}
        for tenant,path in self.registry.items():
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as con:
                if con.execute('SELECT tenant_id FROM businesses').fetchall()!=[(tenant,)]:
                    raise ValueError('Store tenant binding mismatch')
                self.names[tenant]=con.execute('SELECT name FROM businesses WHERE tenant_id=?',(tenant,)).fetchone()[0]
        grants={f'hq:{t}:{a}':(t,a) for t in self.registry for _,a in CAPABILITIES.values()}
        self.service=Service(self.registry,grants)
        self.sessions={}; self.lock=threading.RLock(); self.attempts=[]
        # A fresh owner-only code on each server start. It is never logged or put in a URL.
        self.access_code=access_code or secrets.token_urlsafe(32)
        codefile=self.state/'access-code'
        fd=os.open(codefile,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f: f.write(self.access_code+'\n')
        os.chmod(codefile,0o600)
        self.assets={p.relative_to(self.web).as_posix():p for p in self.web.rglob('*') if p.is_file() and not p.is_symlink()}
        self.gateway_locks={t:threading.RLock() for t in self.registry}
        self.workforce=None
        if workforce_state is not None:
            from .workforce import Workforce
            self.workforce=Workforce(self.registry,workforce_state,reports=self.reports)

    def login(self,code):
        now=self.clock()
        with self.lock:
            self.attempts=[t for t in self.attempts if now-t<60]
            if len(self.attempts)>=5: raise PermissionError('Too many attempts; wait a minute')
            if not secrets.compare_digest(code,self.access_code):
                self.attempts.append(now); raise PermissionError('Invalid access code')
            self.attempts=[]
            self.sessions={k:v for k,v in self.sessions.items() if v.expires>now}
            if len(self.sessions)>=32: raise PermissionError('Session limit reached')
            sid=secrets.token_urlsafe(32)
            session=Session(secrets.token_urlsafe(32),now+8*3600,next(iter(self.registry)))
            self.sessions[sid]=session
            return sid,session

    def session(self,cookie):
        try:
            jar=SimpleCookie(); jar.load(cookie or '')
            sid=jar['nasha_session'].value
        except (KeyError,ValueError): raise PermissionError('Sign in to enter the headquarters')
        with self.lock:
            session=self.sessions.get(sid)
            if not session or session.expires<=self.clock():
                self.sessions.pop(sid,None)
                raise PermissionError('Session expired; sign in again')
            return sid,session

    def metadata(self,session):
        return {'workforce_enabled':self.workforce is not None,'csrf':session.csrf,'selected':session.tenant,'businesses':[{'id':t,'name':n} for t,n in self.names.items()],'synthetic':True,'identity':'Local authorized reviewer','scope':'Read-only review of the server-granted businesses; no real external actions'}

    def view(self,session_id,tenant,view,filters):
        if tenant not in self.registry or view not in CAPABILITIES: raise PermissionError('View unavailable')
        capability,agent=CAPABILITIES[view]
        principal=TenantPrincipal(f'hq:{tenant}:{agent}',agent,tenant)
        upstream=HeadquartersUpstream(self,principal,view,filters)
        from mcp_weir.gateway import Gateway
        from mcp_weir.policy import parse_policy
        from mcp_weir.store import Store
        async def read():
            # Per-tenant Store, per-principal gateway session; never reuse a tenant selector.
            store=Store(str(self.state/f'{tenant}.weir.db'))
            gateway=Gateway(parse_policy(weir_policy()),store,{'showcase':upstream})
            await gateway.start()
            try:
                sid=hashlib.sha256((session_id+tenant+agent).encode()).hexdigest()
                session=gateway.open_session(sid)
                decision=await gateway.call_tool_detailed(session,'showcase__read',{'view':capability})
                if not decision.forwarded or decision.result.get('isError'):
                    raise PermissionError('THE WEIR refused this read')
                result=json.loads(decision.result['content'][0]['text'])
                recent=[]
                for ev in store.events():
                    if ev['kind']=='call.decision':
                        p=ev['payload']
                        if isinstance(p,str): p=json.loads(p)
                        recent.append({'kind':'Gateway read decision','tool':p.get('tool'),'verdict':p.get('verdict') or p.get('decision'),'call':p.get('call')})
                result['gateway']={'chain_valid':store.verify_chain()[0],'read_decisions':recent[-8:],'consequential_actions':0,'scope':'This department read adapter registers read tools only; governed workflow approvals and isolated draft effects are recorded separately when enabled.'}
                return result
            finally:
                await gateway.close(); store.close()
        with self.gateway_locks[tenant]:
            return asyncio.run(read())

class HeadquartersUpstream(ShowcaseUpstream):
    def __init__(self,host,principal,view,filters):
        super().__init__(host.service,principal)
        self.host,self.view_name,self.filters=host,view,filters
    async def call_tool(self,name,arguments,timeout):
        gate=await super().call_tool(name,arguments,timeout)
        if gate['isError']: return gate
        data=read_model(self.host.registry[self.principal.tenant],self.principal.tenant,self.view_name,self.filters,self.host.reports,self.filters.get('source'))
        return {'content':[{'type':'text','text':json.dumps(data)}],'isError':False}


def handler(host):
    class Handler(BaseHTTPRequestHandler):
        server_version='NASHA-Local-Review'
        def log_message(self,*args): pass  # Do not log credentials, cookies, query text or request bodies.
        def send(self,status,body,content_type='application/json',cookie=None):
            data=json.dumps(body).encode() if content_type=='application/json' else body
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if cookie: self.send_header('Set-Cookie',cookie)
            self.end_headers(); self.wfile.write(data)
        def origin_ok(self):
            allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in allowed: return False
            origin=self.headers.get('Origin')
            return not origin or origin in {'http://'+a for a in allowed}
        def do_GET(self):
            if not self.origin_ok(): return self.send(403,{'error':'Invalid request origin'})
            parsed=urlparse(self.path)
            if parsed.path.startswith('/api/'):
                try:
                    sid,session=host.session(self.headers.get('Cookie'))
                    with session.lock:
                        if parsed.path=='/api/session' and not parsed.query:
                            return self.send(200,host.metadata(session))
                        if parsed.path=='/api/workflows':
                            if not host.workforce: return self.send(404,{'error':'Governed workflows are not enabled on this host'})
                            reviewer='reviewer:'+hashlib.sha256(sid.encode()).hexdigest()[:24]
                            engine=host.workforce.tenant(session.tenant)
                            query=parse_qs(parsed.query,keep_blank_values=True)
                            if not query: return self.send(200,engine.catalog(reviewer))
                            if set(query)!={'run'} or len(query['run'])!=1: return self.send(400,{'error':'Invalid workflow selector'})
                            with engine.lock: return self.send(200,engine.snapshot(query['run'][0],reviewer))
                        if parsed.path.startswith('/api/view/'):
                            view=parsed.path.removeprefix('/api/view/')
                            if view not in CAPABILITIES: return self.send(404,{'error':'Unknown department'})
                            raw=parse_qs(parsed.query,keep_blank_values=True)
                            if set(raw)-{'page','month','kind','q','source'} or any(len(v)!=1 for v in raw.values()):
                                return self.send(400,{'error':'Unsupported filter'})
                            f={k:v[0] for k,v in raw.items()}
                            if f.get('page'):
                                if not re.fullmatch(r'\d{1,5}',f['page']): return self.send(400,{'error':'Invalid page'})
                                f['page']=int(f['page'])
                            else: f['page']=0
                            if f.get('source') and f['source'] not in SOURCE_FILES: return self.send(400,{'error':'Unknown evidence ID'})
                            if f.get('month') and not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',f['month']): return self.send(400,{'error':'Invalid month'})
                            if f.get('kind') and f['kind'] not in {'sale','refund','expense','payroll','capital'}: return self.send(400,{'error':'Invalid type'})
                            if len(f.get('q',''))>64: return self.send(400,{'error':'Search is too long'})
                            return self.send(200,host.view(sid,session.tenant,view,f))
                    return self.send(404,{'error':'Unknown endpoint'})
                except PermissionError as e: return self.send(401,{'error':str(e)})
                except ValueError: return self.send(400,{'error':'Invalid evidence or input'})
                except Exception: return self.send(503,{'error':'Source records or gateway unavailable; no data was substituted'})
            name='index.html' if parsed.path=='/' else parsed.path.lstrip('/')
            if name not in host.assets or name=='build-manifest.json': return self.send(404,{'error':'Not found'})
            p=host.assets[name]
            return self.send(200,p.read_bytes(),mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
        def do_POST(self):
            if not self.origin_ok() or self.headers.get('X-Nasha-Request')!='1':
                return self.send(403,{'error':'Same-origin application request required'})
            if self.headers.get('Content-Type')!='application/json': return self.send(415,{'error':'JSON required'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2048: return self.send(413,{'error':'Request size refused'})
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict): raise ValueError()
                if self.path=='/api/login':
                    if set(data)!={'code'} or not isinstance(data['code'],str) or len(data['code'])>256: raise ValueError()
                    sid,session=host.login(data['code'])
                    return self.send(200,host.metadata(session),cookie=f'nasha_session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
                sid,session=host.session(self.headers.get('Cookie'))
                if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),session.csrf): return self.send(403,{'error':'Invalid request token'})
                with session.lock:
                    if self.path.startswith('/api/workflows/'):
                        if not host.workforce: return self.send(404,{'error':'Governed workflows are not enabled'})
                        reviewer='reviewer:'+hashlib.sha256(sid.encode()).hexdigest()[:24]
                        engine=host.workforce.tenant(session.tenant)
                        if self.path=='/api/workflows/start' and set(data)=={'scenario','idempotency_key'} and all(isinstance(v,str) for v in data.values()):
                            return self.send(200,engine.start(reviewer,data['scenario'],data['idempotency_key']))
                        if self.path=='/api/workflows/review' and set(data)=={'run','approval_id','action_hash','decision'} and all(isinstance(v,str) for v in data.values()):
                            return self.send(200,engine.decide(reviewer,data['run'],data['approval_id'],data['action_hash'],data['decision']))
                        return self.send(400,{'error':'Unsupported workflow action or arguments'})
                    if self.path=='/api/select' and set(data)=={'business'} and isinstance(data['business'],str):
                        if data['business'] not in host.registry: return self.send(403,{'error':'Business is not granted'})
                        session.tenant=data['business']
                        return self.send(200,host.metadata(session))
                    if self.path=='/api/logout' and not data:
                        with host.lock: host.sessions.pop(sid,None)
                        return self.send(200,{'signed_out':True},cookie='nasha_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                return self.send(400,{'error':'Unsupported action; this host is read-only'})
            except PermissionError as e: return self.send(401,{'error':str(e)})
            except (ValueError,TypeError): return self.send(400,{'error':'Invalid request'})
            except Exception: return self.send(503,{'error':'Workflow service unavailable; no outcome is assumed. Inspect recorded state before retrying.'})
    return Handler

def make_server(host,port=8765):
    return ThreadingHTTPServer(('127.0.0.1',port),handler(host))

def main():
    p=argparse.ArgumentParser(description='Loopback-only, authenticated NASHA AI review host')
    p.add_argument('--nasha',type=Path,required=True)
    p.add_argument('--meridian',type=Path,required=True)
    p.add_argument('--web',type=Path,required=True)
    p.add_argument('--state',type=Path,required=True)
    p.add_argument('--foundation-report',type=Path)
    p.add_argument('--phase3-report',type=Path)
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--workforce-state',type=Path,help='Enable governed deterministic workflows in an isolated state directory')
    a=p.parse_args()
    h=Headquarters({'nasha-brewery':a.nasha,'meridian-fitness':a.meridian},a.web,a.state,[r for r in (a.foundation_report,a.phase3_report) if r],workforce_state=a.workforce_state)
    server=make_server(h,a.port)
    print(f'NASHA AI local review listening on port {server.server_port}. Access code is in {a.state}/access-code (owner-only).',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        if h.workforce: h.workforce.close()
if __name__=='__main__': main()
