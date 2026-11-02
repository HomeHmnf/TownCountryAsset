"""Approval-gated release validation and promotion for WP1.5 providers.

The proposal is evidence-bound. Approval is an explicit human action; promotion
rechecks every fingerprint before changing the source release ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.connection import REPOSITORY_ROOT
from tools.sources.registry import SourceError, load_registry

ROOT = REPOSITORY_ROOT
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
PROPOSALS = ROOT / "reports" / "sources" / "release-validations"


class ReleaseValidationError(RuntimeError):
    """Invalid release evidence, approval or promotion request."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseValidationError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseValidationError(f"Expected JSON object: {path}")
    return value


def _inside_root(path: Path, *, directory: bool = False) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ReleaseValidationError(f"Release evidence must be inside repository: {path}") from exc
    valid = resolved.is_dir() if directory else resolved.is_file()
    if not valid:
        kind = "directory" if directory else "file"
        raise ReleaseValidationError(f"Release evidence {kind} is missing: {resolved}")
    return resolved


def _fingerprint(path: Path, label: str) -> dict[str, Any]:
    path = _inside_root(path)
    return {
        "label": label,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(path),
        "byte_count": path.stat().st_size,
    }


def _proposal_path(approval_id: str) -> Path:
    if not SAFE_ID.fullmatch(approval_id):
        raise ReleaseValidationError("approval_id contains unsupported characters")
    return PROPOSALS / f"{approval_id}.json"


