"""Approved, auditable reconciliation of the eight identity edge cases.

The command is dry-run by default. Applying writes a fingerprinted application
approval, domain review proposals, explicit per-domain decisions and canonical
country fields in one SQLite transaction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.application_approval import (
    ApplicationApprovalError, build_application_artifact, decide_application,
    propose_application, record_application_applied, require_approved_application,
)
from tools.database.connection import REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database

DEFAULT_DATABASE = REPOSITORY_ROOT / "data/canonical/town_country_asset.sqlite"
DEFAULT_REGISTRY = REPOSITORY_ROOT / "config/country_identity_registry.json"
DEFAULT_DECISIONS = REPOSITORY_ROOT / "config/identity_edge_case_reconciliation.json"
DEFAULT_TAXONOMY = REPOSITORY_ROOT / "config/entity_types.json"
DEFAULT_FLAGS = REPOSITORY_ROOT / "config/country_flag_mapping.json"
DEFAULT_ISO_REPORT = REPOSITORY_ROOT / "reports/iso-assignment-proposals.md"
DEFAULT_FLAG_REPORT = REPOSITORY_ROOT / "reports/flag-source-review.md"
EXPECTED_SOURCE_IDS = {"FLK", "TWN", "SOL", "KOS", "CYN", "IOA", "ATC", "KAS"}
DOMAINS = ("iso", "entity_type", "flag", "catalogue_scope", "naming")


class ReconciliationError(RuntimeError):
    """Raised when an edge-case reconciliation cannot be applied safely."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconciliationError(f"Cannot read JSON input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReconciliationError(f"Expected a JSON object in {path}")
    return value


