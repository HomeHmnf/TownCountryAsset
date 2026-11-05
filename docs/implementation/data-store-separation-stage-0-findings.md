# Data-store separation — Stage 0 findings

**Status:** Stage 0 approved by the owner on 2026-11-05. No schema, source-selection, retention, or filesystem changes have been made.
**Plan:** [Data-store separation plan](../architecture/data-store-separation-plan.md)
**Inventory procedure:** [Stage 0 inventory](data-store-separation-inventory.md)
**Target branch:** work/compiler-hardening
**Last updated:** 2026-11-05

## 1. Scope and evidence boundary

These findings consolidate the owner-supplied read-only local inventory with repository code/test inspection. They are a design baseline, not a claim that the future migration has been implemented or locally validated.

The canonical database is schema v4, 1,896,448 bytes, SQLite integrity check OK, foreign-key check empty, with migrations 001–004 applied. The proposed data/project/project_data.sqlite did not exist at inventory time.

The raw source, manifest, derivative, and report inventories were owner-run. Git-tracked files were checked against HEAD blobs; do not infer that a tracked artifact is local-only merely from configuration.

## 2. Current database disposition matrix

| Current table | Observed rows | Proposed destination | Rationale / migration treatment |
|---|---:|---|---|
| countries | 242 | Game DB | Core game identity and entity records. Preserve IDs and constraints. |
| country_names | 250 | Game DB | Game-facing localized names. |
| country_regions | 237 | Game DB | Game-facing regional classification. Keep classification provenance in project data if needed. |
| country_attributes | 0 | Game DB, subject to field review | Generic game attribute values; empty today but exercised by import/schema tests. Keep acquisition/mapping evidence in project DB. |
| country_flags | 0 | Split | Final selected flag code/reference is game-facing; mapping status, decisions and evidence are project/review data. Preserve tested workflow. |
| country_geometries | 0 | Split | Geometry payload/profile/hash may be game-facing; import_id and source provenance belong in project DB. |
| current_statistics | 796 | Split, primarily Game DB values | Keep game-facing scalar values and required observation/reference period. Move source reference, source version, methodology, retrieval timestamp and import linkage to Project DB. Current rows are four projected indicators for 199 countries, period 2026. |
| selected_game_data | 398 | Split, primarily Game DB values | Keep selected age/sex distribution payload and required value status/reference period. Move source reference, version, methodology, retrieval timestamp and import linkage to Project DB. Current rows are two WP1.5 categories for 199 countries, period 2026. |
| country_sources | 441 | Project DB | Source-to-country associations and current-source state are provenance/research relations. Current counts: Natural Earth 242; UN WPP 199. |
| dataset_imports | 2 | Project DB | Acquisition/import catalogue and artifact metadata. Its current import_status is not authoritative application state. |
| application_approvals | 2 | Project DB | Approval artifacts, hashes, decision state and application identifiers are governance records. |
| database_application_events | 6 | Project DB | Proposed/approved/applied lifecycle audit events. Preserve ordering and idempotency evidence. |
| review_proposals | 0 | Project DB | Review and decision workflow; empty but referenced by code/tests. |
| import_runs | 0 | Undecided pending consumer audit | Empty. Confirm whether still supported or legacy before migrating/retiring. |
| schema_migrations | 4 | Separate table in each DB | Each SQLite database needs its own schema version and migration history. |

### Important current-state observations

- The two applied approvals are un-wpp-2026-11-01 (wp1_5_statistics) and identity-registry-2026-11-01 (identity_registry).
- WPP application event details record 1,194 observations: 796 scalar and 398 structured. Its application ID is wp1-5:un_wpp:2024-main-demographic+2026-01-19-togo-update:286ac36bb141.
- The WPP approval artifact records source inputs, manifests, generated candidate artifacts and source checksums. Preserve this provenance in Project DB.
- dataset_imports.import_status is candidate for both existing imports even though approval/application records show both applied. Preserve this historical inconsistency; do not silently rewrite it during migration.
- Empty tables are not evidence that their functionality is obsolete. Tests and/or tools reference review_proposals, country_flags, country_geometries, country_attributes and import_runs.
- Cross-database application requires a recoverable state machine, idempotency key, explicit transaction boundaries and reconciliation. A single SQLite transaction cannot atomically commit writes to two independent database files under the intended architecture.

## 3. Source artifacts, manifests and derivatives

### 3.1 Manifest reconciliation

