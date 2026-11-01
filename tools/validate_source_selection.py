"""Validate the approved source-selection policy against the central registry."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from tools.database.source_selection import SourceSelectionError, load_policy
from tools.sources.registry import SourceError, load_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("config/source_selection.json"))
    parser.add_argument("--registry", type=Path, default=Path("config/data_sources.json"))
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
        policy = load_policy(args.policy, registry)
    except (SourceError, SourceSelectionError) as exc:
        print(f"Source-selection validation failed: {exc}", file=sys.stderr)
        return 1
    counts = Counter(field["selection_mode"] for field in policy["fields"])
    print(f"Source-selection policy v{policy['policy_version']}: valid")
    print(f"Fields: {len(policy['fields'])}")
    for mode in ("priority_source", "primary_with_fallback", "custom_mixture"):
        print(f"{mode}: {counts.get(mode, 0)}")
    print(f"Registered sources: {len(registry['sources'])}")
    print("Release selection: latest_validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
