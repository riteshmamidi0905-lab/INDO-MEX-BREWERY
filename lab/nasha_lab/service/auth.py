"""Authentication (signed bearer tokens) and authorization (role -> permission, deny by default).

Tokens are JWTs (PyJWT, HS256) with header `kid`. Verification pins the algorithm list to HS256 (no `none`, no alg confusion), requires exp/iat/sub/iss/aud/jti,
rejects unknown key ids, unknown roles and tokens whose lifetime exceeds the configured maximum. Key rotation: add a new kid, switch jwt_active_kid, wait for
old tokens to expire (<= token_max_ttl_s), then remove the old kid. Issuing is for the dev/test issuer and the CLI only; the service never mints tokens in staging."""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from typing import Mapping, Optional

import jwt

from .errors import ApiError

ALG = "HS256"
SUB_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,64}$")
# roles: the three REVIEWER roles are the lab's own (identity.ROLES); READER, OPERATOR and AUDITOR cannot decide approvals.
REVIEWER_ROLES = ("BUYER", "QUALITY_LEAD", "FOUNDER")
ROLES = REVIEWER_ROLES + ("READER", "OPERATOR", "AUDITOR")
PERMISSIONS: dict[str, frozenset[str]] = {
    "BUYER": frozenset({"tools:read", "runs:create", "runs:read_own", "runs:read_all", "runs:decide"}),
    "QUALITY_LEAD": frozenset({"tools:read", "runs:create", "runs:read_own", "runs:read_all", "runs:decide"}),
    "FOUNDER": frozenset({"tools:read", "runs:create", "runs:read_own", "runs:read_all", "runs:decide"}),
    "READER": frozenset({"tools:read", "runs:read_own"}),
    "OPERATOR": frozenset({"tools:read", "runs:read_own", "runs:read_all", "metrics:read", "deadletters:read", "deadletters:resolve", "audit:read"}),
    "AUDITOR": frozenset({"runs:read_own", "runs:read_all", "audit:read"}),
}
ALL_PERMISSIONS = frozenset().union(*PERMISSIONS.values())


@dataclass(frozen=True)
class Principal:
    sub: str
    role: str
    kid: str
    jti: str

    def can(self, permission: str) -> bool: return permission in PERMISSIONS.get(self.role, frozenset())


class TokenService:
    def __init__(self, keys: Mapping[str, str], active_kid: str, issuer: str, audience: str, *, leeway_s: int = 5, max_ttl_s: int = 3600) -> None:
        if active_kid not in keys: raise ValueError("active kid is not in the key ring")
        self._keys, self.active_kid, self.issuer, self.audience, self.leeway, self.max_ttl = dict(keys), active_kid, issuer, audience, leeway_s, max_ttl_s

    def issue(self, sub: str, role: str, ttl_s: int = 900, *, kid: Optional[str] = None, now: Optional[float] = None) -> str:
        if role not in ROLES: raise ValueError(f"unknown role {role!r}")
        if not SUB_RE.match(sub): raise ValueError("invalid subject")
        t = int(time.time() if now is None else now)
        k = kid or self.active_kid
        claims = {"iss": self.issuer, "aud": self.audience, "sub": sub, "role": role, "iat": t, "exp": t + int(ttl_s), "jti": uuid.uuid4().hex}
        return jwt.encode(claims, self._keys[k], algorithm=ALG, headers={"kid": k})

    def verify(self, token: str) -> Principal:
        try:
            hdr = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise ApiError("AUTH_INVALID_TOKEN", "invalid bearer token") from None
        kid = hdr.get("kid")
        if hdr.get("alg") != ALG or not isinstance(kid, str) or kid not in self._keys:
            raise ApiError("AUTH_INVALID_TOKEN", "invalid bearer token")
        try:
            c = jwt.decode(token, self._keys[kid], algorithms=[ALG], audience=self.audience, issuer=self.issuer, leeway=self.leeway,
                           options={"require": ["exp", "iat", "sub", "iss", "aud", "jti"]})
        except jwt.ExpiredSignatureError:
            raise ApiError("AUTH_TOKEN_EXPIRED", "token expired") from None
        except jwt.PyJWTError:
            raise ApiError("AUTH_INVALID_TOKEN", "invalid bearer token") from None
        sub, role = c.get("sub"), c.get("role")
        if not isinstance(sub, str) or not SUB_RE.match(sub) or role not in ROLES: raise ApiError("AUTH_INVALID_TOKEN", "invalid bearer token")
        if not isinstance(c["exp"], (int, float)) or not isinstance(c["iat"], (int, float)) or c["exp"] - c["iat"] > self.max_ttl:
            raise ApiError("AUTH_INVALID_TOKEN", "invalid bearer token")
        return Principal(sub, role, kid, str(c["jti"]))


def parse_bearer(header: Optional[str]) -> str:
    if not header: raise ApiError("AUTH_REQUIRED", "authentication required")
    parts = header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]: raise ApiError("AUTH_INVALID_TOKEN", "invalid bearer token")
    return parts[1]
