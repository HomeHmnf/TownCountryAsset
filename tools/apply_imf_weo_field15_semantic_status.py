#!/usr/bin/env python3
"""Guarded application of the owner-approved IMF WEO field-15 status proposal.

Default mode is read-only preflight. A canonical write requires --apply,
--confirm-semantic-status-application, a verified backup path and SHA-256,
and an identified actor plus decision note. This tool changes only
imf_weo_historical_observations.value_status for the exact approved field-15
rows; it does not modify the source candidate or dataset-import status.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.database.application_approval import (
    ApplicationApprovalError,
    build_application_artifact,
    decide_application,
    propose_application,
    record_application_applied,
    require_approved_application,
)
from tools.database.connection import DEFAULT_DATABASE_PATH, REPOSITORY_ROOT
from tools.database.schema import validate_database

DEFAULT_REVIEW = ROOT / "reports/sources/imf-weo-field15-semantic-review/20261127T152134Z"
DEFAULT_PROPOSAL_SHA256 = "28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006"
DEFAULT_SOURCE_SHA256 = "a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d"
DEFAULT_CANDIDATE_SHA256 = "8f2c2dccfb3263d67544e6772ad2fe3acb47885040967db3a22feb560ed48365"
SOURCE_VERSION = "October 2026 / IMF.RES_WEO_9.0.0"
EXPECTED_ROWS = 9361
EXPECTED_COUNTS = {"observed": 8168, "estimated": 1193}
EXPECTED_RULES = {"integer_latest_actual_year": 178, "fiscal_year_ending_year": 19}
EXPECTED_FIELDS = {
    "game_id", "source_country_code", "source_country_name", "indicator_code",
    "field_id", "observation_year", "value", "current_value_status",
    "proposed_value_status", "latest_actual_annual_data", "reporting_year_months",
    "cutoff_year", "classification_rule", "source_sha256",
}


class SemanticApplyError(RuntimeError):
    """Unsafe or inconsistent semantic status application."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def open_readonly(path: Path) -> sqlite3.Connection:
    uri = "file:" + quote(str(path.resolve()), safe="/:") + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def load_approved_proposal(review_dir: Path) -> tuple[list[dict], dict, dict]:
    proposal_path = review_dir / "classification_proposals.csv"
    summary_path = review_dir / "summary.json"
    approval_path = review_dir / "owner_semantic_approval.md"
    for path in (proposal_path, summary_path, approval_path):
        if not path.is_file():
            raise SemanticApplyError(f"Required approval artifact is missing: {path}")
    digest = sha256_file(proposal_path)
    if digest != DEFAULT_PROPOSAL_SHA256:
        raise SemanticApplyError("Proposal CSV SHA-256 differs from the explicitly approved fingerprint")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("proposal_sha256") != DEFAULT_PROPOSAL_SHA256
        or summary.get("source_sha256") != DEFAULT_SOURCE_SHA256
        or summary.get("candidate_observations_sha256") != DEFAULT_CANDIDATE_SHA256
        or summary.get("complete") is not True
        or summary.get("database_written") is not False
        or summary.get("approval_created") is not False
        or summary.get("proposed_observations") != EXPECTED_ROWS
        or summary.get("proposed_status_counts") != EXPECTED_COUNTS
        or summary.get("metadata_rule_series_counts") != EXPECTED_RULES
        or summary.get("unresolved_series_count") != 0
    ):
        raise SemanticApplyError("Semantic summary does not match the approved complete proposal")
    approval_text = approval_path.read_text(encoding="utf-8")
    required_approval_text = (
        "Decision:** APPROVED",
        DEFAULT_PROPOSAL_SHA256,
        "WP1.5 field 15 only",
        "No `projected` status is inferred",
    )
    if any(token not in approval_text for token in required_approval_text):
        raise SemanticApplyError("Owner semantic approval record is missing or does not bind the exact proposal")
    rows = []
    with proposal_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != EXPECTED_FIELDS:
            raise SemanticApplyError("Proposal CSV column contract differs")
        for line, raw in enumerate(reader, start=2):
            try:
                year = int(raw["observation_year"])
                cutoff = int(raw["cutoff_year"])
                field_id = int(raw["field_id"])
                value = float(raw["value"])
            except (TypeError, ValueError) as exc:
                raise SemanticApplyError(f"Invalid numeric proposal value at CSV line {line}") from exc
            status = raw["proposed_value_status"]
            rule = raw["classification_rule"]
            expected_status = "observed" if year <= cutoff else "estimated"
            if (
                field_id != 15 or raw["indicator_code"] != "NGDPD"
                or status not in {"observed", "estimated"}
                or status != expected_status
                or raw["current_value_status"] != "unclassified"
                or raw["source_sha256"] != DEFAULT_SOURCE_SHA256
                or rule not in EXPECTED_RULES
                or not raw["game_id"].startswith("tc_") or len(raw["game_id"]) != 35
                or not raw["source_country_code"].strip()
            ):
                raise SemanticApplyError(f"Proposal contract/policy violation at CSV line {line}")
            if not (value == value and abs(value) != float("inf")):
                raise SemanticApplyError(f"Non-finite proposal value at CSV line {line}")
            rows.append({**raw, "observation_year": year, "cutoff_year": cutoff,
                         "field_id": field_id, "value": value})
    keys = [(r["game_id"], r["indicator_code"], r["observation_year"], SOURCE_VERSION) for r in rows]
    if len(rows) != EXPECTED_ROWS or len(set(keys)) != EXPECTED_ROWS:
        raise SemanticApplyError("Proposal row count or canonical observation keys are not exactly 9,361 unique")
    counts = dict(Counter(r["proposed_value_status"] for r in rows))
    if counts != EXPECTED_COUNTS or len({r["source_country_code"] for r in rows}) != 197:
        raise SemanticApplyError("Proposal status counts or 197-series coverage differ from approval")
    rules = {}
    for row in rows:
        code = row["source_country_code"]
        value = (row["classification_rule"], row["cutoff_year"])
        if code in rules and rules[code] != value:
            raise SemanticApplyError(f"Inconsistent cutoff/rule within source series {code}")
        rules[code] = value
    if dict(Counter(rule for rule, _ in rules.values())) != EXPECTED_RULES:
        raise SemanticApplyError("Per-series classification rule counts differ from approval")
    return rows, summary, {"proposal": proposal_path, "summary": summary_path, "approval": approval_path}


