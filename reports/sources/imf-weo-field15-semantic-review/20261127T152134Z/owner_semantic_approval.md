# IMF WEO field 15 semantic classification approval

**Decision:** APPROVED  
**Decision date:** 2026-11-27  
**Approver:** project-owner  
**Scope:** WP1.5 field 15 only — IMF WEO October 2026, `NGDPD.A`  
**Approved proposal SHA-256:** `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`

The project owner explicitly approved the semantic convention and the exact 9,361-row proposal identified by the SHA-256 above.

## Approved convention

1. Integer `LATEST_ACTUAL_ANNUAL_DATA`: inclusive cutoff at that year; populated annual columns at or before it are classified `observed`, later columns `estimated`.
2. Fiscal label `FYyyyy/yy`: validate a consecutive fiscal-year span and use its ending year as the inclusive annual-column cutoff; populated annual columns at or before it are classified `observed`, later columns `estimated`.
3. Metadata `0`: all populated observations in that series are `estimated`.
4. Blank or unrecognized metadata is unresolved and must fail closed; no inferred status.
5. No `projected` status is inferred from this metadata.

## Approved artifact and scope

- Proposal: `classification_proposals.csv` in this directory.
- Summary: `summary.json` in this directory.
- Source release: IMF WEO October 2026 / `IMF.RES_WEO_9.0.0`.
- Raw source SHA-256: `a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d`.
- Candidate observations SHA-256: `8f2c2dccfb3263d67544e6772ad2fe3acb47885040967db3a22feb560ed48365`.
- Proposed rows: 9,361 across 197 individual source series.
- Approved status counts: 8,168 `observed`; 1,193 `estimated`.
- Classification rule series: 178 integer latest-actual-year; 19 fiscal-year-ending-year.
- Aggregate series/values remain excluded under the separately approved dispositions: 13 series / 665 populated values.

This approval is a semantic decision on the proposal only. It does **not** itself authorize or perform a canonical database write. The existing observations remain `unclassified` until a separate guarded application is explicitly authorized and independently verified. The field-15 importer remains unchanged and continues to require `unclassified` source candidate rows.
