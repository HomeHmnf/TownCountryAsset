# Canonical SQLite database architecture

**Status:** WP1.1–WP1.3 implemented and locally validated by the owner; WP1.4 implementation committed and awaiting owner validation. No consumer cutover is included.
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

Schema migration 002 upgrades the local database to schema version 2 by adding `countries.entity_type_status` (`unreviewed` or `reviewed`). The v1 table inventory below remains the base table contract; v2 adds review-state enforcement without introducing parallel domain-specific review tables.

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
- Schema v2 requires a matching approved `entity_type` proposal before `entity_type_status` can become `reviewed`, a matching approved Persian localization proposal before `localization_status` can become `reviewed`, and a matching approved ISO proposal before `iso_assignment_status` can become `verified`. The existing alpha-2/alpha-3 requirement remains in force.
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

The generated production snapshot stores source provenance in the top-level `source` object of `manifest.json`; the importer uses that object as authoritative, while accepting legacy/test inputs that carry the same object in `countries.json`. If both are present, they must match. Dataset provenance columns are now populated in the exact schema order, keeping the archive SHA-256 in the checksum column. Regression coverage includes the production manifest layout. The owner subsequently confirmed that all focused WP1.2 tests passed; WP1.2 is locally validated and closed.


## WP1.3 — Country metadata, source attributes and geometry

The WP1.3 importer is implemented in `tools/database/country_data_import.py`, with the operator CLI in `tools/import_country_data.py`. It consumes the existing candidate snapshot without modifying the compiler, registry, source data, approved snapshot, or JSON pipeline.

Before opening the database transaction, the importer verifies the manifest SHA-256 checksums for `countries.json` and all three game-ID geometry files. It validates the candidate schema, unique persistent `game_id` and Natural Earth source IDs, required source attributes, and exact geometry key coverage for the low, medium and high profiles. Geometry input must use `key: game_id` and the matching profile name.

The importer then requires exactly one matching WP1.2 `dataset_imports` row and verifies its source provenance. Candidate source-ID/`game_id` pairs must exactly match the database's current Natural Earth source mappings. No identity is inferred from ordering, ISO codes, or names.

Every entry in `source_attributes` is stored in `country_attributes` with its corresponding schema v1 type. JSON objects/arrays are serialized deterministically; explicit nulls remain SQL NULL with `value_type = 'null'`. The compiler-provided `source_geometry_type` is stored as an additional text attribute. Each geometry is serialized deterministically, hashed with SHA-256, and stored in `country_geometries` with the existing WP1.2 `import_id`.

All writes occur in one transaction. Existing identical rows are accepted for idempotency; conflicting rows, provenance mismatches, identity mismatches, malformed inputs, or incomplete geometry coverage abort and roll back the import. SQLite integrity and foreign-key checks run before commit. The importer does not promote records or mark values verified.

### WP1.3 operator command

Run after WP1.2 has populated the same database:

```fish
uv run python -m tools.import_country_data \
  --database /tmp/tca-wp1-3.sqlite
```

Optional `--candidate-dir` supports isolated snapshots. The importer expects the WP1.2 Natural Earth identity/provenance import to have already run in that database.

### WP1.3 tests and validation

`tests/test_database_country_data_import.py` covers typed attribute preservation, all three geometry profiles and checksums, idempotency, manifest checksum rejection, geometry coverage rejection, candidate/database identity mismatch, and transactional rollback on conflicts.

Owner validation completed on 2026-10-31. The production import reported 242 countries, 40,898 attributes, 726 geometries across all three profiles, and passed SQLite integrity and foreign-key checks. The full repository test suite passed: **145 passed**. `compileall` completed without errors. The operator used `/tmp/tca-wp1-3.sqlite`; the identity and country-data import commands were run sequentially against that same database. WP1.3 is locally validated and closed.


## WP1.4 — Review-domain candidates and evidence

WP1.4 is implemented in `tools/database/review_data_import.py`, with the operator entry point `tools/import_review_data.py`, migration `migrations/002_review_domain_status.sql`, and focused tests in `tests/test_database_review_data_import.py`.

The importer consumes the existing identity registry, captured ISO reference/provenance and proposal report, Persian candidate/provenance snapshots, entity taxonomy, and flag mapping. It requires exact `game_id` coverage and checks the registry's current Natural Earth source mapping against the database. ISO report rows are recomputed from the supplied captured reference and compared field-by-field; the normalized reference checksum must match its provenance. Persian QIDs are checked against the explicit `WIKIDATAID` source attribute already imported into `country_attributes`. It does not use names or ISO codes to infer Wikidata identity.

All four domains use the existing `review_proposals` table and deterministic proposal fingerprints. ISO candidates retain reference labels, match/decision context, and capture provenance. Persian candidates retain the QID, candidate label, endpoint, retrieval timestamp and raw-response checksum; candidate labels are not inserted into `country_names`. Entity proposals retain the configured taxonomy definition and required-evidence guidance, explicitly recording that classification evidence is still empty. Flag proposals retain source metadata, decision notes, evidence and the mapping-file checksum; source codes remain distinct from approved game flag mappings.

No blank values are inferred or filled. Candidate and rejected decisions are retained; approved decisions are accepted only when the input contains an explicit review timestamp and the corresponding reviewed registry value is consistent. Re-importing identical content is idempotent; conflicting content or attempted downgrades are rejected. The operation is transactional and validates SQLite integrity and foreign keys before commit.

Migration 002 adds `countries.entity_type_status` and enforces matching approved proposals for reviewed entity classifications, reviewed Persian localization, and verified ISO assignments. The existing reviewed-flag constraint remains in force. The importer does not edit the registry, taxonomy, flag mapping, captured snapshots, generated assets, or JSON pipeline.

WP1.4 does not approve the currently unreviewed source data, fill nulls, migrate selected game data/current statistics, or produce the consolidated completeness report. That report remains deferred until all WP1 data domains have been visited.