def target_tuple(row: sqlite3.Row) -> tuple:
    return tuple(row[key] for key in (
        "observation_id", "game_id", "source_country_code", "source_country_name",
        "indicator_code", "field_id", "observation_year", "value", "value_status",
        "latest_actual_annual_data", "reporting_year_months", "source_version", "source_sha256",
    ))


def database_rows(connection: sqlite3.Connection) -> dict[tuple, sqlite3.Row]:
    result = {}
    total_release_rows = connection.execute(
        """SELECT COUNT(*) AS n FROM imf_weo_historical_observations
           WHERE field_id=15 AND indicator_code='NGDPD' AND source_version=?""",
        (SOURCE_VERSION,),
    ).fetchone()["n"]
    if int(total_release_rows) != EXPECTED_ROWS:
        raise SemanticApplyError(
            f"Field-15 release row count differs from the approved universe: {total_release_rows}"
        )
    records = connection.execute(
        """SELECT observation_id, game_id, source_country_code, source_country_name,
                  indicator_code, field_id, observation_year, value, value_status,
                  latest_actual_annual_data, reporting_year_months, source_version, source_sha256
           FROM imf_weo_historical_observations
           WHERE field_id=15 AND indicator_code='NGDPD' AND source_version=? AND source_sha256=?""",
        (SOURCE_VERSION, DEFAULT_SOURCE_SHA256),
    ).fetchall()
    for row in records:
        key = (row["game_id"], row["indicator_code"], row["observation_year"], row["source_version"])
        if key in result:
            raise SemanticApplyError(f"Duplicate canonical target key: {key}")
        result[key] = row
    return result


