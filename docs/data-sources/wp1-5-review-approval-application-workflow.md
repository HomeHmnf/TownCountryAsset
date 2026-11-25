# WP1.5 review, approval and database application workflow

**Status:** normative project-wide workflow for every WP1.5 field.  
**Scope:** source acquisition through candidate preparation, consolidated review, edge-case resolution, approval, Project/source database verification, Game database application and field closure.

## 1. Governing rule

Execute one field at a time. A provider may supply multiple fields in one release, but the release acquisition may be shared while review decisions, approved candidate artifacts, Game DB applications, verification and closure remain field-scoped. The next field must not begin until the current field is closed.

For each field:

1. Confirm the authoritative source, exact indicator and field definition.
2. Reuse or acquire immutable source evidence and register the acquisition/artifacts in the Project/source database.
3. Independently verify source bytes, manifest and Project DB registration.
4. Normalize and validate a field-scoped candidate without writing Game DB data.
5. Publish one consolidated field-scoped review package and linked edge-case queue.
6. Resolve identity, semantic, period, unit, status and missingness cases; account for the full expected identity universe.
7. Freeze and fingerprint the exact candidate and dependencies.
8. Record owner approval through the shared application-approval workflow.
9. Apply only that approved field artifact transactionally to the Game DB.
10. Independently verify both databases and update the durable field record.
11. Mark the field complete only after every gate passes; then proceed to the next field.

No batch-level success may be used to imply that every field in that batch is complete.

## 2. Acquisition and Project/source database

- Preserve exact source bytes, release/vintage, retrieval timestamp and its precision, source URL, terms/attribution metadata, byte count and SHA-256 in the established acquisition manifest.
- Reuse a valid existing acquisition. Do not reacquire merely to begin review.
- Register acquisition events and artifact records using the source-specific or shared Project DB registration workflow.
- Independently verify that the Project DB records refer to the expected source, dataset, release, event and artifact roles, and that recorded byte counts and SHA-256 values match the immutable local files.
- Confirm Project DB integrity and foreign-key checks after registration.
- An acquisition in state `acquired` proves provenance registration, not semantic validation, retention, approval or Game DB application.

## 3. Candidate preparation

- Normalize through the source-specific adapter into the WP1.5 observation contract.
- Preserve provider IDs, persistent `game_id`, units/scales, reference periods, status metadata, methodology and source fingerprints.
- Validate schema, numeric finiteness, uniqueness, coverage, crosswalk integrity, source/field contract and missingness.
- Candidate generation is read-only with respect to the Game DB. Acquisition or validation success is not approval.
- Keep the candidate scoped to the field being closed. A shared raw source may be reused, but do not include adjacent fields in the approval artifact.

## 4. One consolidated field review package

Each field must have one clearly designated review package, the single decision surface for observation-level review. Supporting reports remain evidence, not competing decision surfaces.

At minimum, the package contains:

- Field ID/key, provider, indicator, source/release fingerprints, definition, unit, reference periods, status semantics, coverage and validation results.
- A complete observation-level register retaining missing and unresolved rows. Each row identifies persistent `game_id`, provider source ID, field/statistic, period, value/unit/status, provenance, identity decision, semantic gate, evidence and reviewer disposition.
- An explicit crosswalk review including unmatched, ambiguous, aggregate, non-sovereign and proposed identity cases.
- Explicit decisions: `approve`, `exclude`, `hold_for_evidence`, or `not_applicable`. Blank is pending, never approval.
- A machine-readable decision file bound to the exact candidate fingerprint.
- A full expected-identity coverage summary. Every identity must be accounted for; absent source rows remain explicit missingness and are never filled with invented values.

If the candidate changes, stale decisions must be detected. Never carry decisions by row position or silently attach them to changed observations.

## 5. Linked edge-case register

Generate an actionable edge-case queue from the same candidate and review package. It is a work queue, not a second approval surface. Each case has a stable ID, affected observation keys, issue category, evidence, disposition and required action. Record final decisions and rationale only in the review register.

Typical categories include identity, definition/unit, period, methodology/vintage, observation status, missingness, duplicates and anomalies. Reuse settled evidence and keep its scope bounded. Do not reopen settled findings without new contradictory evidence.

## 6. Approval boundary

- Decisions are explicit at the smallest evidence-supported level.
- A field-level conclusion does not automatically approve every country-year observation.
- Unresolved cases remain held or excluded with rationale.
- Approval applies to the exact immutable field candidate and dependencies (manifest, crosswalk, decision file). Record hashes, actor and rationale.
- Use `tools/database/application_approval.py` through the shared CLI adapters. Preserve proposal → approved → applied event history.
- Dataset import status and approval status are distinct.
- Source-selection policy changes, fallback promotion and release promotion require separate decisions and approvals.

## 7. Game DB application and verification

- The importer consumes only the approved field artifact, never the raw review register or an unapproved diagnostic matrix.
- Apply transactionally using the existing importer and explicit source crosswalk.
- Preserve identity, provider ID, field key, value, unit, period, status, methodology, source release, fingerprint and approval/import linkage.
- Do not overwrite or infer unresolved identities, statuses, units, periods or missing values.
- Independently verify approval status/events, applied hash, imported counts by field/status/entity, mapped entities/provider IDs, expected versus imported rows, explicit holds/exclusions, duplicate/conflict checks, idempotency, SQLite integrity and foreign keys.
- Independently verify the corresponding Project DB acquisition/artifact records and their hashes/integrity. Both database checks are mandatory for field closure.

