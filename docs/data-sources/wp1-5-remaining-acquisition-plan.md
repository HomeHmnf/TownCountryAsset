# WP1.5 remaining acquisition and application plan

**Status:** active field-by-field execution plan; governed by the [WP1.5 review, approval and database application workflow](wp1-5-review-approval-application-workflow.md).  
**Last reviewed:** 2026-11-27.

## Completion rule

The unit of completion is one WP1.5 field, not a provider batch or a diagnostic report. Work on fields sequentially. Do not start the next field until the current field has completed source verification/acquisition, normalization, semantic and identity review, approval, Project/source database registration, Game database application, independent verification of both databases, and its durable documentation record.

For every field, explicitly account for the full project identity universe. Each identity must have an evidence-backed disposition: imported value, unavailable, not applicable, excluded with rationale, or held for specific evidence. A field may be closed with documented gaps; it may not be called complete while identities or source rows are silently omitted. Never invent values, infer observation status, or treat an absent row as zero.

The Project/source database and Game database have separate responsibilities. Source bytes, manifests, releases, acquisition events and artifact provenance must be present and verified in the Project/source database. Approved game-facing observations, source references and import linkage must be present and verified in the Game database. A successful write to one database does not imply completion in the other.

## Completed

- UN WPP fields 1, 2, 6, 12, 13 and 14 were previously applied; their field-level evidence and database state remain subject to the final completeness reconciliation.
- World Bank WDI fields 3, 33 and 34 were applied and independently owner-verified on 2026-11-25: approval `wp1-5-wdi-20261125-regenerated` (actor `project-owner`), import ID `4`, 561 scalar observations and 187 crosswalk mappings. The approval ledger is `applied`; persisted rows, SQLite integrity and foreign keys were independently checked. See the [application record](world-bank-wdi-wp1-5-application.md).
- IMF WEO October 2026 source capture and Project DB acquisition registration (acquisition ID `5`) exist. This establishes source acquisition/provenance only; it does not close any WEO field.

## Execution order — one field at a time

1. **Field 15 — GDP (IMF WEO, indicator NGDPD).** Closed on 2026-11-27; see the final closeout below. Reuse the captured October 2026 WEO CSV and Database Appendix and existing Project DB acquisition ID 5. Verify the exact source artifacts and Project DB records; inspect the field-15 candidate rows, country identities, unit/currency/scale, annual reporting periods, latest-actual metadata and WDI comparison. Resolve every field-15 identity and semantic edge case. Create a field-15-only review/decision package and normalized candidate, validate and fingerprint it, obtain owner approval, then verify the source database and apply the approved candidate to the Game DB. Independently verify both databases and record all imported, held, excluded, unavailable and not-applicable cases before closing field 15.
2. **Field 16 — GDP per capita (IMF WEO, NGDPDPC).** Start only after field 15 is closed. Explicitly review denominator population universe, currency/scale, period and status.
3. **Field 18 — GDP PPP (IMF WEO, PPPGDP).** Start only after field 16 is closed. Resolve PPP benchmark/factor construction and status metadata without inference.
4. **Field 20 — Inflation (IMF WEO, PCPIPCH).** Start only after field 18 is closed. Resolve annual-average versus end-period and calendar/fiscal reporting periods.
5. **Field 21 — Unemployment (IMF WEO, LUR).** Start only after field 20 is closed. Resolve unit, labour-force population, definition, reference period and country-specific comparability; preserve settled Bahrain findings unless new evidence justifies reopening.
6. **Field 22 — Labour force (ILOSTAT).** Inspect existing captures and Project DB records first; acquire immutable bytes only if the required source data are absent or invalid. Confirm indicator, age/sex scope, unit, annual aggregation, status and coverage.
7. **All other contracted fields.** Continue in the order recorded in `config/wp1_5_data_sources.json`, one field at a time. Where a provider acquisition covers multiple fields, register the acquisition once, but keep each field's review, approval, application and closure distinct.

## Per-field closeout checklist

