"""Business profiles are scenario assumptions, never claims of operating history."""
from dataclasses import asdict, dataclass
import datetime as dt
import re

@dataclass(frozen=True)
class BusinessConfig:
    tenant: str = 'nasha-brewery'
    name: str = 'NASHA Brewery (fictional)'
    idea: str = 'An Indo-Mexican brewery synthetic enterprise demonstration'
    start: str = '2025-05-09'
    end: str = '2026-10-24'
    seed: int = 20261024
    target_orders: int = 35000
    industry: str = 'hospitality'

    def validate(self):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', self.tenant):
            raise ValueError('invalid tenant identifier')
        a,b=dt.date.fromisoformat(self.start),dt.date.fromisoformat(self.end)
        if not 0 <= (b-a).days <= 730 or type(self.seed) is not int or not 1 <= self.target_orders <= 100000:
            raise ValueError('invalid scenario bounds')
        if self.industry not in ('hospitality','fitness'):
            raise ValueError('unsupported scenario industry')
        return self

    def document(self):
        return asdict(self.validate())

# Role identities are configurable fictional personas, not running agents.
WORKFORCE = [
 ('adrian','Executive','Adrian Rao','CEO',12000000,['summary','organization']),
 ('maya','Finance','Maya Desai','CFO',11000000,['summary','finance']),
 ('daniel','Technology','Daniel Park','CTO',11500000,['summary','evidence']),
 ('amara','Operations','Amara Brooks','COO',10500000,['summary','operations']),
 ('elena','Product','Elena Morris','Product Manager',9000000,['summary','projects']),
 ('noah','Software Engineering','Noah Bennett','Software Engineer',10000000,['evidence','projects']),
 ('aiden','AI Engineering','Aiden Shah','AI Engineer',10500000,['evidence','projects']),
 ('priya','Data Engineering','Priya Nair','Data Engineer',10000000,['summary','operations']),
 ('sofia','Analytics','Sofia Chen','Product/Data Analyst',8500000,['summary','finance']),
 ('ethan','Quality','Ethan Cole','QA Engineer',8500000,['evidence','operations']),
 ('zara','Security','Zara Malik','Security Engineer',10500000,['evidence','organization']),
 ('lucas','CRM','Lucas Reed','Partnerships Manager',8000000,['stakeholders']),
 ('arjun','Procurement','Arjun Mehta','Procurement Analyst',7500000,['stakeholders','operations']),
 ('mateo','Marketing','Mateo Rivera','Marketing Manager',8500000,['summary','projects']),
 ('olivia','People Operations','Olivia Brooks','HR Manager',8000000,['organization']),
]
