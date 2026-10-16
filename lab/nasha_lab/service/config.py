"""Typed, validated, env-driven configuration (Pydantic v2). Fails fast with a clear error that never echoes secret values.

Secrets come ONLY from the environment or from files named by NASHA_SVC_<NAME>_FILE (for mounted secrets). SecretStr keeps them out of repr/str/model_dump_json.
Unknown NASHA_SVC_* variables are rejected (a typo in a security setting must not be silently ignored)."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Literal, Mapping, Optional

from psycopg.conninfo import conninfo_to_dict
from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "NASHA_SVC_"
KID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
PLACEHOLDER_RE = re.compile(r"(?i)(change.?me|placeholder|example|password|secret|default|todo|xxxx)")
MIN_KEY_LEN = 32
SECRET_FIELDS = ("database_url", "jwt_keys", "log_salt")


class ConfigError(Exception):
    """Raised at start-up for invalid configuration. The message lists setting names and reasons, never values."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True, extra="forbid")

    @classmethod
    def settings_customise_sources(cls, settings_cls: Any, init_settings: Any, env_settings: Any, dotenv_settings: Any, file_secret_settings: Any) -> tuple[Any, ...]:
        return (init_settings,)        # constructor values only; load_settings() is the single, audited reader of the environment

    env: Literal["dev", "test", "staging"] = "dev"
    # --- database (PostgreSQL via psycopg 3 pool)
    database_url: SecretStr
    db_pool_min: int = Field(1, ge=0, le=50)
    db_pool_max: int = Field(10, ge=1, le=100)
    db_pool_timeout_s: float = Field(2.0, gt=0, le=30)
    db_connect_timeout_s: int = Field(3, ge=1, le=30)
    db_statement_timeout_ms: int = Field(3000, ge=50, le=60000)
    db_lock_timeout_ms: int = Field(2000, ge=50, le=60000)
    db_breaker_threshold: int = Field(3, ge=1, le=100)
    db_breaker_reset_s: float = Field(5.0, gt=0, le=300)
    require_db_at_start: bool = False          # False: start degraded (liveness ok, readiness 503); True: refuse to start
    allow_newer_schema: bool = False           # False: a database migrated beyond this build is NOT ready (rollback-safe default)
    # --- authentication
    jwt_keys: dict[str, SecretStr]             # {kid: secret}; several kids allow rotation
    jwt_active_kid: str
    jwt_issuer: str = "nasha-lab-dev"
    jwt_audience: str = "nasha-lab-api"
    jwt_leeway_s: int = Field(5, ge=0, le=60)
    token_max_ttl_s: int = Field(3600, ge=60, le=86400)
    dev_token_issuer: bool = False             # only honoured when env is dev/test
    # --- rate limiting (token buckets; in-memory, per process)
    rate_ip_capacity: float = Field(60, gt=0)
    rate_ip_refill_per_s: float = Field(30, gt=0)
    rate_principal_capacity: float = Field(30, gt=0)
    rate_principal_refill_per_s: float = Field(10, gt=0)
    rate_table_max: int = Field(10000, ge=100)
    trusted_proxy_hops: int = Field(0, ge=0, le=5)
    # --- request limits and deadlines
    max_body_bytes: int = Field(16384, ge=256, le=1_048_576)
    default_deadline_s: float = Field(5.0, gt=0, le=60)
    run_deadline_s: float = Field(15.0, gt=0, le=120)
    tool_timeout_s: float = Field(2.0, gt=0, le=30)
    worker_threads: int = Field(16, ge=1, le=256)
    shutdown_grace_s: float = Field(10.0, ge=0, le=120)
    idempotency_ttl_s: int = Field(86400, ge=60)
    # --- exposure
    cors_origins: list[str] = Field(default_factory=list)
    docs_enabled: bool = False
    metrics_enabled: bool = True
    # --- misc
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_salt: Optional[SecretStr] = None       # keys the principal-id hash in logs; random per process when unset
    data_dir: str = "/tmp/nasha_lab"
    world_seed: int = 1

    @field_validator("jwt_keys")
    @classmethod
    def _keys(cls, v: dict[str, SecretStr]) -> dict[str, SecretStr]:
        if not v: raise ValueError("at least one signing key is required")
        for kid, s in v.items():
            if not KID_RE.match(kid): raise ValueError(f"key id {kid!r} must match {KID_RE.pattern}")
            raw = s.get_secret_value()
            if len(raw) < MIN_KEY_LEN: raise ValueError(f"key {kid!r} is shorter than {MIN_KEY_LEN} characters")
            if PLACEHOLDER_RE.search(raw): raise ValueError(f"key {kid!r} looks like a placeholder; generate a random key")
        return v

    @field_validator("database_url")
    @classmethod
    def _dsn(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        try:
            if not (re.match(r"^postgres(ql)?://", raw) or "=" in raw): raise ValueError("x")
            conninfo_to_dict(raw)
        except Exception:
            raise ValueError("must be a PostgreSQL URL (postgresql://...) or libpq conninfo string") from None
        return v

    @field_validator("cors_origins")
    @classmethod
    def _cors(cls, v: list[str]) -> list[str]:
        for o in v:
            if o.strip() == "*" or not re.match(r"^https?://[A-Za-z0-9.-]+(:\d+)?$", o): raise ValueError(f"origin {o!r} must be an explicit http(s)://host[:port]; wildcards are refused")
        return v

    @model_validator(mode="after")
    def _cross(self) -> "Settings":
        if self.jwt_active_kid not in self.jwt_keys: raise ValueError("jwt_active_kid is not one of the configured jwt_keys")
        if self.db_pool_min > self.db_pool_max: raise ValueError("db_pool_min must be <= db_pool_max")
        if self.dev_token_issuer and self.env not in ("dev", "test"): raise ValueError("dev_token_issuer is only allowed when env is dev or test")
        if self.env == "staging" and self.docs_enabled: raise ValueError("docs_enabled must be false when env is staging")
        if self.tool_timeout_s >= self.run_deadline_s: raise ValueError("tool_timeout_s must be below run_deadline_s")
        return self

    # ---- safe views
    def safe_dict(self) -> dict[str, Any]:
        """Settings with every secret replaced by a marker. Safe to log or print."""
        d = json.loads(self.model_dump_json())
        for k in SECRET_FIELDS:
            if k == "jwt_keys": d[k] = {kid: "***" for kid in self.jwt_keys}
            elif d.get(k) is not None: d[k] = "***"
        return d

    def signing_keys(self) -> dict[str, str]:
        return {k: v.get_secret_value() for k, v in self.jwt_keys.items()}


def _read_file(path: str, name: str) -> str:
    try:
        with open(path, encoding="utf-8") as f: return f.read().strip()
    except OSError as e:
        raise ConfigError(f"{ENV_PREFIX}{name.upper()}_FILE: cannot read the secret file ({type(e).__name__})") from None


def load_settings(environ: Optional[Mapping[str, str]] = None, **overrides: Any) -> Settings:
    """Build Settings from the environment (or `environ`). Raises ConfigError (value-free message) on any problem.
    This is the only place environment variables are read: Settings itself takes constructor values only."""
    env = dict(os.environ if environ is None else environ)
    fields = Settings.model_fields
    errors: list[str] = []
    init: dict[str, Any] = {}
    for k, raw in env.items():
        if not k.upper().startswith(ENV_PREFIX): continue
        base = k[len(ENV_PREFIX):].lower()
        if base.endswith("_file") and base[:-5] in SECRET_FIELDS:
            name = base[:-5]
            if f"{ENV_PREFIX}{name.upper()}" not in {x.upper() for x in env}:
                text = _read_file(raw, name)
                if name == "jwt_keys":
                    try: init[name] = json.loads(text)
                    except ValueError: errors.append(f"{k}: file content must be valid JSON (value not shown)")
                else: init[name] = text
            continue
        if base not in fields: errors.append(f"{k}: unknown setting"); continue
        if base in ("jwt_keys", "cors_origins"):
            try: init[base] = json.loads(raw)
            except ValueError: errors.append(f"{k}: must be valid JSON (value not shown)")
        else:
            init[base] = raw
    if errors: raise ConfigError("invalid configuration: " + "; ".join(sorted(errors)))
    init.update(overrides)
    try:
        return Settings(**init)
    except ValidationError as e:
        raise ConfigError("invalid configuration: " + "; ".join(f"{ENV_PREFIX}{'.'.join(str(x) for x in err['loc']).upper() or 'SETTINGS'}: {_msg(err)}" for err in e.errors())) from None


def _msg(err: Mapping[str, Any]) -> str:
    """The validation message without the offending input (which may be a secret)."""
    t = err.get("type", "")
    if t == "missing": return "required setting is missing"
    m = str(err.get("msg", "invalid"))
    return m.replace("Value error, ", "")[:200]
