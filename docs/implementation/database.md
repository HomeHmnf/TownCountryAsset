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

**Status:** Implemented and locally validated by the owner.

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


### WP1.3 owner validation confirmation — 2026-10-31

The owner ran both importers sequentially against `/tmp/tca-wp1-3.sqlite`. Identity import succeeded with **242 countries, 242 source mappings, 250 names, and 237 region memberships**. Country metadata/geometry import succeeded with **242 countries, 40,898 typed attributes, 726 geometries, and all 3 geometry profiles**. Both importers reported successful SQLite integrity and foreign-key checks. `uv run python -m compileall -q tools/database tools/import_country_data.py` completed without errors. The full repository suite passed: **145 passed in 2.42s**. WP1.3 is locally validated and closed.


## WP1.4 — ISO, Persian localization, entity classification and flag review

**Status:** Implemented and locally validated by the owner on `work/compiler-hardening`. No source-data approvals or consumer cutover are claimed.

Added:
- `migrations/002_review_domain_status.sql`
- `tools/database/review_data_import.py`
- `tools/import_review_data.py`
- `tests/test_database_review_data_import.py`

Updated the schema to version 2 with `countries.entity_type_status`. New INSERT/UPDATE triggers require a matching approved proposal before an entity classification can be marked reviewed, Persian localization can be marked reviewed, or ISO codes can be marked verified. Verified ISO still requires both alpha-2 and alpha-3. Reviewed flag mappings continue to require an approved flag proposal.

The importer reads the existing identity registry, explicit ISO reference/provenance/proposal inputs, Persian candidate/provenance snapshots, entity taxonomy, and flag mapping. It checks the ISO reference checksum and recomputes proposal rows against the captured reference; it checks Persian QIDs against the explicit Natural Earth `WIKIDATAID` attribute in `country_attributes`; it validates flag and taxonomy schemas; and it requires exact registry/database current-source mapping parity. All writes are transactional and idempotent by deterministic proposal fingerprint. Changed content, conflicting existing rows, missing identities, stale evidence, and invalid approval transitions are rejected.

Unreviewed ISO/Persian/entity/flag values remain candidates. Persian candidate labels are stored only in `review_proposals`, not as canonical `country_names`. Non-unreviewed entity values are proposals with taxonomy requirements recorded as guidance, not evidence. A reviewed flag source mapping must carry an explicit `reviewed_at` timestamp and is not inferred from a source code. Explicitly approved Persian proposals must match the reviewed Persian canonical value in the registry before the canonical name/status is applied. The importer never edits source JSON or generated assets.

### WP1.4 focused validation commands

Run from the repository root after pulling the branch. Use the ISO provenance file and Persian candidate/provenance files from the same captured refreshes; do not mix timestamps.

```fish
uv run pytest -v \
  tests/test_database_review_data_import.py \
  tests/test_database_schema.py \
  tests/test_database_identity_import.py \
  tests/test_database_country_data_import.py

uv run python -m tools.import_identity_registry \
  --database /tmp/tca-wp1-4.sqlite

uv run python -m tools.import_country_data \
  --database /tmp/tca-wp1-4.sqlite

uv run python -m tools.import_review_data \
  --database /tmp/tca-wp1-4.sqlite \
  --registry config/country_identity_registry.json \
  --iso-reference raw_data/iso/iso-3166-1.csv \
  --iso-provenance raw_data/iso/iso-3166-1-provenance-20261023T183945Z.json \
  --iso-proposals reports/iso-assignment-proposals.md \
  --persian-candidates raw_data/persian/wikidata-persian-candidates-20261023T183946Z.json \
  --persian-provenance raw_data/persian/wikidata-persian-provenance-20261023T183946Z.json \
  --entity-taxonomy config/entity_types.json \
  --flag-mapping config/country_flag_mapping.json

uv run python -m compileall -q \
  tools/database tools/import_review_data.py

uv run pytest -v
git status --short
```

Use the same database for all three imports, in the order shown. These paths select the captured ISO reference and Persian candidate/provenance snapshots currently tracked in this branch; keep each candidate paired with its own provenance file. The focused tests cover candidate-only import, repeat-import idempotency, checksum rejection, source-ID/game-ID mismatch, explicit Wikidata QID crosswalk, flag review timestamp requirements, and database review-status triggers.

Record actual schema version, import counts, integrity/foreign-key results, focused and full-suite results, and any unrelated working-tree files. Do not mark WP1.4 locally validated until the owner reports the run. The consolidated null/empty completeness report remains deferred until every WP1 data domain has been visited.


