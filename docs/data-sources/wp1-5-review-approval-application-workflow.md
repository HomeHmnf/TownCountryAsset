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

## 11. Relationship to existing project contracts

- Persistent `game_id` remains the internal identity; provider identifiers are crosswalk attributes.
- `config/wp1_5_data_sources.json` and `config/data_sources.json` remain authoritative for field and source contracts.
- `config/source_selection.json` remains authoritative for source priority; this workflow does not silently change it.
- The WP1.5 normalized observation/import contract and shared approval engine remain authoritative.
- Existing source-specific assessments are evidence, not approval artifacts.

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


## 13. Field-15 WBG identity evidence update — 2026-11-25

An authoritative review of the IMF October 2026 WEO Database Appendix and the existing project UN M49 reconciliation adds evidence relevant to the 32 unmatched WBG.NGDPD.A values. This is an evidence update, not an identity decision or approval.

### IMF WEO evidence

The official October 2026 appendix is published at:

https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf

Relevant appendix evidence:
- The WEO defines “country” and “economy” broadly; the terms do not always mean a state under international law. The database also maintains separate statistical data for some territorial entities (page 3).
- “West Bank and Gaza” is listed under Emerging and Developing Economies and under Middle East and Central Asia (pages 6 and 8). It is therefore an individual WEO economy entry, not one of the composite country-group series.
- The Country Data Documentation table identifies code WBG, name “West Bank and Gaza”, currency “Israeli new shekel”, national-accounts historical data source NSO, latest actual annual data 2025, base year 2015, and SNA 2008 (page 14).
- The appendix notes that West Bank and Gaza data for 2022–23, previously excluded pending methodological adjustments, are included again; projections for 2024–29 are excluded due to uncertainty (page 19). This is a vintage-specific publication note and must not be used to infer the status of each field-15 annual value.

This evidence establishes the IMF meaning and statistical role of the WBG code. It does not, by itself, establish a project game_id mapping.

### Existing project UN M49 evidence

The project’s read-only UN M49 reconciliation snapshot records:
- registry identity game_id=tc_50c420df8b2c4c6eaae47d795f9a1ea2, display name Palestine, Natural Earth source ID PSX;
- M49 reference name State of Palestine, M49 code 275, alpha-2 PS, alpha-3 PSE;
- an explicit reviewed name-variant match from Palestine to State of Palestine, with alpha-3 agreement;
- no alpha-2 value currently recorded on the registry identity.

Snapshot provenance: retrieved 2026-11-01T06:40:27.732163Z; raw M49 SHA-256 b9048114f6e7f2abda83bf03d4263c9d7cd1bd7230e3d0461025ee7839a7a1fb; normalized reference SHA-256 7575550969de58be3909e0c2290478a4331c5c13be123a1043214c73de929b74. The matching policy used normalized English names and explicitly maintained variants, not fuzzy, code-only or source-ID matching. The M49 report is evidence, not approval; the registry’s PSE assignment remains unverified.

The current UN M49 reference is also publicly available at https://unstats.un.org/unsd/methodology/m49/overview and identifies State of Palestine as M49 275, ISO alpha-2 PS, ISO alpha-3 PSE.

### Field-15 disposition

The combined evidence makes the existing Palestine game_id a strong candidate for an IMF WBG crosswalk, but no direct IMF-to-M49 concordance has been recorded in the project. The labels and statistical scope are consistent enough to propose that mapping for owner review; they are not permission to infer or write it automatically.

Until the owner explicitly decides:
- retain all 32 nonblank WBG field-15 values (1994–2025) in an identity-review hold;
- do not classify WBG as an aggregate or silently exclude it;
- do not create a country_sources mapping, change the identity registry, or write WBG observations to the Game DB;
- do not change the PSE ISO verification state as a side effect of the field-15 review;
- record the IMF appendix, M49 snapshot and exact proposed target game_id in the field-15 evidence register.

A future owner-approved crosswalk must be explicit, source-keyed (imf_weo / WBG), target the persistent game_id, retain both provider and M49 evidence, and be included in the exact candidate fingerprint and approval dependencies. This field-specific decision does not settle any other WEO field or any broader geopolitical/catalogue policy.


