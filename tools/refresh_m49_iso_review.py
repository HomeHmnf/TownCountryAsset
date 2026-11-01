"""Acquire official UN M49 and generate review-only ISO and full identity reconciliation reports."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from tools.database.identity_reconciliation import reconcile_identities
from tools.database.reporting import emit_terminal_report, write_report_bundle
from tools.propose_iso_assignments import (
    REVIEWED_NAME_VARIANTS, propose, read_reference, render_report,
)
from tools.sources.catalog import source_url
from tools.sources.m49 import parse_m49_html, render_iso_reference_csv
from tools.sources.registry import (
    REGISTRY as SOURCE_REGISTRY, SourceError, acquire_one, inspect_snapshots, load_registry,
)

SOURCE_ID = "un_m49"
DOWNLOAD_ID = "country_area_overview_html"
SOURCE_URL = source_url(SOURCE_ID, DOWNLOAD_ID)
DEFAULT_OUTPUT_DIR = Path("raw_data/iso")
DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_REPORT = Path("reports/iso-assignment-proposals.md")
DEFAULT_REPORT_ROOT = Path("reports")
RECONCILIATION_FIELDS = {
    "game_id": "game_id",
    "registry_name": "names.en",
    "source_id": "source.current_source_id",
    "existing_alpha2": "iso.alpha2",
    "existing_alpha3": "iso.alpha3",
    "reference_name": "Country or Area",
    "reference_id": "M49 Code",
    "reference_alpha2": "ISO-alpha2 Code",
    "reference_alpha3": "ISO-alpha3 Code",
}


def _render_reconciliation_summary(result, *, source_url, raw_sha256, normalized_sha256,
                                   registry_sha256, generated_at):
    summary = result["summary"]
    lines = [
        "# Identity reconciliation — UN M49",
        "",
        f"- Generated at (UTC): {generated_at}",
        f"- Reference: {source_url}",
        f"- Raw snapshot SHA-256: {raw_sha256}",
        f"- Normalized reference SHA-256: {normalized_sha256}",
        f"- Identity registry SHA-256: {registry_sha256}",
        "- Matching uses normalized English names and explicitly maintained name variants only.",
        "- ISO codes and source identifiers are compared only after a name match; they are never used to infer identity.",
        "- This report is read-only evidence. It does not change the registry or approve/verify assignments.",
        "",
        "## Coverage",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| Registry identities | {summary['registry_count']} |",
        f"| M49 reference rows | {summary['reference_count']} |",
        f"| Unique name matches | {summary['matched_count']} |",
        f"| Unmatched registry identities | {summary['unmatched_registry_count']} |",
        f"| Ambiguous registry identities | {summary['ambiguous_registry_count']} |",
        f"| Unmatched reference rows | {summary['unmatched_reference_count']} |",
        "",
        "## Code comparisons",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| Exact English-name matches | {summary['name_comparisons']['exact']} |",
        f"| Normalized name variations | {summary['name_comparisons']['normalized_variation']} |",
        f"| Explicit reviewed name variants | {summary['name_comparisons']['explicit_variant']} |",
        f"| Alpha-2 agreements | {summary['alpha2_matches']} |",
        f"| Alpha-2 mismatches | {summary['alpha2_mismatches']} |",
        f"| Alpha-3 agreements | {summary['alpha3_matches']} |",
        f"| Alpha-3 mismatches | {summary['alpha3_mismatches']} |",
        "",
        "## Combined classifications",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    for key, count in summary["code_pair_classifications"].items():
        lines.append(f"| {key} | {count} |")
    lines.extend([
        "",
        "## Source identifier comparison (not an ISO conflict)",
        "",
        f"- Source ID equals reference alpha-3: {summary['source_id_alpha3_same']}",
        f"- Source ID differs from reference alpha-3: {summary['source_id_alpha3_different']}",
        "",
        "A source identifier may happen to equal an ISO alpha-3 code. That coincidence is not independent evidence of an ISO assignment.",
        "",
        "## Artifacts",
        "",
        "- `records.csv`: one row for every registry identity, with individual alpha-2/alpha-3 comparisons.",
        "- `unmatched_registry.csv`: registry identities without a unique name match, including ambiguous matches.",
        "- `unmatched_reference.csv`: M49 rows not uniquely associated with a registry identity.",
        "- `provenance.json`: source, parser, checksums, field mapping and matching policy.",
    ])
    return "\n".join(lines) + "\n"


def refresh(registry_path=DEFAULT_REGISTRY, output_dir=DEFAULT_OUTPUT_DIR,
            report_path=DEFAULT_REPORT, source_url_override=None, now=None,
            source_registry_path=SOURCE_REGISTRY, report_root=DEFAULT_REPORT_ROOT):
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
    registry_bytes = registry_path.read_bytes()
    registry_digest = hashlib.sha256(registry_bytes).hexdigest()
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

    identity_registry = json.loads(registry_bytes.decode("utf-8"))
    reference = read_reference(normalized_path)
    proposals = propose(identity_registry, reference)
    proposal_report = render_report(
        proposals, str(normalized_path),
        f"{url} (official United Nations Statistics Division M49 reference; ISO codes are cross-references)",
        retrieved.date().isoformat(),
    )
    proposal_report += (
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
    report_path.write_text(proposal_report, encoding="utf-8")

    reconciliation = reconcile_identities(
        identity_registry, parsed["all_rows"], fields=RECONCILIATION_FIELDS,
        name_variants=REVIEWED_NAME_VARIANTS,
    )
    reconciliation_summary = _render_reconciliation_summary(
        reconciliation, source_url=url, raw_sha256=digest,
        normalized_sha256=normalized_digest, registry_sha256=registry_digest,
        generated_at=retrieved.isoformat(),
    )
    report_paths = write_report_bundle(
        report_root, database_id="town_country_asset", domain="identity",
        report_id="m49-current", summary_markdown=reconciliation_summary,
        records=reconciliation["records"],
        unmatched_registry=reconciliation["unmatched_registry"] + reconciliation["ambiguous_registry"],
        unmatched_reference=reconciliation["unmatched_reference"],
        provenance={
            "schema_version": 1, "database_id": "town_country_asset",
            "report_type": "identity_reconciliation", "provider": SOURCE_ID,
            "source_url": url, "source_release": item["release"],
            "retrieved_at_utc": retrieved.isoformat(),
            "raw_snapshot": str(raw_path), "raw_sha256": digest,
            "source_manifest": str(manifest_path),
            "normalized_reference": str(normalized_path),
            "normalized_sha256": normalized_digest,
            "normalized_m49_data": str(normalized_m49_path),
            "identity_registry": str(registry_path),
            "identity_registry_sha256": registry_digest,
            "parser": "tools.sources.m49.parse_m49_html",
            "parser_contract_version": 2, "selected_table_id": parsed["table_id"],
            "field_mapping": RECONCILIATION_FIELDS,
            "matching_policy": "normalized English names plus explicit reviewed variants; no fuzzy, code, or source-ID matching",
            "read_only": True,
            "summary": reconciliation["summary"],
        },
    )
    return {
        "raw_snapshot": str(raw_path), "source_manifest": str(manifest_path),
        "normalized_reference": str(normalized_path), "normalized_m49_data": str(normalized_m49_path),
        "provenance": str(metadata_path), "report": str(report_path),
        "raw_sha256": digest, "normalized_sha256": normalized_digest,
        "m49_row_count": parsed["row_count"], "iso_candidate_count": parsed["iso_candidate_count"],
        "excluded_without_iso_count": len(parsed["excluded_without_iso"]),
        "candidate_count": proposals["candidate_count"],
        "identity_reconciliation": reconciliation, "identity_report_paths": report_paths,
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
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--quiet", action="store_true",
                             help="Write reports but suppress the successful terminal summary")
    output_mode.add_argument("--verbose", action="store_true",
                             help="Write reports and print detailed reconciliation counts")
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT,
                        help="Root directory for standardized database report bundles")
    args = parser.parse_args()
    try:
        result = refresh(args.registry, args.output_dir, args.report, args.source_url,
                         source_registry_path=args.source_registry, report_root=args.report_root)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    emit_terminal_report(
        result["identity_reconciliation"], result["identity_report_paths"],
        quiet=args.quiet, verbose=args.verbose,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
