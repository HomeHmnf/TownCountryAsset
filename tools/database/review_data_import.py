"""Transactional import of ISO, Persian, entity-classification and flag review data."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.connection import REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database
from tools.audit_iso_proposal_evidence import TABLE_HEADER, _cells
from tools.propose_iso_assignments import propose, read_reference

DEFAULT_REGISTRY = REPOSITORY_ROOT / "config/country_identity_registry.json"
DEFAULT_TAXONOMY = REPOSITORY_ROOT / "config/entity_types.json"
DEFAULT_FLAGS = REPOSITORY_ROOT / "config/country_flag_mapping.json"


class ReviewDataImportError(RuntimeError):
    """Raised when review inputs cannot be imported without ambiguity."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewDataImportError(f"Cannot read JSON input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReviewDataImportError(f"Expected a JSON object in {path}")
    return value


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ReviewDataImportError(f"Cannot read input {path}: {exc}") from exc


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReviewDataImportError(f"Review proposal is not deterministic JSON: {exc}") from exc


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _status(value: Any, label: str, *, reviewed_alias: bool = False) -> str:
    if reviewed_alias and value == "reviewed":
        return "approved"
    if value in (None, "", "unreviewed", "candidate", "proposed"):
        return "candidate"
    if value not in {"approved", "rejected"}:
        raise ReviewDataImportError(f"{label} has unsupported review status {value!r}")
    return value


