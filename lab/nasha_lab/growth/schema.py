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
WORKFLOW_TABLES = ["workflow_runs", "workflow_events", "idempotency_keys"]          # created by migration 105 (which carries its own RLS and grants)
VERSIONED = ["segments", "accounts", "contacts", "leads", "opportunities", "products", "prices", "offers", "campaigns", "content_items"]
LAUNCH_TABLES = ["launch_projects", "project_assumptions", "project_milestones", "research_findings", "suppliers", "supplier_products", "project_suppliers", "financial_scenarios", "procurement_recommendations"]
LAUNCH_APPEND_ONLY = ["launch_events"]
LAUNCH_TABLES_V10 = ["supplier_sources"]                      # migration 110 (Milestone 4)
ALL_TENANT_TABLES = TENANT_TABLES + WORKFLOW_TABLES + LAUNCH_TABLES + LAUNCH_APPEND_ONLY + LAUNCH_TABLES_V10
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


V006 = [  # HTTP idempotency records: one stored response per (tenant, key); a different request body under the same key is a conflict
    "CREATE TABLE idempotency_keys (tenant_id text NOT NULL, key text NOT NULL, request_hash text NOT NULL, status_code integer NOT NULL, response jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, key))",
    "ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY", "ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY",
    "CREATE POLICY tenant_isolation ON idempotency_keys USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))",
    f"GRANT SELECT, INSERT ON idempotency_keys TO {APP_ROLE}",
]


V007 = [  # business context for the CRM: what the prospect asked for, who owns it, which scenario it belongs to (all synthetic)
    "ALTER TABLE contacts ADD COLUMN job_title text CHECK (job_title IS NULL OR length(job_title) <= 80)",
    "ALTER TABLE leads ADD COLUMN inquiry text CHECK (inquiry IS NULL OR length(inquiry) <= 600)", "ALTER TABLE leads ADD COLUMN assigned_to text",
    "ALTER TABLE leads ADD COLUMN scenario text CHECK (scenario IS NULL OR length(scenario) <= 80)", "ALTER TABLE leads ADD COLUMN inquiry_received date",
    "ALTER TABLE leads ADD CONSTRAINT leads_assigned_fk FOREIGN KEY (tenant_id, assigned_to) REFERENCES users (tenant_id, id)",
]


GUARDED = {"accounts": "id", "contacts": "id", "leads": "id", "opportunities": "id", "activities": "id", "suppression_list": "email", "segments": "id", "products": "id", "prices": "id", "offers": "id", "campaigns": "id", "content_items": "id"}
V008 = [  # D-90 Milestone 3: no CRM mutation commits without audit evidence from the SAME transaction (deferred constraint triggers; the audit row's transaction id is stamped by the database, not supplied by the caller)
    "ALTER TABLE audit_log ADD COLUMN txid bigint",
    "CREATE FUNCTION audit_stamp() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN NEW.txid := txid_current(); RETURN NEW; END $f$",
    "CREATE TRIGGER audit_log_stamp BEFORE INSERT ON audit_log FOR EACH ROW EXECUTE FUNCTION audit_stamp()",
    # TG_ARGV[0] is the key column. Evidence = an 'allow' audit row in this transaction for this tenant that names this row (entity + id) or lists it in detail.also.
    "CREATE FUNCTION require_audit() RETURNS trigger LANGUAGE plpgsql AS $f$ DECLARE r jsonb; k text; BEGIN "
    "IF TG_OP = 'DELETE' THEN r := to_jsonb(OLD); ELSE r := to_jsonb(NEW); END IF; k := r ->> TG_ARGV[0]; "
    "IF NOT EXISTS (SELECT 1 FROM audit_log a WHERE a.tenant_id = r ->> 'tenant_id' AND a.txid = txid_current() AND a.decision = 'allow' AND ((a.entity = TG_TABLE_NAME AND a.entity_id = k) OR (a.detail -> 'also') ? (TG_TABLE_NAME || ':' || k))) THEN "
    "RAISE EXCEPTION 'change to %.% (%) has no audit evidence in this transaction', TG_TABLE_NAME, TG_ARGV[0], k USING ERRCODE = 'integrity_constraint_violation'; END IF; RETURN NULL; END $f$",
] + [f"CREATE CONSTRAINT TRIGGER crm_audit_guard AFTER INSERT OR UPDATE OR DELETE ON {t} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_audit('{k}')" for t, k in GUARDED.items()]