- [ ] Primary source and exact indicator/dataset definition confirmed against the field contract.
- [ ] Exact release/vintage and immutable source bytes verified; manifest includes URL, retrieval date/time precision, release, byte count and SHA-256.
- [ ] Source acquisition and all relevant artifacts registered and independently verified in the Project/source database.
- [ ] Candidate normalized with explicit provider IDs, persistent `game_id` crosswalk, unit/scale, reference period, status and methodology.
- [ ] Full identity/coverage register accounts for every expected game identity and every source row; unresolved cases remain explicit.
- [ ] Field-specific semantic review and linked edge-case decisions complete; no blank decisions treated as approval.
- [ ] Exact candidate and dependencies validated and fingerprinted; owner approval recorded against those hashes.
- [ ] Approved observations applied transactionally to the Game DB; no source policy change or release promotion occurs implicitly.
- [ ] Independent read-only verification confirms expected Game DB values, source references, import linkage, counts, duplicates/conflicts, SQLite integrity and foreign keys.
- [ ] Independent Project DB verification confirms acquisition/artifact identities, hashes, registration state and database integrity/foreign keys.
- [ ] Field-specific implementation record and this plan updated with evidence, counts, gaps, approval ID, import/application IDs and commit.
- [ ] Only then mark the field complete and begin the next field.

## Current gate

**Field 15 is closed; field 16 is the sole active field.** The field-15 application and semantic-status verification are recorded below. Continue with field 16 only; do not reopen field 15 or begin fields 18, 20 or 21. Reuse Project DB acquisition ID 5 after fresh read-only source/artifact verification.

The combined canonical Game DB remains the active target for this phase. Do not begin the future Game DB/Project DB separation cutover during this work; verify the existing Project/source database and combined Game DB independently under their current contracts.

### Field 15 audit update — 2026-11-25

The IMF WEO `NGDPD` source has 210 country/area series and 10,026 nonblank annual values. The existing canonical Game DB has 9,329 matching observations; matched values and compared metadata reconcile with zero mismatches and no extra database keys. The 697 absent source keys comprise 624 values across 12 aggregate/regional series, 41 Euro Area aggregate values (`G163`), and 32 West Bank and Gaza values (`WBG`, 1994–2025).

The 665 aggregate/regional values must be explicitly dispositioned as non-country series in the field-15 review package, rather than silently omitted. The 32 WBG values remain an identity-review hold. The canonical database contains a `PSE` ISO alpha-3 identity, but its ISO assignment is unverified; there is no `WBG` row in `country_sources`, no WBG historical observation, and no “West Bank” name match in `country_names`. Do not map WBG to PSE without authoritative evidence and an explicit decision.

Schema note for future audits: `countries` contains identity/ISO state but no name column; `country_names` stores names by `game_id`; `country_sources` stores provider crosswalk attributes (`dataset`, `source_id`, `is_current`, `import_id`). The earlier audit's attempted `countries.name` reference was invalid; the schema inspection established these actual columns. Both completed read-only integrity checks reported SQLite `ok` and zero foreign-key violations.

This evidence does not approve field 15 or authorize a write. The field-15-only identity and semantic review, full explicit disposition register, approval, dual-database verification and documentation remain outstanding. Field 16 remains blocked.

## Owner-run validation and evidence

The owner runs local tests and database commands. Record exact commands, counts, approval IDs, artifact fingerprints, Project DB acquisition/artifact IDs, Game DB import/application IDs, integrity results and commit references only after receiving the output. Repository documentation or code changes alone do not establish successful local acquisition or database application.


### Field 15 WBG identity evidence update — 2026-11-25

The 32 unmatched nonblank WBG.NGDPD.A values (1994–2025) now have additional authoritative context. The official October 2026 IMF WEO Database Appendix:
- lists West Bank and Gaza as an individual economy within Emerging and Developing Economies and Middle East and Central Asia (pages 6 and 8);
- defines the WEO use of “country/economy” to include some separately maintained territorial statistical entities that are not states under international law (page 3);
- identifies WBG as West Bank and Gaza in the country-data documentation, with Israeli new shekel, NSO historical data, latest actual annual data 2025, 2015 base year and SNA 2008 (page 14);
- notes that 2022–23 data previously excluded pending methodological adjustments are included again, while projections for 2024–29 are excluded due to uncertainty (page 19). This note is not an observation-level status classifier.

