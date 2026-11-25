"""Build the single consolidated IMF WEO–WDI review package.

The package is diagnostic/review-only. It never approves observations or writes
normalized application data or either SQLite database.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_ROOT = ROOT / "reports/sources/imf-weo-wdi-review"
REQUIRED = {
    "game_id", "country_name", "field_id", "year", "identity_gate",
    "semantic_disposition", "field_gate", "country_case_id",
    "country_case_disposition", "evidence_documents",
}
DECISIONS = {"pending", "approve", "exclude", "hold_for_evidence", "not_applicable"}


class ReviewPackageError(RuntimeError):
    """Invalid semantic matrix or review package."""


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:16]}"


def _read_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = REQUIRED - set(reader.fieldnames or [])
            if missing:
                raise ReviewPackageError(f"Semantic matrix missing required columns: {sorted(missing)}")
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        raise ReviewPackageError(f"Cannot read semantic matrix {path}: {exc}") from exc
    if not rows:
        raise ReviewPackageError("Semantic matrix contains no rows")
    return rows


def _edge_case(
    category: str, key: tuple[str, ...], rows: list[dict[str, str]],
    title: str, finding: str, action: str,
) -> dict[str, str]:
    return {
        "edge_case_id": _stable_id("weo", (category, *key)),
        "category": category,
        "group_key": "|".join(key),
        "title": title,
        "finding": finding,
        "required_action": action,
        "affected_row_ids": ";".join(sorted(r["review_row_id"] for r in rows)),
        "affected_row_count": str(len(rows)),
        "evidence_documents": ";".join(sorted({
            doc for row in rows for doc in (row.get("evidence_documents") or "").split(";") if doc
        })),
        "case_state": "open_review_required",
    }


def build_package(input_path: Path, *, field_ids: set[int] | None = None) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    rows = _read_rows(input_path)
    if field_ids is not None:
        if not field_ids or any(field_id <= 0 for field_id in field_ids):
            raise ReviewPackageError("field_ids must be a non-empty set of positive field IDs")
        rows = [row for row in rows if int(row["field_id"]) in field_ids]
        if not rows:
            raise ReviewPackageError(f"No semantic review rows found for fields {sorted(field_ids)}")
    row_ids: set[str] = set()
    for row in rows:
        key = (row["game_id"], row["field_id"], row["year"])
        row_id = _stable_id("obs", key)
        if row_id in row_ids:
            raise ReviewPackageError(f"Duplicate country/field/year review key: {key}")
        row_ids.add(row_id)
        row["review_row_id"] = row_id
        row["review_decision"] = "pending"
        row["review_note"] = ""
        row["reviewer"] = ""
        row["reviewed_at"] = ""

    grouped: dict[tuple[str, tuple[str, ...]], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("identity_gate") != "identity_verified":
            grouped[("identity", (row["game_id"],))].append(row)
        grouped[("field_semantics", (row["field_id"],))].append(row)
        if row.get("country_case_id") not in {"", "no_specific_country_case_recorded"}:
            grouped[("country_case", (row["game_id"], row["field_id"], row["country_case_id"]))].append(row)
        if row.get("imf_observation_status") in {"", "status_unclassified", "not_classified", "unknown"}:
            grouped[("observation_status", (row["game_id"], row["field_id"]))].append(row)
        if row.get("wdi_observation_status") in {
            "", "wdi_actual_estimate_status_not_established", "not_available_in_input",
        }:
            grouped[("comparison_status", (row["game_id"], row["field_id"]))].append(row)

    edge_cases: list[dict[str, str]] = []
    for (category, key), affected in sorted(grouped.items()):
        first = affected[0]
        if category == "identity":
            title = f"Identity mapping review — {first['country_name']}"
            finding = "One or more observations retain an unverified or unresolved project/source identity mapping."
            action = "Resolve the provider-ID to persistent game_id mapping through the identity governance workflow; do not infer from names."
        elif category == "field_semantics":
            title = f"Field {key[0]} semantic gate"
            finding = first.get("field_gate", "Field semantic evidence remains open.")
            action = "Review the field definition, unit, reference period, methodology and evidence; approve only the country-year rows supported by the evidence."
        elif category == "country_case":
            title = f"{first['country_name']} — field {first['field_id']} — {first['country_case_id']}"
            finding = first.get("country_case_disposition", "Country-specific evidence requires review.")
            action = "Apply only the documented year-bounded evidence. Preserve open years and settled dispositions; do not generalize the case."
        elif category == "observation_status":
            title = f"IMF observation status — {first['country_name']} field {first['field_id']}"
            finding = "IMF observation status is unknown or not classified by available source metadata."
            action = "Confirm status from authoritative source evidence or retain unknown; do not infer estimate/projection from year labels or adjacent indicators."
        else:
            title = f"WDI comparison status — {first['country_name']} field {first['field_id']}"
            finding = "WDI observation status is absent or not classified; comparison presence does not establish semantic equivalence."
            action = "Retain the WDI status as unclassified and use comparison values as diagnostic evidence only."
        edge_cases.append(_edge_case(category, key, affected, title, finding, action))

    case_ids_by_row: dict[str, list[str]] = defaultdict(list)
    for case in edge_cases:
        for row_id in case["affected_row_ids"].split(";"):
            case_ids_by_row[row_id].append(case["edge_case_id"])
    for row in rows:
        row["edge_case_ids"] = ";".join(sorted(case_ids_by_row[row["review_row_id"]]))
        row["review_decision_allowed_values"] = "|".join(sorted(DECISIONS - {"pending"}))

    input_hash = _digest(input_path)
    summary = {
        "schema_version": 1,
        "package_type": "imf_weo_wdi_consolidated_review",
        "source": "imf_weo",
        "release": "october_2026",
        "upstream_semantic_matrix": str(input_path),
        "upstream_semantic_matrix_sha256": input_hash,
        "observation_row_count": len(rows),
        "distinct_project_identities": len({r["game_id"] for r in rows}),
        "field_ids": sorted({int(r["field_id"]) for r in rows}),
        "field_counts": dict(sorted(Counter(r["field_id"] for r in rows).items(), key=lambda x: int(x[0]))),
        "review_decision_counts": {"pending": len(rows)},
        "edge_case_count": len(edge_cases),
        "edge_case_counts_by_category": dict(sorted(Counter(c["category"] for c in edge_cases).items())),
        "review_authority": "review_register.csv",
        "edge_case_role": "linked_work_queue_not_a_separate_decision_surface",
        "decision_vocabulary": sorted(DECISIONS),
        "candidate_is_approved": False,
        "approval_created": False,
        "normalized_application_artifact_created": False,
        "database_written": False,
        "source_policy_changed": False,
    }
    return rows, edge_cases, summary


def write_package(rows: list[dict[str, str]], cases: list[dict[str, str]],
                  summary: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=False)

    for filename, records in (("review_register.csv", rows), ("edge_cases.csv", cases)):
        with (target / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]) if records else [])
            writer.writeheader()
            writer.writerows(records)

    summary["package_directory"] = str(target)
    summary["review_register_sha256"] = _digest(target / "review_register.csv")
    summary["edge_cases_sha256"] = _digest(target / "edge_cases.csv")
    (target / "package.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# IMF WEO–WDI consolidated review package", "",
        f"- Observation rows: {summary['observation_row_count']}",
        f"- Project identities: {summary['distinct_project_identities']}",
        f"- Edge cases: {summary['edge_case_count']}",
        f"- Upstream semantic matrix SHA-256: `{summary['upstream_semantic_matrix_sha256']}`",
        f"- Review register SHA-256: `{summary['review_register_sha256']}`",
        "", "## Single review surface", "",
        "`review_register.csv` is the authoritative decision surface. Enter each observation decision there using `approve`, `exclude`, `hold_for_evidence`, or `not_applicable`; record rationale in `review_note` and reviewer identity/time in the corresponding columns. Leave unsupported rows pending or explicitly held.",
        "", "## Linked edge-case work queue", "",
        "`edge_cases.csv` groups exceptions and links them to affected `review_row_id` values. It is a supporting work queue, not a second decision surface. Record final observation decisions only in `review_register.csv`.",
        "", "## Required safeguards", "",
        "- This package is review-only. It is not a normalized import artifact and creates no approval.",
        "- Identity and semantic gates remain explicit; a source series or numerical match is not identity or semantic approval.",
        "- Unknown actual/estimate/projection status remains unknown.",
        "- Country-specific evidence is bounded to the years documented in the source assessments. Settled cases are not reopened without new evidence.",
        "- If the upstream semantic matrix changes, regenerate the package and re-review; do not transplant decisions by row position.",
        "- After review, a separate validated builder must produce the exact normalized application artifact and dependencies for shared approval.",
        "", "## Counts by field", "",
        "| Field | Review rows |", "|---:|---:|",
    ]
    for field_id, count in summary["field_counts"].items():
        lines.append(f"| {field_id} | {count} |")
    lines += ["", "## Edge cases by category", "", "| Category | Cases |", "|---|---:|"]
    for category, count in summary["edge_case_counts_by_category"].items():
        lines.append(f"| {category} | {count} |")
    (target / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Stage 4C semantic_disposition_matrix.csv")
    parser.add_argument("--field-id", type=int, action="append", help="Restrict package to one or more WP1.5 field IDs")
    parser.add_argument("--output-root, type=Path, default=DEFAULT_INPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        rows, cases, summary = build_package(args.input, field_ids=set(args.field_id) if args.field_id else None)
        target = write_package(rows, cases, summary, args.output_root)
    except (ReviewPackageError, OSError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**summary, "package_directory": str(target)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
