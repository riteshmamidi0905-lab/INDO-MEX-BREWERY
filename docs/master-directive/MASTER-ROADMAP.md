# Integrated execution roadmap (2026-10-22)

Status legend: EXISTS (verified), PARTIAL, NEW, BLOCKED (needs decision, see DIRECTIVE-CONFLICTS.md).

| Phase | Deliverable | State | Next concrete step | Gate |
|---|---|---|---|---|
| 0 Discovery | audit, risks, reuse plan, dev branch | DONE (this commit) | - | - |
| 1 Brand world | design system | PARTIAL: `brand/NASHA-IDENTITY-SYSTEM.md`, `website/DESIGN-SYSTEM.md`, noindex prototype (20 pages) | name-agnostic token layer (`BRAND-DESIGN-SYSTEM.md`) | name decision |
| 1 | BADSHAH / PAAPI / food / hoodies | PARTIAL / BLOCKED (#2-#4) | decisions, then rights audit | founder |
| 2 Data foundation | generator, contracts, quality, warehouse | PARTIAL: 3-site generator, DQ rules (11 of 12 defect types), P4 SQLite mart | scale-up + contracts doc + dbt project | merge of P4 |
| 3 BI | executive + store dashboards | PARTIAL: P4 static dashboard (axe/Playwright checked) | KPI tree, store view | Phase 2 |
| 4 Product intelligence | funnel, cohorts, A/B, memo | PARTIAL: P4 experiment + prospective design | loyalty funnel + retention | Phase 2 |
| 5 Ops AI | RAG, tools, governed agent, eval, security | EXISTS in lab (warehouse tools NEW) | warehouse-backed tools via THE WEIR | Phase 2 |
| 6 FDE | second customer, adapters, acceptance | NEW | messy second dataset + mapping config | Phase 2 |
| 7 Showcase | case studies, video, matrix | PARTIAL (portfolio branch, case study) | showcase page + 8-minute script | after 1-6 |
| 8 Mastery | diagnostic, modules, journal | STARTED: `lab/learning/diagnostic` | take the diagnostic | you |

Quality gate for every phase: implementation + tests + reproducibility + docs + security + limits recorded + synthetic labels + learning material. Nothing is marked complete without that evidence.