def _read_iso_report(path: Path) -> list[dict[str, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ReviewDataImportError(f"Cannot read ISO proposal report {path}: {exc}") from exc
    try:
        index = lines.index(TABLE_HEADER)
    except ValueError as exc:
        raise ReviewDataImportError(f"ISO proposal report has no expected table header: {path}") from exc
    expected = [
        "game_id", "Registry English name", "Candidate alpha-2",
        "Candidate alpha-3", "Reference English name", "Match type", "Decision",
    ]
    if _cells(lines[index]) != expected:
        raise ReviewDataImportError("ISO proposal report columns do not match the expected schema")
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(lines[index + 2:], start=index + 3):
        if not line.startswith("|"):
            break
        cells = _cells(line)
        if len(cells) != len(expected):
            raise ReviewDataImportError(f"ISO proposal report line {line_number} has an invalid column count")
        rows.append(dict(zip(expected, cells, strict=True)))
    return rows


def _validate_iso(
    registry: dict[str, Any], reference_path: Path, provenance_path: Path, report_path: Path
) -> dict[str, dict[str, Any]]:
    provenance = _read_json(provenance_path)
    reference_hash = _sha(reference_path)
    raw_hash = provenance.get("raw_sha256")
    if not isinstance(raw_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_hash):
        raise ReviewDataImportError("ISO provenance has no valid raw response SHA-256")
    if provenance.get("normalized_sha256") != reference_hash:
        raise ReviewDataImportError("ISO normalized reference checksum does not match provenance")
    if provenance.get("normalized_reference") and Path(provenance["normalized_reference"]).name != reference_path.name:
        raise ReviewDataImportError("ISO provenance identifies a different normalized reference file")
    reference = read_reference(reference_path)
    report_rows = _read_iso_report(report_path)
    fresh = propose(registry, reference)
    expected = {row["game_id"]: row for row in fresh["proposals"]}
    actual: dict[str, dict[str, Any]] = {}
    for row in report_rows:
        gid = row["game_id"]
        if not gid or gid in actual:
            raise ReviewDataImportError(f"ISO proposal report has an empty or duplicate game_id: {gid!r}")
        if gid not in expected:
            raise ReviewDataImportError(f"ISO proposal report references unknown game_id {gid}")
        checks = {
            "Registry English name": "english_name",
            "Candidate alpha-2": "candidate_alpha2",
            "Candidate alpha-3": "candidate_alpha3",
            "Reference English name": "reference_name",
            "Match type": "match_type",
            "Decision": "decision",
        }
        for report_key, fresh_key in checks.items():
            if row[report_key] != str(expected[gid].get(fresh_key, "")):
                raise ReviewDataImportError(f"{gid}: ISO proposal report field {report_key!r} is stale or edited")
        a2, a3 = row["Candidate alpha-2"], row["Candidate alpha-3"]
        if bool(a2) != bool(a3):
            raise ReviewDataImportError(f"{gid}: ISO candidate must contain both codes or neither")
        if a2 and not any(item["alpha2"] == a2 and item["alpha3"] == a3 and item["english_name"] == row["Reference English name"] for item in reference):
            raise ReviewDataImportError(f"{gid}: ISO candidate pair/label is absent from captured reference")
        actual[gid] = {
            "alpha2": a2 or None, "alpha3": a3 or None,
            "reference_name": row["Reference English name"] or None,
            "match_type": row["Match type"], "decision": row["Decision"],
            "provenance": {
                "source_url": provenance.get("source_url"),
                "source_repository": provenance.get("source_repository"),
                "retrieved_at_utc": provenance.get("retrieved_at_utc"),
                "raw_sha256": provenance.get("raw_sha256"),
                "normalized_sha256": reference_hash,
                "normalized_reference": reference_path.name,
            },
        }
    if set(actual) != set(expected):
        raise ReviewDataImportError(
            f"ISO proposal coverage mismatch; missing={sorted(set(expected)-set(actual))}, "
            f"extra={sorted(set(actual)-set(expected))}"
        )
    return actual


def _validate_persian(
    registry: dict[str, Any], candidates_path: Path, provenance_path: Path
) -> dict[str, dict[str, Any]]:
    payload, provenance = _read_json(candidates_path), _read_json(provenance_path)
    rows = payload.get("rows")
    if not isinstance(rows, list) or payload.get("record_count") != len(rows):
        raise ReviewDataImportError("Persian candidate record_count does not match rows")
    if provenance.get("candidate_count") != payload.get("candidate_count"):
        raise ReviewDataImportError("Persian candidate count does not match provenance")
    if provenance.get("candidate_snapshot") and Path(provenance["candidate_snapshot"]).name != candidates_path.name:
        raise ReviewDataImportError("Persian provenance identifies a different candidate snapshot")
    raw_sha = provenance.get("raw_sha256")
    if not isinstance(raw_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_sha):
        raise ReviewDataImportError("Persian provenance has no valid raw response SHA-256")
    registry_by_id = {record["game_id"]: record for record in registry["records"]}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ReviewDataImportError("Persian candidates contain a non-object row")
        gid = row.get("game_id")
        if not isinstance(gid, str) or gid not in registry_by_id or gid in result:
            raise ReviewDataImportError(f"Persian candidate has an unknown, empty or duplicate game_id: {gid!r}")
        record = registry_by_id[gid]
        source_id = record["source"]["current_source_id"]
        if row.get("source_id") != source_id or row.get("english_name") != record["names"]["en"]:
            raise ReviewDataImportError(f"{gid}: Persian candidate identity/source mapping mismatch")
        qid, label = row.get("wikidata_qid") or None, row.get("candidate_persian_name") or None
        if qid is not None and (not isinstance(qid, str) or not re.fullmatch(r"Q[1-9][0-9]*", qid)):
            raise ReviewDataImportError(f"{gid}: malformed Wikidata QID {qid!r}")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise ReviewDataImportError(f"{gid}: Persian candidate label must be non-empty text")
        result[gid] = {
            "qid": qid, "name": label,
            "status": _status(row.get("review_status"), f"{gid} Persian review"),
            "current_name": row.get("current_persian_name") or None,
            "reviewed_at": row.get("reviewed_at"),
            "provenance": {
                "source_url": provenance.get("source_url"),
                "retrieved_at_utc": provenance.get("retrieved_at_utc"),
                "raw_sha256": raw_sha,
                "wikidata_qid": qid,
                "candidate_snapshot": candidates_path.name,
            },
        }
    if set(result) != set(registry_by_id):
        raise ReviewDataImportError("Persian candidate game_id coverage does not match the identity registry")
    return result


def _validate_registry_and_taxonomy(registry: dict[str, Any], taxonomy: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str]:
    records = registry.get("records")
    if not isinstance(records, list) or not records:
        raise ReviewDataImportError("Identity registry records must be a non-empty array")
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ReviewDataImportError("Identity registry contains a non-object record")
        gid = record.get("game_id")
        source = record.get("source")
        if not isinstance(gid, str) or not re.fullmatch(r"tc_[0-9a-f]{32}", gid) or gid in by_id:
            raise ReviewDataImportError(f"Identity registry has an invalid or duplicate game_id: {gid!r}")
        if not isinstance(source, dict) or not isinstance(source.get("current_source_id"), str):
            raise ReviewDataImportError(f"{gid}: current source mapping is missing")
        if not isinstance(record.get("names"), dict):
            raise ReviewDataImportError(f"{gid}: names object is missing")
        by_id[gid] = record
    types = taxonomy.get("types")
    if taxonomy.get("schema_version") != 1 or not isinstance(types, dict) or not types:
        raise ReviewDataImportError("Entity taxonomy has an unsupported schema or empty types")
    unreviewed = taxonomy.get("unreviewed_value", "unreviewed")
    if unreviewed not in types:
        raise ReviewDataImportError("Entity taxonomy unreviewed_value is not a configured type")
    for gid, record in by_id.items():
        if record.get("entity_type") not in types:
            raise ReviewDataImportError(f"{gid}: entity_type {record.get('entity_type')!r} is not in config/entity_types.json")
    return by_id, unreviewed


def _proposal(
    connection: sqlite3.Connection, gid: str, kind: str, proposed: dict[str, Any],
    evidence: dict[str, Any], status: str, reviewed_at: str | None, now: str,
) -> bool:
    if status == "approved" and not reviewed_at:
        raise ReviewDataImportError(f"{gid}: approved {kind} proposal requires an explicit reviewed_at timestamp")
    if status != "approved" and reviewed_at is not None:
        raise ReviewDataImportError(f"{gid}: non-approved {kind} proposal must not have reviewed_at")
    proposed_json, evidence_json = _canonical(proposed), _canonical(evidence)
    fingerprint = hashlib.sha256(_canonical({"proposal_type": kind, "proposed": proposed, "evidence": evidence}).encode("utf-8")).hexdigest()
    existing = connection.execute(
        """SELECT proposal_id, review_status, reviewed_at, proposed_json, evidence_json
           FROM review_proposals WHERE game_id=? AND proposal_type=? AND proposal_fingerprint=?""",
        (gid, kind, fingerprint),
    ).fetchone()
    if existing:
        actual_content = (existing["proposed_json"], existing["evidence_json"])
        if actual_content != (proposed_json, evidence_json):
            raise ReviewDataImportError(f"{gid}: existing {kind} proposal conflicts with imported evidence/content")
        old_status, old_reviewed_at = existing["review_status"], existing["reviewed_at"]
        if old_status == status and old_reviewed_at == reviewed_at:
            return False
        if old_status != "candidate" or status == "candidate":
            raise ReviewDataImportError(f"{gid}: refusing to downgrade or rewrite an existing {kind} review decision")
        connection.execute(
            "UPDATE review_proposals SET review_status=?, reviewed_at=? WHERE proposal_id=?",
            (status, reviewed_at, existing["proposal_id"]),
        )
        return False
    connection.execute(
        """INSERT INTO review_proposals
           (game_id, proposal_type, proposal_fingerprint, proposed_json, evidence_json,
            review_status, created_at, reviewed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (gid, kind, fingerprint, proposed_json, evidence_json, status, now, reviewed_at),
    )
    return True


def import_review_data(
    database_path: str | Path, registry_path: str | Path, iso_reference_path: str | Path,
    iso_provenance_path: str | Path, iso_proposals_path: str | Path,
    persian_candidates_path: str | Path, persian_provenance_path: str | Path,
    taxonomy_path: str | Path, flag_mapping_path: str | Path,
) -> dict[str, int | str]:
    """Import all review-domain candidates without inventing approvals or filling blanks."""
    registry = _read_json(Path(registry_path))
    taxonomy = _read_json(Path(taxonomy_path))
    by_id, unreviewed_value = _validate_registry_and_taxonomy(registry, taxonomy)
    iso = _validate_iso(registry, Path(iso_reference_path), Path(iso_provenance_path), Path(iso_proposals_path))
    persian = _validate_persian(registry, Path(persian_candidates_path), Path(persian_provenance_path))
    flags_payload = _read_json(Path(flag_mapping_path))
    if flags_payload.get("schema_version") != 1 or not isinstance(flags_payload.get("source"), dict):
        raise ReviewDataImportError("Flag mapping has an unsupported schema or missing source metadata")
    flag_rows = flags_payload.get("records")
    if not isinstance(flag_rows, list) or len(flag_rows) != len(by_id):
        raise ReviewDataImportError("Flag mapping records must cover the identity registry exactly")
    flags: dict[str, dict[str, Any]] = {}
    for row in flag_rows:
        if not isinstance(row, dict):
            raise ReviewDataImportError("Flag mapping contains a non-object record")
        gid = row.get("game_id")
        if not isinstance(gid, str) or gid not in by_id or gid in flags:
            raise ReviewDataImportError(f"Flag mapping has an unknown, empty or duplicate game_id: {gid!r}")
        code = row.get("source_flag_code")
        if code is not None and (not isinstance(code, str) or not re.fullmatch(r"[a-z]{2}", code)):
            raise ReviewDataImportError(f"{gid}: source_flag_code must be null or two lowercase letters")
        manual_path = row.get("manual_svg_path")
        if manual_path is not None and (not isinstance(manual_path, str) or not manual_path.strip()):
            raise ReviewDataImportError(f"{gid}: manual_svg_path must be null or non-empty text")
        if code is not None and manual_path is not None:
            raise ReviewDataImportError(f"{gid}: choose source_flag_code or manual_svg_path, not both")
        evidence = row.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(item, str) or not item.strip() for item in evidence):
            raise ReviewDataImportError(f"{gid}: flag evidence must be an array of non-empty strings")
        status = row.get("status", "unreviewed")
        if status == "reviewed":
            status = "approved"
        else:
            status = _status(status, f"{gid} flag mapping")
        reviewed_at = row.get("reviewed_at")
        if status == "approved" and not reviewed_at:
            raise ReviewDataImportError(f"{gid}: reviewed flag mapping requires an explicit reviewed_at timestamp")
        if status != "approved" and reviewed_at is not None:
            raise ReviewDataImportError(f"{gid}: unapproved flag mapping must not have reviewed_at")
        flags[gid] = {
            "code": code, "manual_svg_path": row.get("manual_svg_path"),
            "note": row.get("decision_note"), "evidence": evidence,
            "status": status, "reviewed_at": reviewed_at,
        }
    if set(flags) != set(by_id):
        raise ReviewDataImportError("Flag mapping game_id coverage does not match the identity registry")

    now = _now()
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        current_rows = connection.execute(
            """SELECT c.game_id, cs.dataset, cs.source_id
               FROM countries c JOIN country_sources cs
                 ON cs.game_id=c.game_id AND cs.is_current=1
               ORDER BY c.game_id"""
        ).fetchall()
        db_sources = {row["game_id"]: (row["dataset"], row["source_id"]) for row in current_rows}
        expected_sources = {
            gid: (record["source"].get("dataset"), record["source"]["current_source_id"])
            for gid, record in by_id.items()
        }
        if db_sources != expected_sources:
            raise ReviewDataImportError("Database current source-ID/game_id mapping does not exactly match the identity registry")
        if connection.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
            raise ReviewDataImportError("Unexpected SQLite user_version")
        for gid, record in by_id.items():
            country = connection.execute(
                "SELECT entity_type, iso_alpha2, iso_alpha3, localization_status FROM countries WHERE game_id=?",
                (gid,),
            ).fetchone()
            if country is None:
                raise ReviewDataImportError(f"{gid}: identity import must run before review-data import")
            iso_record = record.get("iso") or {}
            if (country["entity_type"], country["iso_alpha2"], country["iso_alpha3"]) != (
                record.get("entity_type") or unreviewed_value, iso_record.get("alpha2"), iso_record.get("alpha3")
            ):
                raise ReviewDataImportError(f"{gid}: database identity/ISO values conflict with registry")

        inserted = {"iso": 0, "localization": 0, "entity_type": 0, "flag": 0}
        flag_count = 0
        for gid, record in by_id.items():
            iso_row = iso[gid]
            iso_status = "candidate"
            _proposal(connection, gid, "iso", {
                "alpha2": iso_row["alpha2"], "alpha3": iso_row["alpha3"],
                "reference_name": iso_row["reference_name"], "match_type": iso_row["match_type"],
                "decision": iso_row["decision"],
            }, iso_row["provenance"], iso_status, None, now)
            inserted["iso"] += 1

            fa = persian[gid]
            source_qid = connection.execute(
                """SELECT attribute_value FROM country_attributes
                   WHERE game_id=? AND upper(attribute_key)='WIKIDATAID'""", (gid,)
            ).fetchone()
            if fa["qid"] and (source_qid is None or source_qid["attribute_value"] != fa["qid"]):
                raise ReviewDataImportError(f"{gid}: Persian Wikidata QID does not match the explicit Natural Earth WIKIDATAID source attribute")
            if source_qid is not None and source_qid["attribute_value"] and fa["qid"] != source_qid["attribute_value"]:
                raise ReviewDataImportError(f"{gid}: Persian Wikidata QID conflicts with the Natural Earth WIKIDATAID source attribute")
            persian_status = fa["status"]
            if persian_status == "approved" and (
                not fa["name"] or record["names"].get("fa") != fa["name"]
                or record["names"].get("localization_status") != "reviewed"
            ):
                raise ReviewDataImportError(f"{gid}: approved Persian proposal must match the reviewed registry canonical name")
            _proposal(connection, gid, "localization", {
                "language": "fa", "name": fa["name"], "wikidata_qid": fa["qid"],
            }, fa["provenance"], persian_status, fa["reviewed_at"], now)
            inserted["localization"] += 1
            if persian_status == "approved":
                connection.execute(
                    """INSERT OR IGNORE INTO country_names(game_id, language, name, name_type)
                       VALUES (?, 'fa', ?, 'canonical')""", (gid, fa["name"])
                )
                connection.execute(
                    "UPDATE countries SET localization_status='reviewed', updated_at=? WHERE game_id=?",
                    (now, gid),
                )

            entity_type = record.get("entity_type") or unreviewed_value
            entity_status = "candidate" if entity_type != unreviewed_value else None
            if entity_status:
                entity_definition = taxonomy["types"][entity_type]
                _proposal(connection, gid, "entity_type", {"entity_type": entity_type}, {
                    "taxonomy_definition": entity_definition.get("definition"),
                    "evidence_required": entity_definition.get("evidence_required", []),
                    "evidence": [],
                    "taxonomy_sha256": _sha(Path(taxonomy_path)),
                }, entity_status, None, now)
                inserted["entity_type"] += 1

            flag = flags[gid]
            flag_proposed = {
                "source_flag_code": flag["code"],
                "manual_svg_path": flag["manual_svg_path"],
                "decision_note": flag["note"],
            }
            flag_evidence = {
                "mapping_source": flags_payload.get("source", {}),
                "evidence": flag["evidence"],
                "mapping_sha256": _sha(Path(flag_mapping_path)),
            }
            _proposal(connection, gid, "flag", flag_proposed, flag_evidence, flag["status"], flag["reviewed_at"], now)
            inserted["flag"] += 1
            mapping_status = {"candidate": "candidate", "approved": "reviewed", "rejected": "rejected"}[flag["status"]]
            existing_flag = connection.execute(
                "SELECT source_flag_code, mapping_status, decision_note, evidence_json FROM country_flags WHERE game_id=?",
                (gid,),
            ).fetchone()
            expected_flag = (flag["code"], mapping_status, flag["note"], _canonical(flag["evidence"]))
            if existing_flag is None:
                connection.execute(
                    """INSERT INTO country_flags(game_id, source_flag_code, mapping_status, decision_note, evidence_json)
                       VALUES (?, ?, ?, ?, ?)""", (gid, *expected_flag)
                )
            elif tuple(existing_flag) != expected_flag:
                if (
                    existing_flag["source_flag_code"] == flag["code"]
                    and existing_flag["decision_note"] == flag["note"]
                    and existing_flag["evidence_json"] == _canonical(flag["evidence"])
                    and existing_flag["mapping_status"] == "candidate"
                    and mapping_status in {"reviewed", "rejected"}
                ):
                    connection.execute(
                        "UPDATE country_flags SET mapping_status=? WHERE game_id=?",
                        (mapping_status, gid),
                    )
                else:
                    raise ReviewDataImportError(f"{gid}: existing country flag mapping conflicts with source mapping")
            flag_count += 1

        issues = validate_database(connection)
        if issues:
            raise ReviewDataImportError("Database validation failed: " + "; ".join(issues))
        connection.commit()
        return {
            "countries": len(by_id), "iso_proposals": inserted["iso"],
            "localization_proposals": inserted["localization"],
            "entity_type_proposals": inserted["entity_type"],
            "flag_proposals": inserted["flag"], "flag_mappings": flag_count,
        }
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--iso-reference", type=Path, required=True)
    parser.add_argument("--iso-provenance", type=Path, required=True)
    parser.add_argument("--iso-proposals", type=Path, required=True)
    parser.add_argument("--persian-candidates", type=Path, required=True)
    parser.add_argument("--persian-provenance", type=Path, required=True)
    parser.add_argument("--entity-taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--flag-mapping", type=Path, default=DEFAULT_FLAGS)
    args = parser.parse_args()
    try:
        result = import_review_data(
            args.database, args.registry, args.iso_reference, args.iso_provenance,
            args.iso_proposals, args.persian_candidates, args.persian_provenance,
            args.entity_taxonomy, args.flag_mapping,
        )
    except (OSError, ValueError, sqlite3.Error, ReviewDataImportError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    print("Review-domain import completed; database integrity and foreign-key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