def verify_database(connection: sqlite3.Connection, rows: list[dict]) -> dict:
    actual = database_rows(connection)
    expected_by_key = {
        (r["game_id"], r["indicator_code"], r["observation_year"], SOURCE_VERSION): r
        for r in rows
    }
    if set(actual) != set(expected_by_key) or len(actual) != EXPECTED_ROWS:
        raise SemanticApplyError(
            f"Canonical target coverage mismatch: database={len(actual)}, proposal={len(expected_by_key)}"
        )
    for key, proposal in expected_by_key.items():
        stored = actual[key]
        checks = (
            stored["field_id"] == 15,
            stored["value_status"] == "unclassified",
            stored["source_country_code"] == proposal["source_country_code"],
            stored["source_country_name"] == proposal["source_country_name"],
            float(stored["value"]) == proposal["value"],
            (stored["latest_actual_annual_data"] or "") == proposal["latest_actual_annual_data"],
            (stored["reporting_year_months"] or "") == proposal["reporting_year_months"],
            stored["source_sha256"] == DEFAULT_SOURCE_SHA256,
        )
        if not all(checks):
            raise SemanticApplyError(f"Canonical row differs from approved proposal or is not unclassified: {key}")
    imports = connection.execute(
        """SELECT import_status FROM dataset_imports
           WHERE dataset='world_economic_outlook' AND sha256=?""",
        (DEFAULT_SOURCE_SHA256,),
    ).fetchall()
    if len(imports) != 1 or imports[0]["import_status"] != "candidate":
        raise SemanticApplyError("Expected exactly one matching WEO dataset import in candidate status")
    issues = validate_database(connection)
    if issues:
        raise SemanticApplyError("Database integrity preflight failed: " + "; ".join(issues))
    return {
        "rows": len(actual), "all_unclassified": True, "integrity": "ok",
        "foreign_keys": "ok", "dataset_import_status": "candidate",
    }


def verify_backup(backup_path: Path, backup_sha256: str, rows: list[dict], database_path: Path) -> dict:
    backup_path = backup_path.resolve()
    if backup_path == database_path.resolve() or not backup_path.is_file():
        raise SemanticApplyError("Backup must be a separate existing SQLite file")
    digest = sha256_file(backup_path)
    if digest != backup_sha256:
        raise SemanticApplyError("Backup SHA-256 does not match the supplied confirmation")
    connection = open_readonly(backup_path)
    try:
        result = verify_database(connection, rows)
    finally:
        connection.close()
    return {"path": str(backup_path), "sha256": digest, **result}


def application_artifact(files: dict, summary: dict) -> dict:
    return build_application_artifact(
        domain="imf_weo_field15_semantic_status",
        inputs=list(files.values()),
        metadata={
            "field_id": 15,
            "indicator_code": "NGDPD",
            "source_release": SOURCE_VERSION,
            "proposal_sha256": DEFAULT_PROPOSAL_SHA256,
            "source_sha256": DEFAULT_SOURCE_SHA256,
            "candidate_observations_sha256": DEFAULT_CANDIDATE_SHA256,
            "observation_count": EXPECTED_ROWS,
            "status_counts": EXPECTED_COUNTS,
            "semantic_policy": "latest_actual_inclusive; fiscal_ending_year_inclusive; zero_all_estimated; no_projected",
        },
    )