Official appendix: https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf

The existing project UN M49 snapshot explicitly matched the registry display name Palestine to M49 formal name State of Palestine (M49 275, ISO PS/PSE) using a reviewed name variant; alpha-3 agrees. The matched registry record is game_id=tc_50c420df8b2c4c6eaae47d795f9a1ea2, Natural Earth source ID PSX. M49 snapshot provenance is in reports/database/town_country_asset/identity/m49-current/; the registry PSE status remains unverified.

This makes that persistent identity a strong candidate for an IMF WBG crosswalk, but no direct IMF-to-M49 concordance is recorded. The owner must explicitly decide the mapping. Until then, all 32 values remain held for identity evidence: no aggregate exclusion, no inferred mapping, no country_sources write, no registry edit, and no Game DB write. The evidence and proposed target game_id must be included in the field-15 review register. Do not alter the PSE ISO verification state as a side effect.

Field 15 remains open; fields 16 onward remain blocked.


### Field 15 WBG crosswalk owner approval — 2026-11-25

The project owner approved the exact IMF-specific mapping: `imf_weo / WBG` → `tc_50c420df8b2c4c6eaae47d795f9a1ea2` (Palestine registry identity). It is recorded in `data/manual/source_crosswalks/imf_weo.json`, with the IMF October 2026 appendix evidence and the existing reviewed UN M49 name-variant reconciliation. Scope is limited to field 15 (`NGDPD`) in the current sequential pass. This does not alter the identity registry or PSE verification status, nor authorize the other WEO fields.

The candidate builder/importer will treat the crosswalk file as an exact hashed input. The field-15 candidate must contain the 32 WBG observations; the 13 aggregate series remain explicit non-country review exceptions. No DB write or approval has been performed.


### Field-15 implementation update — 2026-11-25

The owner-approved `imf_weo / WBG` → Palestine `game_id` crosswalk is now in `data/manual/source_crosswalks/imf_weo.json`, separate from the global identity registry. The IMF candidate builder accepts the crosswalk, hashes it into candidate metadata, and supports a field-15-only build. The approval importer verifies the crosswalk hash and includes the file as an application artifact dependency. The WEO–WDI review-package builder now accepts `--field-id 15` to avoid mixing fields in the review surface.

Regression tests were added for the mapping, field scoping, unsupported field IDs, and importer fingerprint checks; they remain unexecuted until the owner syncs and runs them locally. No local IMF candidate or field-15 review package has yet been generated; no database, approval or observation data has been written.

After syncing, build the field-15 candidate with:

```fish
uv run python -m tools.build_imf_weo_historical_candidate --field-id 15
```

Expected acceptance check: 9,361 observations (9,329 previously reconciled country observations plus 32 WBG values), only field 15, and all 13 aggregate series represented as identity exceptions. Verify rather than assume these counts.

Then build the field-scoped review package from the existing Stage 4C semantic matrix:

```fish
uv run python -m tools.build_imf_weo_wdi_review_package --input reports/sources/imf-wdi-semantic-disposition/20261107T145725Z/semantic_disposition_matrix.csv --field-id 15
```

Reconcile that package against the new candidate and crosswalk before entering review decisions. Field 15 remains open; fields 16 onward remain blocked.


### Field 15 aggregate dispositions and candidate build — 2026-11-25

The owner approved `excluded` for all 13 IMF aggregate and regional NGDPD series. The explicit register is:

`reports/sources/imf-weo-historical-candidate/20261125T152006Z/field_15_exclusion_register.csv`

It accounts for 665 populated annual source observations across 13 series. Twelve series have 52 populated years each; G163 (Euro Area) has 41 populated years, 1991–2031. The excluded source codes are G001, G110, G119, G163, G200, G205, G400, G505, G510, G603, G903, G998 and GX123. The register records source names, series codes, year coverage, latest-actual metadata, disposition and rationale.

The common rationale is that IMF regional, economic-group and global aggregates are outside the country-level game identity universe. They remain represented in source evidence and are excluded from country-level field 15 application. They are not country identities and must not be mapped to game IDs.

