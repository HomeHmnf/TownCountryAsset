# Project dataset and acquisition-stream registration — Stage 2

**Status:** Implemented and owner-validated on 2026-11-05.
**Architecture contract:** [Data-store separation plan](../architecture/data-store-separation-plan.md)
**Stage 0 findings:** [Stage 0 findings](data-store-separation-stage-0-findings.md)
**Stage 1 foundation:** [Stage 1 design](data-store-separation-stage-1-design.md)
**Source audit:** [Project source catalogue registration audit](data-store-separation-source-catalogue-audit.md)

## 1. Scope

Register only dataset identities and acquisition-stream boundaries supported by tracked manifests, source documentation and prior validation records. This stage does not create acquisition attempts or artifact rows, migrate canonical values, promote releases, execute retention, or change source selection.

Definitions live in config/project_datasets.json; the project DB is synchronized with:

```fish
uv run python -m tools.sync_project_dataset_catalogue
```

The command is idempotent and supports --database PATH and --config PATH.

## 2. Evidence-backed registrations

| Source | Dataset key | Stream key | Disposition |
|---|---|---|---|
| Bahrain Open Data | 03-unemployment-yearly | rolling_api_snapshot | Registered. One timestamped capture comprises dataset metadata and all record pages. Reuse the already settled Bahrain assessment/approval disposition. |
| UN M49 | country_area_overview_html | rolling_reference_page | Registered. A single current-reference HTML page with an established content contract. The alternate manifest shape remains unchanged. |
| IMF WEO | world_economic_outlook | manual_vintage_bundle | Registered. One vintage bundle requires the statistical CSV and matching Database Appendix as separate artifact roles. No formal acquisition manifest or semantic validation is asserted. |
| UN WPP | demographic_indicators_medium | deferred | Dataset identity registered; stream withheld pending independent retention-boundary review. |
| UN WPP | population_by_age_5_group_sex_medium | deferred | Dataset identity registered; stream withheld pending independent retention-boundary review. |

ICASEES is deliberately not registered yet. Its manifest groups a workbook, definitive accounts PDF and GDP rebasing memo under one publication-bundle snapshot, while Stage 0 explicitly left the independent dataset/stream boundaries unresolved. Registering one broad dataset or assigning separate streams now would prematurely decide that question.

WPP's approved combined candidate establishes that the demographic dataset, age/sex dataset and Togo supplement were used together in one validated application. It does not establish their independent retention units. The two main statistical dataset identities are registered, but no WPP acquisition stream is created. Notes files and the Togo supplement remain evidence/artifacts for the later WPP boundary review, not silently promoted to standalone datasets.

## 3. Synchronizer behaviour

tools.database.dataset_catalogue.sync_dataset_catalogue:

- validates source/dataset/stream identities and rejects duplicates within the input;
- upserts by the schema's stable (source_key, dataset_key) and (dataset_id, stream_key) keys;
- preserves unrelated manually managed rows;
- stores the full reviewed dataset metadata in datasets.metadata_json;
- stores stream validation contract and stream metadata together in acquisition_streams.validation_contract_json;
- uses the schema's fixed retention limit of two;
- performs one transaction and rolls back on invalid input;
- does not create acquisitions or artifacts and does not delete definitions omitted from the config.

The source registry synchronizer must run first so source foreign keys exist. Recommended operator sequence:

```fish
uv run python -m tools.sync_project_source_catalogue
uv run python -m tools.sync_project_dataset_catalogue
```

Expected current result: **5 datasets and 3 streams**. WPP contributes two datasets and zero streams.

## 4. Explicit non-effects

No source files or manifests are rewritten. No existing Bahrain decision is reopened. No ICASEES/WPP stream boundary is guessed. No acquisition, validation, approval, application, release lifecycle, retention cleanup, source-selection policy or Game DB row is changed.

## 5. Acceptance and owner validation

Owner-run validation completed on 2026-11-05 after pulling branch work/compiler-hardening:

- Focused test command covering dataset catalogue, source catalogue, project schema, game schema and application approval: **31 passed in 0.91 seconds**.
- `tools.sync_project_source_catalogue`: **31 sources** and **92 source URL records** synchronized.
- `tools.sync_project_dataset_catalogue`: **5 datasets** and **3 acquisition streams** synchronized.
- Direct project DB count query returned: sources 31; source_urls 92; datasets 5; acquisition_streams 3; acquisitions 0; acquisition_artifacts 0.
- Both synchronizers reported no changes to source-selection settings. The dataset synchronizer also reported no acquisition, artifact, approval or retention operations.
- No Game DB migration or canonical data migration was part of this validation.

The owner-supplied terminal output is the validation evidence. This confirms catalogue registration and schema/test compatibility; it is not evidence that the newly registered IMF or UN M49 data has been acquired or semantically validated. Bahrain's previously settled validation disposition remains unchanged.

## 6. Exit criteria and next stage

Stage 2 is complete. The next bounded stage should design and implement acquisition-manifest adapters and provenance registration for the supported existing manifest variants, without yet enforcing retention or moving canonical data. Preserve the Bahrain rolling manifests, UN M49 alternate manifest representation, WPP edition/supplement variants and ICASEES bundle evidence losslessly. ICASEES and WPP stream boundaries remain explicit gates for stream registration and retention enforcement.
