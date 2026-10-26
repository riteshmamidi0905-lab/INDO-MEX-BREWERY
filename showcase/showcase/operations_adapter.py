"""Offline-only scenario adapter. No provider, action, persistence or identity provisioning.
Host-only inputs: a trusted configuration and retained source snapshot, not HTTP/model fields.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from types import MappingProxyType
from uuid import UUID

from .operations import explain as amara_explain
from .workforce import SCENARIOS
from ._ops_alignment.nasha_lab.growth import ops_explanation as contract

RECORD_HASH_PROFILE = 'record-hash.v1'
OUTPUT_VERSION = 'ops-explanation-output.v1'
RENDERER_REVISION = 'ops-renderer-v2.0-tenant-scoped-labels'
LABEL_POLICY_REVISION = 'amara-tenant-item-labels.v1'
VECTOR_V2_IDENTITY = 'a73ec5df83296d265242f4a17050797a29ea0ad45001e2af7cf116c41fac76cc'
ALIASES = MappingProxyType({'nasha-brewery':'Synthetic packaging','meridian-fitness':'Synthetic towels'})
EFFECTS = ('PURCHASE','INVENTORY_MUTATION','SUPPLIER_CONTACT','APPROVAL','FINANCIAL_MUTATION','ARBITRARY_TOOL')


class AdapterRefused(ValueError):
    def __init__(self, *codes, status='REJECTED'):
        self.codes=tuple(sorted(set(codes)))
        self.status=status
        super().__init__(','.join(self.codes))


def canonical(value):
    """canonical-json.v1; reject floats, non-string keys and invalid Unicode."""
    def check(v):
        if isinstance(v,str):v.encode('utf-8',errors='strict')
        elif isinstance(v,dict):
            for k,x in v.items():
                if type(k) is not str:raise ValueError('Non-string JSON key')
                check(k);check(x)
        elif isinstance(v,(list,tuple)):
            for x in v:check(x)
        elif v is not None and type(v) not in (int,bool):raise ValueError('Non-integer JSON number or unsupported type')
    check(value)
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def sha(value):return hashlib.sha256(canonical(value)).hexdigest()


def _utc(value):
    try:
        if not isinstance(value,str) or not value.endswith('Z'):raise ValueError()
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:raise ValueError()
        return parsed
    except (TypeError,ValueError):raise AdapterRefused('input_invalid') from None


@dataclass(frozen=True)
class OfflineConfig:
    """Explicit trusted host config. No default scopes and no tenant-identity creation."""
    tenant_scopes: object
    source_as_of: str
    max_age_seconds: int = 86400
    record_hash_profile: str = RECORD_HASH_PROFILE

    def __post_init__(self):
        if contract.RENDERER_REVISION!=RENDERER_REVISION:
            raise AdapterRefused('mode_mismatch',status='FAILED')
        if self.record_hash_profile != RECORD_HASH_PROFILE:
            raise AdapterRefused('record_hash_profile_unsupported',status='FAILED')
        scopes=dict(self.tenant_scopes)
        if not scopes or set(scopes)-set(ALIASES) or len(set(scopes.values()))!=len(scopes):
            raise AdapterRefused('input_invalid')
        try:
            if any(str(UUID(v))!=v for v in scopes.values()):raise ValueError()
        except (ValueError,TypeError,AttributeError):raise AdapterRefused('input_invalid') from None
        _utc(self.source_as_of)
        if type(self.max_age_seconds) is not int or self.max_age_seconds<0:raise AdapterRefused('input_invalid')
        object.__setattr__(self,'tenant_scopes',MappingProxyType(scopes))

    @property
    def display_labels(self):
        # Values come only from reviewed server constants; no input alias is inspected.
        return MappingProxyType({(scope,'item:packaging'):ALIASES[tenant]
                                 for tenant,scope in self.tenant_scopes.items()})

    @property
    def sha256(self):
        return sha(dict(tenant_scopes=dict(self.tenant_scopes),source_as_of=self.source_as_of,
                        max_age_seconds=self.max_age_seconds,record_hash_profile=self.record_hash_profile,
                        validator_revision=contract.VALIDATOR_REVISION,renderer_revision=RENDERER_REVISION,
                        vector_identity=VECTOR_V2_IDENTITY,label_policy_revision=LABEL_POLICY_REVISION,
                        display_labels=[dict(scope=scope,item_id=item,label=label)
                                        for (scope,item),label in sorted(self.display_labels.items())]))


@dataclass(frozen=True)
class SourceSnapshot:
    tenant: str
    tenant_scope_id: str
    scenario_id: str
    config_sha256: str
    record_hash_profile: str
    snapshot_id: str
    snapshot_sha256: str
    snapshot_bytes: bytes
    trusted_record_hashes: object

    def __post_init__(self):
        # Copy before freezing: changes to a caller's original dictionary cannot mutate this map.
        object.__setattr__(self,'trusted_record_hashes',MappingProxyType(dict(self.trusted_record_hashes)))
        object.__setattr__(self,'snapshot_bytes',bytes(self.snapshot_bytes))


def record_preimage(scope, fact):
    p=fact['provenance']
    return dict(profile=RECORD_HASH_PROFILE,tenant_scope_id=scope,
                **{k:p[k] for k in ('source_kind','source_ref','record_id','source_revision')},
                **{k:fact[k] for k in ('subject_id','inventory_item_id','field','availability','value','unit','as_of')})


def retain_scenario(config, tenant, scenario_id):
    """Retain authoritative server constants, never a client/DOM-provided Amara payload."""
    if tenant not in config.tenant_scopes:raise AdapterRefused('cross_tenant_reference')
    if scenario_id not in SCENARIOS:raise AdapterRefused('input_invalid')
    scope=config.tenant_scopes[tenant]
    # Reuse Amara's existing records. The third (target) is supplementary evidence from the same Phase 4 source.
    records={r['field']:r['value'] for r in amara_explain(tenant,scenario_id)['records']}
    records['target']=SCENARIOS[scenario_id]['target']
    facts=[];trusted={}
    for field,value in sorted(records.items()):
        name=field+'_units'
        fact=dict(id='fact:'+name,subject_id='item:packaging',inventory_item_id='item:packaging',field=name,
                  availability='MISSING' if value is None else 'PRESENT',value=value,unit='UNITS',as_of=config.source_as_of,
                  provenance=dict(source_kind='SCENARIO_ASSUMPTION',source_ref=f'scenario://{scenario_id}/v1/{name}',
                                  record_id=f'scenario:{scenario_id}',source_revision=f'{scenario_id}:v1'))
        fact['provenance']['record_sha256']=sha(record_preimage(scope,fact))
        key=fact['provenance']['record_id']+'|'+fact['provenance']['source_ref']
        if key in trusted:raise AdapterRefused('source_provenance_missing')
        trusted[key]=fact['provenance']['record_sha256'];facts.append(fact)
    data=dict(as_of=config.source_as_of,entities=[dict(id='item:packaging',kind='INVENTORY_ITEM',alias=ALIASES[tenant])],
              facts=facts,comparison_groups=[],completeness=[])
    return SourceSnapshot(tenant,scope,scenario_id,config.sha256,RECORD_HASH_PROFILE,'snapshot:scenario-v1',
                          sha(data),canonical(data),trusted)


def model_input(config, source, *, tenant, analysis_id, workflow_id, now):
    """Pure transformation. workflow_id must be supplied by a trusted owned-run resolver.
    Test fixtures may supply fixed UUIDs/run IDs; this function never creates a run.
    """
    if contract.RENDERER_REVISION!=RENDERER_REVISION:
        raise AdapterRefused('mode_mismatch',status='FAILED')
    if source.record_hash_profile!=RECORD_HASH_PROFILE:
        raise AdapterRefused('record_hash_profile_unsupported',status='FAILED')
    if tenant!=source.tenant or config.tenant_scopes.get(tenant)!=source.tenant_scope_id:
        raise AdapterRefused('cross_tenant_reference')
    if config.sha256!=source.config_sha256:raise AdapterRefused('source_provenance_missing')
    _utc(now)
    try:
        data=json.loads(source.snapshot_bytes)
        encoded=canonical(data)
    except (ValueError,UnicodeError,TypeError):raise AdapterRefused('input_invalid') from None
    if not isinstance(data,dict):raise AdapterRefused('input_invalid')
    if encoded!=source.snapshot_bytes or sha(data)!=source.snapshot_sha256:raise AdapterRefused('source_hash_mismatch')
    data.update(schema_version='ops-explanation-input.v1',analysis_id=analysis_id,tenant_scope_id=source.tenant_scope_id,
                workflow_id=workflow_id,snapshot_id=source.snapshot_id,snapshot_sha256=source.snapshot_sha256,
                task='EXPLAIN_SYNTHETIC_INVENTORY_DISCREPANCY',prohibited_effects=list(EFFECTS))
    codes=contract.check_input(data,now=now,max_age_seconds=config.max_age_seconds,
                               trusted_record_hashes=source.trusted_record_hashes)
    if codes:raise AdapterRefused('input_refused',*codes)
    return data


def replay(config, source, *, tenant, analysis_id, workflow_id, now):
    """Explicit offline replay. There is NO candidate/provider callback or selectable mode."""
    mi=model_input(config,source,tenant=tenant,analysis_id=analysis_id,workflow_id=workflow_id,now=now)
    output=contract.reference_output(mi)
    if output['schema_version']!=OUTPUT_VERSION:raise AdapterRefused('mode_mismatch',status='FAILED')
    verdict=contract.validate_output(canonical(output),mi,trusted_record_hashes=source.trusted_record_hashes,
                                     now=now,max_age_seconds=config.max_age_seconds)
    if verdict['status']=='REJECTED':raise AdapterRefused(*verdict['codes'])
    text=contract.render_answer(mi,authorized_tenant_scope=config.tenant_scopes[tenant],
                                labels=config.display_labels) if output['status']=='ANSWER' else contract.render_abstention(verdict)
    accepted_hash=contract.accepted_result_sha256(mi,output,text) if output['status']=='ANSWER' else None
    envelope=contract.make_envelope(mi,'AUDIT_PENDING','DETERMINISTIC_REPLAY',output=output,rendered=text,
                                    audit_complete=False,accepted_hash=accepted_hash)
    return dict(model_input=mi,envelope=envelope,verification_status=verdict['status'],
                label='Deterministic contract replay — no model call',live_model=False,provider_calls=0,
                record_hash_profile=RECORD_HASH_PROFILE,config_sha256=config.sha256,
                renderer_revision=contract.RENDERER_REVISION,validator_revision=contract.VALIDATOR_REVISION,
                scope='Offline verified artifact; no persisted explanation audit or approved action.')


def replay_owned_run(engine, reviewer, run_id, config, *, analysis_id, now):
    """Read an existing authorized Phase 4 run only; no start/approve/execute calls.
    Existing access-denied auditing remains owned by engine.owned(). No HTTP route is added.
    """
    with engine.lock:
        engine.owned(run_id,reviewer)
        if not engine.ledger.verify_audit()[0] or not engine.weir.verify_chain()[0]:
            raise AdapterRefused('source_provenance_missing')
        context=engine.context(run_id);scenario=context['scenario_id']
        if scenario not in SCENARIOS or any(context['scenario'].get(k)!=SCENARIOS[scenario][k] for k in ('expected','counted','target')):
            raise AdapterRefused('source_hash_mismatch')
        source=retain_scenario(config,engine.tenant,scenario)
        return replay(config,source,tenant=engine.tenant,analysis_id=analysis_id,workflow_id=run_id,now=now)
