# WP1.5 review, approval and database application workflow

**Status:** normative project-wide workflow for every remaining WP1.5 source/field batch.  
**Scope:** source acquisition through candidate preparation, consolidated review, edge-case resolution, approval and database application.

## 1. Governing rule

Every remaining WP1.5 source/field batch follows one controlled sequence:

1. Acquire and register immutable source evidence.
2. Normalize and validate a candidate without writing canonical game data.
3. Publish one consolidated review package as the single decision surface.
4. Resolve and record edge cases linked to the affected candidate observations.
5. Freeze and fingerprint the exact approved candidate.
6. Record approval through the shared application-approval workflow.
7. Apply only the approved artifact transactionally to the database.
8. Verify the result and update the durable implementation record.

This workflow is reusable across providers and fields. Provider-specific adapters may differ, but must produce the same review/approval/application evidence contract. Do not create a separate approval mechanism for each source.

## 2. Acquisition and candidate preparation

- Preserve the exact source bytes, release/vintage, retrieval time, source URL, terms/attribution, byte count and SHA-256 in the established acquisition manifest and Project DB provenance records.
- Reuse a valid existing acquisition. Do not reacquire merely to begin review.
- Normalize through a source-specific adapter into the WP1.5 observation contract. Preserve provider IDs, units/scales, reference periods, status metadata and methodology.
- Validate schema, numeric finiteness, uniqueness, coverage, crosswalk integrity, source/field contract, missingness and source fingerprint.
- Candidate generation is read-only with respect to canonical game data. Acquisition, validation or comparison success is not approval.

## 3. One consolidated review package

Each source/release review must publish one clearly designated review package. It is the single place where reviewers inspect observations and record decisions; supporting reports remain evidence, not competing decision surfaces.

At minimum, the package contains:

- A human-readable overview with scope, source/release fingerprints, field definitions, units, reference periods, status semantics, coverage and validation results.
- A complete observation-level review register, retaining rows with missing values and unresolved states rather than silently dropping them. Each row identifies the persistent `game_id`, provider source ID, field/statistic, observation period, value/unit/status, provenance, identity decision, semantic gate, evidence references and reviewer disposition.
- An explicit crosswalk review, including unmatched, ambiguous, aggregate, non-sovereign and proposed identity cases. Names alone must never establish identity.
- A decision vocabulary with at least: `approve`, `exclude`, `hold_for_evidence`, and `not_applicable`. A blank decision is pending, never implicit approval. Any source-specific extension must be documented.
- A machine-readable decision file that is authoritative for review decisions and validates against the exact candidate fingerprint.
- Links to supporting comparisons and evidence. Supporting evidence may be extensive, but decisions are entered once in the consolidated package.

A package must identify its schema/version and provide deterministic row keys so that review decisions can be carried forward safely when regenerated. If candidate inputs change, stale decisions must be detected; they must not silently attach to changed observations.

The first implementation is the [Stage 4E IMF WEO–WDI consolidated review package](../implementation/data-store-separation-stage-4e-weo-review-package.md). It provides the observation-level review register and linked edge-case queue; it is intentionally review-only.

## 4. Edge-case register

Generate an actionable edge-case register from the same candidate and review package. It is a linked work queue, not a second approval surface.

Each case records a stable case ID, affected observation keys, issue category, evidence, current disposition and required resolution/action. Cases can group multiple observation rows, but must link back to every affected row. Final observation decisions and their rationale are recorded only in the consolidated review register; the edge-case work queue must not become a competing decision surface. Case closure is reflected by the linked observation decisions and supporting closure evidence.

Typical categories include:

- Identity: unresolved/ambiguous source codes, aggregate codes, territories, changed boundaries and crosswalk conflicts.
- Definition and unit: concept mismatch, unit/scale uncertainty, numerator/denominator differences and conversion assumptions.
- Period: calendar versus fiscal year, annual average versus end-period, reference date and non-calendar reporting periods.
- Methodology/vintage: national-account revisions, PPP/ICP benchmark and linking, population denominator, CPI basket changes, survey redesign and source revisions.
- Observation status: actual/estimate/projection/preliminary/forecast/unknown. Never infer a status from adjacent indicators or year labels.
- Missingness and anomalies: absent values, duplicate rows, implausible values, breaks and outliers.

Known country/field investigations must be reused and cited. Settled cases remain closed unless new contradictory evidence is documented. Do not reopen them by default.

## 5. Review decisions and approval boundary

