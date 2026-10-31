"""Import the persistent identity registry into the local canonical SQLite database."""

from __future__ import annotations

import argparse
import json

from tools.database.connection import DEFAULT_DATABASE_PATH
from tools.database.identity_import import (
    DEFAULT_CANDIDATE_DIR,
    DEFAULT_REGISTRY_PATH,
    import_identity_registry,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import identity registry and source provenance into canonical SQLite."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE_PATH))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATE_DIR))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = import_identity_registry(args.database, args.registry, args.candidate_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    print("Identity registry import completed; database integrity and foreign-key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
