# Project database foundation — Stage 1 design

**Status:** Approved implementation baseline, 2026-11-05. Stage 1 is limited to the project-database foundation; it does not migrate or delete current canonical data.
**Architecture contract:** [Data-store separation plan](../architecture/data-store-separation-plan.md)
**Stage 0 evidence:** [Stage 0 findings](data-store-separation-stage-0-findings.md)

## 1. Stage 1 scope

Create the independent project database at data/project/project_data.sqlite, with its own connection configuration, migration directory/ledger, initial schema and integrity tests.

The first schema establishes the stable source catalogue and acquisition-version model:

- source organisations and stable source identities; source registry metadata is retained losslessly in `metadata_json` and promoted query fields (`domains_json`, `license_status`, `attribution`, `notes`, `acquisition_mode`, `release_discovery_json`, `legacy_source_ids_json`, `field_ids_json`);
- typed source URLs (homepage, documentation, dataset page, API base, download, terms/licence and evidence);
- stable dataset definitions;
- acquisition streams, each representing one independently retained dataset/download/API capture unit;
- acquisition attempts/versions, including acquisition year, timestamps, provider release label and lifecycle status;
- artifacts attached to an acquisition, with repository-relative path, role, checksum, byte count, media type and actual retrieval URL where known.

The schema must represent the approved two-successful-versions-per-stream policy. Promotion and filesystem cleanup behaviour belong to Stage 2; Stage 1 must not run retention or delete files.

## 2. Explicit boundaries

1. Keep data/canonical/town_country_asset.sqlite and its schema-v4 migrations unchanged in Stage 1.
2. Do not move, copy, rewrite or delete existing canonical rows in this stage.
3. Do not move approval/application records or change their transaction semantics; cross-database governance is Stage 4.
4. Do not add source observations, crosswalks, indicator mappings, validation detail, comparisons or research-run retention logic yet; those belong to Stage 3 and later.
5. Do not change config/source_selection.json, data/manual/source_overrides.json, source priorities, fallback rules or selection behaviour.
6. Do not normalize existing manifest formats or decide unresolved ICASEES/WPP stream boundaries merely to seed the initial catalogue. Schema support is generic; stream registration must use the established source-specific decisions.
7. Bahrain's acquisition/validation disposition is settled by the existing Bahrain documentation and assessment evidence. Reuse that disposition when source records are seeded; do not reopen or infer it from identical hashes.
8. Do not update config/data_sources.json storage policy in this stage. The tracked-raw-data mismatch is a separate reviewed configuration decision.

## 3. Proposed initial relational model

| Table | Responsibility | Key relationships |
|---|---|---|
| schema_migrations | Independent project schema version ledger | Project DB only |
| source_organisations | Publisher/provider identity and stable metadata | One organisation may publish multiple sources |
| sources | Stable source key, organisation and descriptive metadata | Organisation parent for source URLs and datasets |
| source_urls | URL plus explicit role and optional dataset association | Belongs to a source; optional dataset relation |
| datasets | Stable provider dataset identity and descriptive/format metadata | Belongs to a source |
| acquisition_streams | Stable retention-unit key and acquisition/validation contract reference | Belongs to a dataset; independent retention window |
| acquisitions | One acquisition attempt/version, acquisition year/time, provider release label and lifecycle status | Belongs to one stream |
| acquisition_artifacts | Files/pages/manifest/derivatives belonging to an acquisition | Belongs to one acquisition; stores checksum and relative path |

The final SQL column definitions must use explicit types, NOT NULL, CHECK, foreign keys and uniqueness constraints where appropriate. Stable IDs are text keys from the source registry/configuration; generated integer primary keys may be used for internal row identity.

### Acquisition lifecycle and retention invariant

Represent at least these states: candidate, acquired, validated, retained, superseded, failed, and rejected. A failed/incomplete candidate is never eligible to displace a retained acquisition. A stream can have no more than two acquisitions in retained state. Promotion logic must transition the oldest retained acquisition out of that state in the same project-DB transaction that retains its validated replacement. The lifecycle implementation and cleanup are not enabled in Stage 1.

A multi-file bundle or complete paginated capture is one acquisition with multiple acquisition_artifacts. Distinct streams under one provider have independent retained-version windows. Identical hashes do not merge distinct acquisition events.

