#!/usr/bin/env python3
"""Build a read-only entity-classification review worksheet from registry and ISO proposals."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from audit_iso_proposal_evidence import read_proposal_report
else:
    from tools.audit_iso_proposal_evidence import read_proposal_report

DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_TAXONOMY = Path("config/entity_types.json")
DEFAULT_PROPOSALS = Path("reports/iso-assignment-proposals.md")
DEFAULT_OUTPUT = Path("reports/entity-classification-review.md")


def _cell(value: Any) -> str:
    if value is None or value == "":
        value = "—"
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def build_review(
    registry: dict[str, Any],
    taxonomy: dict[str, Any],
    proposal_rows: list[dict[str, str]],
) -> dict[str, Any]:
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("registry.records must be an array")
    types = taxonomy.get("types")
    if not isinstance(types, dict) or not types:
        raise ValueError("taxonomy.types must be a non-empty object")
    allowed_types = set(types)
    unreviewed_value = taxonomy.get("unreviewed_value", "unreviewed")
    if unreviewed_value not in allowed_types:
        raise ValueError("taxonomy.unreviewed_value must name a configured type")

    proposal_by_id: dict[str, dict[str, str]] = {}
    duplicate_proposal_ids: set[str] = set()
    for row in proposal_rows:
        gid = row.get("game_id", "")
        if not gid or gid in proposal_by_id:
            duplicate_proposal_ids.add(gid or "<empty>")
        proposal_by_id[gid] = row

    issues: list[str] = []
    if duplicate_proposal_ids:
        issues.append("Duplicate or empty proposal game_id values: " + ", ".join(sorted(duplicate_proposal_ids)))

    registry_ids: list[str] = []
    rows: list[dict[str, str]] = []
    type_counts: Counter[str] = Counter()
    match_counts: Counter[str] = Counter()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append(f"Registry record {index} is not an object")
            continue
        gid = record.get("game_id")
        if not isinstance(gid, str) or not gid.strip():
            issues.append(f"Registry record {index} has no non-empty game_id")
            gid = f"<missing-record-{index}>"
        else:
            registry_ids.append(gid)
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        names = record.get("names") if isinstance(record.get("names"), dict) else {}
        entity_type = record.get("entity_type")
        if not isinstance(entity_type, str) or entity_type not in allowed_types:
            issues.append(f"{gid}: entity_type {entity_type!r} is not in config/entity_types.json")
            type_label = "INVALID"
            type_counts["INVALID"] += 1
        else:
            type_label = entity_type
            type_counts[entity_type] += 1

        proposal = proposal_by_id.get(gid, {})
        match_type = proposal.get("Match type", "missing proposal")
        match_counts[match_type] += 1
        if gid not in proposal_by_id:
            issues.append(f"{gid}: no ISO proposal row found")
        classification_status = (
            "unreviewed" if entity_type == unreviewed_value
            else "classification value set; evidence/review status not represented in registry"
        )
        rows.append({
            "game_id": str(gid),
            "source_id": str(source.get("current_source_id") or ""),
            "english_name": str(names.get("en") or ""),
            "entity_type": type_label,
            "classification_status": classification_status,
            "alpha2": proposal.get("Candidate alpha-2", ""),
            "alpha3": proposal.get("Candidate alpha-3", ""),
            "reference_name": proposal.get("Reference English name", ""),
            "iso_match_type": match_type,
            "evidence_required": (
                "; ".join(types[entity_type].get("evidence_required", []))
                if isinstance(entity_type, str) and entity_type in types else
                "Fix invalid entity_type; then provide source-backed classification evidence"
            ),
        })

    duplicate_registry_ids = sorted(gid for gid, count in Counter(registry_ids).items() if count > 1)
    if duplicate_registry_ids:
        issues.append("Duplicate registry game_id values: " + ", ".join(duplicate_registry_ids))
    for gid in sorted(set(proposal_by_id) - set(registry_ids)):
        issues.append(f"Stale ISO proposal row for unknown registry game_id {gid!r}")

    return {
        "record_count": len(records),
        "unique_registry_ids": len(set(registry_ids)),
        "proposal_row_count": len(proposal_rows),
        "type_counts": type_counts,
        "match_counts": match_counts,
        "rows": rows,
        "issues": issues,
        "unreviewed_count": type_counts.get(unreviewed_value, 0),
        "unreviewed_value": unreviewed_value,
        "taxonomy": taxonomy,
    }


def render_report(result: dict[str, Any], registry_path: Path, taxonomy_path: Path, proposals_path: Path) -> str:
    taxonomy = result["taxonomy"]
    lines = [
        "# Entity classification review worksheet",
        "",
        f"- Registry: {registry_path}",
        f"- Controlled vocabulary: {taxonomy_path}",
        f"- ISO proposal report: {proposals_path}",
        f"- Registry records: {result['record_count']}",
        f"- Unique registry game IDs: {result['unique_registry_ids']}",
        f"- ISO proposal rows: {result['proposal_row_count']}",
        f"- Entity types still unreviewed: {result['unreviewed_count']}",
        f"- Structural issues: {len(result['issues'])}",
        "",
        "## Classification vocabulary",
        "",
        "| Value | Definition | Evidence required |",
        "|---|---|---|",
    ]
    for key, definition in taxonomy["types"].items():
        evidence = "; ".join(definition.get("evidence_required", []))
        lines.append(f"| {_cell(key)} | {_cell(definition.get('definition', ''))} | {_cell(evidence)} |")
    lines.extend(["", "## Current distribution", "", "| Entity type | Records |", "|---|---:|"])
    for key, count in sorted(result["type_counts"].items()):
        lines.append(f"| {_cell(key)} | {count} |")
    lines.extend(["", "## ISO proposal evidence distribution", "", "| Match type | Records |", "|---|---:|"])
    for key, count in sorted(result["match_counts"].items()):
        lines.append(f"| {_cell(key)} | {count} |")
    lines.extend([
        "",
        "## Record-level review worksheet",
        "",
        "| game_id | Source ID | English name | Entity type | Classification status | Candidate alpha-2 | Candidate alpha-3 | Reference name | ISO match type | Evidence needed |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for row in result["rows"]:
        lines.append(
            "| " + " | ".join(_cell(row[key]) for key in (
                "game_id", "source_id", "english_name", "entity_type",
                "classification_status", "alpha2", "alpha3", "reference_name",
                "iso_match_type", "evidence_required",
            )) + " |"
        )
    lines.extend(["", "## Structural issues", ""])
    if result["issues"]:
        lines.extend("- " + _cell(issue) for issue in result["issues"])
    else:
        lines.append("None detected.")
    lines.extend(["", "## Review policy", ""])
    lines.extend("- " + _cell(item) for item in taxonomy.get("policy", []))
    lines.extend([
        "- ISO proposal match type is contextual evidence only and must not be treated as entity classification.",
        "- A non-unreviewed value does not prove that a source-backed review occurred; this schema currently has no separate entity-classification evidence/status fields.",
        "- This tool is read-only. It does not change the registry, ISO assignments, stable IDs, generated assets, or game repository.",
        "- Do not classify entities in bulk from names alone. Review evidence should identify source URL, access date, relevant excerpt, and the rationale for the chosen category.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--proposals", type=Path, default=DEFAULT_PROPOSALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
        proposal_rows = read_proposal_report(args.proposals)
        result = build_review(registry, taxonomy, proposal_rows)
        report = render_report(result, args.registry, args.taxonomy, args.proposals)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(
        f"Entity classification worksheet: {args.output} "
        f"({result['record_count']} records; {len(result['issues'])} structural issues)"
    )
    return 1 if result["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
