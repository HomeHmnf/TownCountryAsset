"""Project-wide approval gate for changes to canonical SQLite data.

Provider adapters prepare immutable application artifacts. This module records
and verifies approval independently of provider or database domain.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from tools.database.connection import REPOSITORY_ROOT

APPROVAL_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{7,119}$")


class ApplicationApprovalError(RuntimeError):
    """An application is not eligible for canonical database changes."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_file(path: str | Path) -> str:
    target = Path(path).resolve()
    try:
        target.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError as exc:
        raise ApplicationApprovalError("Approval inputs must be inside the repository") from exc
    if not target.is_file():
        raise ApplicationApprovalError(f"Approval input does not exist: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_application_artifact(
    *,
    domain: str,
    inputs: Iterable[str | Path],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fingerprint every reviewed input; paths are repository-relative and sorted."""
    if not isinstance(domain, str) or not domain.strip():
        raise ApplicationApprovalError("Application domain must be non-empty text")
    files = []
    for item in inputs:
        path = Path(item).resolve()
        digest = sha256_file(path)
        files.append({
            "path": path.relative_to(REPOSITORY_ROOT.resolve()).as_posix(),
            "sha256": digest,
            "byte_count": path.stat().st_size,
        })
    if not files:
        raise ApplicationApprovalError("At least one reviewed input file is required")
    files.sort(key=lambda row: row["path"])
    if len({row["path"] for row in files}) != len(files):
        raise ApplicationApprovalError("Duplicate approval input paths are not allowed")
    if metadata is not None and not isinstance(metadata, dict):
        raise ApplicationApprovalError("Application metadata must be an object")
    artifact = {
        "schema_version": 1,
        "domain": domain,
        "inputs": files,
        "metadata": metadata or {},
    }
    # Ensure metadata is JSON-safe and deterministic before hashing.
    canonical_json(artifact)
    artifact["artifact_sha256"] = hashlib.sha256(canonical_json(artifact).encode("utf-8")).hexdigest()
    return artifact


def _event(
    connection: sqlite3.Connection,
    approval_id: str,
    event_type: str,
    *,
    actor: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """INSERT INTO database_application_events
           (approval_id, event_type, event_at, actor, details_json)
           VALUES (?, ?, ?, ?, ?)""",
        (approval_id, event_type, utc_now(), actor, canonical_json(details or {})),
    )


def propose_application(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    artifact: dict[str, Any],
) -> None:
    """Register a pending proposal. Does not modify canonical domain tables."""
    if not APPROVAL_ID.fullmatch(approval_id):
        raise ApplicationApprovalError("approval_id must be 8-120 safe characters")
    if artifact.get("schema_version") != 1 or not artifact.get("artifact_sha256"):
        raise ApplicationApprovalError("Unsupported or incomplete application artifact")
    body = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    expected = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    if artifact["artifact_sha256"] != expected:
        raise ApplicationApprovalError("Application artifact fingerprint is invalid")
    connection.execute(
        """INSERT INTO application_approvals
           (approval_id, domain, artifact_sha256, artifact_json, status, created_at)
           VALUES (?, ?, ?, ?, 'pending', ?)""",
        (approval_id, artifact["domain"], expected, canonical_json(artifact), utc_now()),
    )
    _event(connection, approval_id, "proposed", details={"artifact_sha256": expected})


def decide_application(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    decision: str,
    actor: str,
    note: str | None = None,
) -> None:
    """Record an explicit human approval or rejection of a pending proposal."""
    if decision not in {"approved", "rejected"}:
        raise ApplicationApprovalError("Decision must be approved or rejected")
    if not isinstance(actor, str) or not actor.strip():
        raise ApplicationApprovalError("Approval actor must be identified")
    row = connection.execute(
        "SELECT status FROM application_approvals WHERE approval_id = ?", (approval_id,)
    ).fetchone()
    if row is None or row["status"] != "pending":
        raise ApplicationApprovalError("Only a pending application can be approved or rejected")
    now = utc_now()
    if decision == "approved":
        connection.execute(
            """UPDATE application_approvals
               SET status='approved', approved_by=?, approved_at=?, decision_note=?
               WHERE approval_id=? AND status='pending'""",
            (actor.strip(), now, note, approval_id),
        )
    else:
        connection.execute(
            """UPDATE application_approvals
               SET status='rejected', decision_note=?
               WHERE approval_id=? AND status='pending'""",
            (note, approval_id),
        )
    _event(connection, approval_id, decision, actor=actor.strip(), details={"note": note})


def require_approved_application(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    artifact: dict[str, Any],
) -> sqlite3.Row:
    """Verify approval still matches the exact reviewed artifact before any writes."""
    row = connection.execute(
        "SELECT * FROM application_approvals WHERE approval_id = ?", (approval_id,)
    ).fetchone()
    if row is None:
        raise ApplicationApprovalError(f"Unknown application approval: {approval_id}")
    # Re-read every path at apply time. Comparing only a caller-supplied
    # artifact object would allow stale hashes to survive changed input files.
    inputs = artifact.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise ApplicationApprovalError("Application artifact has no reviewed input files")
    refreshed_inputs = []
    for item in inputs:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ApplicationApprovalError("Application artifact contains an invalid input entry")
        path = (REPOSITORY_ROOT / item["path"]).resolve()
        digest = sha256_file(path)
        refreshed_inputs.append({
            "path": path.relative_to(REPOSITORY_ROOT.resolve()).as_posix(),
            "sha256": digest,
            "byte_count": path.stat().st_size,
        })
    refreshed_inputs.sort(key=lambda entry: entry["path"])
    body = {
        "schema_version": artifact.get("schema_version"),
        "domain": artifact.get("domain"),
        "inputs": refreshed_inputs,
        "metadata": artifact.get("metadata", {}),
    }
    actual_digest = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    if actual_digest != artifact.get("artifact_sha256") or actual_digest != row["artifact_sha256"]:
        if row["status"] == "approved":
            connection.execute(
                "UPDATE application_approvals SET status='invalidated' WHERE approval_id=?",
                (approval_id,),
            )
            _event(connection, approval_id, "invalidated", details={"reason": "artifact fingerprint changed"})
        raise ApplicationApprovalError("Reviewed application inputs changed; a new approval is required")
    if row["status"] != "approved":
        raise ApplicationApprovalError(f"Application is not approved (status={row['status']})")
    return row


def record_application_applied(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    application_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Mark the approved artifact applied; call inside the same transaction as domain writes."""
    if not isinstance(application_id, str) or not application_id.strip():
        raise ApplicationApprovalError("application_id must be non-empty text")
    cursor = connection.execute(
        """UPDATE application_approvals
           SET status='applied', applied_at=?, application_id=?
           WHERE approval_id=? AND status='approved'""",
        (utc_now(), application_id, approval_id),
    )
    if cursor.rowcount != 1:
        raise ApplicationApprovalError("Application approval was consumed or is no longer valid")
    _event(connection, approval_id, "applied", details={"application_id": application_id, **(details or {})})
