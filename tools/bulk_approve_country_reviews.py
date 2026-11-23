"""Bulk-approve explicitly reviewed canonical country candidates.

The command is dry-run by default. Applying requires an identified reviewer,
a decision note, and an explicit confirmation flag. Each run is recorded as a
transactional application approval; unresolved or evidence-incomplete proposals
remain candidates.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.application_approval import (
    ApplicationApprovalError,
    approve_application,
    build_application_artifact,
    record_application_applied,
)
from tools.database.connection import REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database

DEFAULT_DATABASE = REPOSITORY_ROOT / "data/canonical/town_country_asset.sqlite"
DEFAULT_REGISTRY = REPOSITORY_ROOT / "config/country_identity_registry.json"
PROPOSAL_TYPES = {"iso", "localization", "entity_type", "flag"}
ISO2 = re.compile(r"^[A-Z]{2}$")
ISO3 = re.compile(r"^[A-Z]{3}$")


class BulkApprovalError(RuntimeError):
    """Raised when a bulk review decision cannot be applied safely."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json(value: str, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise BulkApprovalError(f"{label} contains invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise BulkApprovalError(f"{label} must be a JSON object")
    return parsed


def _load_candidates(
    connection: sqlite3.Connection,
    *,
    approve_records: bool,
    proposal_types: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()

    if approve_records:
        rows = connection.execute(
            """SELECT c.game_id, c.record_status, c.entity_type,
                      COUNT(DISTINCT CASE WHEN cs.is_current=1 THEN cs.dataset || ':' || cs.source_id END) AS current_sources,
                      COUNT(DISTINCT CASE WHEN cn.language='en' AND cn.name_type='canonical' THEN cn.name END) AS english_names
               FROM countries c
               LEFT JOIN country_sources cs ON cs.game_id=c.game_id
               LEFT JOIN country_names cn ON cn.game_id=c.game_id
               GROUP BY c.game_id ORDER BY c.game_id"""
        ).fetchall()
        for row in rows:
            if row["record_status"] != "candidate":
                skipped[f"record_status_{row['record_status']}"] += 1
                continue
            if row["current_sources"] < 1 or row["english_names"] != 1:
                skipped["identity_missing_or_ambiguous_source_or_name"] += 1
                continue
            records.append({"game_id": row["game_id"]})

    for kind in sorted(proposal_types):
        rows = connection.execute(
            """SELECT p.proposal_id, p.game_id, p.proposal_type,
                      p.proposal_fingerprint, p.proposed_json, p.evidence_json,
                      p.review_status, c.iso_alpha2, c.iso_alpha3,
                      c.entity_type, c.entity_type_status,
                      c.localization_status, c.iso_assignment_status,
                      cf.source_flag_code, cf.mapping_status
               FROM review_proposals p
               JOIN countries c ON c.game_id=p.game_id
               LEFT JOIN country_flags cf ON cf.game_id=p.game_id
               WHERE p.proposal_type=? AND p.review_status='candidate'
               ORDER BY p.game_id, p.proposal_id""",
            (kind,),
        ).fetchall()
        for row in rows:
            proposed = _json(row["proposed_json"], f"{kind} proposal {row['proposal_id']}")
            evidence = _json(row["evidence_json"], f"{kind} evidence {row['proposal_id']}")
            reason = None
            if kind == "iso":
                a2, a3 = proposed.get("alpha2"), proposed.get("alpha3")
                if not isinstance(a2, str) or not ISO2.fullmatch(a2) or not isinstance(a3, str) or not ISO3.fullmatch(a3):
                    reason = "missing_or_invalid_iso_pair"
                elif row["iso_assignment_status"] == "not_applicable":
                    reason = "country_marked_not_applicable"
                elif (row["iso_alpha2"], row["iso_alpha3"]) not in ((None, None), (a2, a3)):
                    reason = "canonical_iso_values_conflict"
            elif kind == "localization":
                if proposed.get("language") != "fa" or not isinstance(proposed.get("name"), str) or not proposed["name"].strip():
                    reason = "missing_persian_name"
            elif kind == "entity_type":
                if not isinstance(proposed.get("entity_type"), str) or not proposed["entity_type"].strip():
                    reason = "missing_entity_type"
                elif row["entity_type"] != proposed["entity_type"]:
                    reason = "canonical_entity_type_conflict"
                elif not isinstance(evidence.get("evidence"), list) or not evidence["evidence"]:
                    reason = "classification_evidence_missing"
            elif kind == "flag":
                if not row["source_flag_code"] and not proposed.get("manual_svg_path"):
                    reason = "no_flag_mapping"
                elif not isinstance(evidence.get("evidence"), list) or not evidence["evidence"]:
                    reason = "flag_evidence_missing"
                elif row["mapping_status"] != "candidate":
                    reason = "flag_mapping_status_conflict"
            if reason:
                skipped[f"{kind}_{reason}"] += 1
                continue
            proposals.append({
                "proposal_id": row["proposal_id"],
                "game_id": row["game_id"],
                "proposal_type": kind,
                "proposal_fingerprint": row["proposal_fingerprint"],
                "proposed": proposed,
                "evidence": evidence,
            })

    # Check ISO code uniqueness across both already-assigned countries and the
    # set of proposals being approved in this batch.
    iso_rows = [p for p in proposals if p["proposal_type"] == "iso"]
    if iso_rows:
        selected_ids = {p["game_id"] for p in iso_rows}
        seen2: dict[str, str] = {}
        seen3: dict[str, str] = {}
        existing = connection.execute(
            """SELECT game_id, iso_alpha2, iso_alpha3 FROM countries
               WHERE iso_alpha2 IS NOT NULL OR iso_alpha3 IS NOT NULL"""
        ).fetchall()
        for row in existing:
            if row["game_id"] not in selected_ids:
                if row["iso_alpha2"]:
                    seen2[row["iso_alpha2"]] = row["game_id"]
                if row["iso_alpha3"]:
                    seen3[row["iso_alpha3"]] = row["game_id"]
        unique_iso: list[dict[str, Any]] = []
        for proposal in iso_rows:
            a2, a3 = proposal["proposed"]["alpha2"], proposal["proposed"]["alpha3"]
            owner2, owner3 = seen2.get(a2), seen3.get(a3)
            if (owner2 and owner2 != proposal["game_id"]) or (owner3 and owner3 != proposal["game_id"]):
                skipped["iso_duplicate_verified_code"] += 1
                continue
            if a2 in seen2 or a3 in seen3:
                skipped["iso_duplicate_batch_code"] += 1
                continue
            seen2[a2], seen3[a3] = proposal["game_id"], proposal["game_id"]
            unique_iso.append(proposal)
        proposals = [p for p in proposals if p["proposal_type"] != "iso"] + unique_iso

    return records, proposals, dict(sorted(skipped.items()))


def bulk_approve(
    database_path: str | Path,
    registry_path: str | Path,
    *,
    approve_records: bool = False,
    proposal_types: set[str] | None = None,
    actor: str | None = None,
    note: str | None = None,
    apply: bool = False,
    confirm_reviewed: bool = False,
) -> dict[str, Any]:
    """Preview or transactionally approve explicitly selected reviewed candidates."""
    selected_types = set(proposal_types or ())
    unknown = selected_types - PROPOSAL_TYPES
    if unknown:
        raise BulkApprovalError("Unsupported proposal types: " + ", ".join(sorted(unknown)))
    if not approve_records and not selected_types:
        raise BulkApprovalError("Select --approve-records and/or one or more --proposal-type values")
    if apply:
        if not confirm_reviewed:
            raise BulkApprovalError("--apply requires --confirm-reviewed")
        if not isinstance(actor, str) or not actor.strip():
            raise BulkApprovalError("--apply requires --actor")
        if not isinstance(note, str) or not note.strip():
            raise BulkApprovalError("--apply requires a non-empty --note")

    registry = Path(registry_path).resolve()
    if not registry.is_file():
        raise BulkApprovalError(f"Identity registry does not exist: {registry}")

    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        records, proposals, skipped = _load_candidates(
            connection, approve_records=approve_records, proposal_types=selected_types
        )
        if not records and not proposals:
            connection.rollback()
            return {
                "status": "nothing_eligible",
                "record_candidates_eligible": 0,
                "proposal_candidates_eligible": 0,
                "skipped": skipped,
                "database_written": False,
            }
        summary = {
            "record_candidates_eligible": len(records),
            "proposal_candidates_eligible": len(proposals),
            "proposal_types": dict(sorted(Counter(p["proposal_type"] for p in proposals).items())),
            "skipped": skipped,
        }
        if not apply:
            connection.rollback()
            return {"status": "dry_run", **summary, "database_written": False}

        now = _now()
        snapshot = {
            "records": records,
            "proposals": [
                {key: proposal[key] for key in (
                    "proposal_id", "game_id", "proposal_type",
                    "proposal_fingerprint", "proposed", "evidence",
                )}
                for proposal in proposals
            ],
            "actor": actor.strip(),
            "decision_note": note.strip(),
        }
        artifact = build_application_artifact(
            domain="bulk_country_review",
            inputs=[registry],
            metadata=snapshot,
        )
        approval_id = "bulk-review-" + artifact["artifact_sha256"][:20]
        try:
            approve_application(
                connection,
                approval_id=approval_id,
                artifact=artifact,
                actor=actor.strip(),
                note=note.strip(),
            )
        except ApplicationApprovalError as exc:
            raise BulkApprovalError(str(exc)) from exc

        for record in records:
            cursor = connection.execute(
                """UPDATE countries SET record_status='approved', updated_at=?
                   WHERE game_id=? AND record_status='candidate'""",
                (now, record["game_id"]),
            )
            if cursor.rowcount != 1:
                raise BulkApprovalError(f"{record['game_id']}: record status changed during approval")

        approved_counts: Counter[str] = Counter()
        for proposal in proposals:
            kind, gid, proposed = proposal["proposal_type"], proposal["game_id"], proposal["proposed"]
            cursor = connection.execute(
                """UPDATE review_proposals SET review_status='approved', reviewed_at=?
                   WHERE proposal_id=? AND review_status='candidate'
                     AND proposal_fingerprint=?""",
                (now, proposal["proposal_id"], proposal["proposal_fingerprint"]),
            )
            if cursor.rowcount != 1:
                raise BulkApprovalError(f"{gid}: {kind} proposal changed during approval")
            if kind == "iso":
                connection.execute(
                    """UPDATE countries SET iso_alpha2=?, iso_alpha3=?,
                       iso_assignment_status='verified', updated_at=? WHERE game_id=?""",
                    (proposed["alpha2"], proposed["alpha3"], now, gid),
                )
            elif kind == "localization":
                connection.execute(
                    """INSERT INTO country_names(game_id, language, name, name_type)
                       VALUES (?, 'fa', ?, 'canonical')
                       ON CONFLICT DO NOTHING""",
                    (gid, proposed["name"]),
                )
                existing_name = connection.execute(
                    """SELECT name FROM country_names
                       WHERE game_id=? AND language='fa' AND name_type='canonical'""",
                    (gid,),
                ).fetchone()
                if existing_name is None or existing_name["name"] != proposed["name"]:
                    raise BulkApprovalError(f"{gid}: canonical Persian name conflicts with approved proposal")
                connection.execute(
                    "UPDATE countries SET localization_status='reviewed', updated_at=? WHERE game_id=?",
                    (now, gid),
                )
            elif kind == "entity_type":
                connection.execute(
                    "UPDATE countries SET entity_type_status='reviewed', updated_at=? WHERE game_id=?",
                    (now, gid),
                )
            elif kind == "flag":
                cursor = connection.execute(
                    """UPDATE country_flags SET mapping_status='reviewed'
                       WHERE game_id=? AND mapping_status='candidate'""",
                    (gid,),
                )
                if cursor.rowcount != 1:
                    raise BulkApprovalError(f"{gid}: flag mapping is missing or no longer a candidate")
            approved_counts[kind] += 1

        issues = validate_database(connection)
        if issues:
            raise BulkApprovalError("Database validation failed: " + "; ".join(issues))
        try:
            record_application_applied(
                connection,
                approval_id=approval_id,
                application_id=f"bulk-country-review:{artifact['artifact_sha256'][:16]}",
                details={
                    **summary,
                    "approved_record_count": len(records),
                    "approved_proposal_counts": dict(sorted(approved_counts.items())),
                },
            )
        except ApplicationApprovalError as exc:
            raise BulkApprovalError(str(exc)) from exc
        connection.commit()
        return {
            "status": "applied",
            **summary,
            "approved_record_count": len(records),
            "approved_proposal_counts": dict(sorted(approved_counts.items())),
            "approval_id": approval_id,
            "database_written": True,
        }
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
    parser.add_argument(
        "--approve-records", action="store_true",
        help="Approve eligible candidate country identities (does not verify ISO/entity/localization)",
    )
    parser.add_argument(
        "--proposal-type", action="append", choices=sorted(PROPOSAL_TYPES), default=[],
        help="Approve eligible existing review proposals; repeat to select multiple domains",
    )
    parser.add_argument("--actor", help="Human reviewer identifier recorded in the audit log")
    parser.add_argument("--note", help="Decision rationale recorded with the application approval")
    parser.add_argument("--apply", action="store_true", help="Apply the approval; otherwise run a dry-run")
    parser.add_argument(
        "--confirm-reviewed", action="store_true",
        help="Attest that every eligible item in the selected scope has already been reviewed",
    )
    args = parser.parse_args()
    try:
        result = bulk_approve(
            args.database, args.registry,
            approve_records=args.approve_records,
            proposal_types=set(args.proposal_type),
            actor=args.actor, note=args.note,
            apply=args.apply, confirm_reviewed=args.confirm_reviewed,
        )
    except (OSError, sqlite3.Error, ValueError, BulkApprovalError, ApplicationApprovalError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] == "dry_run":
        print("Dry run only. No canonical records or proposals were changed.")
    elif result["status"] == "applied":
        print("Bulk review approval committed transactionally; database integrity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