- 10 source manifests are tracked; their worktree content matches their Git HEAD blobs.
- All 15 manifest-referenced raw artifacts exist and match manifest byte count and SHA-256; their worktree bytes also match Git HEAD.
- Three raw artifacts are tracked but not represented by current manifests:
  1. ICASEES extracted text: raw_data/sources/icasees/national_accounts_2019_2021/2026-07-30/COMPTES-NATIONAUX-2019_2021.txt.
  2. IMF WEO October 2026 Appendix PDF: raw_data/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf.
  3. IMF WEO October 2026 dataset CSV: raw_data/sources/imf_weo/october_2026/dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv.
- The IMF Appendix PDF and WEO CSV should be registered as artifacts of the same October 2026 release bundle, with distinct roles (supporting documentation and statistical dataset). The PDF is not the primary statistical dataset.
- The ICASEES TXT is an alternate/legacy extraction associated with the national-accounts PDF. It is not an independent publication or acquisition. Its extraction format differs from the structured derived_data/pdf_text output; preserve both until semantic equivalence and consumer dependencies are assessed.
- config/data_sources.json labels raw_data as local_only_untracked, but the inventoried source files and manifests are tracked in Git. This is a confirmed config/documentation mismatch. Resolve it in a separately reviewed configuration step; do not change source-selection policy as part of this inventory.

### 3.2 Acquisition streams and release grouping

- Bahrain Open Data uses the Opendatasoft API and has three timestamped rolling manifests. The provider-specific acquisition/validation disposition was previously reviewed and corrected in the existing Bahrain source documentation and assessment evidence. That established disposition is accepted for this plan; it is not an unresolved Stage 0 question. Identical payload hashes remain separate capture evidence, but retention eligibility follows the documented validation outcomes—not hash uniqueness.
- ICASEES has three related publication artifacts (national accounts workbook, national accounts 2019–2021 PDF, and GDP rebasing aide-memoire PDF) represented as a manual publication bundle. Preserve grouping for now; whether they form one retention stream or multiple independently versioned streams requires a source-domain decision.
- UN WPP has distinct configured download IDs/streams for demographic indicators, age/sex population, demographic notes, location notes and the Togo supplement. The demographic dataset plus Togo supplement was used in the applied WP1.5 release. Do not collapse all WPP download IDs into one retention stream without confirming bundle semantics.
- UN M49 manifest representation differs from the ordinary files/file-ID shape. Normalize manifest formats only after recording its actual artifact and role.
- IMF WEO October 2026 has an unmanifested primary CSV and supporting Appendix PDF; register both under a stable release identity.
- lipis_flag_icons has a discovered Git commit candidate only: no acquisition, validation, or application is recorded. It is not a successful retained acquisition.

### 3.3 PDF derivatives

There are three extracted PDF text files and three JSON sidecars under derived_data/pdf_text: ICASEES GDP rebasing aide-memoire (9 pages), ICASEES national accounts (65 pages), and IMF WEO October 2026 Appendix (31 pages).

Each sidecar records source path/hash, output path/hash, extraction status, page count and pypdf version. These are regenerable derivatives linked to parent source artifacts, not separate acquisitions. Retain or regenerate them according to consumer/cache policy; do not apply source-acquisition version counts to them independently.

The unmanifested ICASEES TXT begins with FILE, PAGES and PAGE markers (2,873 lines). The structured derivative uses --- PAGE n --- markers (2,698 lines). They are not byte-identical and line-based similarity is low due to extraction/layout differences; semantic equivalence has not been established. Both remain preserved pending consumer inspection.

## 4. Reports and research artifacts

