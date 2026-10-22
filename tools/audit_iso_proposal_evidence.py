#!/usr/bin/env python3
"""Audit ISO proposal evidence against the registry, captured reference, and report.

This is a read-only semantic consistency audit. It never changes the registry,
approves assignments, or treats a name match as proof of entity scope.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from propose_iso_assignments import normalize_name, propose, read_reference
else:
    from tools.propose_iso_assignments import normalize_name, propose, read_reference

DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_REFERENCE = Path("raw_data/iso/iso-3166-1.csv")
DEFAULT_PROPOSALS = Path("reports/iso-assignment-proposals.md")
DEFAULT_OUTPUT = Path("reports/iso-proposal-evidence-audit.md")
TABLE_HEADER = "| game_id | Registry English name | Candidate alpha-2 | Candidate alpha-3 | Reference English name | Match type | Decision |"


def _cells(line: str) -> list[str]:
    return [cell.strip().replace("\\|", "|") for cell in line.strip().strip("|").split("|")]


def read_proposal_report(path: Path) -> list[dict[str, str]]:
    """Read proposal rows from the generated Markdown table."""
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        header_index = lines.index(TABLE_HEADER)
    except ValueError as exc:
        raise ValueError(f"proposal report has no expected table header: {path}") from exc
    expected = [
        "game_id", "Registry English name", "Candidate alpha-2",
        "Candidate alpha-3", "Reference English name", "Match type", "Decision",
    ]
    header = _cells(lines[header_index])
    if header != expected:
        raise ValueError("proposal report table columns do not match the expected schema")
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(lines[header_index + 2 :], start=header_index + 3):
        if not line.startswith("|"):
            break
        cells = _cells(line)
        if len(cells) != len(expected):
            raise ValueError(f"proposal report line {line_number}: expected {len(expected)} cells")
        rows.append(dict(zip(expected, cells, strict=True)))
    return rows


def audit_evidence(
    registry: dict[str, Any],
    reference: list[dict[str, str]],
    report_rows: list[dict[str, str]],
) -> dict[str, Any]:
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("registry.records must be an array")

    issues: list[str] = []
    counts: Counter[str] = Counter()
    registry_ids: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append(f"Registry record {index} is not an object")
            continue
        gid = record.get("game_id")
        if not isinstance(gid, str) or not gid.strip():
            issues.append(f"Registry record {index} has no non-empty game_id")
            continue
        registry_ids.append(gid)
    registry_id_counts = Counter(registry_ids)
    for gid, count in sorted(registry_id_counts.items()):
        if count > 1:
            issues.append(f"Registry game_id {gid!r} occurs {count} times")

    report_id_counts = Counter(row.get("game_id", "") for row in report_rows)
    for gid, count in sorted(report_id_counts.items()):
        if not gid or count > 1:
            issues.append(f"Proposal report game_id {gid or '<empty>'!r} occurs {count} times")

    registry_set = set(registry_ids)
    report_set = {gid for gid in report_id_counts if gid}
    for gid in sorted(registry_set - report_set):
        issues.append(f"Missing proposal row for registry game_id {gid!r}")
    for gid in sorted(report_set - registry_set):
        issues.append(f"Stale proposal row for unknown game_id {gid!r}")

    fresh = propose(registry, reference)
    fresh_by_id = {row["game_id"]: row for row in fresh["proposals"]}
    report_by_id = {row.get("game_id", ""): row for row in report_rows}
    compared_fields = (
        ("english_name", "Registry English name"),
        ("candidate_alpha2", "Candidate alpha-2"),
        ("candidate_alpha3", "Candidate alpha-3"),
        ("reference_name", "Reference English name"),
        ("match_type", "Match type"),
        ("decision", "Decision"),
    )
    for gid in sorted(registry_set & report_set):
        expected = fresh_by_id.get(gid)
        actual = report_by_id.get(gid)
        if expected is None or actual is None:
            continue
        for fresh_field, report_field in compared_fields:
            if str(expected.get(fresh_field, "")) != actual.get(report_field, ""):
                issues.append(
                    f"{gid}: stale or edited proposal field {report_field!r}; "
                    f"report={actual.get(report_field, '')!r}, expected={expected.get(fresh_field, '')!r}"
                )

    ref_by_codes = {(row["alpha2"], row["alpha3"]): row for row in reference}
    ref_by_name = {normalize_name(row["english_name"]): row for row in reference}
    code_owners: dict[tuple[str, str], str] = {}
    alpha2_owners: dict[str, str] = {}
    alpha3_owners: dict[str, str] = {}
    for row in report_rows:
        gid = row.get("game_id", "")
        alpha2 = row.get("Candidate alpha-2", "")
        alpha3 = row.get("Candidate alpha-3", "")
        ref_name = row.get("Reference English name", "")
        if bool(alpha2) != bool(alpha3):
            issues.append(f"{gid}: candidate must provide both alpha-2 and alpha-3, or neither")
            continue
        if not alpha2:
            if ref_name:
                issues.append(f"{gid}: reference name exists without candidate codes")
            continue
        if not re.fullmatch(r"[A-Z]{2}", alpha2) or not re.fullmatch(r"[A-Z]{3}", alpha3):
            issues.append(f"{gid}: malformed candidate ISO code pair {alpha2!r}/{alpha3!r}")
            continue
        reference_row = ref_by_codes.get((alpha2, alpha3))
        if reference_row is None:
            issues.append(f"{gid}: candidate code pair {alpha2}/{alpha3} is absent from captured reference")
            continue
        if reference_row["english_name"] != ref_name:
            issues.append(
                f"{gid}: reference label {ref_name!r} does not match captured reference label "
                f"{reference_row['english_name']!r} for {alpha2}/{alpha3}"
            )
        key = (alpha2, alpha3)
        if key in code_owners and code_owners[key] != gid:
            issues.append(
                f"Candidate code pair {alpha2}/{alpha3} is proposed for multiple game_ids "
                f"{code_owners[key]!r} and {gid!r}"
            )
        else:
            code_owners[key] = gid
        if alpha2 in alpha2_owners and alpha2_owners[alpha2] != gid:
            issues.append(f"Candidate alpha-2 {alpha2} is proposed for multiple game_ids {alpha2_owners[alpha2]!r} and {gid!r}")
        else:
            alpha2_owners[alpha2] = gid
        if alpha3 in alpha3_owners and alpha3_owners[alpha3] != gid:
            issues.append(f"Candidate alpha-3 {alpha3} is proposed for multiple game_ids {alpha3_owners[alpha3]!r} and {gid!r}")
        else:
            alpha3_owners[alpha3] = gid

        match_type = row.get("Match type", "")
        registry_record = next(
            (item for item in records if isinstance(item, dict) and item.get("game_id") == gid),
            None,
        )
        registry_name = (
            registry_record.get("names", {}).get("en", "")
            if registry_record and isinstance(registry_record.get("names"), dict)
            else ""
        )
        if match_type == "exact normalized name" and normalize_name(str(registry_name)) != normalize_name(ref_name):
            issues.append(f"{gid}: exact-name proposal does not normalize to the captured reference label")
        if match_type not in {"exact normalized name", "explicit name variant"}:
            issues.append(f"{gid}: unexpected match type for a code proposal: {match_type!r}")

    for issue in issues:
        if issue.startswith("Missing proposal row"):
            counts["missing proposal rows"] += 1
        elif issue.startswith("Stale proposal row"):
            counts["stale proposal rows"] += 1
        elif "occurs" in issue and "game_id" in issue:
            counts["duplicate proposal/registry IDs"] += 1
        elif "multiple game_ids" in issue:
            counts["candidate code conflicts"] += 1
        elif "candidate code pair" in issue or "candidate must provide" in issue:
            counts["invalid candidate evidence"] += 1
        else:
            counts["other consistency issues"] += 1

    return {
        "registry_count": len(records),
        "unique_registry_ids": len(registry_set),
        "reference_count": len(reference),
        "proposal_row_count": len(report_rows),
        "candidate_count": sum(bool(row.get("Candidate alpha-2")) for row in report_rows),
        "issue_count": len(issues),
        "issues": issues,
        "issue_counts": counts,
        "fresh_proposal_summary": fresh,
    }


def render_report(result: dict[str, Any], registry_path: Path, reference_path: Path, proposal_path: Path) -> str:
    counts: Counter[str] = result["issue_counts"]
    lines = [
        "# ISO proposal evidence audit",
        "",
        f"- Registry file: `{registry_path}`",
        f"- Captured reference: `{reference_path}`",
        f"- Proposal report: `{proposal_path}`",
        f"- Registry records: {result['registry_count']}",
        f"- Unique registry game IDs: {result['unique_registry_ids']}",
        f"- Reference rows: {result['reference_count']}",
        f"- Proposal rows: {result['proposal_row_count']}",
        f"- Proposed code pairs: {result['candidate_count']}",
        f"- Consistency issues: {result['issue_count']}",
        "",
        "## Issue summary",
        "",
        "| Issue type | Count |",
        "|---|---:|",
    ]
    for label in (
        "missing proposal rows", "stale proposal rows", "duplicate proposal/registry IDs",
        "candidate code conflicts", "invalid candidate evidence", "other consistency issues",
    ):
        lines.append(f"| {label} | {counts.get(label, 0)} |")
    lines.extend(["", "## Findings", ""])
    if result["issues"]:
        lines.extend("- " + issue.replace("|", "\\|") for issue in result["issues"])
    else:
        lines.append("No proposal/registry/reference consistency issues detected by this audit.")
    lines.extend([
        "",
        "## Interpretation and safeguards",
        "",
        "- This audit checks report freshness, registry coverage, candidate code pairs, and reference-label consistency.",
        "- A passing audit does not establish ISO scope, political/entity semantics, or the correctness of an explicit name variant.",
        "- The captured reference is a third-party distribution; provenance and retrieval metadata must be reviewed separately.",
        "- This tool is read-only: it does not modify the registry, verify or approve assignments, change game IDs, or publish game assets.",
        "- Review explicit variants and unmatched entities individually before designing any registry update workflow.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--proposals", type=Path, default=DEFAULT_PROPOSALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    reference = read_reference(args.reference)
    report_rows = read_proposal_report(args.proposals)
    result = audit_evidence(registry, reference, report_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_report(result, args.registry, args.reference, args.proposals),
        encoding="utf-8",
    )
    print(f"ISO evidence audit: {args.output} ({result['issue_count']} issues)")
    return 1 if result["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
