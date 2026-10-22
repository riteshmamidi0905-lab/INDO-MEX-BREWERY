"""Recipe version management with a human-approval workflow and a tamper-evident audit trail (SQLite).

States: draft -> in_review -> approved | rejected ; approved -> superseded when a newer version is approved.
Rules enforced in code (and tested):
  * a version's content is immutable once submitted (its SHA-256 is recorded; edits create a NEW version);
  * only a HUMAN approver role may approve: an agent identity (role 'agent') can draft, submit and recommend, never approve;
  * maker-checker: the approver must differ from the author;
  * approvals need a comment and are final; every event is appended to a hash chain so any later edit of history is detectable.
"""
import hashlib
import json
import sqlite3
import time

HUMAN_APPROVERS = {"founder", "head_chef", "head_brewer", "food_safety_reviewer"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS versions (recipe_id TEXT, version TEXT, status TEXT, author TEXT, sha256 TEXT, content TEXT, created TEXT, PRIMARY KEY (recipe_id, version));
CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, role TEXT, action TEXT, recipe_id TEXT, version TEXT, detail TEXT, prev_hash TEXT, hash TEXT);
"""


class WorkflowError(Exception):
    pass


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class RecipeStore:
    def __init__(self, path=":memory:"):
        self.con = sqlite3.connect(str(path))
        self.con.executescript(SCHEMA)

    # ------------------------------------------------------------ audit
    def _log(self, actor, role, action, rid, ver, detail=""):
        prev = (self.con.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone() or ("GENESIS",))[0]
        ts = _now()
        h = hashlib.sha256("|".join((prev, ts, actor, role, action, rid, ver, detail)).encode()).hexdigest()
        self.con.execute("INSERT INTO audit (ts,actor,role,action,recipe_id,version,detail,prev_hash,hash) VALUES (?,?,?,?,?,?,?,?,?)", (ts, actor, role, action, rid, ver, detail, prev, h))
        self.con.commit()

    def verify_audit(self):
        prev = "GENESIS"
        for seq, ts, actor, role, action, rid, ver, detail, p, h in self.con.execute("SELECT seq,ts,actor,role,action,recipe_id,version,detail,prev_hash,hash FROM audit ORDER BY seq"):
            if p != prev or hashlib.sha256("|".join((p, ts, actor, role, action, rid, ver, detail)).encode()).hexdigest() != h:
                return False, seq
            prev = h
        return True, None

    # ------------------------------------------------------------ versions
    def _row(self, rid, ver):
        r = self.con.execute("SELECT status, author, sha256, content FROM versions WHERE recipe_id=? AND version=?", (rid, ver)).fetchone()
        if not r:
            raise WorkflowError(f"no such version {rid} {ver}")
        return r

    def create_draft(self, recipe: dict, author: str, role: str):
        rid, ver = recipe["id"], recipe["version"]
        if self.con.execute("SELECT 1 FROM versions WHERE recipe_id=? AND version=?", (rid, ver)).fetchone():
            raise WorkflowError(f"{rid} {ver} already exists: create a NEW version instead of editing")
        self.con.execute("INSERT INTO versions VALUES (?,?,?,?,?,?,?)", (rid, ver, "draft", author, sha(recipe), json.dumps(recipe, ensure_ascii=False), _now()))
        self.con.commit()
        self._log(author, role, "create_draft", rid, ver, f"sha={sha(recipe)[:12]}")

    def submit(self, rid, ver, actor, role):
        status, author, h, content = self._row(rid, ver)
        if status != "draft":
            raise WorkflowError(f"only a draft can be submitted (is {status})")
        if sha(json.loads(content)) != h:
            raise WorkflowError("content hash mismatch")
        self.con.execute("UPDATE versions SET status='in_review' WHERE recipe_id=? AND version=?", (rid, ver)); self.con.commit()
        self._log(actor, role, "submit_for_review", rid, ver)

    def approve(self, rid, ver, approver, role, comment):
        status, author, h, content = self._row(rid, ver)
        if role not in HUMAN_APPROVERS:
            raise WorkflowError(f"role '{role}' may not approve: only a human approver role ({sorted(HUMAN_APPROVERS)})")
        if approver == author:
            raise WorkflowError("maker-checker: the approver must differ from the author")
        if not comment or not comment.strip():
            raise WorkflowError("an approval needs a comment")
        if status != "in_review":
            raise WorkflowError(f"only an in_review version can be approved (is {status})")
        if sha(json.loads(content)) != h:
            raise WorkflowError("content changed after submission")
        self.con.execute("UPDATE versions SET status='superseded' WHERE recipe_id=? AND status='approved'", (rid,))
        self.con.execute("UPDATE versions SET status='approved' WHERE recipe_id=? AND version=?", (rid, ver)); self.con.commit()
        self._log(approver, role, "approve", rid, ver, comment.strip())

    def reject(self, rid, ver, actor, role, comment):
        status, *_ = self._row(rid, ver)
        if role not in HUMAN_APPROVERS:
            raise WorkflowError("only a human approver role may reject")
        if status != "in_review":
            raise WorkflowError(f"only an in_review version can be rejected (is {status})")
        self.con.execute("UPDATE versions SET status='rejected' WHERE recipe_id=? AND version=?", (rid, ver)); self.con.commit()
        self._log(actor, role, "reject", rid, ver, comment)

    # ------------------------------------------------------------ queries
    def status(self, rid, ver):
        return self._row(rid, ver)[0]

    def current(self, rid):
        r = self.con.execute("SELECT version, content FROM versions WHERE recipe_id=? AND status='approved'", (rid,)).fetchone()
        return (r[0], json.loads(r[1])) if r else None

    def history(self, rid):
        return [dict(version=v, status=s, author=a, sha256=h[:12], created=c) for v, s, a, h, c in self.con.execute("SELECT version,status,author,sha256,created FROM versions WHERE recipe_id=? ORDER BY created, version", (rid,))]

    def diff(self, rid, v1, v2):
        """Field-level diff between two versions (quantities, steps, sections)."""
        a, b = json.loads(self._row(rid, v1)[3]), json.loads(self._row(rid, v2)[3])
        out = []

        def walk(x, y, path):
            if isinstance(x, dict) and isinstance(y, dict):
                for k in sorted(set(x) | set(y)):
                    if k not in x:
                        out.append((path + [k], None, y[k]))
                    elif k not in y:
                        out.append((path + [k], x[k], None))
                    else:
                        walk(x[k], y[k], path + [k])
            elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
                for i, (p, q) in enumerate(zip(x, y)):
                    walk(p, q, path + [i])
            elif x != y:
                out.append((path, x, y))
        walk(a, b, [])
        return [{"path": "/".join(map(str, p)), "old": o, "new": n} for p, o, n in out if p and p[-1] not in ("version",)]