VERIFICATION = ("synthetic_fixture", "lead_unverified", "verified_public", "stale")
_fkp = lambda: _fk("project_id", "launch_projects")
V009 = [  # D-90 Milestone 3: persistent business-launch projects, supplier intelligence, financial scenarios and governed procurement recommendations (all tenant-scoped, RLS, audited by the same guard)
    f"CREATE TABLE launch_projects ({_COMMON}, name text NOT NULL, industry text NOT NULL, location text NOT NULL, concept text NOT NULL, budget_cents bigint NOT NULL CHECK (budget_cents >= 0), launch_target date, "
    "stage text NOT NULL DEFAULT 'idea' CHECK (stage IN ('idea','research','sourcing','financial_plan','roadmap')), basis text NOT NULL DEFAULT 'synthetic' CHECK (basis IN ('synthetic','founder_input')), "
    "PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, name))",
    f"CREATE TABLE project_assumptions ({_COMMON}, project_id text NOT NULL, key text NOT NULL, label text NOT NULL, value numeric NOT NULL, unit text NOT NULL, "
    f"basis text NOT NULL CHECK (basis IN ('founder','synthetic_assumption','public_reference')), note text, PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, project_id, key), {_fkp()})",
    f"CREATE TABLE project_milestones ({_COMMON}, project_id text NOT NULL, title text NOT NULL, phase text NOT NULL CHECK (phase IN ('idea','research','sourcing','financial_plan','roadmap')), due date, "
    f"status text NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','doing','done')), note text, PRIMARY KEY (tenant_id, id), {_fkp()})",
    f"CREATE TABLE research_findings ({_COMMON}, project_id text NOT NULL, topic text NOT NULL, finding text NOT NULL, source_kind text NOT NULL CHECK (source_kind IN ('founder_note','synthetic_fixture','search_result','public_source')), "
    "source_url text, retrieved_on date, confidence numeric NOT NULL CHECK (confidence BETWEEN 0 AND 1), limitation text NOT NULL, "
    f"CHECK (source_kind NOT IN ('search_result','public_source') OR (source_url IS NOT NULL AND retrieved_on IS NOT NULL)), PRIMARY KEY (tenant_id, id), {_fkp()})",
    # supplier facts: a public business channel is described in words (no personal contact details can be stored: no e-mail addresses or phone numbers)
    f"CREATE TABLE suppliers ({_COMMON}, name text NOT NULL, category text NOT NULL, service_area text NOT NULL, website_url text, contact_channel text NOT NULL DEFAULT 'none recorded', "
    f"verification_status text NOT NULL CHECK (verification_status IN {VERIFICATION}), verified_on date, source_kind text NOT NULL CHECK (source_kind IN ('synthetic_fixture','search_result','official_site')), source_url text, notes text, "
    r"CHECK (contact_channel !~ '@' AND contact_channel !~ '[0-9]{3}[-. ]?[0-9]{3,4}'), "
    "CHECK (verification_status <> 'verified_public' OR (website_url IS NOT NULL AND source_url IS NOT NULL AND verified_on IS NOT NULL)), "
    "CHECK (source_kind <> 'search_result' OR source_url IS NOT NULL), CHECK (verification_status <> 'synthetic_fixture' OR source_kind = 'synthetic_fixture'), PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, name))",
    f"CREATE TABLE supplier_products ({_COMMON}, supplier_id text NOT NULL, name text NOT NULL, ingredient_ref text, unit text NOT NULL, unit_price_cents numeric CHECK (unit_price_cents >= 0), pack_qty numeric CHECK (pack_qty > 0), "
    "lead_days integer CHECK (lead_days >= 0), min_order_cents bigint CHECK (min_order_cents >= 0), price_class text NOT NULL CHECK (price_class IN ('SYNTHETIC_QUOTE','PUBLIC_REFERENCE','SUPPLIER_QUOTE','NONE_PUBLISHED')), "
    "valid_from date, valid_to date, source_url text, limitation text NOT NULL, CHECK (price_class = 'NONE_PUBLISHED' OR unit_price_cents IS NOT NULL), CHECK (price_class <> 'NONE_PUBLISHED' OR unit_price_cents IS NULL), "
    f"CHECK (price_class NOT IN ('PUBLIC_REFERENCE','SUPPLIER_QUOTE') OR (source_url IS NOT NULL AND valid_from IS NOT NULL)), PRIMARY KEY (tenant_id, id), {_fk('supplier_id', 'suppliers')})",
    f"CREATE TABLE project_suppliers ({_COMMON}, project_id text NOT NULL, supplier_id text NOT NULL, status text NOT NULL CHECK (status IN ('shortlisted','preferred','rejected')), note text, "
    f"PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, project_id, supplier_id), {_fkp()}, {_fk('supplier_id', 'suppliers')})",
    f"CREATE TABLE financial_scenarios ({_COMMON}, project_id text NOT NULL, name text NOT NULL, kind text NOT NULL DEFAULT 'simulated' CHECK (kind = 'simulated'), inputs jsonb NOT NULL, inputs_hash text NOT NULL, results jsonb NOT NULL, "
    f"PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, project_id, name), {_fkp()})",
    f"CREATE TABLE procurement_recommendations ({_COMMON}, project_id text NOT NULL, requester text NOT NULL, role text NOT NULL, idem_key text, period text NOT NULL, "
    "state text NOT NULL CHECK (state IN ('STARTED','PROPOSED','AWAITING_APPROVAL','APPROVED','EXECUTED','REJECTED','BLOCKED','FAILED')), agent_mode text CHECK (agent_mode IN ('engine_offline_heuristic','engine_model','deterministic_fallback')), "
    "items jsonb, totals jsonb, research jsonb, proposal_hash text, approval_id text, failure text, decided_by text, "
    f"PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, idem_key), {_fkp()})",
    "CREATE TABLE launch_events (tenant_id text NOT NULL, run_id text NOT NULL, seq integer NOT NULL, ts timestamptz NOT NULL DEFAULT now(), kind text NOT NULL, detail jsonb NOT NULL DEFAULT '{}', "
    "PRIMARY KEY (tenant_id, run_id, seq), FOREIGN KEY (tenant_id, run_id) REFERENCES procurement_recommendations (tenant_id, id))",
    "CREATE FUNCTION procurement_guard() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN IF OLD.state IN ('EXECUTED','REJECTED') THEN RAISE EXCEPTION 'finished procurement recommendation cannot change' USING ERRCODE = 'check_violation'; END IF; "
    "NEW.version := OLD.version + 1; NEW.updated_at := now(); RETURN NEW; END $f$",
    "CREATE TRIGGER procurement_recommendations_guard BEFORE UPDATE ON procurement_recommendations FOR EACH ROW EXECUTE FUNCTION procurement_guard()",
] + [s for t in LAUNCH_TABLES + LAUNCH_APPEND_ONLY for s in (f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY", f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY",
                                                           f"CREATE POLICY tenant_isolation ON {t} USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))")] \
  + [f"GRANT SELECT, INSERT, UPDATE ON {t} TO {APP_ROLE}" for t in LAUNCH_TABLES] + [f"GRANT SELECT, INSERT ON launch_events TO {APP_ROLE}"] \
  + [s for t in LAUNCH_TABLES if t != "procurement_recommendations" for s in (f"CREATE TRIGGER {t}_bump BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION bump_version()", f"CREATE TRIGGER {t}_snap AFTER INSERT OR UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION snapshot_version()")] \
  + [f"CREATE TRIGGER procurement_recommendations_snap AFTER INSERT OR UPDATE ON procurement_recommendations FOR EACH ROW EXECUTE FUNCTION snapshot_version()"] \
  + [f"CREATE CONSTRAINT TRIGGER crm_audit_guard AFTER INSERT OR UPDATE OR DELETE ON {t} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_audit('id')" for t in LAUNCH_TABLES if t != "procurement_recommendations"] \
  + ["CREATE FUNCTION require_audit_on_execute() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN IF NEW.state = 'EXECUTED' AND OLD.state IS DISTINCT FROM 'EXECUTED' AND NOT EXISTS (SELECT 1 FROM audit_log a WHERE a.tenant_id = NEW.tenant_id AND a.txid = txid_current() "
     "AND a.decision = 'allow' AND a.entity = 'procurement_recommendations' AND a.entity_id = NEW.id) THEN RAISE EXCEPTION 'recording procurement recommendation % has no audit evidence in this transaction', NEW.id USING ERRCODE = 'integrity_constraint_violation'; END IF; RETURN NULL; END $f$",
     "CREATE CONSTRAINT TRIGGER procurement_audit_guard AFTER UPDATE ON procurement_recommendations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_audit_on_execute()"] \
  + ["CREATE INDEX ix_launch_findings ON research_findings (tenant_id, project_id)", "CREATE INDEX ix_supplier_products ON supplier_products (tenant_id, supplier_id)", "CREATE INDEX ix_procurement_project ON procurement_recommendations (tenant_id, project_id, state)"]


