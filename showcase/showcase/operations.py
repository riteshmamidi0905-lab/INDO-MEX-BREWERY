"""Pure, read-only explanation of existing Phase 4 scenario assumptions. No provider."""
from .scenario import digest
from .workforce import SCENARIOS


def explain(tenant, scenario_id='count-gap'):
    if scenario_id not in SCENARIOS:
        raise ValueError('Unknown scenario')
    scenario = SCENARIOS[scenario_id]
    records = [dict(id=f'{tenant}:{scenario_id}:{field}', field=field,
                    value=scenario[field], unit='units',
                    source=f'workforce.py:SCENARIOS/{scenario_id}/{field}',
                    classification='SYNTHETIC_SCENARIO_ASSUMPTION')
               for field in ('expected', 'counted')]
    for record in records:
        record['sha256'] = digest(record)
    missing = scenario['counted'] is None
    difference = None if missing else scenario['expected'] - scenario['counted']
    if missing:
        text = 'The counted quantity is missing. No discrepancy can be established. Verify a count before drawing a conclusion.'
    elif difference > 0:
        text = f"The scenario expects {scenario['expected']} units and records {scenario['counted']} counted units: a shortfall of {difference} units. These supplied assumptions do not establish a cause."
    elif difference < 0:
        text = f'The scenario records a surplus of {-difference} units. The supplied assumptions do not establish a cause.'
    else:
        text = 'Expected and counted quantities match. There is no discrepancy in this scenario snapshot; this does not establish that inventory is correct elsewhere.'
    return dict(tenant=tenant, agent='Amara', role='Fictional Operations persona',
                mode='DETERMINISTIC_REPLAY', live_model=False,
                model_status='DISABLED_REQUIRES_REVIEW',
                status='ABSTAINED' if missing else 'EXPLAINED', scenario_id=scenario_id,
                scenarios=[dict(id=k,title=v['title']) for k,v in SCENARIOS.items()],
                explanation=text, difference=difference, records=records,
                snapshot_sha256=digest({'tenant':tenant,'scenario_id':scenario_id,'records':records}),
                renderer_revision='amara-readonly.v1',
                fallback='Deterministic demonstration selected explicitly; not an automatic fallback from a model call.',
                limitations=['Scenario assumptions, not measured stock or financial records.',
                             'Physical cause is not established.',
                             'No purchase, supplier contact, approval or inventory change is performed.'])
