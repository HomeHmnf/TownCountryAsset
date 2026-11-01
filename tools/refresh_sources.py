"""Refresh configured project-wide source snapshots without importing data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.sources.refresh import run_refresh
from tools.sources.registry import REGISTRY, SourceError, load_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--source", action="append", dest="sources")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
        report = run_refresh(
            registry,
            source_ids=args.sources,
            timeout=args.timeout,
            dry_run=args.dry_run,
        )
        print(json.dumps({
            "run_id": report["run_id"],
            "counts": report["counts"],
            "database_imported": report["database_imported"],
            "reports": report["report_paths"],
        }, indent=2, ensure_ascii=False))
        failures = {"validation_error", "acquisition_failed"}
        return 1 if any(
            item["status"] in failures
            for source in report["sources"]
            for item in source["downloads"]
        ) else 0
    except SourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
