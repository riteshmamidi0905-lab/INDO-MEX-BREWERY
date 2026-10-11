# NASHA: Domain and Handle Inventory

**Status:** `[PLAN]` checklist only. **Nothing was checked successfully, nothing was bought, nothing is owned.** Name status: `SELECTED_BY_FOUNDER — LEGAL CLEARANCE PENDING` (D-62).

## What was attempted (Sprint 6, 2026-10-11T01:52Z, session sandbox)
DNS lookups for `nasha.com`, `nasha.beer`, `nasha.co`, `nashaaustin.com`, `nashabrewing.com` returned **no result**, and an RDAP request returned no response (HTTP 000). The session sandbox blocks outbound lookups, so this is **a failure to check, not evidence that any name is free or taken.** A lookup that "finds nothing" in this environment means nothing. **Do not infer availability.**

## Inventory (all status `UNKNOWN` until the founder or an attorney checks from a normal network)
| Item | Candidate | Status | Notes |
|---|---|---|---|
| Primary domain | `nasha` + common TLD | UNKNOWN | A short exact-match domain is probably held by someone else; unverified. |
| Beer-specific TLD | `nasha.beer` | UNKNOWN | |
| City-qualified | `nashaaustin` + TLD | UNKNOWN | Fallback only; also check it implies a location before one exists. |
| Descriptor-qualified | `nashabrewing`, `nashakitchen` | UNKNOWN | Sub-brand style names are not recommended yet (`NASHA-BRAND-STRATEGY.md` §2). |
| Instagram, TikTok, YouTube, X, Facebook, LinkedIn, Google Business | `nasha`-based handles | UNKNOWN | Many `nasha` handles likely exist for unrelated people and businesses; unverified. |
| Email | `hello@` on an owned domain | NOT_CREATED | The site shows no email because none exists. |

## Rules
1. **No purchases without the founder.** Registering a domain is cheap but it is a commitment and a signal; a trademark attorney should clear the name first (`ip/NASHA-TRADEMARK-ATTORNEY-PACKAGE.md`).
2. Owning a domain or handle is **not** trademark rights, and not owning one is not a legal bar. They are separate questions.
3. When checked, record: date/time, tool and result (registered, unregistered, premium, parked, in use), and who checked. Timestamps matter because availability changes.
4. Registering a name creates an account/credential asset: add it to `ip/founder-asset-register.csv` with the registrant being the **founder or the future company deliberately, not a contractor or friend**.
5. Do not scrape or bulk-query registrars. A handful of manual checks is enough for now.

## Founder actions
Check the five domains and the main handles from a normal network and tell the project the results; or hand the list to the trademark attorney. The website runs on a local build and needs no domain to continue.
