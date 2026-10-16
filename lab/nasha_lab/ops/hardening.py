"""P2 hardening primitives: GAP-08 schema migration with rollback, GAP-09 secrets scanning + config boundary. SYNTHETIC / OFFLINE."""
import json
import os
import re
import sqlite3

from .util import OPS_DIR, load_json

LAB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ======================================================================================================= GAP-09
PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"), "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "provider_style_api_key": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}"),
    "dev_passcode_literal": re.compile(r"\b[a-z]+-dev-passcode\b"), "bearer_literal": re.compile(r"Bearer\s+[A-Za-z0-9._-]{30,}"),
    "assigned_secret": re.compile(r"""(?i)\b(?:api[_-]?key|secret|token|passwd|password|passcode)\b\s*[:=]\s*["']([^"']{8,})["']"""),
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache"}
TEXT_EXT = (".py", ".json", ".md", ".txt", ".yml", ".yaml", ".html", ".toml", ".ini", ".cfg", ".env", ".csv", ".sh")


def load_allowlist(path=os.path.join(OPS_DIR, "secrets-allowlist.json")): return load_json(path) if os.path.exists(path) else {"entries": []}


def scan_tree(root=LAB_ROOT, allowlist=None):
    """Scan text files under `root`. Returns (findings, allowed). A finding is allowed only by an explicit allowlist entry {path_suffix, rule, contains, reason}."""
    al = (allowlist or load_allowlist())["entries"]; findings, allowed = [], []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            p = os.path.join(d, f)
            if not f.endswith(TEXT_EXT) or os.path.getsize(p) > 2_000_000: continue
            try: text = open(p, encoding="utf-8", errors="ignore").read()
            except OSError: continue
            rel = os.path.relpath(p, root)
            for rule, rx in PATTERNS.items():
                for m in rx.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1; item = dict(path=rel, line=line, rule=rule, excerpt=m.group(0)[:6] + "***")
                    ok = next((e for e in al if rel.endswith(e["path_suffix"]) and e["rule"] == rule and e["contains"] in text[max(0, m.start() - 80): m.end() + 80]), None)
                    (allowed if ok else findings).append(dict(item, reason=ok["reason"]) if ok else item)
    return findings, allowed


def config_boundary_report():
    """Static facts about where secrets may live: the Authority secret is process-local random bytes (never written), passcodes are dev fixtures, and trace redaction hides secret-named keys."""
    from .. import identity as ID, tools as T
    a = ID.Authority.dev(); red = T.redact({"api_key": "x" * 12, "nested": {"password": "hunter2hunter2", "ok": 1}, "list": [{"token": "t" * 9}]})
    return dict(authority_secret_is_random_bytes=isinstance(a.secret, bytes) and len(a.secret) == 32, authority_secret_in_repr="secret" not in repr(a.reviewers),
                redaction_hides_secret_keys=json.dumps(red).count("[REDACTED]") == 3, dev_passcodes_are_fixtures=sorted(ID.DEV_PASSCODES), env_config_keys=["NASHA_LLM_MODEL", "NASHA_LLM_ENDPOINT", "NASHA_CORPUS_VERSION", "NASHA_GATE"])


# ======================================================================================================= GAP-08
class MigrationError(Exception): pass


class Migrator:
    """Forward-only versioned migrations for a SQLite store with transactional apply, automatic rollback on failure and a pre-migration backup.
    `migrations`: list of (version:int, name:str, fn(con)). Version is stored in PRAGMA user_version."""
    def __init__(self, con, migrations):
        self.con, self.migrations = con, sorted(migrations, key=lambda m: m[0]); self.con.isolation_level = None

    def version(self): return self.con.execute("PRAGMA user_version").fetchone()[0]

    def backup(self):
        b = sqlite3.connect(":memory:"); self.con.backup(b); return b

    def restore(self, b): b.backup(self.con)

    def migrate(self, target=None):
        applied = []
        for v, name, fn in self.migrations:
            if v <= self.version() or (target is not None and v > target): continue
            self.con.execute("BEGIN")
            try:
                fn(self.con); self.con.execute(f"PRAGMA user_version={int(v)}"); self.con.execute("COMMIT"); applied.append(v)
            except Exception as e:
                self.con.execute("ROLLBACK")
                raise MigrationError(f"migration {v} ({name}) failed and was rolled back; store remains at version {self.version()}: {type(e).__name__}: {e}") from e
        return applied


def _m1(con): con.execute("CREATE TABLE ops_runs(run_id TEXT PRIMARY KEY, record_json TEXT NOT NULL)")
def _m2(con):
    con.execute("ALTER TABLE ops_runs ADD COLUMN outcome_category TEXT"); con.execute("ALTER TABLE ops_runs ADD COLUMN run_ms REAL")
    for rid, js in con.execute("SELECT run_id, record_json FROM ops_runs").fetchall():
        r = json.loads(js); con.execute("UPDATE ops_runs SET outcome_category=?, run_ms=? WHERE run_id=?", (r.get("outcome_category"), r["timing"]["run_ms"], rid))
def _m3(con): con.execute("CREATE INDEX ix_ops_runs_outcome ON ops_runs(outcome_category)")
MIGRATIONS = [(1, "create ops_runs", _m1), (2, "add outcome_category and run_ms with backfill", _m2), (3, "index outcome_category", _m3)]
