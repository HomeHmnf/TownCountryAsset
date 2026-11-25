"""Non-mutating validation for normalized WP1.5 statistics imports."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.database.statistics_import import StatisticsImportError, validate_wp1_5_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path,
        default=Path("config/wp1_5_data_sources.json"),
    )
    args = parser.parse_args(argv)
    try:
        result = validate_wp1_5_dataset(
            observations_path=args.observations,
            crosswalk_path=args.crosswalk,
            manifest_path=args.manifest,
            config_path=args.config,
        )
    except (StatisticsImportError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