SOURCE_KINDS = ("official_site", "contact_page", "trade_directory", "press", "investor_profile", "partner_listing", "government_record")
V010 = [  # D-90 Milestone 4: structured, dated provenance for supplier facts. One row per public source: what kind of page, its URL, the claim it supports, whether the PAGE WAS READ or only a search snippet was seen, and when.
    f"CREATE TABLE supplier_sources ({_COMMON}, supplier_id text NOT NULL, kind text NOT NULL CHECK (kind IN {SOURCE_KINDS}), url text NOT NULL CHECK (url ~ '^https://[^ ]+$'), claim text NOT NULL CHECK (length(claim) BETWEEN 8 AND 400), "
    "access text NOT NULL CHECK (access IN ('page_read','search_snippet')), observed_on date NOT NULL, "
    f"CHECK (claim !~ '@' AND claim !~ '[0-9]{{3}}[-. ]?[0-9]{{3,4}}'), PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, supplier_id, url, claim), {_fk('supplier_id', 'suppliers')})",
] + [s for t in LAUNCH_TABLES_V10 for s in (f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY", f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY",
                                            f"CREATE POLICY tenant_isolation ON {t} USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))",
                                            f"GRANT SELECT, INSERT, UPDATE ON {t} TO {APP_ROLE}", f"CREATE TRIGGER {t}_bump BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION bump_version()",
                                            f"CREATE TRIGGER {t}_snap AFTER INSERT OR UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION snapshot_version()",
                                            f"CREATE CONSTRAINT TRIGGER crm_audit_guard AFTER INSERT OR UPDATE OR DELETE ON {t} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_audit('id')")] \
  + ["CREATE INDEX ix_supplier_sources ON supplier_sources (tenant_id, supplier_id)"]


def migrations(schema):
    """version -> (apply sql list, preflight list) for pg_hardening.migrate(specs=...). Fresh-schema migrations: no data to pre-flight."""
    v3 = [s.replace("{schema}", schema) for s in V003]
    return {"101": (V001, []), "102": (V002, []), "103": (v3, []), "104": (V004, []), "105": (V005, []), "106": (V006, []), "107": (V007, []), "108": (V008, []), "109": (V009, []), "110": (V010, [])}
