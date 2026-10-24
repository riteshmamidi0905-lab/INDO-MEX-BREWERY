import argparse
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from .config import BusinessConfig
from .scenario import build,export,canonical,validate

p=argparse.ArgumentParser(description='Fully synthetic showcase fixtures; no external actions')
p.add_argument('command',choices=['build','check','export'])
p.add_argument('--database',type=Path,required=True)
p.add_argument('--tenant',default='nasha-brewery')
p.add_argument('--industry',choices=['hospitality','fitness'],default='hospitality')
p.add_argument('--orders',type=int,default=35000)
a=p.parse_args()
if a.command=='build':
    c=BusinessConfig(tenant=a.tenant,industry=a.industry,target_orders=a.orders)
    if a.industry=='fitness': c=replace(c,name='Meridian Fitness (fictional)',idea='Synthetic fitness membership business')
    print(json.dumps(build(c,a.database),indent=2))
else:
    with sqlite3.connect(a.database.resolve().as_uri()+'?mode=ro',uri=True) as con:
        validate(con)
        print(canonical(export(con,a.tenant)) if a.command=='export' else 'Validated synthetic records, journal, line items, and event provenance')
