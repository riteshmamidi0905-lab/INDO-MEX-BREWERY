---
name: nasha-rights-audit
description: Check provenance, licence and AI-provider terms before any NASHA asset (image, font, photo, code, dataset) is integrated or published. Use before integrating or publishing an asset.
---
# NASHA rights audit

For each asset record: ID, source/provider and model, date, creator, rights owner, licence, provider-terms status, edits, identifiable people, publication gate.
1. Logo gate (D-66): any logo/monogram/icon/badge/wordmark generation or placement is REJECT. Name status stays "SELECTED_BY_FOUNDER, LEGAL CLEARANCE PENDING"; no TM/R symbols; a search result is never clearance.
2. AI images: look up the provider in docs/ai/PROVIDER-TERMS-MATRIX.csv. Any UNVERIFIED cell, or no primary source read, means PROVISIONAL-LOCAL-ONLY (visuals/NASHA-VISUAL-MANIFEST.csv rights column). Generated imagery adds zero evidence.
3. Photos: `python3 tools/photo_ingest.py` provenance CSV; originals read-only; allowed edits crop/exposure/white balance/rotation only.
4. Fonts and code: `bash tools/security_check.sh` (licence summaries); record licence per font/package.
5. Datasets: ops/templates/dataset-provenance.csv (source, date, owner, licence, transformations, tier).
6. Verdict: PASS / CAUTION / REJECT, smallest fix, and "attorney required" where a legal conclusion is implied.
