/* NASHA Growth OS web interface. Every number and control is backed by the Growth OS HTTP API (/v1/tenants/{tenant}/...); there is no client-side data. SYNTHETIC demo: nothing can be sent, published or purchased. */
(()=>{'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s==null?'—':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=c=>c==null?'—':'$'+(c/100).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=v=>v==null?'—':(100*v).toFixed(1)+'%';
const uid=()=>Math.random().toString(36).slice(2,10)+Math.random().toString(36).slice(2,10);
let S={tenant:null,user:null,role:null,token:null};
try{const x=JSON.parse(sessionStorage.getItem('growth.session')||'null');if(x&&x.token)S=x}catch(e){}
const save=()=>{try{sessionStorage.setItem('growth.session',JSON.stringify(S))}catch(e){}};
const STATE_CHIP={EXECUTED:'ok',AWAITING_APPROVAL:'warn',REJECTED:'bad',BLOCKED:'bad',FAILED:'bad',ABSTAINED:'info',APPROVED:'info',PROPOSED:'info',STARTED:'info',EVIDENCE_COLLECTED:'info'};
const chip=(t,k)=>`<span class="chip ${k||STATE_CHIP[t]||''}">${esc(String(t).replace(/_/g,' '))}</span>`;
function toast(msg,kind='ok',sub=''){const t=document.createElement('div');t.className='toast '+kind;t.innerHTML=esc(msg)+(sub?`<small>${esc(sub)}</small>`:'');$('#toasts').appendChild(t);setTimeout(()=>t.remove(),6000)}
async function api(method,path,body,opts={}){
  const h={'X-Request-Id':'ui-'+uid()};if(S.token)h.Authorization='Bearer '+S.token;if(body!==undefined)h['Content-Type']='application/json';if(method!=='GET'&&opts.idem!==false)h['Idempotency-Key']=opts.key||uid()+uid();
  const r=await fetch(`/v1/tenants/${S.tenant}${path}`,{method,headers:h,body:body===undefined?undefined:JSON.stringify(body)});
  let j=null;try{j=await r.json()}catch(e){}
  if(!r.ok){const e=(j&&j.error)||{code:'error',message:'request failed',request_id:'-'};if(r.status===401&&S.token&&path!=='/session'){signOut(true)}const err=new Error(e.message);err.code=e.code;err.status=r.status;err.rid=e.request_id;throw err}
  return j}
const fail=e=>toast(`${e.message}`,'bad',e.status?`HTTP ${e.status} · ${e.code} · request ${e.rid}`:'');
async function act(fn,okmsg){try{const r=await fn();if(okmsg)toast(okmsg,'ok');return r}catch(e){fail(e);return null}}
const can={write:()=>['OWNER','SALES'].includes(S.role),owner:()=>S.role==='OWNER',pricing:()=>['OWNER','ANALYST'].includes(S.role),content:()=>['OWNER','SALES','MARKETING'].includes(S.role)};

/* ---------------- shell ---------------- */
const NAV=[['dashboard','Executive dashboard'],['crm','CRM'],['pipeline','Sales pipeline'],['pricing','Pricing studio'],['workflows','AI workflow center'],['security','Security and audit'],['settings','Settings']];
function shell(){ $('#login').hidden=true;$('#app').hidden=false;
  $('#nav').innerHTML=NAV.map(([k,l])=>`<a href="#/${k}" data-k="${k}">${l}</a>`).join('');
  $('#who').innerHTML=`<span class="mono">Tenant</span><b>${esc(S.tenant)}</b><span class="mono">Signed in</span><b>${esc(S.user)} · ${esc(S.role)}</b><button class="btn sm" id="signout">Sign out</button>`;
  $('#signout').onclick=()=>signOut(false)}
function signOut(expired){S.token=null;save();$('#app').hidden=true;$('#login').hidden=false;if(expired)$('#l-err').textContent='Your session ended. Sign in again.'}
function setNav(k){$$('#nav a').forEach(a=>a.toggleAttribute('aria-current',a.dataset.k===k)); $$('#nav a').forEach(a=>{if(a.dataset.k===k)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')})}
function page(title,lede,html){$('#main').innerHTML=`<div class="head"><div><h1>${title}</h1></div><p class="muted">${lede}</p></div>${html}`;$('#main').focus({preventScroll:true});document.title=title.replace(/<[^>]+>/g,'')+' · NASHA Growth OS (synthetic demo)'}

/* ---------------- dashboard ---------------- */
async function dashboard(){
  const d=await act(()=>api('GET','/dashboard'));if(!d)return;
  const nu=d.leads.new||0,q=d.leads.qualified||0,qr=d.qualification_runs;
  const max=Math.max(1,...d.pipeline.map(p=>p.count));
  const pend=await act(()=>api('GET','/approvals?state=pending&limit=5'))||{items:[]};
  page('Executive <em>dashboard</em>',`Synthetic data for <b>${esc(S.tenant)}</b>. Every figure below is read from the database through the API.`,`
  <div class="grid g4"><div class="card kpi"><b>${d.lead_total}</b><span>leads</span></div><div class="card kpi"><b>${nu}</b><span>new · ${q} qualified</span></div><div class="card kpi"><b>${money(d.open_value_cents)}</b><span>open pipeline value</span></div><div class="card kpi"><b>${d.approvals_pending}</b><span>awaiting approval</span></div></div>
  <div class="grid g2" style="margin-top:14px"><div class="card"><h2>Pipeline distribution</h2><div class="bars" role="list">${d.pipeline.length?d.pipeline.map(p=>`<div class="bar" role="listitem"><span>${esc(p.stage)}</span><i><b style="width:${100*p.count/max}%"></b></i><span class="mono">${p.count} · ${money(p.amount_cents)}</span></div>`).join(''):'<p class="note">No opportunities yet.</p>'}</div></div>
  <div class="card"><h2>Qualification activity</h2><div class="bars">${Object.keys(qr).length?Object.entries(qr).map(([k,v])=>`<div class="bar"><span>${chip(k)}</span><i><b style="width:${100*v/Math.max(1,...Object.values(qr))}%"></b></i><span class="mono">${v}</span></div>`).join(''):'<p class="note">No workflow runs yet.</p>'}</div></div></div>
  <div class="grid g2" style="margin-top:14px"><div class="card"><h2>Approval queue</h2>${pend.items.length?`<ul class="list">${pend.items.map(p=>`<li>${chip('AWAITING_APPROVAL')}<span><code>${esc(p.lead_id)}</code> · requested by ${esc(p.requester)}</span><a class="btn sm" href="#/workflows/${esc(p.run_id)}">Review</a></li>`).join('')}</ul>`:'<p class="note">Nothing is waiting for a decision.</p>'}</div>
  <div class="card"><h2>Recent workflow events</h2>${d.recent_events.length?`<ul class="timeline">${d.recent_events.map(e=>`<li><span class="mono">${esc(e.kind)}</span><span>${esc(e.name||e.kind)} <small>· ${esc(e.run_id)}</small></span><small>${esc(e.ts.slice(11,19))}</small></li>`).join('')}</ul>`:'<p class="note">No events yet.</p>'}</div></div>`)}

/* ---------------- CRM ---------------- */
const TABS=['accounts','contacts','leads','opportunities','activities'];
async function crm(tab='accounts'){
  tab=TABS.includes(tab)?tab:'accounts';
  const tabs=`<nav class="tabs" aria-label="CRM sections">${TABS.map(t=>`<a class="tab" href="#/crm/${t}" ${t===tab?'aria-current="page"':''}>${t}</a>`).join('')}</nav>`;
  page('<em>CRM</em>','Accounts, contacts, leads, opportunities and activities for this tenant. Writes are role-checked, audited and idempotent.',tabs+`<div id="crm-body"></div>`);
  const body=$('#crm-body'),load=async(cursor)=>{const j=await act(()=>api('GET',`/${tab}?limit=15${cursor?'&cursor='+cursor:''}`));return j};
  const accounts=async()=>(await act(()=>api('GET','/accounts?limit=50')))?.items||[],contacts=async()=>(await act(()=>api('GET','/contacts?limit=50')))?.items||[];
  const colsFor={accounts:['name','kind','version','created_at'],contacts:['full_name','email','consent_status','version'],leads:['source','status','score','version'],opportunities:['name','stage','amount_cents','version'],activities:['kind','body','actor','created_at']};
  let form='';
  if(tab==='accounts')form=can.write()?`<form class="inline" id="f"><label>Name<input name="name" required maxlength="120"></label><label>Kind<select name="kind"><option>business</option><option>household</option></select></label><button class="btn pri">Add account</button></form>`:'';
  if(tab==='contacts'){const acc=await accounts();form=can.write()?`<form class="inline" id="f"><label>Account<select name="account_id" required>${acc.map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('')}</select></label><label>Name<input name="full_name" required></label><label>Email (synthetic only)<input name="email" required placeholder="name@example.invalid" pattern=".+@example\\.invalid"></label><button class="btn pri">Add contact</button></form>`:''}
  if(tab==='leads'){const con=await contacts();form=can.write()||S.role==='MARKETING'?`<form class="inline" id="f"><label>Contact<select name="contact_id" required>${con.map(c=>`<option value="${esc(c.id)}">${esc(c.full_name)} (${esc(c.consent_status)})</option>`).join('')}</select></label><label>Source<select name="source"><option>synthetic-referral</option><option>synthetic-website-form</option><option>synthetic-event-fair</option></select></label><label>Budget confirmed<select name="budget_confirmed"><option value="true">yes</option><option value="false">no</option></select></label><label>Decision maker<select name="decision_maker"><option value="true">yes</option><option value="false">no</option></select></label><label>Timeline (days)<input name="timeline_days" type="number" min="0" max="3650"></label><label>Fit 0–1<input name="fit" type="number" step="0.05" min="0" max="1" value="0.5"></label><label>Engagement 0–1<input name="engagement" type="number" step="0.05" min="0" max="1" value="0.5"></label><button class="btn pri">Add lead</button></form>`:''}
  if(tab==='activities')form=can.content()?`<form class="inline" id="f"><label>Kind<select name="kind"><option>note</option><option>call_log</option><option>meeting</option></select></label><label>Note<input name="body" required maxlength="2000"></label><button class="btn pri">Log activity</button></form><p class="note">Email drafts are created only by the consent-gated outreach path; this screen cannot create or send messages.</p>`:'';
  body.innerHTML=(form||(tab==='opportunities'?'':'<p class="note">Your role is read-only here.</p>'))+`<div class="tablewrap" id="tbl"></div><p><button class="btn sm" id="more" hidden>Load more</button></p>`;
  let rows=[],next=null;
  const draw=()=>{ $('#tbl').innerHTML=`<table><thead><tr>${colsFor[tab].map(c=>`<th>${c.replace(/_/g,' ')}</th>`).join('')}<th>actions</th></tr></thead><tbody>${rows.map(r=>`<tr>${colsFor[tab].map(c=>`<td>${c==='amount_cents'?money(r[c]):c==='status'||c==='stage'||c==='consent_status'?chip(r[c],{qualified:'ok',converted:'ok',opt_in:'ok',disqualified:'bad',opt_out:'bad',won:'ok',lost:'bad'}[r[c]]||'info'):c==='created_at'?esc(String(r[c]).slice(0,19).replace('T',' ')):esc(r[c])}</td>`).join('')}<td>${actions(r)}</td></tr>`).join('')||`<tr><td colspan="9" class="note">No ${tab} yet.</td></tr>`}</tbody></table>`; $('#more').hidden=!next; wire()};
  const actions=r=>{
    if(tab==='contacts'&&(can.write()||S.role==='MARKETING'))return `<select aria-label="Set consent for ${esc(r.full_name)}" data-consent="${esc(r.id)}">${['none','opt_in','opt_out'].map(s=>`<option ${s===r.consent_status?'selected':''}>${s}</option>`).join('')}</select>`;
    if(tab==='leads'&&can.write())return (r.status==='new'?`<button class="btn sm" data-qualify="${esc(r.id)}">Run qualification</button>`:'')+(r.status==='qualified'?`<button class="btn sm" data-convert="${esc(r.id)}">Convert</button>`:'');
    return ''};
  const wire=()=>{ $$('[data-consent]').forEach(s=>s.onchange=async()=>{await act(()=>api('PUT',`/contacts/${s.dataset.consent}/consent`,{status:s.value},{idem:false}),'Consent updated');reload()});
    $$('[data-qualify]').forEach(b=>b.onclick=async()=>{const r=await act(()=>api('POST','/workflows/lead-qualification',{lead_id:b.dataset.qualify}),'Qualification proposed and held for approval');if(r)location.hash=`#/workflows/${r.corr_id}`});
    $$('[data-convert]').forEach(b=>b.onclick=async()=>{const name=prompt('Opportunity name','New opportunity');if(!name)return;const amt=Math.round(parseFloat(prompt('Amount in dollars','1000'))*100);if(!(amt>=0))return;await act(()=>api('POST',`/leads/${b.dataset.convert}/convert`,{opportunity_name:name,amount_cents:amt}),'Opportunity created');reload()})};
  const reload=async()=>{rows=[];const j=await load();if(j){rows=j.items;next=j.next_cursor;draw()}};
  $('#more').onclick=async()=>{const j=await load(next);if(j){rows=rows.concat(j.items);next=j.next_cursor;draw()}};
  const f=$('#f');if(f)f.onsubmit=async e=>{e.preventDefault();const v=Object.fromEntries(new FormData(f));let body=v,path='/'+tab;
    if(tab==='leads'){body={contact_id:v.contact_id,source:v.source,signals:{budget_confirmed:v.budget_confirmed==='true',decision_maker:v.decision_maker==='true',timeline_days:v.timeline_days===''?null:+v.timeline_days,fit:+v.fit,engagement:+v.engagement}}}
    const r=await act(()=>api('POST',path,body),'Saved');if(r){f.reset();reload()}};
  reload()}

/* ---------------- pipeline ---------------- */
async function pipeline(){
  const [p,o]=await Promise.all([act(()=>api('GET','/pipeline')),act(()=>api('GET','/opportunities?limit=50'))]);if(!p||!o)return;
  const accs=Object.fromEntries(((await act(()=>api('GET','/accounts?limit=50')))?.items||[]).map(a=>[a.id,a.name]));
  page('Sales <em>pipeline</em>','Move an opportunity with the selector. The database decides which moves are legal; an illegal move is refused by the backend and shown here.',`<div class="board" id="board">${p.stages.map(s=>`<section class="col" aria-label="${esc(s.stage)}"><h3><span>${esc(s.stage)}</span><span>${s.count} · ${money(s.amount_cents)}</span></h3>${o.items.filter(x=>x.stage===s.stage).map(x=>`<div class="opp"><b>${esc(x.name)}</b><span class="note">${esc(accs[x.account_id]||x.account_id)} · ${money(x.amount_cents)}</span>${can.write()&&!['won','lost'].includes(x.stage)?`<label class="note">Move to<select data-opp="${esc(x.id)}" aria-label="Move ${esc(x.name)}"><option value="">choose…</option>${p.stages.filter(t=>t.stage!==x.stage).map(t=>`<option value="${t.stage}">${t.stage}${s.next.includes(t.stage)?'':' (not allowed)'}</option>`).join('')}</select></label>`:''}</div>`).join('')||'<p class="note">empty</p>'}</section>`).join('')}</div><p class="note">${esc(p.note)}.${o.next_cursor?' First 50 opportunities shown.':''}</p>`);
  $$('[data-opp]').forEach(sel=>sel.onchange=async()=>{if(!sel.value)return;const r=await act(()=>api('POST',`/opportunities/${sel.dataset.opp}/stage`,{to_stage:sel.value}),'Stage updated');pipeline()})}

/* ---------------- pricing ---------------- */
async function pricing(){
  const pr=await act(()=>api('GET','/products?limit=50'));if(!pr)return;
  page('Pricing <em>studio</em>','Scenarios use the Growth OS pricing engine. Costs are planning assumptions and elasticity is an assumed input: no willingness to pay was measured.',`
  ${can.pricing()?'':'<p class="notice">Your role may view products but not run pricing scenarios.</p>'}
  <div class="grid g2"><div class="card"><h2>Product and scenarios</h2><label class="note" for="p-prod">Product</label><select id="p-prod">${pr.items.map(p=>`<option value="${esc(p.id)}">${esc(p.name)} · ${money(p.price_cents)} · cost ${money(p.unit_cost_cents)} · margin ${pct(p.margin)}</option>`).join('')}</select>
  <form id="p-form" class="grid" style="margin-top:12px"><div id="p-rows" class="grid"></div><button type="button" class="btn sm" id="p-add">Add scenario</button>
  <div class="grid g4"><label class="note">Base units<input id="p-units" type="number" min="1" value="200"></label><label class="note">Fixed costs ($)<input id="p-fixed" type="number" min="0" value="1000"></label><label class="note">Assumed elasticity<input id="p-el" type="number" step="0.1" min="-6" max="0" value="-1.5"></label></div>
  <button class="btn pri" ${can.pricing()?'':'disabled'}>Compute scenarios</button></form></div><div class="card" id="p-out"><h2>Comparison</h2><p class="note">Compute scenarios to compare margins, break-even and cost sensitivity.</p></div></div>`);
  const rows=$('#p-rows'),add=(l='',price='',d='0',c='0')=>{const r=document.createElement('div');r.className='srow';r.innerHTML=`<label class="note">Label<input class="s-l" value="${esc(l)}" maxlength="60"></label><label class="note">Price override ($)<input class="s-p" type="number" step="0.01" min="0" value="${price}"></label><label class="note">Discount %<input class="s-d" type="number" min="0" max="100" value="${d}"></label><label class="note">Cost change %<input class="s-c" type="number" min="-50" max="200" value="${c}"></label>`;rows.appendChild(r)};
  add('base');add('10% discount','','10');add('cost +20%','','0','20');$('#p-add').onclick=()=>add('scenario '+(rows.children.length+1));
  $('#p-form').onsubmit=async e=>{e.preventDefault();const sc=$$('.srow',rows).map(r=>({label:$('.s-l',r).value||'scenario',price_cents:$('.s-p',r).value?Math.round(+$('.s-p',r).value*100):null,discount_pct:+$('.s-d',r).value||0,cost_shock:(+$('.s-c',r).value||0)/100}));
    const body={product_id:$('#p-prod').value,base_units:+$('#p-units').value,fixed_costs_cents:Math.round(+$('#p-fixed').value*100),assumed_elasticity:+$('#p-el').value,scenarios:sc.map(s=>s.price_cents==null?(({price_cents,...x})=>x)(s):s)};
    const r=await act(()=>api('POST','/pricing/scenarios',body,{idem:false}));if(!r)return;const mx=Math.max(...r.scenarios.map(s=>Math.abs(s.gross_profit_at_base_units_cents)),1);
    $('#p-out').innerHTML=`<h2>Comparison · ${esc(r.product.name)}</h2><div class="tablewrap"><table><thead><tr><th>scenario</th><th>price</th><th>cost</th><th>margin</th><th>profit @ ${body.base_units}</th><th>break-even units</th></tr></thead><tbody>${r.scenarios.map(s=>`<tr><td>${esc(s.label)}</td><td>${money(s.price_cents)}</td><td>${money(s.cost_cents)}</td><td><b>${pct(s.margin)}</b></td><td>${money(s.gross_profit_at_base_units_cents)}<div class="bar" style="grid-template-columns:1fr"><i><b style="width:${100*Math.max(0,s.gross_profit_at_base_units_cents)/mx}%"></b></i></div></td><td>${s.breakeven_units==null?'—':Math.ceil(s.breakeven_units)}</td></tr>`).join('')}</tbody></table></div>
      <h3 style="margin-top:16px">Cost sensitivity (all else equal)</h3><div class="bars">${r.inflation.map(i=>`<div class="bar"><span>cost +${Math.round(i.shock*100)}%</span><i><b style="width:${100*Math.max(0,i.margin)}%"></b></i><span class="mono">${pct(i.margin)}</span></div>`).join('')}</div>
      ${r.sensitivity?`<h3 style="margin-top:16px">Price what-if</h3><p class="note">${esc(r.sensitivity.assumption)}. Best gross profit in this grid: ${money(r.sensitivity.best_price_cents)}.</p><div class="tablewrap"><table><thead><tr><th>price</th><th>units</th><th>gross profit</th></tr></thead><tbody>${r.sensitivity.rows.map(x=>`<tr><td>${money(x.price_cents)}</td><td>${x.units.toFixed(1)}</td><td>${money(x.gross_profit_cents)}</td></tr>`).join('')}</tbody></table></div>`:''}
      <ul class="note">${r.assumptions.map(a=>`<li>${esc(a)}</li>`).join('')}</ul>`}}

/* ---------------- workflow center ---------------- */
async function workflows(id){ if(id)return runDetail(id);
  const [runs,leads]=await Promise.all([act(()=>api('GET','/workflows/runs?limit=30')),act(()=>api('GET','/leads?status=new&limit=50'))]);if(!runs)return;
  page('AI <em>workflow center</em>','The lead-qualification workflow: evidence, recommendation, THE WEIR hold, a different person approves, then the CRM is updated. It is a deterministic rule-based workflow, not an AI model, and it contacts no one.',`
  <div class="card"><h2>Start a qualification</h2>${can.write()?`<form class="inline" id="q"><label>Lead<select name="lead_id">${(leads?.items||[]).map(l=>`<option value="${esc(l.id)}">${esc(l.id)} · ${esc(l.source)}</option>`).join('')}</select></label><button class="btn pri">Run qualification</button></form>`:'<p class="note">Your role cannot start qualification (THE WEIR denies the write tool for this role).</p>'}</div>
  <h2 style="margin-top:20px">Runs</h2><div class="tablewrap"><table><thead><tr><th>run</th><th>lead</th><th>state</th><th>requested by</th><th>failure</th><th></th></tr></thead><tbody>${runs.items.map(r=>`<tr><td><code>${esc(r.id)}</code></td><td><code>${esc(r.lead_id)}</code></td><td>${chip(r.state)}</td><td>${esc(r.requester)}</td><td>${esc(r.failure||'')}</td><td><a class="btn sm" href="#/workflows/${esc(r.id)}">Open</a></td></tr>`).join('')||'<tr><td colspan="6" class="note">No runs yet.</td></tr>'}</tbody></table></div>`);
  const q=$('#q');if(q)q.onsubmit=async e=>{e.preventDefault();const r=await act(()=>api('POST','/workflows/lead-qualification',{lead_id:new FormData(q).get('lead_id')}),'Proposal held for approval');if(r)location.hash=`#/workflows/${r.corr_id}`}}
async function runDetail(id){
  const r=await act(()=>api('GET',`/workflows/runs/${id}`));if(!r){location.hash='#/workflows';return}
  const p=r.proposal,ev=r.events,evidence=p?Object.entries(p.evidence):[];
  const mine=r.requester===S.user,canDecide=r.state==='AWAITING_APPROVAL'&&S.role==='OWNER'&&!mine;
  const why=r.state!=='AWAITING_APPROVAL'?'This run is not waiting for a decision.':S.role!=='OWNER'?'Only an owner may approve a qualification.':mine?'You requested this: a different person must decide (maker-checker).':'';
  page(`Run <em>${esc(id)}</em>`,`Lead <code>${esc(r.lead_id)}</code> · requested by ${esc(r.requester)} · ${chip(r.state)}`,`
  <div class="grid g2"><div class="card"><h2>Evidence</h2>${evidence.length?`<dl class="kv">${evidence.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(typeof v==='object'?JSON.stringify(v):v)}</dd>`).join('')}</dl>`:'<p class="note">No evidence was assembled (the run stopped earlier).</p>'}</div>
  <div class="card"><h2>Recommendation</h2>${p?`<p><b>${esc(p.proposed_status)}</b> · score ${p.score}/100 · outreach ${p.outreach_allowed?'<span class="chip ok">consent recorded</span>':'<span class="chip warn">not allowed</span>'}</p><ul class="list">${p.reasons.map(x=>`<li><span class="mono">+${x.points}</span><span>${esc(x.text)}</span><code>${esc(x.evidence)}</code></li>`).join('')}</ul><p class="note">${esc(p.notice)}</p>`:'<p class="note">No recommendation was produced.</p>'}</div></div>
  <div class="grid g2" style="margin-top:14px"><div class="card"><h2>Proposed action and approval</h2>${p?`<p>Set lead <code>${esc(p.lead_id)}</code> to <b>${esc(p.proposed_status)}</b> (score ${p.score}). Updates the CRM record only; sends nothing.</p>`:''}<p>Status: ${chip(r.state)} ${r.approval_id?`<code>${esc(r.approval_id)}</code>`:''}</p>
   <div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn pri" id="ap" ${canDecide?'':'disabled'}>Approve this exact action</button><button class="btn" id="rj" ${canDecide?'':'disabled'}>Reject</button></div>${canDecide?'':`<p class="note">${esc(why)}</p>`}
   ${r.failure?`<p class="notice" style="margin-top:12px">Failure: ${esc(r.failure)}</p>`:''}</div>
  <div class="card"><h2>Execution trace</h2><ul class="timeline">${ev.map(e=>{const bad=e.failure||e.kind==='failure',hold=e.held_for_approval;return `<li class="${bad?'bad':hold?'hold':e.ok||e.name==='crm_updated'?'ok':''}"><span class="mono">${e.seq}</span><span>${esc(e.kind==='stage'?e.name:e.kind==='tool_call'?`${e.tool}${hold?' → held for approval':e.forwarded?' → forwarded':e.failure?' → '+e.failure:''}`:e.kind==='approval_decision'?`decision: ${e.decision} by ${e.by||'?'}`:e.kind==='failure'?`failure: ${e.failure_class}`:e.kind==='auth'?`auth: ${e.decision} (${e.user}, ${e.role})`:e.kind)}</span><small>${esc(e.ts.slice(11,19))}</small></li>`}).join('')}</ul></div></div>`);
  const decide=async ok=>{const c=prompt(ok?'Approval comment':'Reason for rejecting','')??'';const d=await act(()=>api('POST',`/workflows/runs/${id}/decision`,{approve:ok,comment:c},{idem:false}),ok?'Approved and applied to the CRM':'Rejected');if(d)runDetail(id)};
  if($('#ap')){$('#ap').onclick=()=>decide(true);$('#rj').onclick=()=>decide(false)}}

/* ---------------- security and audit ---------------- */
async function security(){
  const [au0,hist,v]=await Promise.all([act(()=>api('GET','/audit?limit=50')),act(()=>api('GET','/approvals?state=history&limit=20')),act(()=>api('GET','/audit/verify'))]);if(!au0)return;
  const au={items:[...au0.items]};let cur=au0.next_cursor;for(let i=0;i<3&&cur;i++){const m=await act(()=>api('GET','/audit?limit=50&cursor='+cur));if(!m)break;au.items.push(...m.items);cur=m.next_cursor}
  const deny=au.items.filter(a=>a.decision==='deny').length,allow=au.items.length-deny;
  page('Security and <em>audit</em>','Tenant context, authorization outcomes, approval history and the append-only audit log. The audit chain is hash-linked per tenant.',`
  <div class="grid g4"><div class="card kpi"><b>${esc(S.tenant.replace('tenant-',''))}</b><span>tenant context</span></div><div class="card kpi"><b>${esc(S.role)}</b><span>your role (${esc(S.user)})</span></div><div class="card kpi"><b>${allow}/${deny}</b><span>allowed / denied (latest ${au.items.length})</span></div><div class="card kpi"><b>${v?(v.chain_valid?'valid':'BROKEN'):'—'}</b><span>audit chain${v&&v.rows?` · ${v.rows} rows`:''}</span></div></div>
  <div class="grid g2" style="margin-top:14px"><div class="card"><h2>Approval history</h2>${hist&&hist.items.length?`<ul class="list">${hist.items.map(h=>`<li>${chip(h.detail.decision,h.detail.decision==='approve'?'ok':'bad')}<span><code>${esc(h.run_id)}</code> · by ${esc(h.detail.by||h.detail.user||'?')}${h.detail.code?' · '+esc(h.detail.code):''}</span><small class="dim">${esc(h.ts.slice(0,19).replace('T',' '))}</small></li>`).join('')}</ul>`:'<p class="note">No approval decisions yet.</p>'}</div>
  <div class="card"><h2>Tenant isolation</h2><p class="muted">Your session is bound to <b>${esc(S.tenant)}</b> by that tenant's own signing key. The tenant comes only from the URL path; no request parameter can change it, and PostgreSQL row-level security applies underneath. The other synthetic tenant's data is not reachable from here.</p><button class="btn sm" id="vrf">Verify audit chain now</button> <span id="vout" class="note"></span></div></div>
  <h2 style="margin-top:20px">Audit events (latest ${Math.min(au.items.length,50)} shown)</h2><div class="tablewrap"><table><thead><tr><th>#</th><th>time</th><th>actor</th><th>role</th><th>action</th><th>entity</th><th>decision</th><th>detail</th></tr></thead><tbody>${au.items.slice(0,50).map(a=>`<tr><td>${a.seq}</td><td>${esc(String(a.ts).slice(11,19))}</td><td>${esc(a.actor)}</td><td>${esc(a.role)}</td><td>${esc(a.action)}</td><td><code>${esc(a.entity_id||a.entity)}</code></td><td>${chip(a.decision,a.decision==='allow'?'ok':'bad')}</td><td><code>${esc(JSON.stringify(a.detail))}</code></td></tr>`).join('')}</tbody></table></div>`);
  $('#vrf').onclick=async()=>{const r=await act(()=>api('GET','/audit/verify'));if(r)$('#vout').textContent=r.chain_valid?`Chain valid across ${r.rows} rows.`:`Chain broken at row ${r.first_bad_seq}.`}}

function settings(){page('<em>Settings</em>','Session and tenant information.',`<div class="card"><dl class="kv"><dt>Tenant</dt><dd>${esc(S.tenant)}</dd><dt>User</dt><dd>${esc(S.user)}</dd><dt>Role</dt><dd>${esc(S.role)}</dd><dt>Data</dt><dd>Synthetic. No real customers, contacts, transactions or campaigns exist in this application.</dd><dt>Outbound actions</dt><dd>Disabled by construction: the API and database have no send, publish or purchase operation.</dd><dt>Workflow engine</dt><dd>Deterministic lead qualification on THE WEIR; not run on the Production AI Agent Platform.</dd></dl><p><button class="btn" id="so2">Sign out</button></p></div>`);$('#so2').onclick=()=>signOut(false)}

/* ---------------- router and login ---------------- */
const ROUTES={dashboard,crm,pipeline,pricing,workflows,security,settings:()=>settings()};
async function route(){if(!S.token)return;const [k,a]=(location.hash.slice(2)||'dashboard').split('/');const fn=ROUTES[k]||dashboard;setNav(ROUTES[k]?k:'dashboard');try{await fn(a)}catch(e){fail(e)}}
addEventListener('hashchange',route);
function boot(){ if(S.token){shell();if(!location.hash)location.hash='#/dashboard';route()}else{$('#login').hidden=false;$('#app').hidden=true;pass()} }
const pass=()=>{$('#l-pass').value=`${$('#l-tenant').value}-${$('#l-user').value}-dev-passcode`};
$('#l-tenant').onchange=pass;$('#l-user').onchange=pass;
$('#login-form').onsubmit=async e=>{e.preventDefault();$('#l-err').textContent='';const t=$('#l-tenant').value;
  try{const r=await fetch(`/v1/tenants/${t}/session`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:$('#l-user').value,passcode:$('#l-pass').value})});const j=await r.json();
    if(!r.ok){$('#l-err').textContent='Sign-in failed: '+(j.error?j.error.message:'error');return}
    S={tenant:t,user:j.user,role:j.role,token:j.token};save();location.hash='#/dashboard';boot()}catch(x){$('#l-err').textContent='Could not reach the API.'}};
boot();
})();
