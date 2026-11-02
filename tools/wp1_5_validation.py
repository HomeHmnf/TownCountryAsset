"""Shared WP1.5 candidate discovery, validation, and report orchestration."""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.connection import DEFAULT_DATABASE_PATH, REPOSITORY_ROOT

class ValidationError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"Expected JSON object: {path}")
    return value

def discover_candidate(source: str) -> tuple[Path, dict[str, Any]]:
    candidates = []
    for manifest_path in (REPOSITORY_ROOT / "generated").rglob("application_manifest.json"):
        try:
            manifest = read_json(manifest_path)
        except (OSError, json.JSONDecodeError, ValidationError):
            continue
        if manifest.get("source_key") == source:
            retrieved = manifest.get("retrieved_at")
            if not isinstance(retrieved, str) or not retrieved:
                raise ValidationError(f"Candidate manifest lacks retrieved_at: {manifest_path}")
            candidates.append((retrieved, manifest_path.parent, manifest))
    if not candidates:
        raise ValidationError(f"No generated candidate found for source {source!r}")
    candidates.sort(key=lambda item: item[0], reverse=True)
    newest = candidates[0][0]
    tied = [item for item in candidates if item[0] == newest]
    if len(tied) != 1:
        raise ValidationError(
            f"Ambiguous newest {source} candidate: {len(tied)} candidates share retrieved_at={newest}"
        )
    _, directory, manifest = tied[0]
    observations = directory / "normalized_observations.json"
    if not observations.is_file():
        raise ValidationError(f"Candidate is incomplete; missing {observations}")
    return directory, manifest

def verify_manifest_inputs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    inputs = [{"label": "primary", **manifest}]
    inputs.extend(manifest.get("additional_inputs", []))
    for item in inputs:
        raw_value = item.get("local_raw_path")
        expected = item.get("sha256")
        if not isinstance(raw_value, str) or not isinstance(expected, str):
            raise ValidationError(f"Candidate input lacks path/checksum: {item.get('label', 'primary')}")
        raw = Path(raw_value)
        if not raw.is_absolute():
            raw = (REPOSITORY_ROOT / raw).resolve()
        if not raw.is_file():
            raise ValidationError(f"Candidate source snapshot is missing: {raw}")
        actual = sha256(raw)
        size = raw.stat().st_size
        if actual != expected or (item.get("byte_count") is not None and size != item["byte_count"]):
            raise ValidationError(f"Candidate source snapshot fingerprint mismatch: {raw}")
        results.append({"label": item.get("label", "primary"), "path": str(raw), "sha256": actual, "bytes": size})
    for upstream in manifest.get("upstream_manifests", []):
        path = Path(upstream["path"])
        if not path.is_absolute():
            path = (REPOSITORY_ROOT / path).resolve()
        if not path.is_file() or sha256(path) != upstream.get("sha256"):
            raise ValidationError(f"Upstream acquisition manifest fingerprint mismatch: {path}")
        results.append({"label": "upstream_manifest", "path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    return results

def open_database_readonly(path: Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    if not path.is_file():
        raise ValidationError(f"Canonical database is mandatory but missing: {path}")
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection

def write_reports(source: str, candidate_dir: Path, report: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / source / stamp
    target.mkdir(parents=True, exist_ok=False)
    (target / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    lines = [
        f"# WP1.5 validation: {source}", "",
        f"- Result: **{report['result']}**",
        f"- Candidate: `{candidate_dir.relative_to(REPOSITORY_ROOT)}`",
        f"- Database: `{report['database_path']}`",
        f"- Checked at: {report['checked_at']}", "",
        "## Checks", "",
        "| Check | Status | Detail |", "|---|---|---|",
    ]
    for check in report["checks"]:
        detail = str(check.get("detail", "")).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    lines.extend(["", "## Exceptions", ""])
    if report["exceptions"]:
        lines.extend(f"- {item}" for item in report["exceptions"])
    else:
        lines.append("None.")
    (target / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (target / "validation_exceptions.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["severity", "check", "message"])
        writer.writeheader()
        writer.writerows(report["exception_rows"])
    return target

def run_validation(source: str, validator, output_root: Path | None = None) -> tuple[dict[str, Any], Path]:
    candidate_dir, manifest = discover_candidate(source)
    snapshots = verify_manifest_inputs(manifest)
    observations_payload = read_json(candidate_dir / "normalized_observations.json")
    if observations_payload.get("source_key") != source or observations_payload.get("release") != manifest.get("release"):
        raise ValidationError("Normalized observations do not match candidate manifest source/release")
    if observations_payload.get("schema_version") != 1 or not isinstance(observations_payload.get("observations"), list):
        raise ValidationError("Normalized observations have an unsupported schema")
    connection = open_database_readonly()
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok":
            raise ValidationError(f"Canonical database integrity_check failed: {integrity}")
        if foreign_keys:
            raise ValidationError(f"Canonical database has {len(foreign_keys)} foreign-key violations")
        checks = [
            {"name": "snapshot_fingerprints", "status": "PASS", "detail": f"{len(snapshots)} immutable inputs verified"},
            {"name": "database_integrity", "status": "PASS", "detail": "integrity_check=ok; foreign_key_check=0"},
        ]
        checks.extend(validator.validate(
            connection=connection, candidate_dir=candidate_dir, manifest=manifest,
            observations=observations_payload["observations"],
        ))
    finally:
        connection.close()
    exception_rows = []
    for check in checks:
        if check["status"] in {"FAIL", "WARNING"}:
            exception_rows.append({
                "severity": check["status"], "check": check["name"], "message": check.get("detail", "")
            })
    result = "FAIL" if any(x["status"] == "FAIL" for x in checks) else (
        "WARNING" if any(x["status"] == "WARNING" for x in checks) else "PASS"
    )
    report = {
        "schema_version": 1, "source": source, "result": result,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "candidate_directory": str(candidate_dir), "release": manifest.get("release"),
        "database_path": str(DEFAULT_DATABASE_PATH), "snapshots": snapshots,
        "checks": checks, "exceptions": [x["detail"] for x in checks if x["status"] in {"FAIL", "WARNING"}],
        "exception_rows": exception_rows,
        "side_effects": {"database_write": False, "approval_created": False, "application_performed": False, "release_promoted": False},
    }
    output = write_reports(source, candidate_dir, report, output_root or (REPOSITORY_ROOT / "reports" / "database" / "town_country_asset" / "wp1-5"))
    return report, output
