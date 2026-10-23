"""PostgreSQL schema for NASHA Growth OS, as ordered, checksummed migrations applied by the existing safe migration runner (`warehouse/pg_hardening.migrate`).
Design rules (each is enforced by the database, and each has a test):
  * every business table carries tenant_id and PRIMARY KEY (tenant_id, id); every foreign key is (tenant_id, x_id), so a row can never reference another tenant's row;
  * row-level security is ENABLED and FORCED on every business table, default-deny: with no `app.tenant_id` setting a session sees nothing; the application role has no BYPASSRLS;
  * contacts must use the reserved example.invalid domain (synthetic data only); campaigns, content and offers have no 'sent' / 'published' / 'running' state at all;
  * stage changes follow a global rules table enforced by a trigger, whatever SQL tries it; every update bumps `version` and snapshots the row into entity_versions;
  * audit_log, stage_transitions and entity_versions are append-only by privilege (no UPDATE/DELETE grant), and audit rows are hash-chained per tenant."""

APP_ROLE = "growth_app"
TENANT_TABLES = ["tenants", "users", "segments", "accounts", "contacts", "suppression_list", "leads", "opportunities", "stage_transitions", "activities", "products", "prices", "offers", "campaigns", "content_items",
                 "audit_log", "entity_versions"]
APPEND_ONLY = ["audit_log", "stage_transitions", "entity_versions"]
WORKFLOW_TABLES = ["workflow_runs", "workflow_events"]          # created by migration 105 (which carries its own RLS and grants)
VERSIONED = ["segments", "accounts", "contacts", "leads", "opportunities", "products", "prices", "offers", "campaigns", "content_items"]
ALL_TENANT_TABLES = TENANT_TABLES + WORKFLOW_TABLES
STAGES = ["new", "qualified", "proposal", "negotiation", "won", "lost"]
STAGE_RULES = [("new", "qualified"), ("new", "lost"), ("qualified", "proposal"), ("qualified", "lost"), ("proposal", "negotiation"), ("proposal", "lost"), ("negotiation", "won"), ("negotiation", "lost"), ("negotiation", "proposal")]
ROLES = ["OWNER", "SALES", "MARKETING", "ANALYST", "VIEWER"]

_COMMON = "tenant_id text NOT NULL, id text NOT NULL, version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), created_by text"


def _fk(col, ref):
    return f"FOREIGN KEY (tenant_id, {col}) REFERENCES {ref} (tenant_id, id)"


