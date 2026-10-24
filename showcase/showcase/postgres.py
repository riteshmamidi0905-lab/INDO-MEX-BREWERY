"""Optional migration for a NEW dedicated showcase schema; never alters existing tables.
Caller supplies an explicitly selected connection. No production connection defaults.
"""
import re
from pathlib import Path
from .scenario import TABLES

def migrate(connection,schema):
    if not re.fullmatch(r'showcase_v1_[a-z][a-z0-9_]{0,32}',schema):
        raise ValueError('new isolated showcase_v1_ schema required')
    # Refuses an existing schema; no DROP or IF NOT EXISTS disguises an overwrite.
    with connection.transaction():
        connection.execute(f'CREATE SCHEMA {schema}')
        connection.execute(f'SET LOCAL search_path TO {schema}')
        connection.execute(Path(__file__).with_name('schema.sql').read_text())
        for table in TABLES:
            connection.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
            connection.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
            connection.execute(f"CREATE POLICY tenant_scope ON {table} USING (tenant_id=current_setting('showcase.tenant_id',true)) WITH CHECK (tenant_id=current_setting('showcase.tenant_id',true))")
        # PG views otherwise run with owner privileges; require PG15+ invoker mode.
        connection.execute('ALTER VIEW finance_summary SET (security_invoker=true)')
