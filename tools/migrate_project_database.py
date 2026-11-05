"""Create or upgrade the local project source/research SQLite database."""

from __future__ import annotations

import argparse
from contextlib import closing

from tools.database.project_connection import (
    DEFAULT_PROJECT_DATABASE_PATH,
    PROJECT_MIGRATIONS_DIR,
    connect_project_database,
)
from tools.database.schema import (
    apply_migrations,
    current_schema_version,
    validate_database,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        default=str(DEFAULT_PROJECT_DATABASE_PATH),
        help="Local project database path",
    )
    args = parser.parse_args()

    with closing(connect_project_database(args.database)) as connection:
        previous = current_schema_version(connection)
        current = apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        issues = validate_database(connection)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    print(f"Project database: {args.database}")
    print(f"Schema version: {previous} -> {current}")
    print("SQLite integrity and foreign-key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
