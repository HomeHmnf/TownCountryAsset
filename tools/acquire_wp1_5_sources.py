"""Capture an immutable WP1.5 source snapshot and tracked manifest."""
from __future__ import annotations
import argparse
import json
from tools.database.source_acquisition import SourceAcquisitionError, acquire_source_snapshot

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--url", required=True, help="direct HTTPS download URL")
    parser.add_argument("--filename", required=True)
    parser.add_argument("--terms-url")
    parser.add_argument("--attribution")
    parser.add_argument("--license-status", default="unclear_or_unverified")
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    try:
        result = acquire_source_snapshot(source_key=args.source, release=args.release,
            url=args.url, filename=args.filename, terms_url=args.terms_url,
            attribution=args.attribution, license_status=args.license_status,
            expected_sha256=args.sha256)
    except SourceAcquisitionError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