V001 = [
    f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN CREATE ROLE {APP_ROLE} LOGIN NOBYPASSRLS; END IF; END $$",
    "CREATE TABLE tenants (tenant_id text PRIMARY KEY, name text NOT NULL, vertical text NOT NULL, synthetic boolean NOT NULL DEFAULT true CHECK (synthetic), settings jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now())",
    f"CREATE TABLE users ({_COMMON}, display_name text NOT NULL, role text NOT NULL CHECK (role IN ({', '.join(repr(r) for r in ROLES)})), PRIMARY KEY (tenant_id, id), FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id))",
    f"CREATE TABLE segments ({_COMMON}, name text NOT NULL, kind text NOT NULL CHECK (kind IN ('icp','behavioral')), criteria jsonb NOT NULL DEFAULT '{{}}', "
    "evidence_basis text NOT NULL CHECK (evidence_basis IN ('synthetic_assumption','synthetic_data_derived','researched_public')), confidence numeric NOT NULL CHECK (confidence BETWEEN 0 AND 1), est_value_cents bigint CHECK (est_value_cents >= 0), "
    "PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, name), FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id))",
    f"CREATE TABLE accounts ({_COMMON}, name text NOT NULL, kind text NOT NULL CHECK (kind IN ('business','household')), segment_id text, PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, name), {_fk('segment_id', 'segments')})",
    f"CREATE TABLE contacts ({_COMMON}, account_id text NOT NULL, full_name text NOT NULL, email text NOT NULL CHECK (email LIKE '%@example.invalid'), "
    f"consent_status text NOT NULL DEFAULT 'none' CHECK (consent_status IN ('none','opt_in','opt_out')), PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, email), {_fk('account_id', 'accounts')})",
    "CREATE TABLE suppression_list (tenant_id text NOT NULL, email text NOT NULL CHECK (email LIKE '%@example.invalid'), reason text NOT NULL, added_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, email), FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id))",
    f"CREATE TABLE leads ({_COMMON}, contact_id text NOT NULL, source text NOT NULL, status text NOT NULL DEFAULT 'new' CHECK (status IN ('new','qualified','disqualified','converted')), score integer CHECK (score BETWEEN 0 AND 100), "
    f"PRIMARY KEY (tenant_id, id), {_fk('contact_id', 'contacts')})",
    f"CREATE TABLE opportunities ({_COMMON}, account_id text NOT NULL, lead_id text, name text NOT NULL, stage text NOT NULL DEFAULT 'new' CHECK (stage IN ({', '.join(repr(s) for s in STAGES)})), "
    f"amount_cents bigint NOT NULL CHECK (amount_cents >= 0), expected_close date, closed_at timestamptz, PRIMARY KEY (tenant_id, id), {_fk('account_id', 'accounts')}, {_fk('lead_id', 'leads')})",
    f"CREATE TABLE stage_transitions ({_COMMON}, opportunity_id text NOT NULL, from_stage text NOT NULL, to_stage text NOT NULL, actor text NOT NULL, PRIMARY KEY (tenant_id, id), {_fk('opportunity_id', 'opportunities')})",
    f"CREATE TABLE activities ({_COMMON}, opportunity_id text, contact_id text, kind text NOT NULL CHECK (kind IN ('note','call_log','meeting','email_draft')), body text NOT NULL, actor text NOT NULL, "
    f"PRIMARY KEY (tenant_id, id), {_fk('opportunity_id', 'opportunities')}, {_fk('contact_id', 'contacts')})",
    f"CREATE TABLE products ({_COMMON}, name text NOT NULL, kind text NOT NULL, unit_cost_cents bigint CHECK (unit_cost_cents >= 0), cost_basis text NOT NULL DEFAULT 'synthetic_assumption', PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, name))",
    f"CREATE TABLE prices ({_COMMON}, product_id text NOT NULL, amount_cents bigint NOT NULL CHECK (amount_cents > 0), valid_from date NOT NULL, status text NOT NULL CHECK (status IN ('current','scenario','draft')), basis text NOT NULL, "
    f"PRIMARY KEY (tenant_id, id), {_fk('product_id', 'products')})",
    f"CREATE TABLE offers ({_COMMON}, name text NOT NULL, product_id text NOT NULL, discount_pct numeric NOT NULL CHECK (discount_pct BETWEEN 0 AND 100), starts date NOT NULL, ends date NOT NULL, "
    f"status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved','expired')), CHECK (ends >= starts), PRIMARY KEY (tenant_id, id), {_fk('product_id', 'products')})",
    f"CREATE TABLE campaigns ({_COMMON}, name text NOT NULL, offer_id text, segment_id text, status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','in_review','approved','archived')), "
    f"PRIMARY KEY (tenant_id, id), {_fk('offer_id', 'offers')}, {_fk('segment_id', 'segments')})",
    f"CREATE TABLE content_items ({_COMMON}, campaign_id text NOT NULL, kind text NOT NULL CHECK (kind IN ('social','landing_copy','email_draft','ad_concept','brief')), body text NOT NULL, "
    f"status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','in_review','approved','rejected')), claims_checked boolean NOT NULL DEFAULT false, PRIMARY KEY (tenant_id, id), {_fk('campaign_id', 'campaigns')})",
    "CREATE TABLE audit_log (tenant_id text NOT NULL, seq bigint NOT NULL, ts timestamptz NOT NULL DEFAULT now(), actor text NOT NULL, role text NOT NULL, action text NOT NULL, entity text, entity_id text, "
    "decision text NOT NULL CHECK (decision IN ('allow','deny')), detail jsonb NOT NULL DEFAULT '{}', prev_hash text NOT NULL, hash text NOT NULL, PRIMARY KEY (tenant_id, seq), FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id))",
    "CREATE TABLE entity_versions (tenant_id text NOT NULL, entity text NOT NULL, entity_id text NOT NULL, version integer NOT NULL, snapshot jsonb NOT NULL, changed_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, entity, entity_id, version))",
]
V002 = [  # global reference data + enforcement triggers
    "CREATE TABLE stage_rules (from_stage text NOT NULL, to_stage text NOT NULL, PRIMARY KEY (from_stage, to_stage))",
    "INSERT INTO stage_rules VALUES " + ", ".join(f"('{a}','{b}')" for a, b in STAGE_RULES),
    "CREATE FUNCTION enforce_stage_rules() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN IF NEW.stage IS DISTINCT FROM OLD.stage THEN IF NOT EXISTS (SELECT 1 FROM stage_rules WHERE from_stage = OLD.stage AND to_stage = NEW.stage) "
    "THEN RAISE EXCEPTION 'illegal stage transition % -> %', OLD.stage, NEW.stage USING ERRCODE = 'check_violation'; END IF; IF NEW.stage IN ('won','lost') THEN NEW.closed_at := now(); END IF; END IF; RETURN NEW; END $f$",
    "CREATE TRIGGER opp_stage_rules BEFORE UPDATE OF stage ON opportunities FOR EACH ROW EXECUTE FUNCTION enforce_stage_rules()",
    "CREATE FUNCTION no_reopen() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN IF OLD.stage IN ('won','lost') THEN RAISE EXCEPTION 'closed opportunity cannot change' USING ERRCODE = 'check_violation'; END IF; RETURN NEW; END $f$",
    "CREATE TRIGGER opp_closed_is_final BEFORE UPDATE ON opportunities FOR EACH ROW EXECUTE FUNCTION no_reopen()",
    "CREATE FUNCTION bump_version() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN NEW.version := OLD.version + 1; NEW.updated_at := now(); RETURN NEW; END $f$",
    "CREATE FUNCTION snapshot_version() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN INSERT INTO entity_versions (tenant_id, entity, entity_id, version, snapshot) VALUES (NEW.tenant_id, TG_TABLE_NAME, NEW.id, NEW.version, to_jsonb(NEW)); RETURN NEW; END $f$",
] + [s for t in VERSIONED for s in (f"CREATE TRIGGER {t}_bump BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION bump_version()",
                                     f"CREATE TRIGGER {t}_snap AFTER INSERT OR UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION snapshot_version()")]