The field-15-only candidate was successfully built at:
`reports/sources/imf-weo-historical-candidate/20261125T152006Z/`

Verified candidate metadata:
- 9,361 NGDPD observations.
- 197 distinct game IDs.
- Year range 1980–2031.
- 13 identity exceptions, corresponding to the aggregate codes in the exclusion register.
- Source SHA-256: `a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d`.
- Crosswalk SHA-256: `df72a50e9fd37cbc05088a074367be05e3e067194b932997f7e7ec95589f91a9`.
- Candidate observation SHA-256: `47d8e3ac053eb0842e632ba71aaca02dc76fe780d9665ee431ab775dfcb9f76d`.
- Candidate exception SHA-256: `b35a2984fd5704fa3c47fed01e067b9baed16e8c8785a1ca4218938c3d1c148e`.
- `database_written=false`; `approval_created=false`.

The 32 WBG observations are included under the owner-approved IMF-specific field-15 crosswalk and are not excluded as aggregates. The earlier WBG identity hold is superseded by that explicit owner decision.

**Current gate:** aggregate dispositions and candidate construction are complete. Field 15 is not yet approved or applied. The field-15 semantic review must still be reconciled against the candidate, crosswalk and exclusion register. Approval, application and independent verification of both databases remain outstanding. Field 16 remains blocked.


## Field 15 current status — 2026-11-26

This status supersedes the earlier "Current gate" and audit statements above where they describe field 15 as not yet approved or applied.

The IMF WEO October 2026 NGDPD / field-15 identity review, owner approval, Game DB application and technical verification have completed. The owner-approved application is `imf-weo-oct2026-1eb2e784bf93821c` (`applied`). The local read-only database check returned **PASS**: 9,361 observations, 197 game IDs, 197 source codes, years 1980–2031, zero non-`unclassified` statuses, zero checksum mismatches, one import ID (3), dataset import status `candidate`, SQLite integrity `ok`, and zero foreign-key violations. See the [shared application workflow](wp1-5-review-approval-application-workflow.md) for the recorded verification.

**Field 15 is not yet closed.** The database check confirms row presence and technical integrity; it does not satisfy the field-specific semantic review and closure checklist. In particular, observation statuses remain `unclassified`, and the dataset import remains `candidate`. Therefore field 16 remains blocked. The next action is to complete and document field-15 semantic classification and the remaining per-field closeout requirements; do not begin field-16 acquisition or application before that gate passes.


### Field 15 semantic audit update — 2026-11-27

The owner ran a read-only full-coverage audit of IMF WEO October 2026 `NGDPD.A` against all 197 individual source series and reported **9,361 / 9,361** populated observations accounted for: 8,168 proposed `observed`, 1,193 proposed `estimated`, 178 integer-metadata series, 19 fiscal-year metadata series (861 observations), zero unresolved series, and no database writes. Fiscal-year labels were interpreted by ending year and reconciled against the October 2026 WEO Database Appendix country documentation.

### Field 15 semantic proposal build — 2026-11-27

The owner ran the read-only semantic proposal builder twice; both runs returned identical complete results. The generated artifact package was committed in `7e064a4` at `reports/sources/imf-weo-field15-semantic-review/20261127T152134Z/`. It contains 9,361 proposed classifications across 197 individual series: 8,168 `observed`, 1,193 `estimated`, zero unresolved, and zero `projected`. The 13 aggregate series / 665 populated values remain excluded under the existing owner-approved dispositions. The raw source, candidate observations and proposal fingerprints are recorded in `summary.json`; proposal SHA-256 is `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`. Both runs reported `database_written=false` and `approval_created=false`.

The initial focused test run exposed five failures, including the fiscal-year parser escaping defect. The parser fix was committed in `ec38d21`; the post-fix test result still needs to be recorded. The complete proposal CSV also remains subject to detailed artifact review and explicit owner semantic approval. Canonical statuses remain `unclassified`; field 15 is open and field 16 remains blocked.


