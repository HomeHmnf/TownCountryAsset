"""Shared source refresh and source-selection report artifacts.

Reports are operational/audit outputs only. Writing them never applies data to SQLite.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ARTIFACT_FIELDS = {
    "records": [
        "game_id", "field_key", "field_id", "storage", "record_key", "subfield_key",
        "source_id", "download_id", "release_id", "status", "selection_status",
        "selected_source", "primary_source", "selection_mode", "value", "unit",
        "observation_period", "source_reference", "methodology", "retrieved_at",
        "fallback_used", "override_id", "override_reason", "override_author", "effective_at",
        "compatibility_reference", "assigned_source", "primary_candidate", "prior_provider_candidate",
        "rejected_candidates", "reason", "detail",
    ],
    "missing": [
        "game_id", "field_key", "field_id", "record_key", "subfield_key",
        "selection_status", "unit", "reason",
    ],
    "fallbacks": [
        "game_id", "field_key", "record_key", "subfield_key", "primary_source",
        "selected_source", "release_id", "compatibility_reference", "reason",
    ],
    "conflicts": [
        "game_id", "field_key", "record_key", "subfield_key", "primary_source",
        "selected_source", "candidate_source", "candidate_release_id", "reason",
    ],
    "overrides": [
        "game_id", "field_key", "record_key", "subfield_key", "override_id",
        "selected_source", "override_reason", "override_author", "effective_at",
        "prior_provider_candidate",
    ],
    "release_changes": [
        "source_id", "download_id", "release_id", "release_kind", "status",
        "sha256", "provider_commit_timestamp", "fetched_at", "detail",
    ],
    "failures": [
        "source_id", "download_id", "status", "detail",
    ],
}


def _safe_segment(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value) is None:
        raise ValueError(f"unsafe source report path segment: {value!r}")
    return value


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def write_source_report_bundle(
    output_root: Path | str,
    *,
    report_id: str,
    report_type: str,
    summary_markdown: str,
    records: Sequence[Mapping[str, Any]] = (),
    missing: Sequence[Mapping[str, Any]] = (),
    fallbacks: Sequence[Mapping[str, Any]] = (),
    conflicts: Sequence[Mapping[str, Any]] = (),
    overrides: Sequence[Mapping[str, Any]] = (),
    release_changes: Sequence[Mapping[str, Any]] = (),
    failures: Sequence[Mapping[str, Any]] = (),
    provenance: Mapping[str, Any],
) -> dict[str, str]:
    """Write one stable Markdown/CSV/JSON bundle for any source-management report."""
    report_id = _safe_segment(report_id)
    report_type = _safe_segment(report_type)
    directory = Path(output_root) / report_id
    directory.mkdir(parents=True, exist_ok=True)
    paths = {"directory": str(directory), "summary": str(directory / "summary.md"),
             "provenance": str(directory / "provenance.json")}
    (directory / "summary.md").write_text(summary_markdown.rstrip() + "\n", encoding="utf-8")
    groups = {
        "records": records, "missing": missing, "fallbacks": fallbacks,
        "conflicts": conflicts, "overrides": overrides,
        "release_changes": release_changes, "failures": failures,
    }
    for name, rows in groups.items():
        path = directory / f"{name}.csv"
        _write_csv(path, rows, ARTIFACT_FIELDS[name])
        paths[name] = str(path)
    provenance_doc = {
        "report_schema_version": 1,
        "report_type": report_type,
        "report_id": report_id,
        **dict(provenance),
        "artifacts": {key: Path(value).name for key, value in paths.items() if key != "directory"},
    }
    (directory / "provenance.json").write_text(
        json.dumps(provenance_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return paths


def write_refresh_report_bundle(report: Mapping[str, Any], output_root: Path | str) -> dict[str, str]:
    """Render refresh outcomes, discovered release candidates and failures."""
    records: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for source in report.get("sources", []):
        source_id = source.get("source_id")
        git_ref = source.get("git_ref")
        if git_ref:
            row = {
                "source_id": source_id, "release_id": git_ref.get("release_id"),
                "status": "discovered", "provider_commit_timestamp": git_ref.get("commit_timestamp"),
                "fetched_at": git_ref.get("fetched_at"), "detail": git_ref.get("detail"),
            }
            records.append(row)
            changes.append(row)
        elif not source.get("downloads"):
            records.append({
                "source_id": source_id, "status": source.get("discovery_status"),
                "detail": source.get("detail") or "No generic download was configured for this source",
            })
        if source.get("discovery_status") == "discovery_failed":
            failures.append({
                "source_id": source_id, "status": source.get("discovery_status"),
                "detail": source.get("detail") or "Release discovery failed",
            })
        for item in source.get("downloads", []):
            row = {
                "source_id": source_id, "download_id": item.get("download_id"),
                "release_id": item.get("discovered_release") or item.get("configured_release"),
                "release_kind": item.get("release_kind"), "status": item.get("status"),
                "sha256": item.get("sha256") or item.get("discovered_sha256"),
                "fetched_at": item.get("fetched_at") or item.get("discovered_fetched_at"),
                "detail": item.get("detail"),
            }
            records.append(row)
            if item.get("discovered_release") or item.get("status") == "acquired_pending_source_validation":
                changes.append(row)
            if item.get("status") in {
                "validation_error", "acquisition_failed", "discovery_or_acquisition_failed",
                "changed_during_acquisition",
            }:
                failures.append(row)
    counts = report.get("counts", {})
    lines = [
        "# Source refresh audit", "",
        f"- Run: {report.get('run_id')}",
        f"- Checked: {report.get('checked_at')}",
        f"- Dry run: {report.get('dry_run')}",
        "- Canonical database imported: no", "",
        "## Outcomes", "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(counts.items()))
    lines.extend([
        "", "## Release changes and snapshot outcomes", "",
        f"- Release/snapshot records: {len(records)}",
        f"- Candidate release changes: {len(changes)}",
        f"- Failures or manual-review items: {len(failures)}",
        "", "## Boundaries", "",
    ])
    lines.extend(f"- {item}" for item in report.get("limitations", []))
    run_id = str(report.get("run_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    return write_source_report_bundle(
        output_root, report_id=run_id, report_type="refresh",
        summary_markdown="\n".join(lines),
        records=records, release_changes=changes, failures=failures,
        provenance={
            "run_id": run_id, "checked_at": report.get("checked_at"),
            "dry_run": report.get("dry_run"), "source_count": report.get("source_count"),
            "counts": counts, "database_imported": False,
            "limitations": report.get("limitations", []),
            "release_state_policy": "latest_available may change; latest_validated/latest_applied are not promoted by refresh",
        },
    )


def _selection_rows(decisions: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], ...]:
    records: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    fallbacks: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    overrides: list[dict[str, Any]] = []

    def add_decision(decision: Mapping[str, Any], base: Mapping[str, Any]) -> None:
        row = {**base, **dict(decision)}
        records.append(row)
        if row.get("selection_status") == "unavailable":
            missing.append({key: row.get(key) for key in ARTIFACT_FIELDS["missing"]})
        if row.get("fallback_used"):
            fallbacks.append({
                "game_id": row.get("game_id"), "field_key": row.get("field_key"),
                "record_key": row.get("record_key"), "subfield_key": row.get("subfield_key"),
                "primary_source": row.get("primary_source"),
                "selected_source": row.get("selected_source"), "release_id": row.get("release_id"),
                "compatibility_reference": row.get("compatibility_reference"),
                "reason": row.get("reason"),
            })
            primary = row.get("primary_candidate")
            if primary:
                conflicts.append({
                    "game_id": row.get("game_id"), "field_key": row.get("field_key"),
                    "record_key": row.get("record_key"), "subfield_key": row.get("subfield_key"),
                    "primary_source": row.get("primary_source"),
                    "selected_source": row.get("selected_source"),
                    "candidate_source": primary.get("source_id"),
                    "candidate_release_id": primary.get("release_id"),
                    "reason": "Primary candidate was not selected because an approved fallback filled the gap",
                })
        for candidate in row.get("rejected_candidates", []):
            conflicts.append({
                "game_id": row.get("game_id"), "field_key": row.get("field_key"),
                "record_key": row.get("record_key"), "subfield_key": row.get("subfield_key"),
                "primary_source": row.get("primary_source"),
                "selected_source": row.get("selected_source"),
                "candidate_source": candidate.get("source_id"),
                "candidate_release_id": candidate.get("release_id"),
                "reason": candidate.get("reason"),
            })
        if row.get("selected_source") == "manual_override":
            overrides.append({
                "game_id": row.get("game_id"), "field_key": row.get("field_key"),
                "record_key": row.get("record_key"), "subfield_key": row.get("subfield_key"),
                "override_id": row.get("override_id"), "selected_source": "manual_override",
                "override_reason": row.get("override_reason"), "override_author": row.get("override_author"),
                "effective_at": row.get("effective_at") or row.get("retrieved_at"),
                "prior_provider_candidate": row.get("prior_provider_candidate"),
            })

    for item in decisions:
        if item.get("storage") == "structured":
            result = item["result"]
            base = {
                "game_id": result["game_id"], "field_key": result["field_key"],
                "field_id": result["field_id"], "storage": "structured",
                "primary_source": result["primary_source"], "selection_mode": result["selection_mode"],
            }
            for decision in result.get("records", []):
                add_decision(decision, base)
        else:
            result = item["result"]
            base = {
                "game_id": result["game_id"], "field_key": result["field_key"],
                "field_id": result["field_id"], "storage": "scalar",
                "primary_source": result["primary_source"], "selection_mode": result["selection_mode"],
            }
            add_decision(result, base)
    return records, missing, fallbacks, conflicts, overrides


def write_selection_report_bundle(
    *,
    output_root: Path | str,
    report_id: str,
    decisions: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Write field/record decisions and consolidated coverage/audit tables."""
    records, missing, fallbacks, conflicts, overrides = _selection_rows(decisions)
    status_counts = Counter(str(row.get("selection_status")) for row in records)
    country_ids = sorted({item["result"]["game_id"] for item in decisions})
    field_keys = sorted({item["result"]["field_key"] for item in decisions})
    source_counts = Counter(str(row.get("selected_source")) for row in records if row.get("selected_source"))
    release_counts = Counter(str(row.get("release_id")) for row in records if row.get("release_id"))

    def coverage(key: str) -> dict[str, dict[str, int]]:
        grouped: dict[str, dict[str, int]] = {}
        for row in records:
            label = str(row.get(key))
            metrics = grouped.setdefault(label, {"total": 0, "populated": 0, "unavailable": 0, "not_applicable": 0})
            metrics["total"] += 1
            status = row.get("selection_status")
            if status in {"observed", "estimated", "projected"}:
                metrics["populated"] += 1
            elif status in {"unavailable", "not_applicable"}:
                metrics[status] += 1
        return grouped

    country_coverage = coverage("game_id")
    field_coverage = coverage("field_key")
    empty_metrics = {"total": 0, "populated": 0, "unavailable": 0, "not_applicable": 0}
    for game_id in country_ids:
        country_coverage.setdefault(game_id, dict(empty_metrics))
    for field_key in field_keys:
        field_coverage.setdefault(field_key, dict(empty_metrics))

    summary = {
        "decision_count": len(records),
        "selected_count": sum(row.get("selection_status") in {"observed", "estimated", "projected"} for row in records),
        "unavailable_count": status_counts.get("unavailable", 0),
        "not_applicable_count": status_counts.get("not_applicable", 0),
        "fallback_count": len(fallbacks), "override_count": len(overrides),
        "conflict_count": len(conflicts), "country_count": len(country_ids),
        "field_count": len(field_keys), "by_status": dict(status_counts),
        "coverage_by_country": country_coverage, "coverage_by_field": field_coverage,
        "by_selected_source": dict(source_counts), "by_release": dict(release_counts),
    }
    lines = [
        "# Source-selection resolution audit", "",
        f"- Run: {report_id}",
        f"- Policy version: {provenance.get('policy_version')}",
        f"- Countries/entities: {summary['country_count']}",
        f"- Resolved field/record decisions: {summary['decision_count']}",
        f"- Populated selections: {summary['selected_count']}",
        f"- Unavailable: {summary['unavailable_count']}",
        f"- Not applicable: {summary['not_applicable_count']}",
        f"- Fallbacks: {summary['fallback_count']}",
        f"- Manual overrides: {summary['override_count']}",
        f"- Conflicts/rejected candidates: {summary['conflict_count']}",
        "- Canonical database imported: no", "",
        "## Coverage by status", "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(summary["by_status"].items()))
    lines.extend(["", "## Coverage by country/entity", ""])
    lines.extend(
        f"- {key}: {value['populated']}/{value['total']} populated; "
        f"{value['unavailable']} unavailable; {value['not_applicable']} not applicable"
        for key, value in sorted(summary["coverage_by_country"].items())
    )
    lines.extend(["", "## Coverage by field", ""])
    lines.extend(
        f"- {key}: {value['populated']}/{value['total']} populated; "
        f"{value['unavailable']} unavailable; {value['not_applicable']} not applicable"
        for key, value in sorted(summary["coverage_by_field"].items())
    )
    lines.extend(["", "## Selected values by source", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(source_counts.items()))
    lines.extend(["", "## Selected values by release", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(release_counts.items()))
    lines.extend([
        "", "## Audit artifacts", "",
        "- records.csv: every resolved scalar field and structured record/subfield",
        "- missing.csv: unavailable decisions only; not-applicable is kept separate",
        "- fallbacks.csv: approved fallback selections and compatibility evidence",
        "- conflicts.csv: rejected candidates and primary candidates superseded by an approved fallback",
        "- overrides.csv: scoped manual overrides and their prior provider candidate",
        "", "Resolution is read-only. No canonical database values were imported or changed.",
    ])
    paths = write_source_report_bundle(
        output_root, report_id=report_id, report_type="selection",
        summary_markdown="\n".join(lines), records=records, missing=missing,
        fallbacks=fallbacks, conflicts=conflicts, overrides=overrides,
        provenance={**dict(provenance), "summary": summary, "database_imported": False},
    )
    return paths, summary
