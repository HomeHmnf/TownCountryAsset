# WP1.5 remaining acquisition and application plan

**Status:** execution plan; governed by the [WP1.5 review, approval and database application workflow](wp1-5-review-approval-application-workflow.md).  
**Last reviewed:** 2026-11-25.

## Completed

- UN WPP fields 1, 2, 6, 12, 13 and 14 were previously applied.
- World Bank WDI fields 3, 33 and 34 were imported and owner-verified: 561 observations across 187 mapped entities, with integrity and foreign-key checks passing.
- The shared project-wide application approval engine and CLI adapters were implemented and owner-tested.
- IMF WEO October 2026 source capture, Project DB acquisition registration, coverage assessment, WDI comparison, Stage 4C semantic disposition and Stage 4D macro decomposition are existing evidence. These are not yet semantic approval or canonical application.

## Mandatory process for every remaining field

Use one authoritative review package per coherent source/release batch. It must contain the complete observation-level review register and machine-readable decisions. Generate a linked edge-case register from that same package. Resolve or explicitly hold each case before freezing the approval artifact. Apply only through the shared approval engine and existing transactional importer.

See [WP1.5 review, approval and database application workflow](wp1-5-review-approval-application-workflow.md) for the complete contract. No provider may bypass this process or create an independent approval mechanism.

## Execution order

### 1. IMF WEO — fields 15, 16, 18, 20 and 21

- Reuse the existing October 2026 CSV and Database Appendix; do not reacquire.
- Reuse the existing coverage, frozen WDI comparison, semantic disposition, macro decomposition and country-specific evidence.
- Build one consolidated review package containing the complete candidate universe, provenance, crosswalk/identity status, values, periods, status metadata, semantic evidence and explicit reviewer decisions.
- Derive a linked edge-case register covering unresolved identity, national-account vintages, PPP/ICP construction, CPI annual/fiscal periods, unemployment definitions and unknown observation status.
- Preserve settled findings (including Bahrain unemployment) unless new evidence warrants a documented reopening.
- Do not infer WEO PPP actual/estimate status or WDI actual/estimate status where source metadata is blank.
- Freeze and fingerprint the reviewed application artifact. Approve it through the shared workflow and apply only eligible observations. Keep held/excluded rows visible in the review package.
- Do not change source-selection priority or promote WDI as a fallback as a side effect of import approval.

### 2. ILOSTAT — field 22 (labour force)

- Inspect the central source registry, existing raw captures, manifests, Project DB acquisition records and source-specific work before acquiring anything.
- Confirm the selected indicator’s labour-force concept, age range, sex scope, unit, reference period, annual aggregation, status and country coverage.
- Capture immutable source bytes and manifest only if the required release/data are not already validly present.
- Build the normalized candidate, consolidated review package and linked edge-case register using the same workflow.
- Approve and apply only after explicit crosswalk and semantic decisions.

### 3. All other uncompleted WP1.5 fields

For each remaining source/field batch, inspect existing evidence first, then acquire only missing/invalid source data. Use the same normalized candidate, consolidated review package, linked edge-case register, exact-artifact approval, transactional application and post-application verification sequence.

## Current gate

The next implementation task is the IMF WEO consolidated review package and linked edge-case workflow. Existing Stage 4 diagnostic reports are inputs to this package, not substitutes for it. The package must not mark all rows approvable merely because the source file is complete or a numeric comparison exists. Identity and semantic gates remain explicit, and unresolved rows remain held or excluded.

## Owner-run validation and evidence

The owner runs tests and database commands locally. Record exact commands, counts, approval IDs, artifact fingerprints, integrity results and commit references after receiving the output. Repository code changes alone do not establish successful local application.