| Report location/type | Classification | Retention treatment |
|---|---|---|
| icasees-national-accounts/<timestamp>/ assessment JSON, provenance JSON, CSVs and summary | Per-run acquisition/assessment evidence | Link to candidate/release and validation result. Keep with associated acquisition evidence; outputs are not separate acquisitions. |
| imf-weo/<timestamp>/ assessment JSON/Markdown and CSVs | Per-run read-only release assessment | Link to WEO release candidate. Regenerable, but useful evidence for release review. |
| world-bank-wdi/<timestamp>/ assessment JSON/Markdown and coverage CSV | Per-run read-only API assessment | Keep separate from acquired snapshots; API assessment is not itself an acquisition. |
| imf-wdi-comparison/<timestamp>/ | Comparative research runs | Persistent analytical subject with dated outputs. Not subject to source-acquisition retention merely because timestamped. |
| imf-wdi-discrepancy-investigation/<timestamp>/ | Targeted comparative research | Preserve findings and reproducible evidence; deduplicate repeated runs only under an explicit research-artifact policy. |
| crosswalk-review/ | Persistent crosswalk review evidence | Keep with crosswalk/mapping governance. |
| source-licenses.md | Persistent source catalogue/reference | Keep in project documentation/catalogue. |
| releases/*.json | Release lifecycle registry | Keep stable release identity and lifecycle state in Project DB; JSON may remain an export/bootstrap representation. |
| release-validations/*.json | Release-specific validation evidence | Link to release and validation run in Project DB. |
| refreshes/*.json and *.md | Operational run history | Model as project run records/artifacts; retention policy remains separate from source-version retention. |

The two-latest-successful-validated-acquisitions rule applies to source acquisition streams and their associated raw release artifacts. It must not automatically delete persistent cross-source research, stable catalogues, mappings, or governance history. Retention for failed candidates and operational run logs remains undecided.

## 5. Release lifecycle reconciliation

The UN WPP release registry reports checked_at 2026-11-02, status validated, applied_at null and latest_applied null.

The canonical DB and approval artifact confirm that the same release was approved and applied on 2026-11-01. The DB event log contains proposed, approved and applied events; the applied event identifies the WPP application ID and 1,194 observations.

Conclusion: the release registry is stale/incomplete relative to the application ledger. The application ledger and approval artifact are evidence of actual application. The future Project DB should have one authoritative lifecycle model; registry JSON must be updated from that model or generated as a projection, not maintained as an independent competing truth.

The Lipis flag-icons registry is only at discovered; its missing acquisition/validation/application fields are consistent with candidate status.

## 6. Retention policy constraints confirmed by inventory

1. Retain exactly the two latest successful, validated acquisitions per stable source dataset/acquisition stream.
2. A multi-file release bundle or complete paginated API capture counts as one acquisition version.
3. Independent streams from one provider have independent retention windows.
4. A candidate must finish acquisition and validation before it can displace a retained version.
5. Failed or incomplete candidates cannot evict either retained successful version.
6. Expired acquisition rows and associated raw artifacts/derivatives are removed together only after successful promotion and referential checks.
7. Stable source catalogue entries, URL roles, dataset definitions, field mappings and crosswalk definitions are not subject to acquisition retention.
8. Repeated captures with identical content hashes remain distinct acquisition events/provenance records if they are distinct successful validated acquisitions; content blobs may be deduplicated separately.

The Bahrain acquisition/validation disposition is accepted from the existing provider-specific documentation and assessment evidence. This consolidated inventory does not supersede that evidence. Identical hashes alone are not the basis for validation or retention eligibility.

## 7. Open design gates for later stages

1. Stream boundaries: confirm ICASEES bundle versus independent dataset streams; confirm UN WPP stream/bundle dependencies; formalize stable stream IDs for every source before retention enforcement.
2. Raw/derivative consumer map: finish exact runtime/tool/test references for the three unmanifested files and alternate ICASEES extraction; confirm whether any consumer depends on the legacy TXT.
4. Table consumer completion: finish production/runtime versus test-only references, especially country_flags, country_attributes, country_geometries and import_runs.
5. Run/report retention: specify retention for failed candidates, assessment runs, refresh logs and non-acquisition research evidence without conflating these with the two-version source policy.
6. Manifest normalization: document and support current schema variants (Bahrain rolling, ICASEES manual bundle, UN M49 alternate representation, WPP edition/supplement).
7. Registry reconciliation: decide whether release registry JSON becomes a generated projection or synchronized cache of authoritative Project DB lifecycle state.
8. Config mismatch: decide the correct tracked/local storage policy for raw_data and update config/data_sources.json in a separately reviewed change.
9. Migration parity: capture deterministic row-level export/count/hash baselines for both target databases and prove rollback/recovery before cutover.
10. Two-database application protocol: specify crash recovery for partial cross-DB application and ensure replay is idempotent.

## 8. Stage 0 disposition

The owner approved Stage 0 on 2026-11-05. The table/artifact disposition and retention constraints in this document are the accepted baseline. The Bahrain provider-specific validation disposition remains grounded in the existing Bahrain documentation and assessment evidence, which takes precedence over the earlier unresolved wording in this consolidated inventory.

Stage 1 may begin within the approved plan and is scoped by [the Stage 1 design](data-store-separation-stage-1-design.md). Remaining unresolved items are tracked as design/implementation gates: stream identity and manifest normalization must be settled before retention enforcement; consumer mapping must be complete before table retirement; run/report retention must be specified before cleanup; migration parity and cross-database recovery must be proven before cutover. No source-selection policy change is authorized.