## 4. Connection and migration design

- Add a project-specific default path and connection factory; do not change the existing DEFAULT_DATABASE_PATH or its callers.
- Reuse the migration engine only through an explicitly supplied project migration directory, or add a narrowly scoped project wrapper. The project DB must never apply migrations/001–004 from the game DB.
- Keep separate migration ledgers, independent schema versions and integrity/foreign-key checks.
- Preserve the existing SQLite safety settings: foreign keys enabled, busy timeout, full synchronous writes and WAL for file-backed connections.
- A fresh project DB must be creatable without opening or migrating the game DB.
- Add tests for path isolation, connection pragmas, fresh schema, migration idempotency, migration rollback, future-schema rejection, foreign-key enforcement and retention-state constraints.
- Keep the project DB and its SQLite sidecars local-only; do not commit the live database file.

## 5. Seed and registration policy

The initial schema is generic. Stable source and organisation records may be synchronized from the existing source registry after an explicit key/URL mapping audit. Dataset and stream registration must not invent bundle boundaries. In particular:

- use the already documented Bahrain validation outcomes;
- preserve ICASEES and WPP stream grouping as unresolved until their source-domain review is complete;
- register the IMF WEO CSV and Appendix PDF as artifacts of the same October 2026 release bundle, with distinct roles;
- preserve the UN M49 alternate manifest representation until its manifest adapter is designed.

No raw source file is copied into the project database. The database records metadata and repository-relative artifact references.

## 6. Stage 1 acceptance criteria

- The project DB is created at the approved path and has a distinct connection factory.
- Project migrations are isolated from game migrations and maintain their own contiguous ledger.
- The schema supports the source catalogue, typed URLs, datasets, streams, acquisitions and artifacts described above.
- The source synchronizer registers all 31 configured source keys and all 92 configured URL records without inventing publisher organisations or unresolved dataset/stream boundaries.
- Database constraints prevent invalid relationships, duplicate stable keys and more than two retained acquisitions in one stream.
- Tests prove that project DB setup does not create, migrate or modify the game DB.
- Existing game DB schema remains v4 and all existing game DB files/rows are left untouched by Stage 1 commands.
- No acquisition, retention cleanup, source-selection, approval migration or game-runtime cutover is introduced.
- Relevant architecture, implementation and operator documentation is updated with the code and tests.

## 7. Operator commands

Create or upgrade the local project DB with `uv run python -m tools.migrate_project_database`. The command targets only the project DB by default; `--database PATH` may be used for an isolated test copy. It applies only `migrations/project/` and reports SQLite integrity and foreign-key results.

Synchronize stable source identities and configured URLs with `uv run python -m tools.sync_project_source_catalogue`. Optional `--database PATH` and `--config PATH` arguments support isolated runs. The synchronizer upserts source records and replaces only URL rows it previously marked as managed by `config/data_sources.json`; manually managed URL rows are not deleted. It preserves the complete source object in `metadata_json`, fills explicit query fields, and does not assign publisher organisations, create datasets/streams/acquisitions, alter manifests, or change source-selection policy. Re-running the command is idempotent.

## 8. Owner-run validation record

**Validated locally by the repository owner on 2026-11-05.** The following focused command passed: `uv run --extra dev python -m pytest -v tests/test_project_database_schema.py tests/test_database_schema.py tests/test_application_approval.py` — 24 passed in 0.54 seconds.

The owner then ran `uv run python -m tools.migrate_project_database`; it created `data/project/project_data.sqlite`, advanced schema version 0 to 1, and reported successful SQLite integrity and foreign-key checks. The subsequent `git status --short --branch` showed the branch synchronized with origin and only the two pre-existing deletions of `data/canonical/town_country_asset.sqlite-shm` and `data/canonical/town_country_asset.sqlite-wal`. Those deletions were not staged or restored.

This is owner-supplied local validation evidence; no broader test suite or production data migration is implied.


## Schema version progression

The initial project foundation is migration 001 (schema version 1). Migration 002 adds explicit source-registry metadata fields without replacing the lossless source metadata JSON. A fresh project database therefore reaches schema version 2. Existing local version-1 databases upgrade transactionally to version 2 when `tools.migrate_project_database` runs. The schema tests assert version 2 and verify the added columns.
