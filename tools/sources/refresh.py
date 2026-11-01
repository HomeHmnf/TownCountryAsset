"""Project-wide source refresh orchestration.

Refresh captures configured immutable snapshots and validates their registered
response contracts. It deliberately does not promote release state or import data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tools.sources.registry import ROOT, SourceError, acquire_one, inspect_snapshots


def run_refresh(
    registry: dict,
    *,
    source_ids: list[str] | None = None,
    timeout: int = 60,
    dry_run: bool = False,
    report_root: Path | None = None,
) -> dict:
    """Refresh configured downloads, retaining immutable snapshots and a report."""
    sources = registry["sources"]
    selected_ids = list(dict.fromkeys(source_ids if source_ids is not None else list(sources)))
    unknown = sorted(set(selected_ids) - set(sources))
    if unknown:
        raise SourceError("Unknown source ID(s): " + ", ".join(unknown))
    if timeout < 1 or timeout > 600:
        raise SourceError("timeout must be between 1 and 600 seconds")

    snapshot_rows = {
        (row["source_id"], row["download_id"]): row
        for row in inspect_snapshots(registry)
    }
    results = []
    for source_id in selected_ids:
        source = sources[source_id]
        discovery = source["release_discovery"]
        source_result = {
            "source_id": source_id,
            "discovery_mode": discovery["mode"],
            "discovery_automation": discovery["automation_status"],
            "discovery_status": (
                "manual_review_required"
                if discovery["automation_status"] != "implemented"
                else "adapter_not_supported_by_generic_runner"
            ),
            "downloads": [],
        }
        for item in source.get("downloads", []):
            prior = snapshot_rows[(source_id, item["id"])]
            result = {
                "download_id": item["id"],
                "configured_release": item["release"],
                "release_kind": item["release_kind"],
                "prior_snapshot_status": prior["status"],
            }
            if prior["status"] == "valid":
                result.update(status="unchanged", detail="Existing immutable snapshot and manifest passed checksum validation")
            elif prior["status"] == "invalid":
                result.update(status="validation_error", detail=prior["detail"])
            elif dry_run:
                result.update(status="would_acquire", detail="Configured snapshot is missing; dry run made no network request")
            else:
                try:
                    manifest = acquire_one(registry, source_id, item, timeout=timeout)
                    result.update(
                        status="acquired_pending_source_validation",
                        sha256=manifest["sha256"],
                        byte_count=manifest["byte_count"],
                        manifest_path=registry["storage"]["manifest_root"] + "/" + source_id + "/" + item["id"] + "/" + item["release"] + ".json",
                        detail="Acquisition and registered response checks passed; provider data-contract validation is still required",
                    )
                except Exception as exc:
                    result.update(status="acquisition_failed", detail=str(exc))
            source_result["downloads"].append(result)
        if not source.get("downloads"):
            source_result["discovery_status"] = "manual_review_required"
            source_result["detail"] = "No generic HTTPS download is configured; use a provider-specific adapter or manual workflow"
        results.append(source_result)

    counts = {}
    for source in results:
        for download in source["downloads"]:
            counts[download["status"]] = counts.get(download["status"], 0) + 1
    counts["sources_manual_review_required"] = sum(
        source["discovery_status"] == "manual_review_required" for source in results
    )
    counts["sources_with_no_generic_download"] = sum(
        not source["downloads"] for source in results
    )
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%S%fZ")
    output_root = report_root or (ROOT / registry["storage"]["reports_root"] / "refreshes")
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    report = {
        "report_schema_version": 1,
        "run_id": run_id,
        "checked_at": now.isoformat(),
        "selection_policy": registry["release_management"]["selection_policy"],
        "dry_run": dry_run,
        "database_imported": False,
        "source_count": len(results),
        "counts": counts,
        "sources": results,
        "limitations": [
            "Only explicitly configured HTTPS downloads are acquired by this generic refresh runner.",
            "Provider release discovery adapters are not inferred from discovery-mode declarations.",
            "Acquired snapshots have passed only their registered response contract; source-specific semantic validation is still required.",
            "latest_available, latest_validated and latest_applied are not promoted or modified by this command.",
            "No canonical database import or approval is performed.",
        ],
    }
    json_path = output_root / f"refresh-{run_id}.json"
    markdown_path = output_root / f"refresh-{run_id}.md"
    report["report_paths"] = {"json": json_path.as_posix(), "markdown": markdown_path.as_posix()}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Source refresh report",
        "",
        f"- Run: {run_id}",
        f"- Checked: {now.isoformat()}",
        f"- Dry run: {dry_run}",
        "- Canonical database imported: no",
        "",
        "## Counts",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(counts.items()))
    lines.extend(["", "## Source results", ""])
    for source in results:
        lines.append(f"### {source['source_id']}")
        lines.append(f"- Discovery: {source['discovery_status']} ({source['discovery_mode']})")
        if source.get("detail"):
            lines.append(f"- Note: {source['detail']}")
        for item in source["downloads"]:
            lines.append(f"- {item['download_id']} [{item['configured_release']}]: **{item['status']}** — {item['detail']}")
        lines.append("")
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {value}" for value in report["limitations"])
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