def _proposal_digest(proposal: dict[str, Any]) -> str:
    payload = {key: value for key, value in proposal.items() if key not in {"approval", "proposal_sha256"}}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_evidence(source: str, report_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report_path = _inside_root(report_path)
    report = _json(report_path)
    if report.get("source") != source or report.get("result") != "PASS":
        raise ReleaseValidationError("A PASS WP1.5 validation report for the requested source is required")
    if report.get("side_effects", {}).get("release_promoted") is not False:
        raise ReleaseValidationError("Validation report does not attest that release promotion was not performed")
    required_checks = {
        "snapshot_fingerprints",
        "database_integrity",
        "candidate_field_coverage",
        "wpp_age_sex_population_semantics",
        "canonical_database_value_parity",
        "togo_supplement_provenance",
        "source_selection_resolver_compatibility",
    }
    checks = {item.get("name"): item for item in report.get("checks", [])}
    missing = required_checks - set(checks)
    failed = [name for name in required_checks if checks.get(name, {}).get("status") != "PASS"]
    if missing or failed:
        raise ReleaseValidationError(
            f"Validation evidence is incomplete or not passing; missing={sorted(missing)}, non_pass={sorted(failed)}"
        )
    candidate = _inside_root(Path(report["candidate_directory"]), directory=True)
    manifest_path = _inside_root(candidate / "application_manifest.json")
    observations_path = _inside_root(candidate / "normalized_observations.json")
    manifest = _json(manifest_path)
    if manifest.get("source_key") != source or manifest.get("release") != report.get("release"):
        raise ReleaseValidationError("Candidate manifest source/release does not match validation report")
    evidence = [
        _fingerprint(report_path, "wp1_5_validation_report"),
        _fingerprint(manifest_path, "candidate_application_manifest"),
        _fingerprint(observations_path, "normalized_observations"),
        _fingerprint(ROOT / "config" / "source_selection.json", "source_selection_policy"),
        _fingerprint(ROOT / "config" / "data_sources.json", "source_registry"),
    ]
    for index, snapshot in enumerate(report.get("snapshots", [])):
        evidence.append(_fingerprint(ROOT / snapshot["path"], f"snapshot_{index}_{snapshot.get('label', 'input')}"))
    return report, evidence


def propose_release(source: str, approval_id: str, report_path: Path, actor: str, note: str) -> dict[str, Any]:
    if source != "un_wpp":
        raise ReleaseValidationError("This initial release-validation workflow is scoped to un_wpp")
    path = _proposal_path(approval_id)
    if path.exists():
        raise ReleaseValidationError(f"Release validation proposal already exists and is immutable: {path}")
    report, evidence = _load_evidence(source, report_path)
    proposal = {
        "schema_version": 1,
        "approval_id": approval_id,
        "source_id": source,
        "release_id": report["release"],
        "candidate_directory": Path(report["candidate_directory"]).resolve().relative_to(ROOT).as_posix(),
        "validation_report": next(item["path"] for item in evidence if item["label"] == "wp1_5_validation_report"),
        "validation_result": report["result"],
        "validation_checked_at": report["checked_at"],
        "validation_checks": {item["name"]: item["status"] for item in report["checks"]},
        "resolver_eligibility": "simulated_in_memory_only",
        "evidence": evidence,
        "created_at": _now(),
        "created_by": actor,
        "note": note,
        "approval": {"status": "pending", "approved_at": None, "actor": None, "note": None},
    }
    proposal["proposal_sha256"] = _proposal_digest(proposal)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return {"approval_id": approval_id, "status": "pending", "release_id": proposal["release_id"],
            "proposal_sha256": proposal["proposal_sha256"], "evidence_files": len(evidence), "path": str(path)}


def decide_release(approval_id: str, actor: str, note: str, approve: bool) -> dict[str, Any]:
    path = _proposal_path(approval_id)
    proposal = _json(path)
    if proposal.get("proposal_sha256") != _proposal_digest(proposal):
        raise ReleaseValidationError("Proposal content does not match its immutable proposal SHA-256")
    if proposal.get("approval", {}).get("status") != "pending":
        raise ReleaseValidationError("Only a pending release proposal can be decided")
    proposal["approval"] = {
        "status": "approved" if approve else "rejected",
        "approved_at": _now() if approve else None,
        "actor": actor,
        "note": note,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(proposal, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return {"approval_id": approval_id, "status": proposal["approval"]["status"],
            "proposal_sha256": proposal["proposal_sha256"]}


def promote_release(approval_id: str) -> dict[str, Any]:
    path = _proposal_path(approval_id)
    proposal = _json(path)
    if proposal.get("proposal_sha256") != _proposal_digest(proposal):
        raise ReleaseValidationError("Proposal content does not match its immutable proposal SHA-256")
    if proposal.get("approval", {}).get("status") != "approved":
        raise ReleaseValidationError("Release promotion requires an explicitly approved proposal")
    for item in proposal.get("evidence", []):
        evidence_path = _inside_root(ROOT / item["path"])
        if _sha256(evidence_path) != item["sha256"] or evidence_path.stat().st_size != item["byte_count"]:
            raise ReleaseValidationError(f"Approved release evidence changed: {item['path']}")
    report = _json(ROOT / proposal["validation_report"])
    if report.get("result") != "PASS" or report.get("release") != proposal["release_id"]:
        raise ReleaseValidationError("Validation report no longer supports this release")
    registry = load_registry()
    source_id = proposal["source_id"]
    if source_id not in registry["sources"]:
        raise ReleaseValidationError(f"Unknown source in approved proposal: {source_id}")
    ledger_path = ROOT / "reports" / "sources" / "releases" / f"{source_id}.json"
    if ledger_path.exists():
        ledger = _json(ledger_path)
    else:
        ledger = {
            "source_id": source_id, "checked_at": None,
            "discovery_mode": registry["sources"][source_id]["release_discovery"]["mode"],
            "latest_available": None, "latest_validated": None, "latest_applied": None, "history": [],
        }
    current = ledger.get("latest_validated")
    if isinstance(current, dict) and current.get("release_id") == proposal["release_id"] and current.get("approval_id") == approval_id:
        raise ReleaseValidationError("This approved release proposal has already been promoted")
    if isinstance(current, dict) and current.get("release_id") != proposal["release_id"]:
        raise ReleaseValidationError(
            f"Refusing to replace existing latest_validated release {current.get('release_id')!r}; "
            "a separate supersession decision is required"
        )
    candidate_manifest_path = _inside_root(
        ROOT / proposal["candidate_directory"] / "application_manifest.json"
    )
    candidate_manifest = _json(candidate_manifest_path)
    if (
        candidate_manifest.get("source_key") != source_id
        or candidate_manifest.get("release") != proposal["release_id"]
    ):
        raise ReleaseValidationError("Candidate application manifest no longer matches the approved release")
    acquired_at = candidate_manifest.get("retrieved_at")
    if not isinstance(acquired_at, str) or not acquired_at.strip():
        raise ReleaseValidationError("Candidate manifest has no valid retrieval timestamp")

    now = _now()
    entry = {
        "release_id": proposal["release_id"],
        "provider_release_label": proposal["release_id"],
        "provider_published_at": None,
        "provider_commit_timestamp": None,
        "fetched_at": acquired_at,
        "discovered_at": None,
        "acquired_at": acquired_at,
        "validated_at": now,
        "applied_at": current.get("applied_at") if isinstance(current, dict) else None,
        "status": "applied" if isinstance(current, dict) and current.get("status") == "applied" else "validated",
        "snapshot_manifest": (Path(proposal["candidate_directory"]) / "application_manifest.json").as_posix(),
        "notes": "Approved WP1.5 release validation; see approval artifact " + approval_id,
        "approval_id": approval_id,
        "proposal_sha256": proposal["proposal_sha256"],
    }
    history = ledger.setdefault("history", [])
    if not isinstance(history, list):
        raise ReleaseValidationError("Release ledger history must be an array")
    history = [item for item in history if not (isinstance(item, dict) and item.get("release_id") == proposal["release_id"])]
    history.append(entry)
    ledger["history"] = history
    ledger["latest_validated"] = entry
    ledger["checked_at"] = now
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = ledger_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(ledger_path)
    return {"source_id": source_id, "release_id": proposal["release_id"],
            "latest_validated": proposal["release_id"], "ledger": str(ledger_path),
            "approval_id": approval_id, "promoted_at": now}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    propose = sub.add_parser("propose")
    propose.add_argument("--source", required=True)
    propose.add_argument("--approval-id", required=True)
    propose.add_argument("--report", type=Path, required=True)
    propose.add_argument("--actor", required=True)
    propose.add_argument("--note", required=True)
    for name in ("approve", "reject"):
        decision = sub.add_parser(name)
        decision.add_argument("--approval-id", required=True)
        decision.add_argument("--actor", required=True)
        decision.add_argument("--note", required=True)
    promote = sub.add_parser("promote")
    promote.add_argument("--approval-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "propose":
            result = propose_release(args.source, args.approval_id, args.report, args.actor, args.note)
        elif args.command in {"approve", "reject"}:
            result = decide_release(args.approval_id, args.actor, args.note, args.command == "approve")
        else:
            result = promote_release(args.approval_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ReleaseValidationError, SourceError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