The read-only proposal builder and focused tests are now in:
- `tools/build_imf_weo_field15_semantic_review.py`
- `tests/test_imf_weo_field15_semantic_review.py`
- [Field-15 semantic review record](imf-weo-field15-semantic-review.md)

These are implementation artifacts only. Their local tests and builder execution remain pending owner-run validation. All canonical field-15 statuses remain `unclassified`; the 8,168 / 1,193 split is a proposal, not an approved database state. No status application has been authorized or performed. Field 15 remains open and field 16 remains blocked.


### Field 15 semantic validation gate update — 2026-11-27

This update supersedes the earlier statements above that the post-fix semantic tests and full proposal CSV audit were still pending.

The owner reports the focused semantic-review suite passed (**12 passed in 0.03s**). A read-only audit of the complete committed proposal CSV also returned **PASS**: the file SHA-256 matches the recorded proposal fingerprint; all 9,361 rows have unique source-code/year keys across 197 series; the year range is 1980–2031; proposed counts are 8,168 `observed` and 1,193 `estimated`; the rule counts are 178 integer-cutoff and 19 fiscal-year-ending-year series; every status agrees with its cutoff; and every current status remains `unclassified`.

These checks validate implementation and artifact integrity. They do not constitute semantic owner approval and have not changed the canonical database. The next gate is the owner's explicit decision on the semantic convention and exact proposal SHA-256 `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`. Only after approval may a separate guarded status-application workflow be designed and run with explicit authorization, backup/preflight and independent post-write verification.

**Field 15 remains open; field 16 remains blocked.** Do not change any observation status or begin field 16 at this stage.


### Field 15 semantic owner approval — 2026-11-27

The project owner explicitly approved the semantic classification convention and the exact 9,361-row proposal. The immutable decision record is `reports/sources/imf-weo-field15-semantic-review/20261127T152134Z/owner_semantic_approval.md`, bound to proposal SHA-256 `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`. Approved counts are 8,168 `observed` and 1,193 `estimated`; no `projected` statuses are inferred.

This semantic approval is not authorization for a database status write. The existing 9,361 Game DB observations remain `unclassified`. A separate fingerprint-bound application workflow, fresh verified backup, read-only preflight, explicit application authorization, transactional update and independent post-write verification are still required. Field 15 remains open and field 16 remains blocked.


### Field 15 guarded semantic application tooling — 2026-11-27

A separate fingerprint-bound application tool and focused tests have been added: `tools/apply_imf_weo_field15_semantic_status.py` and `tests/test_apply_imf_weo_field15_semantic_status.py`. The default command is read-only and validates the exact owner-approved proposal, approval record, every target Game DB row, current `unclassified` status, dataset-import candidate status, SQLite integrity and foreign keys. The explicit write path requires `--apply`, a separate confirmation flag, actor/note, and a fresh verified backup path plus SHA-256. It updates only the field-15 `value_status` values and records the application event transactionally.

The new tool and tests have not yet been executed locally. The owner must sync, run the focused tests and read-only preflight, and report results. No status write has been authorized or performed. Field 15 remains open; field 16 remains blocked.


### Field 15 semantic status application and backup automation — 2026-11-27

The owner-approved IMF WEO October 2026 NGDPD semantic proposal has now been applied to the canonical Game DB. The guarded transaction updated all 9,361 target observations: 8,168 `observed` and 1,193 `estimated`. Application approval ID: `imf-weo-field15-sem-28e8b9c1afd983e4`. Dataset import status remains `candidate`; SQLite integrity is `ok` and foreign-key violations are zero. The pre-application backup was verified at 28,688,384 bytes with SHA-256 `36702add308d50071bb683ecb7d3a2bb626d2ba99b85f036b3bea8b240e2c3cb`.

Reusable SQLite backup automation is now provided by `tools/database/backup.py` and `tools/backup_database.py`; focused tests are in `tests/test_database_backup.py`. The standalone command `uv run python tools/backup_database.py` creates a timestamped online backup, refuses overwrite, verifies integrity and foreign keys, and prints its SHA-256. The field-15 guarded application CLI also accepts `--create-backup`; it creates the backup, calculates the checksum, and passes that checksum directly to its existing backup-verification gate before application. Do not rerun the field-15 one-shot application after its successful completion.