### WP1.4 validation corrections after first owner run

The first focused run correctly exposed stale WP1.1 schema-test expectations: schema migration 002 means a fresh database now reaches version 2 and records two migrations. The schema tests have been updated to assert version 2 and two ledger entries.

The production ISO proposal report reader now locates its table by parsed column names rather than requiring byte-for-byte equality with one Markdown header string. This tolerates harmless whitespace variation while still requiring exactly one table with the expected seven columns. A focused regression test covers that formatting variation.

The first owner run also confirmed schema migration 0→2, successful identity import (242 countries, 250 names, 237 region memberships, 242 source mappings), and successful country data import (40,898 attributes, 242 countries, 726 geometries across three profiles). The review import did not write any data because the ISO header was rejected. WP1.4 remains unvalidated pending rerun of the corrected tests and import.


### WP1.4 owner validation confirmation — 2026-10-31

After pulling the parser and schema-test corrections, the owner ran the focused tests: **33 passed in 0.97s**. The review-domain import completed with **242 countries, 0 entity-type proposals, 242 flag mappings, 242 flag proposals, 242 ISO proposals, and 242 localization proposals**. The importer reported successful SQLite integrity and foreign-key checks. The full repository suite passed: **153 passed in 2.02s**. WP1.4 is locally validated and closed.

The first run's two stale schema-version assertions and strict ISO Markdown-header comparison were corrected before this successful run. The owner reported unrelated working-tree changes (including refreshed source/reference files, generated candidate flags, and modified inspection/review reports); those files were not staged, discarded, or included in this implementation.


## WP1.5 — Selective game data and current statistics

**Status:** In progress. Schema migration 003, field-level source contracts, candidate resource catalogue, source methodology and initial source-licence register are committed. Production source acquisition/importers and owner-side validation remain outstanding.

The owner confirmed that the approved WP1.5 selection is the 41 distinct field IDs in the source contract. Religion (48) and Gini index (56) are included; no additional fields are in scope. Natural Earth is excluded as a source for all WP1.5 statistics/classifications. Candidate assignments are in `config/wp1_5_data_sources.json`; the source methodology and known coverage constraints are in `docs/data-sources/wp1-5-sources.md`; the candidate resource vocabulary is in `config/wp1_5_resource_catalog.json`.

Migration `003_statistics_provenance.sql` upgrades the schema to version 3. It preserves existing scalar observations and adds:
- nullable numeric values with an explicit `unavailable` or `not_applicable` status for SQL NULL;
- `observed`, `estimated` and `projected` states for populated values;
- separate observation period, source reference, source release/version, methodology and retrieval timestamp;
- equivalent source/observation metadata on structured `selected_game_data` rows.

The schema test suite now expects migration version 3 and includes explicit NULL/status and provenance metadata constraints. The future-schema test uses version 4. These tests have been committed but have not yet been run by the owner.

Raw source datasets remain local and untracked. Source contracts, URLs, release identifiers, manifests and SHA-256 checksums are tracked. The initial source-rights review is in `reports/wp1-5-source-licenses.md`; restricted or unclear terms are informational and do not block local acquisition, but do not imply redistribution permission.

Production acquisition must preserve immutable raw snapshots, explicit `game_id` crosswalks, reference periods, release vintages and source coverage. No source value is inferred or filled. The single consolidated completeness report is deferred until every selected field/domain has been visited. Existing JSON pipeline consumers remain unchanged.


### WP1.5 source acquisition foundation

Added `tools/database/source_acquisition.py`, the `tools.acquire_wp1_5_sources` CLI and `tests/test_wp1_5_source_acquisition.py`. The utility accepts only direct HTTPS URLs for source keys declared in the WP1.5 contract, validates safe release/filename components, records final redirect URL and response content type, computes SHA-256 while streaming, optionally checks an expected checksum, and refuses to overwrite an existing raw snapshot or manifest. Raw bytes are kept under `raw_data/wp1_5/`; provenance manifests are written under `data_manifests/wp1_5/` for Git tracking. Failed downloads or checksum mismatches remove the incomplete/untrusted raw file.

This is acquisition infrastructure only. It does not infer provider download URLs, scrape landing pages, normalize source records, map provider country codes, or import values. Those tasks require source-specific contracts and explicit country crosswalks. The source tests and schema-v3 migration tests are pending owner execution.

Run the focused WP1.5 checks after pulling:

```fish
uv run pytest -v tests/test_wp1_5_source_contract.py tests/test_wp1_5_source_acquisition.py tests/test_database_schema.py
uv run python -m tools.migrate_database --database /tmp/tca-wp1-5-schema.sqlite
uv run python -m tools.acquire_wp1_5_sources --help
uv run python -m compileall -q tools/database tools/acquire_wp1_5_sources.py
```

