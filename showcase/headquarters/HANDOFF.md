# Phase 3 handoff

## Preservation and scope

Base: `6c177d7ac8afa3d5573c46d6298a83bdc09138fd`, the remotely backed-up Enterprise Showcase foundation. Branch: `codex/enterprise-headquarters-phase3`. All Phase 3 work is additive under `showcase/`. The original foundation source, fixtures, validation logs and saved cloud setup instructions were not replaced. Claude Code's engineering branch and the production portfolio were not edited. No push, merge, PR, deployment or publication was performed.

## Architecture

`Browser -> same-origin authenticated loopback host -> server-selected granted business -> principal-bound THE WEIR read -> existing Service authorization -> new read model -> existing per-business read-only database`.

`showcase/hq.py` supplies the local HTTP/session host and a bounded extension of the foundation's actual WEIR upstream. `showcase/hq_data.py` adds typed-by-route aggregate queries, schema inspection, fixed evidence IDs and actual JUnit parsing. The foundation's generator, schemas, Service, agentplatform Tool adapter and all tests remain intact. The UI is dependency-free HTML/CSS/ES modules with original SVG artwork and existing OFL-licensed local fonts. No alternative agent runtime or approval engine was created.

Financial views query `financial_records`, joined through `transactions` and `business_events`. Monthly figures sum to the scenario totals, and cash movement sums to ending cash. Record filters affect only the explorer, not the full-period headline metrics. Exports say whether they contain a displayed page or a full monthly summary. Fixture sizes, modeled losses and scenario dates are displayed as stored.

Each new host gateway session is bound to a browser session, tenant and server-configured persona. A per-tenant persistent WEIR Store records actual read decisions. No write or egress tool is registered, so there are no invented approvals or consequential activities. The approved-reviewer experience combines explicitly granted read capabilities; it does not claim fictional personas are authenticated human users.

## Validation

- **37 automated tests passed**, including the original 18 foundation tests, actual PostgreSQL checks, and 19 new host/build tests. No expensive model evaluations were run.
- Frontend build: **9 local assets**, entrypoint verification and content-hash manifest. JavaScript syntax check passed.
- Real Chromium: all **11 departments for both businesses**, financial filtering/pagination/provenance/export, employee search/profile, source inspection, guided blueprint/export, escaped HTML injection, keyboard search, logout, mobile navigation/reflow, and reduced-motion behavior passed. Zero page/console application errors.
- axe-core WCAG 2 A/AA, 2.1 AA and 2.2 AA checks on Headquarters, Finance, People, Creation and Engineering: **zero automated violations** after contrast and scroll-focus corrections. This is not a complete accessibility certification or an assistive-technology user study.
- Screenshots and actual JSON/JUnit logs are retained under `/workspace/.nasha-hq/evidence/`. Runtime credentials and gateway databases are outside Git. Original foundation reports remain under `/workspace/.brewery-setup/`.

## Security and honest limitations

This is a **local authenticated review host**, not a production identity solution. An owner-only random access code establishes one local reviewer identity with access to only the businesses explicitly configured at startup. Sessions are random, expire after eight hours, use HttpOnly/SameSite=Strict cookies, and require CSRF tokens for selection/logout. Sign-in is rate limited. Host/origin checks, a strict self-only CSP, no CORS, JSON-only bounded requests, fixed evidence paths, and read-only SQLite connections constrain the interface.

The host binds to loopback and uses HTTP; it intentionally does not offer public hosting. The cookie lacks Secure because this is local HTTP. Do not expose it through an untrusted forwarding/public tunnel or treat the access code as production SSO. Local privileged filesystem users and the trusted host can access all fixtures. The server-granted registry is not an external authorization service. For multi-user deployment, reuse the existing identity authority, authenticated tenant grants, TLS, Secure cookies, identity-bound gateway sessions and scoped roles; review deployment/network controls separately.

Persistent gateway decisions are actual review-host reads, not proof of live fictional agent work. The source event chain is a deterministic fixture hash chain, not a signed immutable commercial ledger. Runtime uses SQLite. PostgreSQL schemas/RLS are independently tested, not a live warehouse connection. Quality cards report explicitly scoped read-time checks, not full replay or external certification. The historical playbook remains a plan in places. Existing upstream model/evaluation results were not represented as newly executed work.

## Remaining work and integrations

- Production SSO and server-authoritative per-user tenant/capability grants; there is no public tenant-selection API.
- PostgreSQL runtime adapter using the already-tested existing schemas, with scoped non-owner roles.
- Explicitly approved agent task execution through existing agentplatform and THE WEIR; no persona is secretly running.
- A reviewed provisioning workflow for exported business blueprints. The current wizard creates a local draft only.
- Existing Growth CRM integration for individual fictional relationship workflows; no real HubSpot/Slack connectors are necessary here.
- Broader accessibility review, cross-browser/user studies, and an authorized CI job for this new surface.

No paid services, image generation, avatar subscriptions, new provider credentials or live external integrations are required to review Phase 3.