def run(*, review_dir: Path, database_path: Path, apply: bool = False,
        confirm: bool = False, actor: str | None = None, note: str | None = None,
        backup_path: Path | None = None, backup_sha256: str | None = None) -> dict:
    rows, summary, files = load_approved_proposal(review_dir.resolve())
    if not database_path.is_file():
        raise SemanticApplyError(f"Game DB does not exist: {database_path}")
    if not apply:
        connection = open_readonly(database_path)
        try:
            preflight = verify_database(connection, rows)
        finally:
            connection.close()
        return {
            "status": "preflight_passed",
            "proposal_sha256": DEFAULT_PROPOSAL_SHA256,
            "observations": len(rows),
            "status_counts": EXPECTED_COUNTS,
            "database_preflight": preflight,
            "database_written": False,
            "approval_created": False,
        }
    if not confirm:
        raise SemanticApplyError("--apply requires --confirm-semantic-status-application")
    if not actor or not note or len(note.strip()) < 20:
        raise SemanticApplyError("--apply requires --actor and a decision --note of at least 20 characters")
    if backup_path is None or not backup_sha256:
        raise SemanticApplyError("--apply requires --backup and --backup-sha256")
    backup = verify_backup(backup_path, backup_sha256, rows, database_path)
    artifact = application_artifact(files, summary)
    approval_id = "imf-weo-field15-sem-" + DEFAULT_PROPOSAL_SHA256[:16]
    connection = sqlite3.connect(str(database_path), timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute("BEGIN IMMEDIATE")
        preflight = verify_database(connection, rows)
        # The semantic approval is already recorded in the immutable owner
        # decision file. Record that approval and its application event in
        # the shared ledger in the same transaction as the status changes.
        propose_application(connection, approval_id=approval_id, artifact=artifact)
        decide_application(connection, approval_id=approval_id, decision="approved",
                           actor=actor, note=note.strip())
        require_approved_application(connection, approval_id=approval_id, artifact=artifact)
        actual = database_rows(connection)
        updated = 0
        for proposal in rows:
            key = (proposal["game_id"], "NGDPD", proposal["observation_year"], SOURCE_VERSION)
            stored = actual[key]
            cursor = connection.execute(
                """UPDATE imf_weo_historical_observations
                   SET value_status=?
                   WHERE observation_id=? AND value_status='unclassified'
                     AND field_id=15 AND indicator_code='NGDPD' AND source_version=?""",
                (proposal["proposed_value_status"], stored["observation_id"], SOURCE_VERSION),
            )
            if cursor.rowcount != 1:
                raise SemanticApplyError(f"Concurrent or conflicting status update detected: {key}")
            updated += 1
        counts = {row["value_status"]: int(row["n"]) for row in connection.execute(
            """SELECT value_status, COUNT(*) AS n
               FROM imf_weo_historical_observations
               WHERE field_id=15 AND indicator_code='NGDPD' AND source_version=? AND source_sha256=?
               GROUP BY value_status""",
            (SOURCE_VERSION, DEFAULT_SOURCE_SHA256),
        )}
        if counts != EXPECTED_COUNTS:
            raise SemanticApplyError(f"Post-update status counts differ: {counts}")
        issues = validate_database(connection)
        if issues:
            raise SemanticApplyError("Post-update database validation failed: " + "; ".join(issues))
        record_application_applied(
            connection, approval_id=approval_id,
            application_id="imf-weo-field15-semantic-" + DEFAULT_PROPOSAL_SHA256[:16],
            details={"updated": updated, "proposal_sha256": DEFAULT_PROPOSAL_SHA256,
                     "backup_sha256": backup["sha256"], "status_counts": EXPECTED_COUNTS},
        )
        connection.commit()
        return {
            "status": "applied",
            "approval_id": approval_id,
            "updated": updated,
            "proposal_sha256": DEFAULT_PROPOSAL_SHA256,
            "status_counts": EXPECTED_COUNTS,
            "backup": backup,
            "preflight": preflight,
            "integrity": "ok",
            "foreign_keys": "ok",
            "dataset_import_status_unchanged": "candidate",
        }
    except (sqlite3.Error, ApplicationApprovalError, SemanticApplyError):
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--apply", action="store_true", help="Apply the approved statuses transactionally")
    parser.add_argument("--confirm-semantic-status-application", action="store_true",
                        help="Explicitly authorize the canonical status write")
    parser.add_argument("--actor")
    parser.add_argument("--note")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--backup-sha256")
    args = parser.parse_args(argv)
    try:
        result = run(
            review_dir=args.review_dir, database_path=args.database, apply=args.apply,
            confirm=args.confirm_semantic_status_application, actor=args.actor, note=args.note,
            backup_path=args.backup, backup_sha256=args.backup_sha256,
        )
    except (OSError, ValueError, csv.Error, json.JSONDecodeError, sqlite3.Error,
            SemanticApplyError, ApplicationApprovalError) as exc:
        parser.exit(1, f"IMF WEO field-15 semantic application failed: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    if result["status"] == "preflight_passed":
        print("Read-only preflight only. No approval or database changes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