Do not run a source acquisition until the exact provider file URL, release identifier, format, country-code scheme and terms URL have been verified. The placeholder URL in the source-methodology documentation is intentionally non-operational. No WP1.5 production data has yet been acquired or imported.


### WP1.5 explicit source identity crosswalk validation

Added `tools/database/source_crosswalk.py` and `tests/test_wp1_5_source_crosswalk.py`. The validator reads a versioned JSON crosswalk and enforces the expected dataset key, persistent `game_id` syntax, optional membership in the canonical identity set, explicit non-empty provider IDs, unique provider IDs and game IDs, approved match-method vocabulary, and HTTPS evidence URLs. It deliberately rejects fuzzy/name-only matching and does not infer ISO or other provider identifiers. Partial provider coverage is allowed and returned as an explicit coverage summary; uncovered identities remain missing rather than being filled.

The crosswalk JSON shape and a minimal example are documented in `docs/data-sources/wp1-5-sources.md`. This commit adds validation only: it does not yet write provider mappings into `country_sources` or import statistical/game values. Owner-side test execution is pending.

Focused validation:

```fish
uv run pytest -v tests/test_wp1_5_source_crosswalk.py tests/test_wp1_5_source_acquisition.py tests/test_wp1_5_source_contract.py
uv run python -m compileall -q tools/database
``


### WP1.5 transactional normalized-observation importer

Added `tools/database/statistics_import.py`, the `tools/import_wp1_5.py` CLI, and `tests/test_wp1_5_statistics_import.py`. The importer accepts normalized provider observations, an explicit source crosswalk, and the immutable acquisition manifest. It verifies the captured raw-file checksum, source/release consistency, the 41-field contract, contracted primary-source ownership, crosswalk identity pairs, canonical database identities, observation periods, scalar/structured value types, and status/null semantics before writing.

Scalar observations populate `current_statistics`; structured observations populate `selected_game_data`. Both retain source reference, release, method, observation period, retrieval timestamp and observed/estimated/projected status. Explicit scalar NULL is accepted only with `unavailable` or `not_applicable`. Duplicate country/field rows are rejected. A new release from the same contracted provider replaces that provider's current value while retaining its source-import record; a conflicting value owned by a different provider is rejected. Writes are transactional, and SQLite integrity/foreign-key checks run before commit.

This importer is deliberately downstream of provider-specific parsers: it does not parse raw provider formats, decide field methodology, infer country matches, or fill absent rows. It does not approve source imports or country review states, populate `country_sources`, change JSON consumers, or generate the consolidated completeness audit.

Focused validation commands:

```fish
uv run pytest -v \
  tests/test_wp1_5_statistics_import.py \
  tests/test_wp1_5_source_crosswalk.py \
  tests/test_wp1_5_source_acquisition.py \
  tests/test_wp1_5_source_contract.py \
  tests/test_database_schema.py

uv run python -m tools.import_wp1_5 --help
uv run python -m compileall -q tools/database tools/import_wp1_5.py
```

Owner-side validation is pending.


### WP1.5 normalized observation importer and crosswalk persistence

The existing normalized importer in \`tools/database/statistics_import.py\` is the single import implementation; the CLI is \`tools/import_wp1_5.py\`. It validates the 41-field contract, source assignment, manifest release/checksum, explicit crosswalk pairs, canonical country identities, observation period, units, status and scalar/structured value shape before writing.

The importer now persists every explicit provider-ID mapping from the crosswalk in \`country_sources\`, linked to the source dataset import. Existing current mappings are accepted only when they identify the same \`game_id\`; a remapping is rejected and requires a separate identity-review operation. The importer also rejects crosswalk identities absent from the canonical database and timezone-naive retrieval timestamps. For scalar observations, \`observed_at\` is left NULL because the source reference period is stored separately in \`observation_period\`; this avoids treating a period label such as \`2024\` as a timestamp. Missing methodology text falls back to the field contract's documented method.

All source mappings, dataset provenance and observation rows are written in one transaction. A conflict rolls back the complete import. Existing current values from another source are protected; a newer release from the same contracted provider may replace its current value while the previous \`dataset_imports\` provenance row remains. The importer does not parse provider-native files, invent missing observations, or promote review/verification statuses.

Added regression coverage for crosswalk persistence (including mapped countries with no observation in that file) and timezone-aware retrieval metadata. Owner-side execution of the updated importer tests is pending.
