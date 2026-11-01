"""Shared database report artifact writer and terminal presentation helpers."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


RECORD_FIELDS = [
    "game_id", "registry_name", "source_id", "existing_alpha2", "existing_alpha3",
    "match_type", "variant_note", "reference_name", "reference_id",
    "reference_alpha2", "reference_alpha3", "alpha2_comparison",
    "alpha3_comparison", "code_pair_classification",
    "source_id_vs_reference_alpha3",
]
UNMATCHED_REGISTRY_FIELDS = RECORD_FIELDS
UNMATCHED_REFERENCE_FIELDS = [
    "reference_name", "reference_id", "reference_alpha2", "reference_alpha3", "reason",
]


def _safe_segment(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        raise ValueError(f"unsafe report path segment: {value!r}")
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report_bundle(
    report_root: Path | str,
    *,
    database_id: str,
    domain: str,
    report_id: str,
    summary_markdown: str,
    records: Sequence[Mapping[str, Any]],
    unmatched_registry: Sequence[Mapping[str, Any]],
    unmatched_reference: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, Any],
) -> dict[str, str]:
    """Write the standard Markdown/CSV/JSON report bundle to a stable directory."""
    database_id, domain, report_id = map(_safe_segment, (database_id, domain, report_id))
    directory = Path(report_root) / "database" / database_id / domain / report_id
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "directory": str(directory),
        "summary": str(directory / "summary.md"),
        "records": str(directory / "records.csv"),
        "unmatched_registry": str(directory / "unmatched_registry.csv"),
        "unmatched_reference": str(directory / "unmatched_reference.csv"),
        "provenance": str(directory / "provenance.json"),
    }
    (directory / "summary.md").write_text(summary_markdown.rstrip() + "\n", encoding="utf-8")
    _write_csv(directory / "records.csv", records, RECORD_FIELDS)
    _write_csv(directory / "unmatched_registry.csv", unmatched_registry, UNMATCHED_REGISTRY_FIELDS)
    _write_csv(directory / "unmatched_reference.csv", unmatched_reference, UNMATCHED_REFERENCE_FIELDS)
    (directory / "provenance.json").write_text(
        json.dumps(dict(provenance), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return paths


def render_terminal_summary(summary: Mapping[str, Any], paths: Mapping[str, str]) -> str:
    """Concise default terminal output; detailed row data belongs in CSV artifacts."""
    lines = [
        "Identity reconciliation",
        f"  Registry records: {summary.get('registry_count', 0)}",
        f"  Reference rows: {summary.get('reference_count', 0)}",
        f"  Unique name matches: {summary.get('matched_count', 0)}",
        f"  Unmatched registry: {summary.get('unmatched_registry_count', 0)}",
        f"  Ambiguous registry: {summary.get('ambiguous_registry_count', 0)}",
        f"  Unmatched reference: {summary.get('unmatched_reference_count', 0)}",
        f"  Alpha-2 matches / mismatches: {summary.get('alpha2_matches', 0)} / {summary.get('alpha2_mismatches', 0)}",
        f"  Alpha-3 matches / mismatches: {summary.get('alpha3_matches', 0)} / {summary.get('alpha3_mismatches', 0)}",
        f"  Reports: {paths.get('directory', '')}",
    ]
    return "\n".join(lines)


def render_terminal_verbose(result: Mapping[str, Any], paths: Mapping[str, str]) -> str:
    lines = [render_terminal_summary(result["summary"], paths), "", "Code-pair classifications:"]
    for key, count in result["summary"].get("code_pair_classifications", {}).items():
        lines.append(f"  {key}: {count}")
    lines.extend(["", "Source ID vs reference alpha-3 (separate from ISO comparison):"])
    lines.append(f"  Same: {result['summary'].get('source_id_alpha3_same', 0)}")
    lines.append(f"  Different: {result['summary'].get('source_id_alpha3_different', 0)}")
    lines.extend(["", "Record-level results:", "  game_id | registry name | match | alpha-2 | alpha-3 | classification"])
    for row in result.get("records", []):
        lines.append(
            "  {game_id} | {registry_name} | {match_type} | {alpha2_comparison} | "
            "{alpha3_comparison} | {code_pair_classification}".format(**row)
        )
    return "\n".join(lines)


def emit_terminal_report(result: Mapping[str, Any], paths: Mapping[str, str], *, quiet: bool = False, verbose: bool = False, stream=None) -> None:
    """Print default or verbose summary; quiet suppresses only successful summaries."""
    if quiet:
        return
    stream = stream or sys.stdout
    output = render_terminal_verbose(result, paths) if verbose else render_terminal_summary(result["summary"], paths)
    print(output, file=stream)
