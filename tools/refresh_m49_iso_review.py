"""Acquire official UN M49 through the central source manager and propose ISO candidates."""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tools.propose_iso_assignments import propose, read_reference, render_report
from tools.sources.catalog import source_url
from tools.sources.m49 import parse_m49_html, render_iso_reference_csv
from tools.sources.registry import REGISTRY as SOURCE_REGISTRY, SourceError, acquire_one, inspect_snapshots, load_registry

SOURCE_ID = "un_m49"
DOWNLOAD_ID = "country_area_overview_html"
SOURCE_URL = source_url(SOURCE_ID, DOWNLOAD_ID)
DEFAULT_OUTPUT_DIR = Path("raw_data/iso")
DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_REPORT = Path("reports/iso-assignment-proposals.md")

def refresh(registry_path=DEFAULT_REGISTRY, output_dir=DEFAULT_OUTPUT_DIR,
            report_path=DEFAULT_REPORT, source_url_override=None, now=None,
            source_registry_path=SOURCE_REGISTRY):
    retrieved = now or datetime.now(timezone.utc)
    if retrieved.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    retrieved = retrieved.astimezone(timezone.utc)
    stamp = retrieved.strftime("%Y%m%dT%H%M%SZ")

    source_registry = load_registry(source_registry_path)
    source = source_registry["sources"].get(SOURCE_ID)
    if not source:
        raise SourceError(f"Source registry does not contain {SOURCE_ID}")
    item = next((entry for entry in source.get("downloads", [])
                 if entry.get("id") == DOWNLOAD_ID), None)
    if not item:
        raise SourceError("UN M49 HTML download is not configured")
    if source_url_override:
        item = {**item, "url": source_url_override}

    snapshot = next((row for row in inspect_snapshots(source_registry)
                     if row["source_id"] == SOURCE_ID and row["download_id"] == DOWNLOAD_ID), None)
    if snapshot is None:
        raise SourceError("UN M49 snapshot status could not be determined")
    if snapshot["status"] == "missing":
        acquire_one(source_registry, SOURCE_ID, item)
        snapshot = next(row for row in inspect_snapshots(source_registry)
                        if row["source_id"] == SOURCE_ID and row["download_id"] == DOWNLOAD_ID)
    if snapshot["status"] != "valid":
        raise SourceError(f"UN M49 source snapshot is {snapshot['status']}: {snapshot['detail']}")

    root = source_registry.get("_root")
    raw_path = root / source_registry["storage"]["raw_root"] / SOURCE_ID / item["id"] / item["release"] / item["filename"]
    manifest_path = root / source_registry["storage"]["manifest_root"] / SOURCE_ID / item["id"] / f"{item['release']}.json"
    raw = raw_path.read_bytes()
    url = item["url"]
    try:
        parsed = parse_m49_html(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"UN M49 HTML parsing failed: {exc}") from exc

    normalized = render_iso_reference_csv(parsed)
    digest = hashlib.sha256(raw).hexdigest()
    normalized_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = output_dir / "m49-iso-reference.csv"
    normalized_m49_path = output_dir / "m49-country-area.json"
    metadata_path = output_dir / f"m49-provenance-{stamp}.json"
    if metadata_path.exists():
        raise FileExistsError(f"Review provenance already exists for timestamp {stamp}")
    normalized_path.write_text(normalized, encoding="utf-8", newline="")
    normalized_m49_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "source_id": SOURCE_ID, "dataset": "UNSD M49 country and area overview",
        "source_url": url, "retrieved_at_utc": retrieved.isoformat(),
        "raw_snapshot": str(raw_path), "source_manifest": str(manifest_path),
        "raw_sha256": digest, "normalized_reference": str(normalized_path),
        "normalized_m49_data": str(normalized_m49_path),
        "normalized_sha256": normalized_digest,
        "m49_row_count": parsed["row_count"],
        "iso_candidate_count": parsed["iso_candidate_count"],
        "rows_without_iso_codes": parsed["excluded_without_iso"],
        "table_headers": parsed["headers"],
        "parser": "tools.sources.m49.parse_m49_html",
        "parser_contract_version": 2,
        "selected_table_id": parsed["table_id"],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    identity_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    reference = read_reference(normalized_path)
    result = propose(identity_registry, reference)
    report = render_report(
        result, str(normalized_path),
        f"{url} (official United Nations Statistics Division M49 reference; ISO codes are cross-references)",
        retrieved.date().isoformat(),
    )
    report += (
        "\n## M49 acquisition and parsing provenance\n\n"
        f"- Raw HTML snapshot: {raw_path}\n"
        f"- Source manifest: {manifest_path}\n"
        f"- Parser provenance: {metadata_path}\n"
        f"- Raw SHA-256: {digest}\n"
        f"- M49 rows: {parsed['row_count']}\n"
        f"- Rows without ISO codes (retained in provenance, not proposed): {len(parsed['excluded_without_iso'])}\n"
        "- UN M49 republishes ISO alpha-code cross-references; it is not the ISO 3166 assignment authority. All proposals require human review.\n"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return {
        "raw_snapshot": str(raw_path), "source_manifest": str(manifest_path),
        "normalized_reference": str(normalized_path), "normalized_m49_data": str(normalized_m49_path),
        "provenance": str(metadata_path),
        "report": str(report_path), "raw_sha256": digest,
        "normalized_sha256": normalized_digest, "m49_row_count": parsed["row_count"],
        "iso_candidate_count": parsed["iso_candidate_count"],
        "excluded_without_iso_count": len(parsed["excluded_without_iso"]),
        "candidate_count": result["candidate_count"],
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY,
                        help="Country identity registry used for review proposals")
    parser.add_argument("--source-registry", type=Path, default=SOURCE_REGISTRY,
                        help="Central project source registry")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-url", default=None)
    args = parser.parse_args()
    try:
        result = refresh(args.registry, args.output_dir, args.report, args.source_url,
                         source_registry_path=args.source_registry)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