## 14. Owner decision — IMF WEO WBG source crosswalk — 2026-11-25

The project owner explicitly approved the following field-specific source crosswalk:

- Source key: `imf_weo`
- Provider code: `WBG` (IMF October 2026 WEO name: West Bank and Gaza)
- Target persistent identity: `tc_50c420df8b2c4c6eaae47d795f9a1ea2` (registry display name: Palestine)
- Match method: `reviewed_manual`
- Scope: WP1.5 field 15 / IMF indicator `NGDPD` only for this sequential application.
- Crosswalk artifact: `data/manual/source_crosswalks/imf_weo.json`

The crosswalk is provider-specific and fingerprinted as a candidate input. It does not change the identity registry, ISO alpha-2/alpha-3 assignments, PSE verification status, Natural Earth mapping, WDI mapping, or any other provider crosswalk. It does not authorize field 16/18/20/21 application. The 13 non-country aggregate series remain excluded from country observations with explicit review dispositions; they are not mapped to a game identity.

The WBG mapping restores the 32 source-populated field-15 observations to the candidate observation set. No Game DB write, approval record, or observation status classification is performed by this decision or by the candidate builder.


## 15. Field-15 crosswalk and field-scoped review tooling — 2026-11-25

The owner-approved IMF WEO crosswalk is stored separately from the global identity registry at `data/manual/source_crosswalks/imf_weo.json`. It contains one reviewed-manual mapping, source key `imf_weo`, source code `WBG`, and target `game_id=tc_50c420df8b2c4c6eaae47d795f9a1ea2`. Its approval scope is field 15 only. The global identity registry was not edited; the Palestine record's ISO alpha-3 `PSE` verification state remains unchanged.

The IMF WEO candidate builder now:
- accepts the explicit crosswalk through `--crosswalk` (defaulting to the approved file);
- validates the crosswalk against the existing identity registry and rejects conflicts;
- accepts repeatable `--field-id` arguments, with unsupported field IDs rejected;
- records the crosswalk path and SHA-256 plus selected field IDs in `candidate.json`.

The IMF WEO importer now requires the same crosswalk path and SHA-256 at candidate validation time and includes the crosswalk file in the exact application artifact inputs and metadata. A changed crosswalk therefore invalidates the candidate's approval fingerprint. The importer also checks that declared field scope covers every observation row.

The consolidated WEO–WDI review-package builder now supports repeatable `--field-id` filtering and records the actual field scope in its package summary. This allows a field-15-only review package to be built from the Stage 4C semantic matrix without including fields 16, 18, 20 or 21.

Regression coverage was added for explicit WBG mapping, field-15 filtering, unsupported field IDs, importer crosswalk fingerprint enforcement, and field-scoped review packages. These tests have been authored but have not yet been executed in the owner's local environment. No candidate has yet been generated from the local IMF CSV, no review decisions have been recorded, and no approval/application or database write has occurred.

Owner-side read-only candidate command after syncing this branch:

```fish
uv run python -m tools.build_imf_weo_historical_candidate --field-id 15
```

The resulting candidate must be checked for exactly 9,361 finite numeric observations (9,329 previously reconciled country observations plus the 32 owner-approved WBG observations), with all 13 aggregate series retained as explicit identity exceptions and no field IDs other than 15. The expected observation total is an acceptance target to verify, not an assertion that generation has already succeeded.

A field-15-only review package can then be built from the local Stage 4C matrix:

```fish
uv run python -m tools.build_imf_weo_wdi_review_package --input reports/sources/imf-wdi-semantic-disposition/20261107T145725Z/semantic_disposition_matrix.csv --field-id 15
```

The resulting package must be reconciled to the candidate and its explicit crosswalk before any decisions are made. The field-15 package is review-only; the separate importer approval gate remains mandatory.


## 16. Field-15 aggregate exclusion register — 2026-11-25

