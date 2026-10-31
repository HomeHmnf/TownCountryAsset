# Canonical database implementation log

**Scope:** WP1 introduces local SQLite canonical storage through a parallel migration. Existing JSON/configuration assets remain available until later migration stages validate parity and approve consumer cutover.

## Decisions

- Database: `data/canonical/town_country_asset.sqlite`.
- Imported identity status: `candidate`.
- Database versioning: local; schema migration SQL and tooling are tracked in Git, database binaries are not.
- Migration strategy: parallel; do not replace or mutate approved JSON snapshots during migration.
- Scope: all applicable country/source/review data, selective game data, and current statistics.
- Repository layout: adapt existing layout; do not reorganize unrelated tools.
- Stable identity: preserve every existing `game_id`; source IDs and ISO codes remain separate attributes.

## WP1.1 — SQLite schema, connection layer, and local version management

**Status:** Implemented and locally validated by the owner.

Added the version 1 schema in `migrations/001_initial_schema.sql`, SQLite connection configuration in `tools/database/connection.py`, transactional migration management in `tools/database/schema.py`, and the local initialization/upgrade CLI in `tools/migrate_database.py`. Added `tests/test_database_schema.py`.

The schema includes dataset provenance, countries, current/historical source IDs, names and aliases, regions, typed source attributes, low/medium/high geometries, import runs, current statistics, selective game data, flag mappings, review proposals, and the local schema migration ledger. Constraints enforce exact `tc_` plus 32 lowercase-hex identity syntax, foreign keys, unique current source IDs, one canonical name per language, ISO syntax and verified-code requirements, valid JSON, geometry profile values, current-statistic uniqueness, proposal fingerprint deduplication, and review timestamp/flag approval requirements.

The migration runner applies sequential numbered SQL files in one transaction per migration, records local application timestamps, rejects unsupported future versions and migration-file mismatches, and rolls back failed schema changes. The default database is repository-relative at `data/canonical/town_country_asset.sqlite`; no database file is created by committing the schema implementation. WP1.1 does not import production data or alter pipeline consumers.

### WP1.1 validation record

Run from the repository root:

```fish
uv run pytest -v tests/test_database_schema.py
uv run python tools/migrate_database.py --database /tmp/tca-wp1-1.sqlite
uv run python -m compileall -q tools/database tools/migrate_database.py
```

Owner-reported validation: `tests/test_database_schema.py` — **12 passed**; `uv run python -m tools.migrate_database --database /tmp/tca-wp1-1-fixed.sqlite` advanced schema 0 → 1 and passed SQLite integrity/foreign-key checks. The module invocation is required so the repository root is on the import path.

### WP1.1 migration-ledger correction — 2026-10-30

The first local validation attempt exposed a duplicate ledger definition: the migration manager creates `schema_migrations` before applying pending migrations, while migration 001 also attempted to create it. Removed the duplicate `CREATE TABLE schema_migrations` statement from migration 001. The migration manager is the sole owner of this local bookkeeping table; migration SQL defines application schema only.

The existing fresh-database, repeat-application, and failed-migration rollback tests exercise this boundary. The reported run failed during migration setup (1 failed, 9 setup errors, 2 passed); this is a confirmed implementation defect, not a passing validation. Re-run the focused tests, initialization CLI, and compile check after pulling this correction. WP1.1 remains locally unvalidated until the developer reports successful results.


## WP1.2 — Identity registry and source provenance

**Status:** Implemented and locally validated by the owner.

Added `tools/database/identity_import.py`, `tools/import_identity_registry.py`, and `tests/test_database_identity_import.py`. The importer reads `config/country_identity_registry.json` and `generated/town_country_asset_candidate/{countries.json,manifest.json}`. It verifies manifest SHA-256, registry/candidate coverage, persistent `game_id` equality, current source IDs, English canonical names/aliases, region memberships, and ISO alpha-3 candidate consistency before writing.

The importer populates `dataset_imports`, `countries`, `country_sources` (including historical IDs), `country_names`, and `country_regions`. It preserves current registry statuses as candidate/unverified values where the database schema requires them; no data is approved or guessed during this partial stage. It does not import source attributes, geometry, Persian localization, selected game data, current statistics, or flags.

The operation is transactional and idempotent for the same dataset/archive checksum. It rejects conflicting existing country/source/name mappings, validates SQLite integrity and foreign keys before commit, and rolls back on failure. It does not edit the JSON registry or generated candidate files.

### Data completeness and verification policy