## 8. Field closure and progress record

A field is complete only when source acquisition/provenance, Project DB verification, semantic/identity review, exact-artifact approval, Game DB application, independent verification of both databases and documentation are complete. A field may have explicitly documented unavailable, not-applicable, excluded or held observations; it may not silently omit them. Record exact commands, timestamps, source/release, hashes, counts, coverage, decisions, approval ID, Project DB acquisition/artifact IDs, Game DB import/application IDs and integrity results.

The owner runs local commands. Never claim owner-side validation or application until output is supplied. Do not begin the next field before closure.

## 9. Completed application reference — World Bank WDI

The owner applied and independently verified the World Bank WDI WP1.5 candidate on 2026-11-25. The exact approval ID is `wp1-5-wdi-20261125-regenerated`; actor `project-owner`; candidate artifact SHA-256 `86196b1cdb1783c00e6d391d11d5314cf5c50ad4351b1664f24fa65735349c5b`. The application created import ID `4` and application ID `wp1-5:world_bank_wdi:api_snapshot_20261121T074357472382Z:7196c4bf58e6`, with 561 scalar observations and 187 explicit crosswalk mappings. The approval ledger records `proposed` → `approved` → `applied`; independent read-only verification confirmed 561 `current_statistics` rows and 187 `country_sources` rows for import ID 4, one `dataset_imports` row, SQLite integrity `ok`, and no foreign-key violations. The first application correctly reports `idempotent=false`. See the [application record](world-bank-wdi-wp1-5-application.md).

## 10. Current field order

1. Field 15 — IMF WEO NGDPD (GDP).
2. Field 16 — IMF WEO NGDPDPC (GDP per capita).
3. Field 18 — IMF WEO PPPGDP (GDP at PPP).
4. Field 20 — IMF WEO PCPIPCH (inflation).
5. Field 21 — IMF WEO LUR (unemployment).
6. Field 22 — ILOSTAT labour force.
7. Remaining fields in `config/wp1_5_data_sources.json` order.

The October 2026 IMF WEO acquisition is already registered in the Project DB as acquisition ID `5`; it is source evidence, not a completed field. Start with field 15 only. The Stage 4C semantic matrix and Stage 4E multi-field review package are supporting tools, not field approvals. The field-15 candidate and review package must exclude fields 16, 18, 20 and 21.

## 12. Field-15 reconciliation and canonical identity schema audit — 2026-11-25

The October 2026 IMF WEO field-15 source uses composite annual series codes of the form `<source-country-or-area-code>.NGDPD.A`. The country/area code is the prefix before `.NGDPD.A`; `NGDPD` is not the complete `SERIES_CODE`. The source contains 210 NGDPD series rows and 10,026 nonblank annual values (1980–2031). The canonical Game DB contains 9,329 observations for the matching source fingerprint. A read-only value reconciliation found zero value mismatches, zero extra canonical keys and zero metadata mismatches among matched records; 697 source values have no corresponding canonical observation.

The 697-value gap is classified by source series:
- Twelve aggregate/regional codes (`G001`, `G110`, `G119`, `G200`, `G205`, `G400`, `G505`, `G510`, `G603`, `G903`, `G998`, `GX123`) account for 624 values.
- `G163` (Euro Area) accounts for 41 values.
- `WBG` (West Bank and Gaza) accounts for 32 values, for 1994–2025. These are not to be silently classified as aggregates or excluded; they require an explicit identity disposition.

Canonical identity schema confirmed by read-only inspection:
- `countries` stores identity state and ISO attributes, keyed by `game_id`; it has no country-name column. Relevant columns include `entity_type`, `record_status`, `iso_alpha2`, `iso_alpha3`, `iso_assignment_status`, `localization_status` and `entity_type_status`.
- `country_names` stores names separately, linked by `game_id`, with `language`, `name` and `name_type`.
- `country_sources` stores provider crosswalks using `game_id`, `dataset`, `source_id`, `is_current` and `import_id`; names are not stored in this table.

WBG identity audit findings:
- No `country_sources` row exists for source ID `WBG`.
- No `imf_weo_historical_observations` row exists for source country code `WBG`.
- A canonical country record exists with ISO alpha-3 `PSE`, but `iso_assignment_status='unverified'`, `entity_type='unreviewed'` and `record_status='approved'`. The `country_names` search for “West Bank” returned no matching name row.
- These facts do not establish that WBG maps to the PSE identity. Do not create or infer the mapping from the ISO code, display name or geography alone. Keep the 32 WBG values in an identity-review hold until authoritative identity evidence and an explicit owner decision are recorded.

The first corrected crosswalk audit attempt failed because it assumed `countries.name`; that column does not exist. The schema above is the verified contract for future read-only identity queries. The corrected schema inspection completed with SQLite integrity `ok` and zero foreign-key violations. The earlier field-15 value reconciliation also completed with integrity `ok` and zero foreign-key violations.

These are diagnostic/reconciliation findings only. They do not constitute semantic approval, identity approval, field approval, or a Game DB write. Field 15 remains open; do not proceed to field 16.

## 11. Relationship to existing project contracts

- Persistent `game_id` remains the internal identity; provider identifiers are crosswalk attributes.
- `config/wp1_5_data_sources.json` and `config/data_sources.json` remain authoritative for field and source contracts.
- `config/source_selection.json` remains authoritative for source priority; this workflow does not silently change it.
- The WP1.5 normalized observation/import contract and shared approval engine remain authoritative.
- Existing source-specific assessments are evidence, not approval artifacts.