The owner's next action is to run the new backup-helper tests and the independent read-only post-application verification. Field 15 remains open until those checks and closeout documentation are complete. Field 16 remains blocked.


## Field-15 final closeout and field-16 gate — 2026-11-27

Field 15 (IMF WEO October 2026, `NGDPD.A`) is **closed**. The owner completed semantic application and independent post-application verification. The final Game DB audit returned **PASS**: 9,361 observations; 197 game IDs; 197 source codes; 1980–2031; 8,168 `observed`; 1,193 `estimated`; no other statuses; no malformed checksum values; one matching dataset-import record remaining `candidate`; SQLite integrity `ok`; zero foreign-key violations. The audit was read-only. Backup-helper and semantic-application regression tests passed (**8 passed in 0.08s**). Application approval ID: `imf-weo-field15-sem-28e8b9c1afd983e4`; approved proposal SHA-256: `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`.

The Project/source DB remains the acquisition/provenance ledger and the Game DB remains the observation store; these roles are not duplicated. The October 2026 WEO acquisition (Project DB acquisition ID 5) already contains the raw CSV and appendix used for field 15. Field 16 uses the same provider release and raw CSV, so **do not reacquire** if the existing source artifacts and acquisition registration pass a fresh read-only verification.

### Field 16 — GDP per capita (IMF WEO, NGDPDPC)

**Identity-scope hardening:** the existing WBG and KOS crosswalk decisions are approved for field 15 only. The candidate builder now resolves crosswalk mappings by field ID and source code. A mapping without an explicit field_ids list defaults to field 15, matching the existing owner approval; any future broader mapping must carry an explicit field list and separate owner approval. This prevents field-15 approvals from leaking into field 16 or an unfiltered multi-field build. Regression tests cover field-15 retention, field-16 holds and multi-field behavior.

**Field-16 identity review preparation:** the first regenerated field-16 candidate correctly contains zero observations and 197 unresolved source identities. Its immutable diagnostic package is `reports/sources/imf-weo-historical-candidate/20261127T180903Z/` (candidate SHA-256 is recorded in its manifest); it is retained as evidence and is not an import candidate. A read-only comparison against the 242-record registry found 195 unique exact `current_source_id` matches and two unmatched codes: SSD and WBG. All 195 matched registry records are currently `proposed`, not approved. KOS is among the 195 and must receive a new field-16-specific decision; the field-15 KOS approval is not reusable.

The prepare-only generator `tools/build_imf_weo_field16_identity_review.py` creates ten review batches (20 rows each for batches 1–9, 15 rows in batch 10), with source names and populated-year coverage from the fingerprinted IMF CSV. It records the exact candidate, registry and source fingerprints in `review_manifest.json`. It emits 195 proposals based solely on unique exact registry `current_source_id` matches, plus separate unresolved records for SSD and WBG. Every proposal begins as `PENDING`; `approved_game_id` is `-`; registry status and entity type are shown as review context, not treated as approval. WBG remains unresolved because its existing crosswalk approval is field-15-only. The generator refuses unexpected counts, duplicate source codes, changed candidate checksums, missing source rows or a registry other than the expected 242 records. It creates no owner approval, changes no crosswalk or registry, and writes neither database.

After syncing, run the focused tests:
```fish
uv run --extra dev python -m pytest -q tests/test_imf_weo_field16_identity_review.py
```
If they pass, generate the review package:
```fish
uv run python -m tools.build_imf_weo_field16_identity_review
```
Commit the generated package and provide its manifest and review CSVs for audit. Do not enter owner decisions until the proposal evidence and all 195 target identities have been checked. No approval validator/application or database-write path is included in this preparation step.

Field 16 is now the sole active field. Contract: scalar `current_usd_per_person`, primary source `imf_weo`; source indicator `NGDPDPC.A`. The existing candidate builder supports `--field-id 16`, and the source observation schema permits field 16 / indicator `NGDPDPC`.

The following gates apply before any Game DB application:

