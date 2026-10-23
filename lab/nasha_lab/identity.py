"""Minimal LOCAL reviewer identity and signed approval grants (prototype; NOT enterprise authentication, no external provider).

Session token : HMAC-signed {sub, role, iat, exp}. Obtained with a reviewer id + passcode that exist in the local reviewer table.
Grant         : HMAC-signed {sub, role, run_id, actions:[{tool, args_hash}], nonce, iat, exp}, minted only when an authorised reviewer approves a
                specific proposal. Execution verifies signature, expiry, run id, tool, the SHA-256 of the exact arguments, role permission and that the
                nonce has not been used. Approving cannot be replayed, retargeted to other arguments, or reused in another run.
Limits        : one process-local secret; no revocation list beyond nonce consumption; passcodes are dev fixtures; no rate limiting; not for production."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

ROLES = ("BUYER", "QUALITY_LEAD", "FOUNDER")
# which roles may approve which simulated mutation (tool, target-table or None)
ROLE_POLICY = {
    ("release_draft", None): {"BUYER", "FOUNDER"},
    ("create_draft_purchase_order", None): {"BUYER", "FOUNDER"},          # D-89: a draft PO from the governed procurement workflow
    ("apply_lead_qualification", None): {"OWNER"},                         # D-90: Growth OS lead qualification (a different person from the requester approves)
    ("adjust_inventory_record", None): {"BUYER", "QUALITY_LEAD", "FOUNDER"},
    ("flag_record_for_review", "inventory_counts"): {"QUALITY_LEAD", "BUYER", "FOUNDER"},
    ("flag_record_for_review", "orders"): {"QUALITY_LEAD", "FOUNDER"},
    ("flag_record_for_review", "order_lines"): {"QUALITY_LEAD", "FOUNDER"},
    ("flag_record_for_review", "supplier_proposals"): {"FOUNDER"},      # dietary-policy decisions belong to the founder (D-54)
}
DEV_PASSCODES = {"alice": ("BUYER", "alice-dev-passcode"), "bob": ("QUALITY_LEAD", "bob-dev-passcode"), "founder": ("FOUNDER", "founder-dev-passcode")}


class AuthError(Exception):
    def __init__(self, code, message=""):
        super().__init__(f"{code}: {message}" if message else code); self.code, self.message = code, message


@dataclass(frozen=True)
class Identity:
    id: str; role: str


def _b64(b): return base64.urlsafe_b64encode(b).decode().rstrip("=")
def _unb64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Authority:
    def __init__(self, reviewers, secret=None, session_ttl=900, grant_ttl=900, clock=time.time, autologin=None):
        """reviewers: {id: (role, salted_hash_hex, salt)}; autologin: a reviewer id used when no session is supplied (tests/eval only)."""
        self.reviewers, self.secret, self.session_ttl, self.grant_ttl, self.clock, self.autologin = reviewers, secret or secrets.token_bytes(32), session_ttl, grant_ttl, clock, autologin
        self.used = set()

    @staticmethod
    def _hash(passcode, salt): return hashlib.sha256((salt + passcode).encode()).hexdigest()

    @classmethod
    def dev(cls, autologin=None, **kw):
        rv = {}
        for rid, (role, pc) in DEV_PASSCODES.items():
            salt = secrets.token_hex(8); rv[rid] = (role, cls._hash(pc, salt), salt)
        return cls(rv, autologin=autologin, **kw)

    def _sign(self, payload):
        body = _b64(json.dumps(payload, sort_keys=True).encode()); sig = _b64(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{sig}"

    def _open(self, token, kind):
        try:
            body, sig = token.split(".")
            if not hmac.compare_digest(sig, _b64(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())): raise AuthError("BAD_SIGNATURE")
            p = json.loads(_unb64(body))
        except AuthError: raise
        except Exception: raise AuthError("MALFORMED_TOKEN")
        if p.get("kind") != kind: raise AuthError("WRONG_TOKEN_KIND")
        if p["exp"] < self.clock(): raise AuthError("EXPIRED")
        return p

    def login(self, reviewer_id, passcode):
        r = self.reviewers.get(reviewer_id)
        if not r or not hmac.compare_digest(r[1], self._hash(passcode, r[2])): raise AuthError("BAD_CREDENTIALS")
        now = self.clock(); return self._sign(dict(kind="session", sub=reviewer_id, role=r[0], iat=now, exp=now + self.session_ttl))

    def identify(self, session):
        if session is None:
            if self.autologin: r = self.reviewers[self.autologin]; return Identity(self.autologin, r[0])
            raise AuthError("AUTH_REQUIRED")
        p = self._open(session, "session")
        r = self.reviewers.get(p["sub"])
        if not r or r[0] != p["role"]: raise AuthError("UNKNOWN_REVIEWER")
        return Identity(p["sub"], p["role"])

    def dev_session(self, reviewer_id):
        r = self.reviewers[reviewer_id]; now = self.clock(); return self._sign(dict(kind="session", sub=reviewer_id, role=r[0], iat=now, exp=now + self.session_ttl))

    @staticmethod
    def role_allowed(role, tool, args):
        table = args.get("table") if tool == "flag_record_for_review" else None
        return role in ROLE_POLICY.get((tool, table), set())

    def issue_grant(self, identity, run_id, actions):
        """actions: [{tool, args, args_hash}] taken from the proposal the reviewer is looking at. Raises if the role may not approve any of them."""
        for a in actions:
            if not self.role_allowed(identity.role, a["tool"], a["args"]):
                raise AuthError("ROLE_NOT_PERMITTED", f"{identity.role} may not approve {a['tool']} {a['args'].get('table', '')}".strip())
        now = self.clock()
        return self._sign(dict(kind="grant", sub=identity.id, role=identity.role, run_id=run_id, actions=[[a["tool"], a["args_hash"]] for a in actions], nonce=secrets.token_hex(8), iat=now, exp=now + self.grant_ttl))

    def verify_grant(self, grant, run_id, tool, args, args_hash, consume=True):
        """Return (ok, reason, identity)."""
        if not grant: return False, "NO_GRANT", None
        try: p = self._open(grant, "grant")
        except AuthError as e: return False, e.code, None
        if p["run_id"] != run_id: return False, "WRONG_RUN", None
        if [tool, args_hash] not in p["actions"]: return False, "ARGUMENTS_OR_TOOL_NOT_APPROVED", None
        if not self.role_allowed(p["role"], tool, args): return False, "ROLE_NOT_PERMITTED", None
        key = (p["nonce"], tool, args_hash)
        if key in self.used: return False, "REPLAYED", None
        if consume: self.used.add(key)
        return True, "", Identity(p["sub"], p["role"])