V003 = (  # tenant isolation (RLS, default deny) and least-privilege grants
    [s for t in TENANT_TABLES for s in (f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY", f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY",
                                        f"CREATE POLICY tenant_isolation ON {t} USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))")]
    + [f"GRANT USAGE ON SCHEMA {{schema}} TO {APP_ROLE}", f"GRANT SELECT ON stage_rules TO {APP_ROLE}"]
    + [f"GRANT SELECT, INSERT ON {t} TO {APP_ROLE}" for t in APPEND_ONLY]
    + [f"GRANT SELECT, INSERT, UPDATE ON {t} TO {APP_ROLE}" for t in TENANT_TABLES if t not in APPEND_ONLY + ["tenants"]]
    + [f"GRANT SELECT ON tenants TO {APP_ROLE}", f"GRANT DELETE ON suppression_list TO {APP_ROLE}"])
V004 = [  # indexes for the hot read paths (all lead with tenant_id, the RLS predicate)
    "CREATE INDEX ix_contacts_account ON contacts (tenant_id, account_id)", "CREATE INDEX ix_leads_status ON leads (tenant_id, status)", "CREATE INDEX ix_opps_stage ON opportunities (tenant_id, stage)",
    "CREATE INDEX ix_opps_account ON opportunities (tenant_id, account_id)", "CREATE INDEX ix_activities_opp ON activities (tenant_id, opportunity_id)", "CREATE INDEX ix_prices_product ON prices (tenant_id, product_id, status)",
    "CREATE INDEX ix_audit_entity ON audit_log (tenant_id, entity, entity_id)"]


V005 = [  # D-90 Phase B: lead evidence, governed workflow state and its append-only trace (RLS, grants and indexes included: this migration is self-contained)
    "ALTER TABLE leads ADD COLUMN signals jsonb, ADD COLUMN qualified_by_run text, ADD CONSTRAINT leads_source_synthetic CHECK (source LIKE 'synthetic%')",
    f"CREATE TABLE workflow_runs (tenant_id text NOT NULL, id text NOT NULL, version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), "
    "workflow text NOT NULL, requester text NOT NULL, role text NOT NULL, lead_id text NOT NULL, idem_key text, "
    "state text NOT NULL CHECK (state IN ('STARTED','EVIDENCE_COLLECTED','PROPOSED','AWAITING_APPROVAL','APPROVED','EXECUTED','REJECTED','ABSTAINED','BLOCKED','FAILED')), "
    "proposal jsonb, proposal_hash text, lead_version integer, approval_id text, failure text, result jsonb, PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, idem_key), FOREIGN KEY (tenant_id, lead_id) REFERENCES leads (tenant_id, id))",
    "CREATE TABLE workflow_events (tenant_id text NOT NULL, run_id text NOT NULL, seq integer NOT NULL, ts timestamptz NOT NULL DEFAULT now(), kind text NOT NULL, detail jsonb NOT NULL DEFAULT '{}', "
    "PRIMARY KEY (tenant_id, run_id, seq), FOREIGN KEY (tenant_id, run_id) REFERENCES workflow_runs (tenant_id, id))",
    "ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY", "ALTER TABLE workflow_runs FORCE ROW LEVEL SECURITY", "ALTER TABLE workflow_events ENABLE ROW LEVEL SECURITY", "ALTER TABLE workflow_events FORCE ROW LEVEL SECURITY",
    "CREATE POLICY tenant_isolation ON workflow_runs USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))",
    "CREATE POLICY tenant_isolation ON workflow_events USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))",
    f"GRANT SELECT, INSERT, UPDATE ON workflow_runs TO {APP_ROLE}", f"GRANT SELECT, INSERT ON workflow_events TO {APP_ROLE}",
    "CREATE FUNCTION workflow_run_guard() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN IF OLD.state IN ('EXECUTED','REJECTED') THEN RAISE EXCEPTION 'finished workflow run cannot change' USING ERRCODE = 'check_violation'; END IF; "
    "NEW.version := OLD.version + 1; NEW.updated_at := now(); RETURN NEW; END $f$",
    "CREATE TRIGGER workflow_runs_guard BEFORE UPDATE ON workflow_runs FOR EACH ROW EXECUTE FUNCTION workflow_run_guard()",
    "CREATE INDEX ix_wfruns_lead ON workflow_runs (tenant_id, lead_id)", "CREATE INDEX ix_wfruns_state ON workflow_runs (tenant_id, state)",
]


def migrations(schema):
    """version -> (apply sql list, preflight list) for pg_hardening.migrate(specs=...). Fresh-schema migrations: no data to pre-flight."""
    v3 = [s.replace("{schema}", schema) for s in V003]
    return {"101": (V001, []), "102": (V002, []), "103": (v3, []), "104": (V004, []), "105": (V005, [])}
