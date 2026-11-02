"""Run the automatic, read-only WP1.5 validation suite."""
from __future__ import annotations

import argparse
import json
import sys

from tools.wp1_5_validation import ValidationError, run_validation
from tools.wp1_5_validators.un_wpp import UNWPPValidator

VALIDATORS = {"un_wpp": UNWPPValidator}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=sorted(VALIDATORS))
    args = parser.parse_args(argv)
    try:
        report, output = run_validation(args.source, VALIDATORS[args.source]())
    except (ValidationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"WP1.5 validation failed to run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "source": args.source, "result": report["result"],
        "candidate": report["candidate_directory"], "release": report["release"],
        "checks": len(report["checks"]), "exceptions": len(report["exception_rows"]),
        "report_directory": str(output),
        "database_written": False, "approval_created": False, "release_promoted": False,
    }, indent=2))
    return 1 if report["result"] == "FAIL" else 0

if __name__ == "__main__":
    raise SystemExit(main())
