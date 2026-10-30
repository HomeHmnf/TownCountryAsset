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

**Status:** Implemented; local test execution is pending in the developer checkout.

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

Record the actual local output here after running these commands. Do not mark WP1.1 locally validated until they pass in the developer checkout.
