-- 0001_core: run state, approvals, audit log, idempotency keys, dead letters. SYNTHETIC DATA / NOT PRODUCTION DEPLOYED.
CREATE TABLE runs (
    run_id         text PRIMARY KEY,
    event_id       text NOT NULL,
    owner          text NOT NULL,
    status         text NOT NULL,
    awaiting_human boolean NOT NULL DEFAULT false,
    request_id     text NOT NULL,
    summary        jsonb NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);
-- one live run per event, matching the agent's own de-duplication by event id
CREATE UNIQUE INDEX ux_runs_live_event ON runs (event_id) WHERE status NOT IN ('FAILED', 'DUPLICATE_IGNORED');

CREATE TABLE approvals (
    approval_id   bigserial PRIMARY KEY,
    run_id        text NOT NULL REFERENCES runs (run_id),
    decision      text NOT NULL CHECK (decision IN ('approve', 'reject', 'edit', 'request_more_evidence')),
    reviewer      text NOT NULL,
    role          text NOT NULL,
    note          text NOT NULL DEFAULT '',
    result_status text NOT NULL,
    request_id    text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    audit_id       bigserial PRIMARY KEY,
    at             timestamptz NOT NULL DEFAULT now(),
    request_id     text NOT NULL,
    principal_hash text NOT NULL,
    action         text NOT NULL,
    resource       text NOT NULL,
    outcome        text NOT NULL,
    detail         jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE idempotency_keys (
    principal       text NOT NULL,
    key             text NOT NULL,
    route           text NOT NULL,
    request_hash    text NOT NULL,
    response_status integer NOT NULL,
    response_body   jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    PRIMARY KEY (principal, key)
);

CREATE TABLE dead_letters (
    dl_id               text PRIMARY KEY,
    created_at          timestamptz NOT NULL DEFAULT now(),
    correlation_id      text NOT NULL,
    run_id              text NOT NULL DEFAULT '',
    operation           text NOT NULL,
    tool                text,
    op_class            text NOT NULL,
    failure_code        text,
    failure_class       text NOT NULL,
    attempts            integer NOT NULL,
    reason              text NOT NULL,
    args_hash           text NOT NULL,
    args_json           jsonb NOT NULL DEFAULT '{}'::jsonb,
    status              text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ALREADY_APPLIED', 'REPLAYED', 'DISCARDED')),
    replay_instructions text NOT NULL,
    resolution          text,
    resolved_by         text
);
