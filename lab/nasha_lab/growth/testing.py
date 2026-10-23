"""Test and evidence-tool helper (never imported by the application): perform a raw SQL mutation of a guarded table WITH its audit evidence in the same transaction, the way the service does.
Used to set up conditions (planted rows, direct stage updates) while the database's audit guard stays enabled."""
from contextlib import contextmanager


@contextmanager
def audited(svc, entity, entity_id, also=None, action="test.raw"):
    """with audited(svc, 'opportunities', oid): svc.con.execute('UPDATE ...')  -> the update and an 'allow' audit row commit together (or both roll back)."""
    with svc.con.transaction():
        yield
        svc._audit(action, entity, entity_id, "allow", {"also": also} if also else None)


def attempt(svc, entity, entity_id, sql, params, refused_by):
    """Run a raw statement WITH audit evidence (so the audit guard is satisfied) and report whether the database's OTHER controls refused it: True = refused by one of `refused_by`, False = accepted."""
    try:
        with audited(svc, entity, entity_id):
            svc.con.execute(sql, params)
        return False
    except refused_by:
        return True
