"""Import one normalized WP1.5 source dataset into canonical SQLite."""
from __future__ import annotations

import argparse
import json

from tools.database.statistics_import import StatisticsImportError, import_wp1_5_dataset
from tools.database.schema import MigrationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import normalized WP1.5 observations with source manifest and explicit country crosswalk."
    )
    parser.add_argument("--observations", required=True, help="Normalized WP1.5 observations JSON")
    parser.add_argument("--crosswalk", required=True, help="Explicit provider-ID to game_id crosswalk JSON")
    parser.add_argument("--manifest", required=True, help="Immutable source acquisition manifest JSON")
    parser.add_argument("--database", help="Canonical SQLite database path")
    parser.add_argument("--config", help="WP1.5 field contract JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    kwargs = {
        "observations_path": args.observations,
        "crosswalk_path": args.crosswalk,
        "manifest_path": args.manifest,
    }
    if args.database:
        kwargs["database_path"] = args.database
    if args.config:
        kwargs["config_path"] = args.config
    try:
        result = import_wp1_5_dataset(**kwargs)
    except (StatisticsImportError, MigrationError, OSError, ValueError) as exc:
        print(f"WP1.5 import failed: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
