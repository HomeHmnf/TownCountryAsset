# Data-store separation — Stage 0 inventory

**Status:** In progress; repository inspection only. Local database and filesystem baselines are pending owner-run read-only inventory.
**Plan:** [Data-store separation plan](../architecture/data-store-separation-plan.md)
**Target branch:** `work/compiler-hardening`
**Last updated:** 2026-11-05

## Purpose and safety boundary

Establish a reproducible baseline of the current schema-v4 database, all database consumers, source configuration, source snapshots, manifests, derived files and reports before any schema or retention implementation.

This stage is read-only. It must not:
- create or migrate either database;
- alter source-selection configuration or overrides;
- download, move, rename, rewrite or delete source files;
- delete older snapshots in advance of the future retention feature;
- stage or commit generated/local data artifacts.

Repository inspection through GitHub is useful for code and tracked documentation, but it does not reveal ignored/local-only files or the actual contents of the owner's local SQLite database. The owner-run inventory is therefore the authoritative local baseline.

## 1. Repository-level inventory

Record:
- all migration files and schema version;
- every database connection, schema initializer, importer, resolver, approval/apply tool and runtime consumer;
- every direct reference to the canonical database path and source configuration;
- all source IDs, dataset IDs and acquisition stream definitions in JSON;
- source-selection policy coverage and override references, without changing them;
- documentation for source-specific acquisition, validation, extraction and application;
- configured roots and actual tracked/untracked/ignored status of raw data, manifests, reports and PDF derivatives.

Repository inspection has confirmed migrations 001–004 and the current schema-v4 design. The canonical database currently mixes game-facing records with source/research and approval records. Exact table/column disposition remains pending local inventory and code-consumer review.

## 2. Owner-run local baseline

Run the read-only command below from the repository root using Fish. It reports:
- Git branch and working-tree status;
- SQLite schema version, tables, columns, indexes, foreign keys and row counts;
- database file size;
- file counts, total bytes, extensions and symlink counts under source snapshots, manifests, PDF text derivatives and source reports;
- whether the proposed project DB path already exists.

It does not read or print source payload contents, and does not modify files or databases.

```fish
uv run python - <<'PY'
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

root = Path.cwd()
db_path = root / "data/canonical/town_country_asset.sqlite"
print("REPOSITORY:", root)
print("DATABASE_EXISTS:", db_path.is_file())
if db_path.is_file():
    print("DATABASE_BYTES:", db_path.stat().st_size)
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    print("SQLITE_VERSION:", sqlite3.sqlite_version)
    print("INTEGRITY_CHECK:", [r[0] for r in con.execute("PRAGMA integrity_check")])
    print("FOREIGN_KEY_CHECK:", [tuple(r) for r in con.execute("PRAGMA foreign_key_check")])
    tables = [
        r["name"] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    print("TABLE_COUNT:", len(tables))
    for table in tables:
        quoted = '"' + table.replace('"', '""') + '"'
        count = con.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
        columns = [dict(r) for r in con.execute(f"PRAGMA table_info({quoted})")]
        indexes = [dict(r) for r in con.execute(f"PRAGMA index_list({quoted})")]
        foreign_keys = [dict(r) for r in con.execute(f"PRAGMA foreign_key_list({quoted})")]
        print("TABLE:", json.dumps({
            "name": table,
            "rows": count,
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": foreign_keys,
        }, ensure_ascii=False))
    migration_rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if migration_rows:
        print("MIGRATIONS:", [dict(r) for r in con.execute("SELECT * FROM schema_migrations ORDER BY 1")])
    con.close()

for rel in (
    "raw_data/sources",
    "data_manifests/sources",
    "derived_data/pdf_text",
    "reports/sources",
):
    base = root / rel
    if not base.exists():
        print("FILESYSTEM:", json.dumps({"root": rel, "exists": False}))
        continue
    files = 0
    total_bytes = 0
    symlinks = 0
    extensions = Counter()
    for path in base.rglob("*"):
        if path.is_symlink():
            symlinks += 1
            continue
        if path.is_file():
            files += 1
            total_bytes += path.stat().st_size
            extensions[path.suffix.lower() or "<no extension>"] += 1
    print("FILESYSTEM:", json.dumps({
        "root": rel,
        "exists": True,
        "files": files,
        "bytes": total_bytes,
        "symlinks": symlinks,
        "extensions": dict(sorted(extensions.items())),
    }, ensure_ascii=False))

project_db = root / "data/project/project_data.sqlite"
print("PROJECT_DATABASE_ALREADY_EXISTS:", project_db.exists())
PY

git status --short --branch
```

Paste the complete output. If it is too long, save it locally and paste it in sections, preserving all `TABLE:`, `FILESYSTEM:`, integrity and migration lines. Do not commit the output or database.

## 3. Detailed classification to complete from baseline

For every current table and column, classify it as one of:
- **Game DB:** required by game runtime or game-facing application.
- **Project DB:** source catalogue, URLs, acquisitions, source observations, crosswalks, field mappings, validation/comparison or governance.
- **Split:** current table/record combines game and project responsibilities and needs a normalized migration.
- **Retire:** demonstrably obsolete only after its replacement and all references are verified.
- **Undecided:** insufficient evidence; no migration decision until resolved.

For each filesystem artifact, record:
- owning source ID and dataset/acquisition stream ID;
- acquisition/version identity where known;
- artifact role (snapshot, manifest, extracted text, validation report, comparison report, other);
- whether it is source payload, a derivative, or a stable catalogue/configuration file;
- whether it is tracked, ignored, local-only or generated;
- exact retention dependency and deletion safety requirements.

Do not infer that a file is disposable because it is old or unreferenced by a guessed naming convention.

## 4. Required Stage 0 outputs

Stage 0 is complete only when the following are documented and reviewed:
1. Exact local DB table/column/index/FK/row-count baseline and integrity results.
2. Table/column disposition matrix with evidence of which code paths consume each record.
3. Complete inventory of source acquisition streams and their retained local artifacts.
4. File-to-manifest/database reference reconciliation, including orphan and missing-reference lists.
5. Consumer map: game runtime, build/compiler, acquisition, validation, source selection, approval and application.
6. Existing approval transaction/recovery behavior and constraints for a two-database replacement.
7. Data parity and rollback baseline for migration.
8. Explicit list of unresolved questions. Unknowns remain unresolved; do not silently decide them.

## 5. Stage 0 exit gate

No schema implementation or cleanup begins until the owner has reviewed the inventory and the table/file disposition. The inventory must establish what the future two-version retention process would keep and what it would remove, without deleting anything now.