1. Verify Project DB acquisition ID 5 and the raw CSV / October 2026 Appendix bytes, recorded byte counts and SHA-256 values. Verify Project DB integrity and foreign keys. Reuse this acquisition; do not register duplicate acquisition events or reacquire unchanged bytes.
2. Build a **field-16-only** candidate from the original raw WEO CSV using `uv run python -m tools.build_imf_weo_historical_candidate --field-id 16`. This is candidate generation only and must not write either database.
3. Treat all reused IMF source-code-to-`game_id` mappings as **field-16 identity proposals**, not as automatically approved field-16 decisions. The existing WBG and KOS decisions and the 195 other identity approvals were explicitly scoped to field 15. Re-review the field-16 source identities against the canonical registry and evidence, preserve the existing source-code discrepancy qualifications, and obtain field-16-scoped owner decisions. Do not broaden the existing crosswalk approval scope or alter global identity/ISO assignments.
4. Audit every populated `NGDPDPC.A` source cell, source series, unit and scale, year coverage, reporting-year metadata, latest-actual metadata, duplicate keys and all 242 expected project identities. Record aggregates, unmapped identities, missing rows and unavailable/not-applicable cases explicitly.
5. Resolve the field-16 denominator/population universe and comparability semantics. Do not derive GDP per capita by dividing field 15 by a population series; use the IMF-published `NGDPDPC` values. Preserve source unit/scale and the October 2026 vintage. Do not infer `observed` / `estimated` / `projected` status from field-15 decisions without an independently reviewed field-16 rule.
6. Produce a field-16-only consolidated review package, immutable candidate fingerprint and field-scoped approval. No Game DB write is authorized by candidate generation or review.
7. Only after explicit owner authorization, use the guarded application workflow with a verified automatic backup, apply transactionally, then independently verify the Game DB and Project DB and update this plan and the field-specific record.

**Current boundary:** field 16 may proceed through source verification, candidate generation and review preparation. No field-16 identity approval, semantic approval, application, dataset-import promotion or database write is implied or authorized by closing field 15.


### Field-16 owner identity review workflow — 2026-11-27

The next-stage owner-review workflow is implemented in `tools/manage_imf_weo_field16_owner_review.py`. It consumes the committed 195-row proposal package at `reports/sources/imf-weo-field16-identity-review/20261127T181310Z/` and the exact fingerprinted 242-record identity registry. It does not change the original proposal package, registry, crosswalk or either database.

Build the editable owner-review package after syncing:

```fish
uv run --extra dev python -m pytest -q tests/test_imf_weo_field16_owner_review.py
uv run python -m tools.manage_imf_weo_field16_owner_review build
```

The generated package contains:
- `owner_review.csv`: editable owner decision surface, grouped into the original ten batches.
- `owner_review_baseline.csv`: immutable identity-evidence baseline used to detect edits to source IDs, proposed game IDs, names, registry metadata, flags or batch assignment.
- `owner_review_manifest.json`: fingerprints and counts for the input package, registry and review baseline.

Each row displays the IMF source name and series, proposed game ID, registry name and aliases, registry status/entity type, previous source IDs, ISO codes and assignment status, regions, geometry key, year coverage, name comparison and manual-review flags. Flags explicitly distinguish unapproved registry status, unreviewed entity type, source/registry name differences, unapproved ISO assignment and a curated territory/disputed-identity manual-review set. These are review prompts, not automatic rejections or approvals. In particular, an exact source-code match is not treated as sufficient evidence that a proposed game identity is correct.

The owner fills `owner_decision` with exactly `APPROVE`, `REJECT` or `HOLD`, supplies a rationale for every row, and for `APPROVE` supplies both the exact proposed game ID and a source/evidence reference. The immutable baseline prevents changes to identity evidence while decisions are entered.

After all 195 rows have explicit decisions, validate the completed file and emit a separate immutable decision-proposal artifact:

```fish
uv run python -m tools.manage_imf_weo_field16_owner_review validate --review-dir reports/sources/imf-weo-field16-owner-review/<generated_timestamp>
```

