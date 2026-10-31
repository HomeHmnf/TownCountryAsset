"""Acquire official UN M49 HTML and generate review-only ISO proposals."""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tools.propose_iso_assignments import propose, read_reference, render_report
from tools.sources.catalog import source_url
from tools.sources.m49 import parse_m49_html, render_iso_reference_csv
from tools.refresh_iso_review import fetch_bytes

SOURCE_ID = "un_m49"
SOURCE_URL = source_url(SOURCE_ID, "country_area_overview_html")
DEFAULT_OUTPUT_DIR = Path("raw_data/iso")
DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_REPORT = Path("reports/iso-assignment-proposals.md")

def refresh(registry_path=DEFAULT_REGISTRY, output_dir=DEFAULT_OUTPUT_DIR,
            report_path=DEFAULT_REPORT, source_url_override=None, now=None):
    retrieved = now or datetime.now(timezone.utc)
    if retrieved.tzinfo is None: raise ValueError("now must be timezone-aware")
    retrieved = retrieved.astimezone(timezone.utc)
    stamp = retrieved.strftime("%Y%m%dT%H%M%SZ")
    url = source_url_override or SOURCE_URL
    raw = fetch_bytes(url)
    try:
        parsed = parse_m49_html(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"UN M49 HTML validation failed: {exc}") from exc
    normalized = render_iso_reference_csv(parsed)
    digest = hashlib.sha256(raw).hexdigest()
    normalized_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"m49-country-area-{stamp}.html"
    normalized_path = output_dir / "m49-iso-reference.csv"
    metadata_path = output_dir / f"m49-provenance-{stamp}.json"
    if raw_path.exists() or metadata_path.exists():
        raise FileExistsError(f"Snapshot already exists for timestamp {stamp}")
    raw_path.write_bytes(raw)
    normalized_path.write_text(normalized, encoding="utf-8", newline="")
    metadata = {
        "source_id": SOURCE_ID, "dataset": "UNSD M49 country and area overview",
        "source_url": url, "retrieved_at_utc": retrieved.isoformat(),
        "raw_snapshot": str(raw_path), "raw_sha256": digest,
        "normalized_reference": str(normalized_path),
        "normalized_sha256": normalized_digest,
        "m49_row_count": parsed["row_count"],
        "iso_candidate_count": parsed["iso_candidate_count"],
        "rows_without_iso_codes": parsed["excluded_without_iso"],
        "table_headers": parsed["headers"],
        "parser": "tools.sources.m49.parse_m49_html",
        "parser_contract_version": 1,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    reference = read_reference(normalized_path)
    result = propose(registry, reference)
    report = render_report(
        result, str(normalized_path),
        f"{url} (official United Nations Statistics Division M49 reference; ISO codes are cross-references)",
        retrieved.date().isoformat(),
    )
    report += (
        "\\n## M49 acquisition and parsing provenance\\n\\n"
        f"- Raw HTML snapshot: `{raw_path}`\\n"
        f"- Provenance: `{metadata_path}`\\n"
        f"- Raw SHA-256: `{digest}`\\n"
        f"- M49 rows: {parsed['row_count']}\\n"
        f"- Rows without ISO codes (retained in provenance, not proposed): {len(parsed['excluded_without_iso'])}\\n"
        "- UN M49 republishes ISO alpha-code cross-references; it is not the ISO 3166 assignment authority. All proposals require human review.\\n"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return {"raw_snapshot": str(raw_path), "normalized_reference": str(normalized_path),
            "provenance": str(metadata_path), "report": str(report_path),
            "raw_sha256": digest, "normalized_sha256": normalized_digest,
            "m49_row_count": parsed["row_count"],
            "iso_candidate_count": parsed["iso_candidate_count"],
            "excluded_without_iso_count": len(parsed["excluded_without_iso"]),
            "candidate_count": result["candidate_count"]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-url", default=None)
    args = parser.parse_args()
    try:
        result = refresh(args.registry, args.output_dir, args.report, args.source_url)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
