"""Create or upgrade the local canonical SQLite database schema."""

from __future__ import annotations

import argparse
from contextlib import closing

from tools.database.connection import DEFAULT_DATABASE_PATH, connect_database
from tools.database.schema import apply_migrations, current_schema_version, validate_database


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_DATABASE_PATH), help="Local SQLite database path")
    args = parser.parse_args()

    with closing(connect_database(args.database)) as connection:
        previous = current_schema_version(connection)
        current = apply_migrations(connection)
        issues = validate_database(connection)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    print(f"Database: {args.database}")
    print(f"Schema version: {previous} -> {current}")
    print("SQLite integrity and foreign-key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
