# NASHA Logo Governance and Protection

**Status:** `[PLAN]` governance for the future NASHA identity, from the founder's Sprint 7 **Logo Protection Directive** (D-66). It **overrides** any Sprint 7 instruction that could be read as permission to casually generate, publish, finalize or modify a logo. Name status: `SELECTED_BY_FOUNDER — LEGAL CLEARANCE PENDING`.

## 1. Current status (honest)
- **No NASHA logo exists.** None is designed, shortlisted, approved or released.
- The website and a few concept images show the word NASHA as a **temporary typographic wordmark** (tracked capitals in Instrument Serif, an open-licence font). It is `CONCEPT — NOT OFFICIAL`, is disclosed as temporary in the site footer and About page, and **is not a logo**. The browser favicon is deliberately **empty** so no mark is implied.
- No trademark clearance, registration, ownership or exclusivity is claimed. **No ™ or ® appears anywhere** and none may appear unless a legal basis exists.
- No AI-generated logo has been created, and none becomes official automatically.

## 2. Approval gate (status vocabulary)
`EXPLORATION` → `SHORTLISTED` → `FOUNDER REVIEW` → `FOUNDER APPROVED` → `LEGAL REVIEW` → `PRODUCTION MASTER`. **Only the last stages may be treated as official brand assets**, and only the founder can move a mark forward. AI-generated explorations stay `CONCEPT — NOT OFFICIAL`, and AI is used for identity exploration only when explicitly authorised.

## 3. Trademark gate
Before significant public deployment the selected mark must pass the trademark process (`ip/NASHA-TRADEMARK-ATTORNEY-PACKAGE.md`), including **visual-similarity** review against breweries, restaurants, alcohol brands, hospitality, fashion, Indian and Mexican brands and major consumer brands, in addition to the word NASHA.

## 4. Repository structure (conceptual vault)
```
brand/logo/
  PUBLIC-EXPORTS/        web-safe exports only (SVG/PNG/favicon) of an APPROVED mark; EMPTY today
  CONTROLLED-MASTERS/    editable masters, source files, explorations and rejected marks; EMPTY today; never deployed
  LEGAL-OWNERSHIP/       designer agreements, assignments, clearance reports, checksum records; EMPTY today
```
The website build (`website/build.py`) reads **only** `website/src` and `website/data` and writes `website/dist`; it never reads `brand/logo/`. `tools/validate_site.py` fails if `dist/` holds design-source files, anything from `brand/logo/CONTROLLED-MASTERS`, attorney documents, or filenames suggesting logo explorations. When a production master exists: record version, creation date, creator, source format, modifications, approval, rights status, trademark status and a **SHA-256 checksum** in a master-record file kept under the LEGAL-OWNERSHIP folder, make the master read-only, change it only by deliberate new version, and have the site consume exports, not the master.

## 5. No uncontrolled modification
Never stretch, distort, skew, redraw, recolor arbitrarily, add effects or shadows, alter proportions or letterforms, place patterns inside the mark, destructively animate it, or auto-generate derivative logos. Do not use the approved master as reference or training material for any generator, and do not upload a confidential master to third-party services without understanding their terms.

## 6. Final identity system (later, after approval)
Primary wordmark; primary logo; secondary lockup; compact mark; favicon; monochrome; reversed; signage lockup; packaging lockup; merchandise application; digital/social avatar. Clear space, minimum digital and print size, approved backgrounds, monochrome and reversed use and prohibited treatments become part of the brand guidelines.

## 7. Brand guidelines (to create **only after founder approval**)
Sections: Logo, Wordmark, Icon, Typography, Color, Spacing, Photography, Motion, Food, Beer, Architecture, Packaging, Merchandise, Digital, Co-branding, Incorrect usage. Typography, colour and photography foundations already exist in `NASHA-IDENTITY-SYSTEM.md` and `visuals/NASHA-VISUAL-DIRECTION-V3.md` as proposals.

## 8. Ownership before any designer is commissioned
Require a **written agreement reviewed by counsel** covering deliverable ownership, copyright/IP assignment, commercial use, modification rights, source-file delivery, third-party materials, font licensing, stock assets and **AI-usage disclosure**. Paying a designer does not automatically settle ownership (`ip/IP-OWNERSHIP-FRAMEWORK.md` §5).

## 9. Register
Six brand-asset records (wordmark, primary mark, secondary mark, icon, guidelines, source design files) are in `ip/founder-asset-register.csv` (FA-19..FA-24) with unknowns left `UNKNOWN`.

## 10. Originality
Distinctiveness is a requirement. The mark must not imitate existing marks. A professional conflict review precedes approval.
