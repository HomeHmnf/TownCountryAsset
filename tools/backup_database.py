#!/usr/bin/env python3
"""Create and verify a timestamped SQLite online backup."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.database.backup import create_verified_backup
from tools.database.connection import DEFAULT_DATABASE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path.home() / "Backups/TownCountryAsset",
    )
    parser.add_argument("--prefix")
    args = parser.parse_args()
    result = create_verified_backup(args.database, args.backup_dir, prefix=args.prefix)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
