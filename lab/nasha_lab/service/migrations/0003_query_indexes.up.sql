-- 0003: indexes for the owner/recency listings and the open dead-letter queue.
CREATE INDEX ix_runs_owner_created ON runs (owner, created_at DESC);
CREATE INDEX ix_runs_created ON runs (created_at DESC);
CREATE INDEX ix_dead_letters_open ON dead_letters (created_at) WHERE status = 'OPEN';
CREATE INDEX ix_idempotency_expires ON idempotency_keys (expires_at);
CREATE INDEX ix_audit_at ON audit_log (at DESC);
