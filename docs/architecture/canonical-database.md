# Canonical SQLite database architecture

**Status:** WP1.1 implemented and locally validated; WP1.2 identity/provenance importer implemented, awaiting developer validation. No consumer cutover is included.
**Canonical local path:** `data/canonical/town_country_asset.sqlite`
**Schema versioning:** Local database ledger; migration SQL is version-controlled.

## Scope and authority

SQLite is the planned canonical structured store for country identity, source provenance, names, regions, source attributes, geometry profiles, review evidence, selected game data, and current statistics. The database is local application data and is not committed to Git. Existing JSON configuration, registry, generated assets, and pipeline behavior remain in place during the parallel migration.

Persistent `game_id` values remain the internal identity. They are exactly `tc_` followed by 32 lowercase hexadecimal characters. Natural Earth source identifiers and ISO codes are separate attributes. Imported records default to `candidate`. Populated source values are treated as the supplied dataset values unless the owner identifies an error; completeness reporting focuses on empty/null values. Verification is applied after the relevant data domains have been populated, not prematurely during partial imports.

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

SQLite database, WAL, and shared-memory files are local state and ignored by Git. Migration SQL, database code, tests, and architecture documentation are tracked. WP1.1 does not import production records. WP1.2 imports identity and source provenance only.

## Migration policy

The migration manager owns the `schema_migrations` ledger and creates it before applying pending migration files. Numbered migration SQL must not create or modify this bookkeeping table; it defines application schema only. This avoids duplicate ledger creation on a fresh database.


Migrations are numbered, sequential, immutable once applied, and committed with the code that uses them. Each migration runs in its own `BEGIN IMMEDIATE` transaction; schema DDL and the migration-ledger entry commit together. A failed migration is rolled back. A database with a newer schema version than this checkout is rejected without downgrade. There is no automatic destructive downgrade. Schema changes require a new migration file and tests.

## Validation

WP1.1 tests cover fresh creation, repeat application, exact identity format, unique identity, source ID uniqueness and history, canonical-name uniqueness, ISO constraints and verified-status triggers, JSON validity, geometry profiles, current-statistic and selected-data uniqueness, proposal deduplication and approval timestamps, flag approval requirements, failed-migration rollback, future-schema rejection, and SQLite integrity/foreign-key checks.

No source registry, generated asset, approved snapshot, or game repository is modified by WP1.1.


## WP1.2 — Identity registry and source provenance

The importer is implemented in `tools/database/identity_import.py` with the CLI `tools/import_identity_registry.py`. It reads the persistent registry and the isolated generated candidate snapshot, verifies the candidate manifest checksum and exact one-to-one source-ID/`game_id` coverage, and imports the registry's identity relationships into schema v1.

The import populates `dataset_imports`, `countries`, `country_sources`, `country_names`, and `country_regions`. It preserves the registry's current and historical source IDs and English canonical names/aliases. It does not import source attributes, geometry, Persian localization, game data, statistics, flags, or review proposals; those remain assigned to later WP1 stages.

The operation is transactional and repeatable. It reuses the dataset import row for the same dataset/archive checksum, rejects conflicting existing country/source/name records, validates database integrity and foreign keys before commit, and rolls back the entire import on failure. It never changes a `game_id`, infers a missing value, or promotes a candidate record.

### Data completeness and verification policy

- Treat populated source values as correct as supplied unless the owner identifies a specific error; do not turn an unreviewed workflow label into a data-quality warning.
- Report actual empty and `null` values in the consolidated completeness report after all planned data domains have been visited.
- Do not fill missing values by guesswork. A genuinely inapplicable field may remain null and should be distinguishable from an expected-but-missing value in the final report.
- Apply the appropriate verified/reviewed statuses only after the relevant data population is complete. For example, schema v1 requires both ISO alpha-2 and alpha-3 values before an ISO assignment can be marked `verified`.
- WP1.2 is intentionally partial: its records remain candidate/unverified where later stages still need to populate fields. This is not a finding that the supplied values are incorrect.

### WP1.2 operator command

```fish
uv run python -m tools.import_identity_registry \
  --database /tmp/tca-wp1-2.sqlite
```

Optional `--registry` and `--candidate-dir` arguments allow isolated fixtures or alternate candidate snapshots. The command does not modify the JSON registry or generated candidate directory.


### WP1.2 implementation correction — 2026-10-31

The generated production snapshot stores source provenance in the top-level `source` object of `manifest.json`; the importer uses that object as authoritative, while accepting legacy/test inputs that carry the same object in `countries.json`. If both are present, they must match. Dataset provenance columns are now populated in the exact schema order, keeping the archive SHA-256 in the checksum column. Regression coverage includes the production manifest layout. Local WP1.2 validation is still pending.
