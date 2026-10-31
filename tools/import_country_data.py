"""Import Natural Earth country attributes and geometries into canonical SQLite."""

from __future__ import annotations

import argparse
import json

from tools.database.connection import DEFAULT_DATABASE_PATH
from tools.database.country_data_import import DEFAULT_CANDIDATE_DIR, import_country_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Natural Earth source attributes and game-ID geometry profiles into canonical SQLite."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE_PATH))
    parser.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATE_DIR))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = import_country_data(args.database, args.candidate_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    print("Country metadata and geometry import completed; database integrity and foreign-key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
