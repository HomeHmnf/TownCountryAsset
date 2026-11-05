"""Synchronize stable source identities and configured URLs into the project DB."""

from __future__ import annotations

import argparse

from tools.database.project_connection import DEFAULT_PROJECT_DATABASE_PATH
from tools.database.source_catalogue import (
    DEFAULT_SOURCE_CONFIG_PATH,
    sync_source_catalogue,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_PROJECT_DATABASE_PATH))
    parser.add_argument("--config", default=str(DEFAULT_SOURCE_CONFIG_PATH))
    args = parser.parse_args()
    counts = sync_source_catalogue(database_path=args.database, config_path=args.config)
    print(f"Project database: {args.database}")
    print(f"Sources synchronized: {counts['sources']}")
    print(f"Source URLs synchronized: {counts['source_urls']}")
    print("No datasets, acquisition streams, acquisitions or source-selection settings were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