The owner approved the explicit `excluded` disposition for all 13 unmapped IMF aggregate and regional series. These are global, regional or economic-group aggregates, not individual country identities in the game catalogue. They must not be mapped to country `game_id` values.

The shared rationale recorded in the exclusion register is:

> IMF regional, economic-group and global aggregates are outside the country-level game identity universe. Their populated observations are retained in source evidence but excluded from country-level field 15 candidate application.

The register is:
`reports/sources/imf-weo-historical-candidate/20261125T152006Z/field_15_exclusion_register.csv`

It records 13 series and 665 populated annual observations. Twelve series contain 52 populated years each; G163 (Euro Area) contains 41 populated years, 1991–2031. All 13 rows have disposition `excluded`.

The 13 source codes are G001, G110, G119, G163, G200, G205, G400, G505, G510, G603, G903, G998 and GX123. The register retains each source name, series code, populated-year count, year range, latest-actual metadata and source SHA-256.

The field-15 candidate generated at
`reports/sources/imf-weo-historical-candidate/20261125T152006Z/`
contains 9,361 observations for NGDPD, across 197 distinct game identities, covering 1980–2031. Its 13 identity exceptions correspond to the aggregate series explicitly covered by the exclusion register. The candidate metadata records `database_written: false` and `approval_created: false`.

The 32 WBG observations are included through the separately owner-approved, field-15-only IMF crosswalk. They are not part of the aggregate exclusions.

This is a source-row disposition and candidate-reconciliation update only. It is not semantic approval, field approval, an application authorization or a database write. Field 15 remains open pending the complete review, approval, application and independent verification workflow. Fields 16, 18, 20 and 21 remain outside this field-scoped decision.


## 18. Owner decision — IMF WEO KOS source crosswalk — 2026-11-26

The project owner explicitly approved a second provider-specific identity mapping for the October 2026 IMF WEO field-15 candidate:

- Source key: `imf_weo`
- WEO source code: `KOS` (source name identifies Kosovo)
- Target persistent identity: `tc_28aa17b84db24952b92fc51b421075e0` (the existing Kosovo registry/Game DB identity)
- Match method: `reviewed_manual`
- Scope: IMF WEO October 2026, NGDPD, WP1.5 field 15 only.
- Crosswalk artifact: `data/manual/source_crosswalks/imf_weo.json`

### Evidence and qualification

The WEO CSV uses source code `KOS`, while the October 2026 IMF Appendix Country Data Documentation identifies Kosovo with code `UVK`. The target persistent game_id is present in both identity stores, but their review states must be distinguished. The canonical registry record names Kosovo and records source/geometry key KOS; its registry status is `proposed`, `entity_type` is `unreviewed`, and ISO assignment status is `unverified`. The separate Game DB `countries` record for the same game_id has `record_status='approved'`, `entity_type='disputed_or_partially_recognized_entity'`, and `entity_type_status='reviewed'`; its ISO alpha-2 and alpha-3 values are null. The owner-approved IMF WEO crosswalk is provider-specific and does not promote or modify the canonical registry record or global identity attributes.

The UN M49 FAQ's statistical-use numerical code 412 is relevant statistical context, but it does not itself establish an IMF KOS-to-UVK code concordance. The owner decision is therefore an explicit provider-specific crosswalk based on the source identity and project identity evidence, with the IMF Appendix code discrepancy retained as a qualification. It is not an ISO assignment or a geopolitical/legal determination.

### Limits and legacy observations

- This mapping applies only to `imf_weo / KOS`, October 2026 NGDPD, field 15.
- Do not change the canonical identity registry, Game DB identity record, ISO assignments, M49 assignments, or any other provider crosswalk as a consequence.
- Preserve the 32 existing KOS observations for 2000–2031. Their existing values and provenance must be checked against the rebuilt candidate exactly; this decision does not authorize deletion, remapping, overwriting, or status classification.
- The mapping must be included in the exact candidate and approval fingerprints. The prior `hold_for_evidence` disposition for KOS is superseded for this field-15 source only.
- No database application is authorized merely by recording this identity decision. The normal explicit application approval, safe backup, compatibility preflight, transactional import and independent verification remain mandatory.

