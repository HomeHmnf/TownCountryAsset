# Canonical SQLite database architecture

**Status:** WP1.1 implementation committed; local database initialization and test execution await developer validation. No production-data migration or consumer cutover is included in WP1.1.
**Canonical local path:** `data/canonical/town_country_asset.sqlite`
**Schema versioning:** Local database ledger; migration SQL is version-controlled.

## Scope and authority

SQLite is the planned canonical structured store for country identity, source provenance, names, regions, source attributes, geometry profiles, review evidence, selected game data, and current statistics. The database is local application data and is not committed to Git. Existing JSON configuration, registry, generated assets, and pipeline behavior remain in place during the parallel migration.

Persistent `game_id` values remain the internal identity. They are exactly `tc_` followed by 32 lowercase hexadecimal characters. Natural Earth source identifiers and ISO codes are separate attributes. Imported records default to `candidate`; syntax validation never constitutes approval.

## WP1.1 implementation

- `migrations/001_initial_schema.sql` defines the initial schema.
- `tools/database/connection.py` configures SQLite connections, foreign keys, WAL for file-backed databases, FULL synchronous writes, and a 5-second busy timeout.
- `tools/database/schema.py` applies numbered SQL migrations in order, records applied versions locally, rejects gaps, mismatched migration names, and databases newer than the available code, and rolls back failed migration DDL and ledger writes.
- `tools/migrate_database.py` creates or upgrades the local database and runs SQLite integrity and foreign-key checks.
- The default database path is repository-relative: `data/canonical/town_country_asset.sqlite`. A `--database` override supports isolated testing and alternate local locations.

## Schema v1 table contract

| Table | Responsibility |
|---|---|
| `schema_migrations` | Local applied migration version/name/time ledger |
| `dataset_imports` | Dataset provenance, SHA-256, attribution, license, import status |
| `countries` | Stable identity, entity type, record status, ISO values/status, localization status |
| `country_sources` | Current and historical source identifiers by dataset |
| `country_names` | Language-specific canonical names and aliases |
| `country_regions` | Explicit region membership and classification source |
| `country_attributes` | Typed source attributes, including validated JSON values |
| `country_geometries` | Low/medium/high geometry payloads and checksums |
| `import_runs` | Import execution status and source checksum |
| `current_statistics` | One current value per country/statistic key |
| `selected_game_data` | Explicitly selected game-data payloads only |
| `country_flags` | Flag source mapping, review status, decision note and evidence |
| `review_proposals` | Deduplicated ISO/localization/entity/flag proposals and evidence |

The exact SQL definitions and constraints are authoritative in `migrations/001_initial_schema.sql`.

## Integrity and review constraints

- Country primary keys enforce the exact persistent `game_id` shape; no source ID, display name, ISO code, or row order is an identity fallback.
- Foreign keys are enabled on every application connection. Related records cannot be orphaned and identity deletion is restricted.
- Only one current source ID may exist per dataset/source ID pair. Historical source IDs remain retained with `is_current = 0`.
- Only one canonical name may exist per country/language; aliases are separate rows.
- ISO values are nullable. Alpha-2/alpha-3 syntax is checked, and `verified` status requires both codes on INSERT and UPDATE.
- Candidate is the default record/import/proposal status. Approved proposals require a review timestamp. A reviewed flag requires an approved flag proposal.
- Geometry profiles are limited to low, medium, and high. Geometry and selected game-data payloads must be valid JSON; geometry and provenance hashes must be 64-character lowercase SHA-256 strings.
- Current statistics are unique by country/statistic key. Historical statistics are not part of this current-only table contract.
- Proposal fingerprints make repeated imports idempotent at the proposal-record level.

## Local operation

Create or upgrade the local schema:

```fish
uv run python tools/migrate_database.py
```

Use an isolated database path for tests or inspection:

```fish
uv run python tools/migrate_database.py --database /tmp/tca-test.sqlite
```

SQLite database, WAL, and shared-memory files are local state and ignored by Git. Migration SQL, database code, tests, and architecture documentation are tracked. Backups and production-data import are later WP1 stages; WP1.1 does not create or import production records.

## Migration policy

Migrations are numbered, sequential, immutable once applied, and committed with the code that uses them. Each migration runs in its own `BEGIN IMMEDIATE` transaction; schema DDL and the migration-ledger entry commit together. A failed migration is rolled back. A database with a newer schema version than this checkout is rejected without downgrade. There is no automatic destructive downgrade. Schema changes require a new migration file and tests.

## Validation

WP1.1 tests cover fresh creation, repeat application, exact identity format, unique identity, source ID uniqueness and history, canonical-name uniqueness, ISO constraints and verified-status triggers, JSON validity, geometry profiles, current-statistic and selected-data uniqueness, proposal deduplication and approval timestamps, flag approval requirements, failed-migration rollback, future-schema rejection, and SQLite integrity/foreign-key checks.

No source registry, generated asset, approved snapshot, or game repository is modified by WP1.1.