Validation rejects missing decisions, missing rationales, unsupported decisions, altered identity evidence, an approval targeting a different game ID, or an approval without an evidence reference. The output is explicitly a **decision proposal, not an approval record**. It creates no approval, changes no registry/crosswalk and writes neither database. Any subsequent formal approval and application must be a separately reviewed, field-16-scoped workflow with explicit owner authorization, verified backup/preflight and independent post-write checks.


### Field-16 owner-review history enrichment — 2026-11-27

The initial owner-review package exposed the canonical registry but omitted prior project source crosswalks and the explicit identity edge-case decisions. The review builder now incorporates read-only evidence from:

- `data/manual/source_crosswalks/world_bank_wdi_wp1_5_area.json` (owner-approved WDI crosswalk);
- `data/manual/source_crosswalks/un_wpp.json` (owner-approved UN WPP crosswalk, including its explicit Taiwan exception);
- `data/manual/source_crosswalks/world_bank_icp.json` (pending ICP candidate mappings, visibly distinguished from approvals);
- `data/manual/source_crosswalks/imf_weo.json` (IMF WEO mappings, including the explicit field-15-only WBG/KOS approval scope);
- `config/identity_edge_case_reconciliation.json` (prior identity, ISO, entity, catalogue and naming decisions).

The editable review and immutable baseline now include `existing_project_source_mappings` and `prior_project_identity_decision`. Existing mapping targets are explicitly compared with the proposed `game_id` (`same_game_id` / `different_game_id`), and conflicts receive a review flag. The two unresolved identities are retained in a separate immutable `unresolved_identity_history.csv`, so the existing IMF field-15 WBG-to-Palestine mapping is visible without turning WBG into a field-16 proposal. Each source mapping records its dataset, source identifier/name, mapped persistent game ID, match method, evidence reference, approval status, approval scope and approval record where present. Prior edge-case records expose the recorded decision dimensions and policy version. The review manifest fingerprints every history file.

Crosswalk evidence is matched by source identifier and/or the exact persistent `game_id`; it is not used to infer or rewrite identity mappings. In particular, an approved WDI or WPP mapping remains scoped to that provider, an ICP candidate remains pending, and the existing IMF WEO WBG/KOS approval remains field 15 only. None is promoted to field-16 approval. The existing owner-review package at `20261127T183743Z` remains immutable historical evidence; generate a new timestamped package after syncing the enriched builder.

Focused regression coverage now checks that the history sources are displayed, pending mappings remain pending, field-15 scope is retained verbatim (including the unresolved WBG record), previous identity decisions are surfaced, and existing crosswalk targets are compared with the proposed persistent game IDs. The workflow remains prepare-only: no approval creation, registry/crosswalk mutation or database write.

### Field-16 owner-review evidence tiers — 2026-11-27

The owner-review builder now assigns each of the 195 exact-registry proposals an explicit `identity_evidence_tier`, with supporting dataset columns and manifest counts. Classification is intentionally conservative:

- `approved_source_corroboration`: at least one same-game-ID, owner-approved WDI or UN WPP mapping. These are independent provider-scoped precedents, not IMF field-16 approvals.
- `pending_candidate_only`: no approved WDI/WPP corroboration, but a same-game-ID ICP mapping remains pending.
- `field_scoped_mapping_only`: no approved WDI/WPP corroboration or pending ICP candidate, but an approved IMF WEO mapping exists. Its recorded field scope remains visible and is not treated as field-16 approval.
- `registry_match_only`: none of the above; the proposal is supported only by the exact unique registry current-source-ID match used to create the proposal.

If a row has both approved WDI/WPP corroboration and pending ICP evidence, the tier is `approved_source_corroboration`; the separate `pending_candidate_datasets` column still exposes the pending evidence. The row also retains the full `existing_project_source_mappings` JSON and prior identity-decision evidence. Manifest counts report all four mutually exclusive tiers and the overlapping approved, pending and field-scoped evidence counts. No tier creates an approval, changes a source crosswalk or modifies either database.

The regression tests cover all four tiers, including mixed approved-plus-pending evidence and a field-15-only IMF mapping. Regenerate a new timestamped review package after syncing; preserve the committed `20261127T185010Z` package as the prior evidence snapshot.
