#!/usr/bin/env python3
"""Generate a read-only review report for the canonical identity registry."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def audit_registry(registry: dict[str, Any]) -> dict[str, Any]:
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("registry.records must be an array")

    counts: Counter[str] = Counter()
    issues: list[str] = []
    review_rows: list[dict[str, str]] = []
    seen_game_ids: set[str] = set()
    seen_current: dict[str, str] = {}
    seen_source_history: dict[str, str] = {}

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append(f"Record {index}: record is not an object")
            continue
        gid = record.get("game_id")
        gid_text = gid if isinstance(gid, str) and gid.strip() else ""
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        names = record.get("names") if isinstance(record.get("names"), dict) else {}
        iso = record.get("iso") if isinstance(record.get("iso"), dict) else {}
        current = source.get("current_source_id")
        previous = source.get("previous_source_ids", [])
        reasons: list[str] = []

        if not gid_text:
            issues.append(f"Record {index}: missing game_id")
            reasons.append("missing game_id")
        elif gid_text in seen_game_ids:
            issues.append(f"Record {index}: duplicate game_id {gid_text!r}")
            reasons.append("duplicate game_id")
        else:
            seen_game_ids.add(gid_text)

        if not isinstance(current, str) or not current.strip():
            issues.append(f"{gid_text or index}: missing current_source_id")
            reasons.append("missing current source ID")
        else:
            if current in seen_current and seen_current[current] != gid_text:
                issues.append(f"Source ID {current!r} is assigned to multiple game_ids")
                reasons.append("source ID collision")
            seen_current[current] = gid_text
            if record.get("geometry_key") != current:
                issues.append(f"{gid_text or index}: geometry_key differs from current_source_id")
                reasons.append("geometry key mismatch")

        if not isinstance(previous, list) or not all(isinstance(x, str) and x.strip() for x in previous):
            issues.append(f"{gid_text or index}: previous_source_ids must be an array of non-empty strings")
            reasons.append("invalid source history")
            previous = []
        if current in previous:
            issues.append(f"{gid_text or index}: current source ID also appears in previous_source_ids")
            reasons.append("current ID repeated in history")
        for old_id in previous:
            if old_id in seen_source_history and seen_source_history[old_id] != gid_text:
                issues.append(f"Historical source ID {old_id!r} is claimed by multiple game_ids")
                reasons.append("historical source ID collision")
            seen_source_history[old_id] = gid_text
            if old_id in seen_current and seen_current[old_id] != gid_text:
                issues.append(f"Source ID {old_id!r} is current for another game_id and historical for {gid_text!r}")
                reasons.append("current/history source ID collision")

        entity_type = record.get("entity_type")
        if not isinstance(entity_type, str) or not entity_type.strip() or entity_type == "unreviewed":
            reasons.append("entity type unreviewed")
        iso_status = iso.get("assignment_status")
        if iso_status != "verified":
            reasons.append(f"ISO status {iso_status or 'missing'}")
        if iso.get("alpha2") is None:
            reasons.append("ISO alpha-2 missing")
        if iso.get("alpha3") is None:
            reasons.append("ISO alpha-3 missing")
        localization_status = names.get("localization_status")
        if localization_status != "reviewed":
            reasons.append(f"localization {localization_status or 'missing'}")
        if not isinstance(names.get("fa"), str) or not names.get("fa", "").strip():
            reasons.append("Persian name missing")
        if not isinstance(names.get("en"), str) or not names.get("en", "").strip():
            issues.append(f"{gid_text or index}: English name missing")
            reasons.append("English name missing")
        if not isinstance(record.get("regions"), list):
            issues.append(f"{gid_text or index}: regions must be an array")
            reasons.append("invalid regions")
        if record.get("status") != "approved":
            reasons.append(f"record status {record.get('status', 'missing')}")

        for reason in reasons:
            counts[reason] += 1
        if reasons:
            review_rows.append({
                "game_id": gid_text or "MISSING",
                "source_id": _text(current),
                "name": _text(names.get("en")),
                "reasons": "; ".join(dict.fromkeys(reasons)),
            })

    return {
        "record_count": len(records),
        "registry_status": _text(registry.get("status")),
        "unique_game_ids": len(seen_game_ids),
        "structural_issues": issues,
        "review_counts": counts,
        "review_rows": review_rows,
    }


def render_report(result: dict[str, Any]) -> str:
    counts: Counter[str] = result["review_counts"]
    lines = [
        "# Canonical country identity review",
        "",
        f"- Registry status: {result['registry_status']}",
        f"- Records: {result['record_count']}",
        f"- Unique non-empty game IDs: {result['unique_game_ids']}",
        f"- Structural issues detected by this report: {len(result['structural_issues'])}",
        "",
        "## Review summary",
        "",
        "| Review item | Records requiring review |",
        "|---|---:|",
    ]
    for item in [
        "record status proposed",
        "entity type unreviewed",
        "ISO status unverified",
        "ISO alpha-2 missing",
        "ISO alpha-3 missing",
        "localization unreviewed",
        "Persian name missing",
    ]:
        lines.append(f"| {item} | {counts.get(item, 0)} |")
    lines.extend(["", "## Structural issues", ""])
    if result["structural_issues"]:
        lines.extend(f"- {_text(issue)}" for issue in result["structural_issues"])
    else:
        lines.append("None detected by this report.")
    lines.extend([
        "",
        "## Records requiring review",
        "",
        "| game_id | Current source ID | English name | Review reasons |",
        "|---|---|---|---|",
    ])
    for row in result["review_rows"]:
        lines.append(
            f"| {_text(row['game_id'])} | {_text(row['source_id'])} | "
            f"{_text(row['name'])} | {_text(row['reasons'])} |"
        )
    lines.extend([
        "",
        "## Interpretation and safeguards",
        "",
        "- This is a read-only review report; it does not approve or change any record.",
        "- A syntactically valid ISO code is not evidence that the code belongs to the entity. Verify assignments against an authoritative source before marking them verified.",
        "- Missing ISO codes are allowed where no appropriate code applies; document the reason rather than inventing a value.",
        "- Entity type, Persian localization, aliases, and region assignments require source-backed review.",
        "- Do not regenerate, replace, or derive canonical game IDs from source IDs, names, ISO codes, or record order.",
        "- Review rows can have multiple reasons; counts are per reason, not mutually exclusive categories.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/country_identity_registry.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/country-identity-review.md"))
    args = parser.parse_args()
    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        if not isinstance(registry, dict):
            raise ValueError("registry must contain a JSON object")
        result = audit_registry(registry)
        report = render_report(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Identity review report written to {args.output}")
    print(f"Records: {result['record_count']}; review rows: {len(result['review_rows'])}; structural issues: {len(result['structural_issues'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
