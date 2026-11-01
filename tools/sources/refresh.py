"""Project-wide source refresh orchestration.

Rolling/current-reference discovery uses content fingerprints. Discovery never
promotes latest_validated or imports data into the canonical database.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from tools.sources.registry import ROOT, SourceError, acquire_one, inspect_snapshots


FINGERPRINT_MODES = {"rolling_url", "website_page"}
FINGERPRINT_KINDS = {"rolling", "current_reference"}
MAX_DISCOVERY_BYTES = 250 * 1024 * 1024


def _discover_fingerprint(item: dict, timeout: int) -> dict:
    """GET a configured resource and identify its exact bytes by SHA-256."""
    request = urllib.request.Request(
        item["url"],
        headers={"User-Agent": "TownCountryAsset-SourceRefresh/1.0", "Accept": "*/*"},
    )
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            parsed = urlparse(final_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise SourceError("Release discovery redirect target must remain HTTPS")
            content_type = response.headers.get("Content-Type")
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_DISCOVERY_BYTES:
                    raise SourceError("Release discovery response exceeds the 250 MiB safety limit")
                digest.update(chunk)
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError(f"Release discovery failed for {item['id']}: {exc}") from exc
    if not size:
        raise SourceError("Release discovery response is empty")
    sha256 = digest.hexdigest()
    return {
        "release_id": "content-" + sha256,
        "provider_release_label": "content-sha256:" + sha256,
        "sha256": sha256,
        "byte_count": size,
        "content_type": content_type,
        "url": final_url,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }


def _discover_git_ref(discovery: dict, timeout: int) -> dict:
    """Resolve the latest commit on a GitHub repository's default branch."""
    parsed = urlparse(discovery.get("provider_url") or "")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"github.com", "www.github.com"} or len(parts) < 2:
        raise SourceError("git_ref discovery currently requires a GitHub repository URL")
    owner, repository = parts[0], parts[1].removesuffix(".git")
    api_url = "https://api.github.com/repos/" + owner + "/" + repository + "/commits?per_page=1"
    request = urllib.request.Request(api_url, headers={
        "User-Agent": "TownCountryAsset-SourceRefresh/1.0",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.geturl().split(":", 1)[0].lower() != "https":
                raise SourceError("GitHub discovery redirect target must remain HTTPS")
            payload = json.loads(response.read().decode("utf-8"))
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError("GitHub commit discovery failed: " + str(exc)) from exc
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise SourceError("GitHub returned no default-branch commit")
    commit = payload[0]
    sha = commit.get("sha")
    metadata = commit.get("commit", {})
    timestamp = metadata.get("committer", {}).get("date") or metadata.get("author", {}).get("date")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-fA-F]{40,64}", sha) is None:
        raise SourceError("GitHub returned an invalid commit SHA")
    return {
        "release_id": "git-" + sha.lower(),
        "provider_release_label": "git-commit:" + sha.lower(),
        "provider_published_at": None,
        "provider_commit_timestamp": timestamp,
        "sha256": None,
        "byte_count": None,
        "content_type": "application/json",
        "url": "https://github.com/" + owner + "/" + repository + "/commit/" + sha,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }


def _release_state_path(registry: dict, source_id: str) -> Path:
    root = registry.get("_root", ROOT)
    template = registry["release_management"]["release_record"]["path_template"]
    relative = template.replace("<source-id>", source_id)
    return root / relative


def _record_release(
    registry: dict,
    source_id: str,
    discovered: dict,
    *,
    status: str,
    snapshot_manifest: str | None = None,
) -> Path:
    """Append/update one content-fingerprint release without touching other states."""
    path = _release_state_path(registry, source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceError(f"Cannot read release state {path}: {exc}") from exc
        if record.get("source_id") != source_id or not isinstance(record.get("history"), list):
            raise SourceError(f"Release state identity/schema mismatch: {path}")
    else:
        record = {
            "schema_version": 1,
            "source_id": source_id,
            "checked_at": None,
            "discovery_mode": registry["sources"][source_id]["release_discovery"]["mode"],
            "latest_available": None,
            "latest_validated": None,
            "latest_applied": None,
            "history": [],
        }

    entry = next(
        (row for row in record["history"] if row.get("release_id") == discovered["release_id"]),
        None,
    )
    if entry is None:
        entry = {
            "release_id": discovered["release_id"],
            "provider_release_label": discovered["provider_release_label"],
            "provider_published_at": None,
            "discovered_at": discovered["discovered_at"],
            "acquired_at": None,
            "validated_at": None,
            "applied_at": None,
            "status": status,
            "snapshot_manifest": snapshot_manifest,
            "notes": "Content-fingerprint candidate; no provider publication date or semantic edition is inferred.",
            "sha256": discovered.get("sha256"),
            "byte_count": discovered.get("byte_count"),
            "content_type": discovered["content_type"],
            "url": discovered["url"],
        }
        record["history"].append(entry)
    else:
        entry["status"] = status
        if snapshot_manifest is not None:
            entry["snapshot_manifest"] = snapshot_manifest
        if status == "acquired" and entry.get("acquired_at") is None:
            entry["acquired_at"] = datetime.now(timezone.utc).isoformat()

    record["checked_at"] = discovered["discovered_at"]
    record["latest_available"] = dict(entry)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise SourceError(f"Cannot persist release state {path}: {exc}") from exc
    return path


def _inspect_release_snapshot(registry: dict, source_id: str, item: dict) -> dict:
    """Reuse the shared checksum/manifest inspector for a discovered release ID."""
    scoped = copy.deepcopy(registry)
    scoped["sources"][source_id]["downloads"] = [item]
    return inspect_snapshots(scoped)[0]


def _is_fingerprint_source(discovery: dict, item: dict) -> bool:
    return (
        discovery["automation_status"] == "implemented"
        and discovery["mode"] in FINGERPRINT_MODES
        and item.get("release_kind") in FINGERPRINT_KINDS
    )


def run_refresh(
    registry: dict,
    *,
    source_ids: list[str] | None = None,
    timeout: int = 60,
    dry_run: bool = False,
    report_root: Path | None = None,
) -> dict:
    """Discover/acquire configured resources, retaining immutable snapshots."""
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
                else "implemented_adapter_not_applicable"
            ),
            "downloads": [],
        }

        if (
            not source.get("downloads")
            and discovery["automation_status"] == "implemented"
            and discovery["mode"] == "git_ref"
        ):
            try:
                discovered = _discover_git_ref(discovery, timeout)
                state_path = _record_release(registry, source_id, discovered, status="discovered")
                source_result["discovery_status"] = "git_ref_discovery"
                source_result["git_ref"] = {
                    "release_id": discovered["release_id"],
                    "commit_timestamp": discovered["provider_commit_timestamp"],
                    "release_state_path": state_path.as_posix(),
                    "detail": "Default-branch commit discovered; source archive acquisition and content validation remain separate",
                }
            except Exception as exc:
                source_result["discovery_status"] = "discovery_failed"
                source_result["detail"] = str(exc)

        for item in source.get("downloads", []):
            if _is_fingerprint_source(discovery, item):
                if dry_run:
                    source_result["downloads"].append({
                        "download_id": item["id"],
                        "configured_release": item["release"],
                        "release_kind": item["release_kind"],
                        "status": "would_discover",
                        "detail": "Dry run does not contact the provider or inspect fingerprinted releases",
                    })
                    source_result["discovery_status"] = "dry_run_not_checked"
                    continue
                try:
                    discovered = _discover_fingerprint(item, timeout)
                    dynamic_item = {**item, "release": discovered["release_id"]}
                    prior = _inspect_release_snapshot(registry, source_id, dynamic_item)
                    state_path = _record_release(
                        registry,
                        source_id,
                        discovered,
                        status="acquired" if prior["status"] == "valid" else "discovered",
                    )
                    result = {
                        "download_id": item["id"],
                        "configured_release": item["release"],
                        "discovered_release": discovered["release_id"],
                        "release_kind": item["release_kind"],
                        "prior_snapshot_status": prior["status"],
                        "release_state_path": state_path.as_posix(),
                        "discovered_sha256": discovered["sha256"],
                    }
                    if prior["status"] == "valid":
                        result.update(
                            status="unchanged",
                            detail="Provider content fingerprint matches an existing immutable snapshot",
                        )
                    elif prior["status"] == "invalid":
                        result.update(status="validation_error", detail=prior["detail"])
                    elif prior["status"] == "missing" and (
                        (registry.get("_root", ROOT) / prior["raw_path"]).exists()
                        or (
                            registry.get("_root", ROOT)
                            / registry["storage"]["manifest_root"]
                            / source_id
                            / item["id"]
                            / f"{dynamic_item['release']}.json"
                        ).exists()
                    ):
                        result.update(
                            status="validation_error",
                            detail="Incomplete fingerprinted snapshot preserved without overwrite",
                        )
                    else:
                        manifest = acquire_one(registry, source_id, dynamic_item, timeout=timeout)
                        if manifest["sha256"] != discovered["sha256"]:
                            result.update(
                                status="changed_during_acquisition",
                                acquired_sha256=manifest["sha256"],
                                detail="Provider content changed between discovery and acquisition; snapshot retained but not accepted as the discovered fingerprint",
                            )
                        else:
                            manifest_path = (
                                registry["storage"]["manifest_root"]
                                + "/"
                                + source_id
                                + "/"
                                + item["id"]
                                + "/"
                                + dynamic_item["release"]
                                + ".json"
                            )
                            _record_release(
                                registry,
                                source_id,
                                discovered,
                                status="acquired",
                                snapshot_manifest=manifest_path,
                            )
                            result.update(
                                status="acquired_pending_source_validation",
                                sha256=manifest["sha256"],
                                byte_count=manifest["byte_count"],
                                manifest_path=manifest_path,
                                detail="Fingerprint matched acquired bytes and registered response checks passed; source-specific semantic validation is still required",
                            )
                    source_result["downloads"].append(result)
                    source_result["discovery_status"] = "content_fingerprint_discovery"
                except Exception as exc:
                    source_result["downloads"].append({
                        "download_id": item["id"],
                        "configured_release": item["release"],
                        "release_kind": item["release_kind"],
                        "status": "discovery_or_acquisition_failed",
                        "detail": str(exc),
                    })
                    source_result["discovery_status"] = "discovery_failed"
                continue

            prior = snapshot_rows[(source_id, item["id"])]
            result = {
                "download_id": item["id"],
                "configured_release": item["release"],
                "release_kind": item["release_kind"],
                "prior_snapshot_status": prior["status"],
            }
            if prior["status"] == "valid":
                result.update(
                    status="unchanged",
                    detail="Existing immutable snapshot and manifest passed checksum validation",
                )
            elif prior["status"] == "invalid":
                result.update(status="validation_error", detail=prior["detail"])
            elif prior["status"] == "missing" and (
                (registry.get("_root", ROOT) / prior["raw_path"]).exists()
                or (
                    registry.get("_root", ROOT)
                    / registry["storage"]["manifest_root"]
                    / prior["snapshot_source_id"]
                    / item["id"]
                    / f"{item['release']}.json"
                ).exists()
            ):
                result.update(
                    status="validation_error",
                    detail="Incomplete snapshot: raw file or manifest exists without its counterpart; preserved without overwrite",
                )
            elif dry_run:
                result.update(
                    status="would_acquire",
                    detail="Configured snapshot is missing; dry run made no network request",
                )
            else:
                try:
                    manifest = acquire_one(registry, source_id, item, timeout=timeout)
                    result.update(
                        status="acquired_pending_source_validation",
                        sha256=manifest["sha256"],
                        byte_count=manifest["byte_count"],
                        manifest_path=(
                            registry["storage"]["manifest_root"]
                            + "/"
                            + source_id
                            + "/"
                            + item["id"]
                            + "/"
                            + item["release"]
                            + ".json"
                        ),
                        detail="Acquisition and registered response checks passed; provider data-contract validation is still required",
                    )
                except Exception as exc:
                    result.update(status="acquisition_failed", detail=str(exc))
            source_result["downloads"].append(result)

        if not source.get("downloads"):
            source_result["discovery_status"] = "manual_review_required"
            source_result["detail"] = (
                "No generic HTTPS download is configured; use a provider-specific adapter or manual workflow"
            )
        results.append(source_result)

    counts = {}
    for source in results:
        for download in source["downloads"]:
            status = download["status"]
            counts[status] = counts.get(status, 0) + 1
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
            "Rolling/current-reference discovery uses content fingerprints, not provider semantic release labels.",
            "Only sources explicitly marked automation_status=implemented use fingerprint discovery.",
            "Acquired snapshots have passed only their registered response contract; source-specific semantic validation is still required.",
            "latest_available is recorded in a separate release ledger; latest_validated and latest_applied are never promoted by refresh.",
            "No canonical database import or approval is performed.",
        ],
    }
    json_path = output_root / f"refresh-{run_id}.json"
    markdown_path = output_root / f"refresh-{run_id}.md"
    report["report_paths"] = {
        "json": json_path.as_posix(),
        "markdown": markdown_path.as_posix(),
    }
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
            lines.append(
                f"- {item['download_id']} [{item.get('discovered_release', item['configured_release'])}]: "
                f"**{item['status']}** — {item['detail']}"
            )
        lines.append("")
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {value}" for value in report["limitations"])
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