Treat populated source values as correct unless the owner identifies an error. Do not report `unreviewed` workflow states as data-quality errors. After all WP1 data domains have been visited, produce one consolidated report of genuinely empty/null fields and test results; distinguish intentional inapplicability from missing expected data. Do not infer or fill missing values. Apply verified/reviewed statuses only after the relevant data is complete. In particular, schema v1 requires both ISO alpha-2 and alpha-3 before ISO status can become `verified`.

### WP1.2 validation commands

```fish
uv run pytest -v tests/test_database_identity_import.py tests/test_database_schema.py tests/test_country_identity_registry.py

uv run python -m tools.import_identity_registry \
  --database /tmp/tca-wp1-2.sqlite

uv run python -m compileall -q tools/database tools/import_identity_registry.py
git status --short
```

Record the actual local output before marking WP1.2 validated or proceeding to WP1.3.


### WP1.2 validation correction — 2026-10-31

The first owner-run validation exposed two importer defects. Production candidate provenance is stored in the top-level `source` object in `manifest.json`, not in `countries.json`; the importer now reads that production layout and retains compatibility with isolated fixtures that place provenance in `countries.json`. If both locations are present, they must agree. The dataset-import INSERT also had its attribution value shifted into the SHA-256 column; the value ordering now matches the schema columns. Added a regression test for manifest-based provenance.

The owner-reported run had **6 identity-import failures**, while the schema and identity-registry tests passed (**18 passed** across the combined run). The migration CLI advanced schema 0 → 1 and passed integrity/foreign-key checks; the data import then failed. These are confirmed implementation defects. WP1.2 validation was subsequently completed: the owner confirmed that all focused tests passed after the preflight mismatch assertion correction. WP1.2 is locally validated and closed.


### WP1.2 follow-up test correction — 2026-10-31

The owner reran WP1.2 after the importer fixes. The production database migration succeeded (schema 0 → 1 with SQLite integrity and foreign-key checks passing), and the real identity import succeeded with **242 countries, 242 source mappings, 250 names, and 237 region memberships**. The focused suite reported **24 passed, 1 failed**. Investigation of the remaining failure showed the importer correctly rejects a registry/candidate `game_id` mismatch during preflight, before opening or creating the SQLite database; the test incorrectly attempted to query schema tables in a database that should not exist. Corrected the test to assert that no database file is created on this preflight rejection. Re-run the focused suite to confirm all 25 tests pass before marking WP1.2 locally validated.


### WP1.2 owner validation confirmation — 2026-10-31

The owner confirmed that all focused WP1.2 tests passed after the preflight mismatch assertion correction. WP1.2 is therefore locally validated and closed.

## WP1.3 — Country metadata, source attributes and geometry

**Status:** Implemented; owner validation pending.

Added `tools/database/country_data_import.py`, the `tools/import_country_data.py` CLI, and `tests/test_database_country_data_import.py`. The importer reads the candidate `countries.json`, manifest, and low/medium/high geometry files keyed by persistent `game_id`.

Before database writes, it validates all four input file checksums, input schema/profile declarations, unique source and game identities, required attribute objects, and exact geometry identity coverage. It requires the existing WP1.2 dataset import and checks source provenance plus exact current source-ID/`game_id` mapping parity.

The importer preserves source attribute types in schema v1: text, integer, real, boolean, JSON, and null. It stores the source geometry type as an additional text attribute. Geometry payloads are deterministically serialized and SHA-256 hashed. All metadata and geometry writes share one transaction; identical existing rows are idempotent, while conflicts or invalid inputs roll back the import. The importer does not modify source files, generated snapshots, the registry, or existing JSON pipeline consumers, and it does not promote candidate records.

### WP1.3 validation commands

```fish
uv run pytest -v \
  tests/test_database_country_data_import.py \
  tests/test_database_identity_import.py \
  tests/test_database_schema.py \
  tests/test_country_identity_registry.py

uv run python -m tools.import_identity_registry \
  --database /tmp/tca-wp1-3.sqlite

uv run python -m tools.import_country_data \
  --database /tmp/tca-wp1-3.sqlite

uv run python -m compileall -q tools/database tools/import_country_data.py

uv run pytest -v
git status --short
```

The identity import command is included to make the isolated WP1.3 database self-contained; run the country-data import against the same database. Record actual counts for attributes and geometries, the three profile counts, integrity/foreign-key results, and test outcomes. WP1.3 remains pending until the owner reports successful validation.