This decision resolves the provider-specific identity disposition for KOS in field 15. It does not close field 15 or authorize field 16/18/20/21.

## 17. Consolidated IMF WEO field-15 owner review

The ten source-derived identity batches are consolidated into one owner-review Markdown file and one explicit application CLI. Follow [the field-15 owner review workflow](imf-weo-field15-owner-review-workflow.md). The review document is generated from the automatic final register, not the historical manual batches. It carries forward the existing WBG and KOS field-15-only approvals and 13 aggregate exclusions (665 values). KOS/UVK is documented as a source-code discrepancy; no ISO/M49 assignment changes. Use `tools/approve_imf_weo_field15_all.py` to bulk approve the 195 new proposals. Dry-run is the default; `--prepare-only --confirm-all-proposals` builds the candidate and runs read-only identity/value/provenance preflight, including exact reconciliation of the 32 legacy KOS rows, without a database approval or database writes. Only after inspecting that report and creating a verified SQLite online backup should `--apply --confirm-all-proposals` be run. The command creates a separate fingerprint-bound approval copy and reuses the existing WEO application ledger/importer. Generation and dry-run validation do not write to either database.


## 19. Field-15 identity approval and application result — 2026-11-26

The owner-approved IMF WEO October 2026 NGDPD field-15 identity review and application completed successfully. The immutable verification report is:

`reports/sources/imf-weo-field15-reviewed-candidate/656073575edb005a/verification_report.json`

Application approval ID: `imf-weo-oct2026-1eb2e784bf93821c` (status `applied`). The approved review contains 195 newly approved source-derived mappings. The previously approved WBG and KOS provider-specific crosswalk decisions were reused, as were the 13 aggregate exclusions covering 665 populated source values.

The candidate contains 9,361 NGDPD observations across 197 game identities, with 13 explicit aggregate exceptions. The Game DB verification reports 9,361 actual observations, 32 inserted and 9,329 unchanged. The existing-row preflight found no rows outside the candidate. All 197 candidate game IDs were present in the canonical identity store. SQLite integrity and foreign-key checks passed; approval events are `proposed`, `approved`, and `applied`.

The 32 pre-existing KOS observations were reconciled as part of the successful preflight and application. No observation rows were deleted, remapped or overwritten. The original IMF WEO crosswalk and canonical identity registry were not modified.

Project DB acquisition ID 5 was independently verified: both recorded source artifacts matched their byte counts and SHA-256 fingerprints, and Project DB SQLite integrity and foreign-key checks passed. The Project DB remains the acquisition/provenance ledger; observation rows reside in the Game DB, not duplicated in the Project DB. No Project DB write was performed by this application.

All observation statuses remain `unclassified`, and the dataset import ledger remains `candidate`; the field-scoped application approval is `applied`. This establishes completion of the field-15 identity-review, candidate-approval, application and technical-verification stages. It does not establish semantic classification of the observations. Do not advance to field 16 until any separately required field-level semantic review and closure documentation are complete.



## 20. Independent local field-15 database presence check — 2026-11-26

The project owner ran the read-only SQLite verification command against the local canonical Game DB after synchronizing the documentation and application result. The returned result was **PASS**.

Verified directly in the database:

- 9,361 field-15 / NGDPD observations.
- 197 distinct game IDs and 197 distinct IMF source-country codes.
- Observation-year range 1980–2031.
- Zero observations with a status other than `unclassified`.
- Zero source-checksum mismatches.
- Exactly one dataset import ID (3).
- Application approval `imf-weo-oct2026-1eb2e784bf93821c` has status `applied`.
- Dataset import ID 3 remains `candidate`.
- SQLite `integrity_check=ok`; zero foreign-key violations.

All eleven command checks returned true. This independently confirms that the expected field-15 observation rows exist in the local Game DB and that their recorded provenance and database integrity checks pass. It does not semantically classify the observations or change the dataset import status. The field-15 semantic review/closure gate remains outstanding; field 16 must not start until that gate is satisfied and documented.