- Review decisions must be explicit at the smallest level supported by evidence: observation, country-field-year, crosswalk mapping, or a documented group of equivalent rows.
- A general field-level conclusion does not automatically approve every country-year observation.
- Unresolved cases remain held or excluded according to the documented decision; they are not coerced into a successful import.
- Approval applies to the exact immutable candidate artifact and its dependencies (manifest, crosswalk and decision file). Record their hashes and the reviewer/actor and rationale.
- Use `tools/database/application_approval.py` through the existing shared CLI adapters. Preserve the proposal → approved → applied event history and deterministic approval ID/recovery behavior.
- Dataset import status and approval status are distinct. Do not promote a candidate dataset/release merely because an application approval was recorded.
- Source-selection policy changes, fallback promotion and provider comparability decisions require their own documented decision and approval. An observation import approval does not imply those policy decisions.

## 6. Database application

- The importer consumes only the approved artifact, never the raw review register or an unapproved diagnostic matrix.
- Apply in a transaction using the existing WP1.5 importer and its explicit source crosswalk.
- Preserve `game_id`, provider source ID, field/statistic key, numeric or structured value, unit, reference period, value status, methodology, source release, source fingerprint and import/approval linkage.
- Do not overwrite or infer unresolved identities, statuses, units, reference periods or missing values.
- Respect the existing distinction between candidate and verified data. Only a separately authorized promotion may change that state.
- Reapplication must follow the importer’s idempotency/recovery contract; never create duplicate observations or bypass the approval ID.

## 7. Required post-application verification

Record and inspect:

- approval status and complete approval-event sequence;
- applied artifact hash and source/crosswalk fingerprints;
- imported row counts by field, status and entity;
- distinct mapped entities and provider IDs;
- expected versus imported observations and explicit exclusions/holds;
- duplicate/conflict checks and idempotency result;
- SQLite integrity and foreign-key checks;
- any importer warnings or rejected rows.

The owner runs local tests and database verification. Documentation must distinguish repository implementation from owner-verified execution; do not claim local validation without supplied output.

## 7.1 Completed application reference — World Bank WDI

The owner applied and independently verified the World Bank WDI WP1.5 candidate on 2026-11-25. The exact approval ID is `wp1-5-wdi-20261125-regenerated`; actor `project-owner`; candidate artifact SHA-256 `86196b1cdb1783c00e6d391d11d5314cf5c50ad4351b1664f24fa65735349c5b`. The application created import ID `4` and application ID `wp1-5:world_bank_wdi:api_snapshot_20261121T074357472382Z:7196c4bf58e6`, with 561 scalar observations and 187 explicit crosswalk mappings. The approval ledger records `proposed` → `approved` → `applied`; independent read-only verification confirmed 561 `current_statistics` rows and 187 `country_sources` rows for import ID 4, one `dataset_imports` row, SQLite integrity `ok`, and no foreign-key violations. The first application correctly reports `idempotent=false`. Full evidence is in [World Bank WDI WP1.5 application record](world-bank-wdi-wp1-5-application.md).

## 8. Applying the workflow to remaining WP1.5 fields

The sequence above applies uniformly to all remaining fields and providers, not only IMF WEO.

The current execution order is:

1. **IMF WEO — fields 15, 16, 18, 20 and 21:** reuse the captured October 2026 release and completed comparison/country investigations. Consolidate existing evidence into one review package, resolve the open identity and semantic cases, then approve and apply eligible observations.
2. **ILOSTAT — field 22 (labour force):** inspect existing source/manifest state first; acquire only if evidence shows a required capture is missing or invalid. Then use the same candidate → review → edge-case → approval → application sequence.
3. **All other uncompleted WP1.5 fields:** follow the same sequence in source/field batches. A source may cover multiple fields, but each field’s definition, unit, period, status, rights and comparability gates must be explicit in the shared package.

The workflow does not require all 41 fields to be reviewed together. It requires one authoritative review package per coherent source/release batch and a consistent governance path across every batch.

## 9. Relationship to existing project contracts

- Persistent `game_id` remains the internal identity; provider identifiers are crosswalk attributes.
- The field/source contract in `config/wp1_5_data_sources.json` and central source registry remain authoritative.
- The source-selection policy remains in `config/source_selection.json`; this workflow does not silently change it.
- The WP1.5 normalized observation/import contract and shared approval engine remain authoritative for application.
- Existing source-specific assessments remain evidence. They are not approval artifacts.