def _validate_payload(
    registry: dict[str, Any], payload: dict[str, Any], taxonomy: dict[str, Any],
    flags_payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if registry.get("schema_version") != 1 or payload.get("schema_version") != 1:
        raise ReconciliationError("Unsupported identity registry or reconciliation schema")
    if payload.get("policy_version") != "identity-edge-case-reconciliation-2026-11-20":
        raise ReconciliationError("Unexpected reconciliation policy version")
    records = registry.get("records")
    decisions = payload.get("records")
    types = taxonomy.get("types")
    if not isinstance(records, list) or not isinstance(decisions, list) or not isinstance(types, dict):
        raise ReconciliationError("Registry, decision records or entity taxonomy are malformed")
    by_id = {r.get("game_id"): r for r in records if isinstance(r, dict)}
    decision_by_id: dict[str, dict[str, Any]] = {}
    for item in decisions:
        if not isinstance(item, dict):
            raise ReconciliationError("Reconciliation contains a non-object record")
        gid = item.get("game_id")
        if not isinstance(gid, str) or gid in decision_by_id or gid not in by_id:
            raise ReconciliationError(f"Unknown, empty or duplicate reconciliation game_id: {gid!r}")
        source = by_id[gid].get("source", {})
        if item.get("source_id") != source.get("current_source_id"):
            raise ReconciliationError(f"{gid}: source ID does not match the persistent identity registry")
        if item.get("name") != by_id[gid].get("names", {}).get("en"):
            raise ReconciliationError(f"{gid}: display name does not match the identity registry")
        decision_by_id[gid] = item
    expected_ids = {r["game_id"] for r in records if r.get("source", {}).get("current_source_id") in EXPECTED_SOURCE_IDS}
    if len(expected_ids) != 8 or set(decision_by_id) != expected_ids:
        raise ReconciliationError("Reconciliation must cover exactly the eight approved edge-case identities")
    flag_rows = flags_payload.get("records")
    if not isinstance(flag_rows, list):
        raise ReconciliationError("Flag mapping records are malformed")
    flags_by_id = {r.get("game_id"): r for r in flag_rows if isinstance(r, dict)}
    if len(flags_by_id) != len(flag_rows):
        raise ReconciliationError("Flag mapping contains duplicate or malformed game IDs")
    for gid, item in decision_by_id.items():
        iso, entity, flag, catalogue, naming = (
            item.get("iso"), item.get("entity"), item.get("flag"),
            item.get("catalogue"), item.get("naming"),
        )
        if not all(isinstance(x, dict) for x in (iso, entity, flag, catalogue, naming)):
            raise ReconciliationError(f"{gid}: all five decision domains are required")
        status = iso.get("assignment_status")
        a2, a3 = iso.get("alpha2"), iso.get("alpha3")
        if status not in {"verified", "not_applicable"}:
            raise ReconciliationError(f"{gid}: unsupported ISO decision status")
        if status == "verified":
            if not isinstance(a2, str) or len(a2) != 2 or not isinstance(a3, str) or len(a3) != 3:
                raise ReconciliationError(f"{gid}: verified ISO decision requires both codes")
        elif a2 is not None or a3 is not None:
            raise ReconciliationError(f"{gid}: not-applicable ISO decision must keep both codes null")
        if entity.get("entity_type") not in types:
            raise ReconciliationError(f"{gid}: entity type is not present in the approved taxonomy")
        if flag.get("decision_status") not in {"approved", "not_applicable", "unresolved"}:
            raise ReconciliationError(f"{gid}: unsupported flag decision status")
        code = flag.get("source_flag_code")
        if code is not None and (not isinstance(code, str) or len(code) != 2 or code.lower() != code):
            raise ReconciliationError(f"{gid}: source flag code must be two lowercase letters")
        if flag.get("decision_status") == "approved" and code is None and flag.get("decision_code") != "parent_flag_fallback":
            raise ReconciliationError(f"{gid}: approved flag decision needs a source code or parent fallback")
        if catalogue.get("decision_status") not in {"approved", "excluded"}:
            raise ReconciliationError(f"{gid}: unsupported catalogue-scope decision")
        if naming.get("decision_status") != "approved" or not isinstance(naming.get("aliases_en"), list):
            raise ReconciliationError(f"{gid}: naming decision must be approved and aliases_en must be an array")
        for domain, decision in (("iso", iso), ("entity", entity), ("flag", flag)):
            if not isinstance(decision.get("evidence"), list) or not decision["evidence"]:
                raise ReconciliationError(f"{gid}: {domain} decision requires source evidence")
        flag_row = flags_by_id.get(gid)
        if flag_row is None:
            raise ReconciliationError(f"{gid}: flag mapping has no corresponding registry row")
        if flag_row.get("source_flag_code") != code:
            raise ReconciliationError(f"{gid}: flag mapping file does not match the reconciliation decision")
        if code and flag.get("decision_status") != "approved":
            raise ReconciliationError(f"{gid}: a source flag code cannot be attached to an unresolved/non-applicable decision")
    return by_id, decision_by_id


def _approved_proposal(
    connection: sqlite3.Connection, gid: str, kind: str,
    proposed: dict[str, Any], evidence: dict[str, Any], now: str,
) -> None:
    connection.execute(
        """UPDATE review_proposals SET review_status='rejected', reviewed_at=?
           WHERE game_id=? AND proposal_type=? AND review_status='candidate'""",
        (now, gid, kind),
    )
    proposed_json, evidence_json = _canonical(proposed), _canonical(evidence)
    fingerprint = hashlib.sha256(_canonical({
        "proposal_type": kind, "proposed": proposed, "evidence": evidence,
    }).encode("utf-8")).hexdigest()
    existing = connection.execute(
        """SELECT proposal_id, review_status, proposed_json, evidence_json
           FROM review_proposals
           WHERE game_id=? AND proposal_type=? AND proposal_fingerprint=?""",
        (gid, kind, fingerprint),
    ).fetchone()
    if existing:
        if (existing["proposed_json"], existing["evidence_json"]) != (proposed_json, evidence_json):
            raise ReconciliationError(f"{gid}: conflicting {kind} proposal fingerprint")
        if existing["review_status"] == "approved":
            return
        if existing["review_status"] != "candidate":
            raise ReconciliationError(f"{gid}: cannot promote an already rejected {kind} proposal")
        connection.execute(
            "UPDATE review_proposals SET review_status='approved', reviewed_at=? WHERE proposal_id=?",
            (now, existing["proposal_id"]),
        )
        return
    connection.execute(
        """INSERT INTO review_proposals
           (game_id, proposal_type, proposal_fingerprint, proposed_json, evidence_json,
            review_status, created_at, reviewed_at)
           VALUES (?, ?, ?, ?, ?, 'approved', ?, ?)""",
        (gid, kind, fingerprint, proposed_json, evidence_json, now, now),
    )


def _decision(
    connection: sqlite3.Connection, *, gid: str, domain: str, code: str,
    status: str, details: dict[str, Any], evidence: list[Any],
    actor: str, approval_id: str, now: str,
) -> None:
    body = {
        "game_id": gid, "decision_domain": domain, "decision_code": code,
        "decision_status": status, "decision": details, "evidence": evidence,
    }
    fingerprint = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    existing = connection.execute(
        """SELECT decision_code, decision_status, decision_json, evidence_json
           FROM country_review_decisions
           WHERE game_id=? AND decision_domain=? AND decision_fingerprint=?""",
        (gid, domain, fingerprint),
    ).fetchone()
    if existing:
        expected = (code, status, _canonical(details), _canonical(evidence))
        actual = tuple(existing)
        if actual != expected:
            raise ReconciliationError(f"{gid}: existing {domain} decision conflicts with reconciliation")
        return
    connection.execute(
        """INSERT INTO country_review_decisions
           (game_id, decision_domain, decision_code, decision_status,
            decision_json, evidence_json, decision_fingerprint, actor,
            decided_at, approval_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (gid, domain, code, status, _canonical(details), _canonical(evidence),
         fingerprint, actor, now, approval_id),
    )


def apply_reconciliation(
    connection: sqlite3.Connection, registry: dict[str, Any], payload: dict[str, Any],
    taxonomy: dict[str, Any], flags_payload: dict[str, Any], *,
    actor: str, approval_id: str, now: str | None = None,
) -> dict[str, int]:
    """Apply the approved edge-case decisions inside the caller's transaction."""
    now = now or _now()
    by_id, decisions = _validate_payload(registry, payload, taxonomy, flags_payload)
    expected_sources = {
        gid: (record["source"]["dataset"], record["source"]["current_source_id"])
        for gid, record in by_id.items() if gid in decisions
    }
    current_rows = connection.execute(
        """SELECT game_id, dataset, source_id FROM country_sources
           WHERE is_current=1 ORDER BY game_id, dataset"""
    ).fetchall()
    # A canonical identity may have one current mapping per source dataset
    # (for example Natural Earth and UN WPP). Validate the registry's own
    # dataset mapping without allowing another dataset to overwrite it.
    actual_sources = {
        (row["game_id"], row["dataset"]): row["source_id"]
        for row in current_rows
    }
    for gid, (dataset, source_id) in expected_sources.items():
        if actual_sources.get((gid, dataset)) != source_id:
            raise ReconciliationError(f"{gid}: canonical current source mapping is missing or conflicts")
    flag_rows = {r["game_id"]: r for r in flags_payload["records"]}
    for gid, item in decisions.items():
        country = connection.execute(
            """SELECT entity_type, record_status, iso_alpha2, iso_alpha3,
                      iso_assignment_status, entity_type_status
               FROM countries WHERE game_id=?""", (gid,)
        ).fetchone()
        if country is None:
            raise ReconciliationError(f"{gid}: canonical identity must be imported before reconciliation")
        if connection.execute(
            "SELECT 1 FROM review_proposals WHERE game_id=? AND proposal_type='iso' LIMIT 1", (gid,)
        ).fetchone() is None:
            raise ReconciliationError(
                f"{gid}: WP1.4 review-data import must run before edge-case reconciliation"
            )
        flag_state = connection.execute(
            "SELECT source_flag_code, mapping_status FROM country_flags WHERE game_id=?", (gid,)
        ).fetchone()
        if flag_state is None:
            raise ReconciliationError(
                f"{gid}: WP1.4 review-data import must create the country_flags row before reconciliation"
            )
        configured_flag = flag_rows[gid]
        expected_mapping_status = {
            "reviewed": "reviewed", "rejected": "rejected",
            "unreviewed": "candidate", "candidate": "candidate",
        }.get(configured_flag.get("status", "unreviewed"))
        if (flag_state["source_flag_code"], flag_state["mapping_status"]) != (
            configured_flag.get("source_flag_code"), expected_mapping_status
        ):
            raise ReconciliationError(
                f"{gid}: canonical flag mapping does not match the reviewed WP1.4 input"
            )
        entity = item["entity"]
        iso = item["iso"]
        flag = item["flag"]
        catalogue = item["catalogue"]
        naming = item["naming"]
        evidence = {
            "sources": {
                "iso": iso["evidence"], "entity_type": entity["evidence"],
                "flag": flag["evidence"],
            },
            "policy_version": payload["policy_version"],
        }
        iso_proposed = {
            "alpha2": iso["alpha2"], "alpha3": iso["alpha3"],
            "reference_name": iso.get("reference_name"),
            "match_type": "explicit reviewed external assignment" if iso["assignment_status"] == "verified" else "not applicable",
            "decision": iso["decision_code"],
        }
        _approved_proposal(connection, gid, "iso", iso_proposed, evidence["sources"]["iso"], now)
        entity_proposed = {"entity_type": entity["entity_type"]}
        _approved_proposal(connection, gid, "entity_type", entity_proposed, evidence["sources"]["entity_type"], now)
        connection.execute(
            """UPDATE countries SET entity_type=?, entity_type_status='reviewed',
               iso_alpha2=?, iso_alpha3=?, iso_assignment_status=?, updated_at=?
               WHERE game_id=?""",
            (entity["entity_type"], iso["alpha2"], iso["alpha3"],
             iso["assignment_status"], now, gid),
        )
        if catalogue["decision_status"] == "excluded":
            connection.execute(
                "UPDATE countries SET record_status='retired', updated_at=? WHERE game_id=?",
                (now, gid),
            )
        elif country["record_status"] == "retired":
            raise ReconciliationError(f"{gid}: refusing to reactivate a retired identity implicitly")

        for alias in naming["aliases_en"]:
            if not isinstance(alias, str) or not alias.strip():
                raise ReconciliationError(f"{gid}: English alias must be non-empty text")
            connection.execute(
                """INSERT OR IGNORE INTO country_names(game_id, language, name, name_type)
                   VALUES (?, 'en', ?, 'alias')""", (gid, alias)
            )

        flag_row = flag_rows[gid]
        if flag["decision_status"] == "unresolved":
            if flag_row.get("status") not in {"unreviewed", "candidate", None}:
                raise ReconciliationError(f"{gid}: unresolved flag decision conflicts with a reviewed mapping")
        else:
            mapping_status = "reviewed" if flag.get("source_flag_code") else "rejected"
            code = flag.get("source_flag_code")
            if code:
                owner = connection.execute(
                    "SELECT game_id FROM country_flags WHERE source_flag_code=? AND game_id<>?",
                    (code, gid),
                ).fetchone()
                if owner:
                    raise ReconciliationError(f"{gid}: flag source code {code!r} is already assigned to {owner['game_id']}")
            flag_evidence = flag["evidence"]
            note = flag.get("decision_note") or flag["decision_code"]
            connection.execute(
                """UPDATE country_flags SET source_flag_code=?, mapping_status=?,
                   decision_note=?, evidence_json=? WHERE game_id=?""",
                (code, mapping_status, note, _canonical(flag_evidence), gid),
            )
            flag_proposed = {
                "source_flag_code": code, "manual_svg_path": None,
                "decision_code": flag["decision_code"],
                "parent_game_id": flag.get("parent_game_id"),
            }
            _approved_proposal(connection, gid, "flag", flag_proposed, {"evidence": flag_evidence}, now)

        iso_status = "approved" if iso["assignment_status"] == "verified" else "not_applicable"
        _decision(connection, gid=gid, domain="iso", code=iso["decision_code"],
                   status=iso_status, details=iso, evidence=iso["evidence"],
                   actor=actor, approval_id=approval_id, now=now)
        _decision(connection, gid=gid, domain="entity_type", code="entity_type_assigned",
                   status="approved", details=entity, evidence=entity["evidence"],
                   actor=actor, approval_id=approval_id, now=now)
        _decision(connection, gid=gid, domain="flag", code=flag["decision_code"],
                   status=flag["decision_status"], details=flag, evidence=flag["evidence"],
                   actor=actor, approval_id=approval_id, now=now)
        _decision(connection, gid=gid, domain="catalogue_scope", code=catalogue["decision_code"],
                   status=catalogue["decision_status"], details=catalogue,
                   evidence=entity["evidence"], actor=actor, approval_id=approval_id, now=now)
        _decision(connection, gid=gid, domain="naming", code=naming["decision_code"],
                   status="approved", details=naming, evidence=iso["evidence"],
                   actor=actor, approval_id=approval_id, now=now)

    issues = validate_database(connection)
    if issues:
        raise ReconciliationError("Database validation failed: " + "; ".join(issues))
    return {
        "records": len(decisions),
        "decisions": len(decisions) * len(DOMAINS),
        "iso_verified": sum(x["iso"]["assignment_status"] == "verified" for x in decisions.values()),
        "iso_not_applicable": sum(x["iso"]["assignment_status"] == "not_applicable" for x in decisions.values()),
        "entity_types_approved": len(decisions),
        "flags_resolved": sum(x["flag"]["decision_status"] != "unresolved" for x in decisions.values()),
        "flags_unresolved": sum(x["flag"]["decision_status"] == "unresolved" for x in decisions.values()),
        "retired": sum(x["catalogue"]["decision_status"] == "excluded" for x in decisions.values()),
    }


def build_reconciliation_artifact(
    registry_path: Path = DEFAULT_REGISTRY, decisions_path: Path = DEFAULT_DECISIONS,
    taxonomy_path: Path = DEFAULT_TAXONOMY, flags_path: Path = DEFAULT_FLAGS,
    iso_report_path: Path = DEFAULT_ISO_REPORT, flag_report_path: Path = DEFAULT_FLAG_REPORT,
) -> dict[str, Any]:
    registry = _read_json(registry_path)
    payload = _read_json(decisions_path)
    taxonomy = _read_json(taxonomy_path)
    flags_payload = _read_json(flags_path)
    _, decisions = _validate_payload(registry, payload, taxonomy, flags_payload)
    return build_application_artifact(
        domain="identity_edge_case_reconciliation",
        inputs=[registry_path, decisions_path, taxonomy_path, flags_path, iso_report_path, flag_report_path],
        metadata={"record_count": len(decisions), "decision_count": len(decisions) * len(DOMAINS),
                  "policy_version": payload["policy_version"]},
    )


def apply_from_files(
    database_path: Path, registry_path: Path, decisions_path: Path, taxonomy_path: Path,
    flags_path: Path, iso_report_path: Path, flag_report_path: Path, *,
    actor: str, note: str, apply: bool,
) -> dict[str, Any]:
    registry = _read_json(registry_path)
    payload = _read_json(decisions_path)
    taxonomy = _read_json(taxonomy_path)
    flags_payload = _read_json(flags_path)
    _, decisions = _validate_payload(registry, payload, taxonomy, flags_payload)
    summary = {
        "records": len(decisions), "decisions": len(decisions) * len(DOMAINS),
        "iso_verified": sum(x["iso"]["assignment_status"] == "verified" for x in decisions.values()),
        "iso_not_applicable": sum(x["iso"]["assignment_status"] == "not_applicable" for x in decisions.values()),
        "flags_resolved": sum(x["flag"]["decision_status"] != "unresolved" for x in decisions.values()),
        "flags_unresolved": sum(x["flag"]["decision_status"] == "unresolved" for x in decisions.values()),
        "retired": sum(x["catalogue"]["decision_status"] == "excluded" for x in decisions.values()),
    }
    if not apply:
        return {"status": "dry_run", **summary, "database_written": False}
    if not actor.strip() or not note.strip():
        raise ReconciliationError("--apply requires --actor and --note")
    artifact = build_reconciliation_artifact(
        registry_path, decisions_path, taxonomy_path, flags_path, iso_report_path, flag_report_path
    )
    approval_id = "edge-case-" + artifact["artifact_sha256"][:20]
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT status, artifact_sha256 FROM application_approvals WHERE approval_id=?",
            (approval_id,),
        ).fetchone()
        if existing and existing["status"] == "applied" and existing["artifact_sha256"] == artifact["artifact_sha256"]:
            connection.rollback()
            return {"status": "already_applied", **summary, "approval_id": approval_id, "database_written": False}
        if existing:
            raise ReconciliationError(f"Approval {approval_id} already exists with status {existing['status']}")
        propose_application(connection, approval_id=approval_id, artifact=artifact)
        decide_application(connection, approval_id=approval_id, decision="approved", actor=actor, note=note)
        require_approved_application(connection, approval_id=approval_id, artifact=artifact)
        applied = apply_reconciliation(
            connection, registry, payload, taxonomy, flags_payload,
            actor=actor, approval_id=approval_id,
        )
        record_application_applied(
            connection, approval_id=approval_id,
            application_id=f"identity-edge-cases:{artifact['artifact_sha256'][:16]}",
            details={**applied, "decision_note": note},
        )
        connection.commit()
        return {"status": "applied", **applied, "approval_id": approval_id, "database_written": True}
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--entity-taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--flag-mapping", type=Path, default=DEFAULT_FLAGS)
    parser.add_argument("--iso-proposals", type=Path, default=DEFAULT_ISO_REPORT)
    parser.add_argument("--flag-report", type=Path, default=DEFAULT_FLAG_REPORT)
    parser.add_argument("--actor", default="project-owner")
    parser.add_argument("--note", default="Owner-approved reconciliation of the eight documented identity edge cases; preserve canonical game IDs and record unresolved flag assets explicitly.")
    parser.add_argument("--apply", action="store_true", help="Apply transactionally; default is a read-only dry run")
    args = parser.parse_args()
    try:
        result = apply_from_files(
            args.database, args.registry, args.decisions, args.entity_taxonomy,
            args.flag_mapping, args.iso_proposals, args.flag_report,
            actor=args.actor, note=args.note, apply=args.apply,
        )
    except (OSError, ValueError, sqlite3.Error, ApplicationApprovalError, ReconciliationError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] == "dry_run":
        print("Dry run only. No canonical database records were changed.")
    elif result["status"] == "applied":
        print("Identity edge-case reconciliation committed; integrity and foreign-key checks passed.")
    elif result["status"] == "already_applied":
        print("The exact reconciliation artifact was already applied; no database writes were repeated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
