"""Approval-gated transactional importer for annual IMF WEO historical observations."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from tools.database.application_approval import (
    ApplicationApprovalError, build_application_artifact, decide_application,
    propose_application, record_application_applied, require_approved_application,
)
from tools.database.connection import DEFAULT_DATABASE_PATH, REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database

DEFAULT_CANDIDATE = REPOSITORY_ROOT / "reports/sources/imf-weo-historical-candidate"
DEFAULT_SOURCE = REPOSITORY_ROOT / "raw_data/sources/imf_weo/october_2026/dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv"
DEFAULT_IDENTITY = REPOSITORY_ROOT / "config/country_identity_registry.json"
DEFAULT_MIGRATION = REPOSITORY_ROOT / "migrations/008_imf_weo_historical_observations.sql"
DEFAULT_ACQUISITION_RECORD = REPOSITORY_ROOT / "docs/data-sources/imf-weo-october-2026-manual-acquisition.md"
SOURCE_URL = "https://data.imf.org/datasets/WEO"
DATASET = "world_economic_outlook"
RELEASE = "October 2026 / IMF.RES_WEO_9.0.0"
ACQUIRED_ON = "2026-11-02"


class WEOImportError(RuntimeError):
    """Unsafe or invalid IMF WEO historical import."""


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _candidate_files(candidate_dir: Path) -> tuple[Path, Path, Path]:
    paths = (candidate_dir / "observations.csv", candidate_dir / "identity_exceptions.csv",
             candidate_dir / "candidate.json")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise WEOImportError("Candidate package is incomplete: " + ", ".join(missing))
    return paths


def _load_candidate(candidate_dir: Path, source_path: Path, identity_path: Path,
                    migration_path: Path, acquisition_record_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[Path]]:
    observations_path, exceptions_path, summary_path = _candidate_files(candidate_dir)
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WEOImportError(f"Cannot read candidate summary: {exc}") from exc
    if summary.get("candidate_type") != "imf_weo_annual_historical_observations":
        raise WEOImportError("Unsupported WEO candidate type")
    if summary.get("source_sha256") != _sha(source_path):
        raise WEOImportError("Raw IMF WEO snapshot checksum differs from candidate summary")
    if summary.get("source_byte_count") != source_path.stat().st_size:
        raise WEOImportError("Raw IMF WEO snapshot byte count differs from candidate summary")
    if summary.get("observations_sha256") != _sha(observations_path):
        raise WEOImportError("Candidate observations.csv checksum differs from candidate summary")
    if summary.get("exceptions_sha256") != _sha(exceptions_path):
        raise WEOImportError("Candidate identity_exceptions.csv checksum differs from candidate summary")
    if summary.get("source_path") != source_path.relative_to(REPOSITORY_ROOT).as_posix():
        raise WEOImportError("Candidate source path does not identify the recorded raw snapshot")
    if summary.get("identity_registry_path") != identity_path.relative_to(REPOSITORY_ROOT).as_posix():
        raise WEOImportError("Candidate identity registry path does not match the configured registry")
    if not acquisition_record_path.is_file():
        raise WEOImportError("IMF WEO manual acquisition record is missing")
    acquisition_text = acquisition_record_path.read_text(encoding="utf-8")
    if summary["source_sha256"] not in acquisition_text or source_path.name not in acquisition_text:
        raise WEOImportError("Manual acquisition record does not corroborate the captured WEO CSV")

    required = {
        "game_id", "source_country_code", "source_country_name", "indicator_code",
        "field_id", "observation_year", "value", "unit", "scale", "value_status",
        "latest_actual_annual_data", "reporting_year_months", "source_reference",
        "source_version", "source_sha256", "acquired_on", "acquisition_time_precision",
    }
    rows: list[dict[str, Any]] = []
    with observations_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != required:
            raise WEOImportError("Candidate observations.csv has an invalid column contract")
        seen: set[tuple[str, str, int, str]] = set()
        for index, raw in enumerate(reader, start=2):
            try:
                value = float(raw["value"])
                year = int(raw["observation_year"])
                field_id = int(raw["field_id"])
            except (TypeError, ValueError) as exc:
                raise WEOImportError(f"Invalid numeric candidate value at CSV line {index}") from exc
            if not math.isfinite(value):
                raise WEOImportError(f"Non-finite candidate value at CSV line {index}")
            if raw["value_status"] != "unclassified":
                raise WEOImportError(f"Candidate status must remain unclassified at CSV line {index}")
            if raw["indicator_code"] not in {"NGDPD", "NGDPDPC", "PPPGDP", "PCPIPCH", "LUR"}:
                raise WEOImportError(f"Unsupported indicator code at CSV line {index}")
            expected_fields = {"NGDPD": 15, "NGDPDPC": 16, "PPPGDP": 18, "PCPIPCH": 20, "LUR": 21}
            if field_id != expected_fields[raw["indicator_code"]] or not 1900 <= year <= 2200:
                raise WEOImportError(f"Indicator/field/year mismatch at CSV line {index}")
            if raw["source_sha256"] != summary["source_sha256"] or raw["source_version"] != RELEASE:
                raise WEOImportError(f"Source provenance mismatch at CSV line {index}")
            if raw["source_reference"] != SOURCE_URL or raw["acquired_on"] != ACQUIRED_ON:
                raise WEOImportError(f"Source acquisition metadata mismatch at CSV line {index}")
            if raw["acquisition_time_precision"] != "day":
                raise WEOImportError(f"Acquisition precision mismatch at CSV line {index}")
            if not raw["source_country_code"].strip() or not raw["source_country_name"].strip():
                raise WEOImportError(f"Source country code/name missing at CSV line {index}")
            if not raw["game_id"] or len(raw["game_id"]) != 35 or not raw["game_id"].startswith("tc_"):
                raise WEOImportError(f"Invalid persistent game_id at CSV line {index}")
            key = (raw["game_id"], raw["indicator_code"], year, raw["source_version"])
            if key in seen:
                raise WEOImportError(f"Duplicate candidate observation key at CSV line {index}: {key}")
            seen.add(key)
            rows.append({
                **raw, "value": value, "observation_year": year, "field_id": field_id,
                "unit": raw["unit"] or None, "scale": raw["scale"] or None,
                "latest_actual_annual_data": raw["latest_actual_annual_data"] or None,
                "reporting_year_months": raw["reporting_year_months"] or None,
            })
    if len(rows) != summary.get("observation_count"):
        raise WEOImportError("Candidate observation count does not match candidate.json")
    return rows, summary, [observations_path, exceptions_path, summary_path, source_path, identity_path, migration_path, acquisition_record_path]


def _artifact(candidate_dir: Path, source_path: Path, identity_path: Path,
              migration_path: Path, acquisition_record_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    rows, summary, inputs = _load_candidate(candidate_dir, source_path, identity_path, migration_path, acquisition_record_path)
    artifact = build_application_artifact(
        domain="imf_weo_historical_observations",
        inputs=inputs,
        metadata={
            "source_key": "imf_weo", "dataset": DATASET, "release": "october_2026",
            "source_sha256": summary["source_sha256"],
            "candidate_observation_count": len(rows),
            "candidate_sha256": summary["observations_sha256"],
            "status_policy": "unclassified",
            "identity_policy": "preserve_existing_game_id_and_identity_status",
        },
    )
    return artifact, rows, summary


def prepare_application(candidate_dir: str | Path, *, database_path: str | Path = DEFAULT_DATABASE_PATH,
                        source_path: str | Path = DEFAULT_SOURCE,
                        identity_path: str | Path = DEFAULT_IDENTITY,
                        migration_path: str | Path = DEFAULT_MIGRATION,
                        acquisition_record_path: str | Path = DEFAULT_ACQUISITION_RECORD,
                        approval_id: str | None = None) -> dict[str, Any]:
    candidate_dir, source_path, identity_path, migration_path, acquisition_record_path = map(
        lambda item: Path(item).resolve(), (candidate_dir, source_path, identity_path, migration_path, acquisition_record_path)
    )
    artifact, rows, summary = _artifact(candidate_dir, source_path, identity_path, migration_path, acquisition_record_path)
    if not approval_id:
        approval_id = "imf-weo-oct2026-" + artifact["artifact_sha256"][:16]
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT artifact_sha256, status FROM application_approvals WHERE approval_id=?",
            (approval_id,),
        ).fetchone()
        if existing:
            if existing["artifact_sha256"] != artifact["artifact_sha256"]:
                raise WEOImportError("Approval ID already exists for a different artifact")
            connection.rollback()
            return {"approval_id": approval_id, "status": existing["status"],
                    "artifact_sha256": artifact["artifact_sha256"], "observation_count": len(rows),
                    "database_observations_written": False, "idempotent": True}
        propose_application(connection, approval_id=approval_id, artifact=artifact)
        connection.commit()
        return {"approval_id": approval_id, "status": "pending",
                "artifact_sha256": artifact["artifact_sha256"], "observation_count": len(rows),
                "candidate_sha256": summary["observations_sha256"],
                "database_observations_written": False, "approval_created": True}
    except (sqlite3.Error, ApplicationApprovalError, WEOImportError):
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def decide_application_for_weo(approval_id: str, *, decision: str, actor: str, note: str,
                               database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        approval = connection.execute(
            "SELECT domain, status FROM application_approvals WHERE approval_id=?", (approval_id,)
        ).fetchone()
        if approval is None or approval["domain"] != "imf_weo_historical_observations":
            raise WEOImportError("Approval ID does not identify an IMF WEO historical application")
        decide_application(connection, approval_id=approval_id, decision=decision, actor=actor, note=note)
        connection.commit()
        return {"approval_id": approval_id, "status": decision, "actor": actor, "database_observations_written": False}
    except (sqlite3.Error, ApplicationApprovalError):
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def apply_application(candidate_dir: str | Path, approval_id: str, *,
                      database_path: str | Path = DEFAULT_DATABASE_PATH,
                      source_path: str | Path = DEFAULT_SOURCE,
                      identity_path: str | Path = DEFAULT_IDENTITY,
                      migration_path: str | Path = DEFAULT_MIGRATION,
                      acquisition_record_path: str | Path = DEFAULT_ACQUISITION_RECORD) -> dict[str, Any]:
    candidate_dir, source_path, identity_path, migration_path, acquisition_record_path = map(
        lambda item: Path(item).resolve(), (candidate_dir, source_path, identity_path, migration_path, acquisition_record_path)
    )
    artifact, rows, summary = _artifact(candidate_dir, source_path, identity_path, migration_path, acquisition_record_path)
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            require_approved_application(connection, approval_id=approval_id, artifact=artifact)
        except ApplicationApprovalError:
            status = connection.execute("SELECT status FROM application_approvals WHERE approval_id=?",
                                        (approval_id,)).fetchone()
            if status and status["status"] == "invalidated":
                connection.commit()
            elif connection.in_transaction:
                connection.rollback()
            raise
        unknown = sorted({row["game_id"] for row in rows} - {
            item["game_id"] for item in connection.execute("SELECT game_id FROM countries")
        })
        if unknown:
            raise WEOImportError(
                "Candidate game_id values are absent from canonical countries; import the identity registry "
                "without changing its proposal/unverified status first: " + ", ".join(unknown[:12])
            )

        existing_imports = connection.execute(
            "SELECT import_id, source_version, source_url, retrieval_date, import_status "
            "FROM dataset_imports WHERE dataset=? AND sha256=? ORDER BY import_id",
            (DATASET, summary["source_sha256"]),
        ).fetchall()
        if len(existing_imports) > 1:
            raise WEOImportError("Multiple dataset_imports rows exist for the same WEO source checksum")
        if existing_imports:
            imp = existing_imports[0]
            if (imp["source_version"], imp["source_url"], imp["retrieval_date"], imp["import_status"]) != (
                RELEASE, SOURCE_URL, ACQUIRED_ON, "candidate"
            ):
                raise WEOImportError("Existing WEO dataset import metadata conflicts with candidate provenance")
            import_id = int(imp["import_id"])
        else:
            cur = connection.execute(
                """INSERT INTO dataset_imports
                   (dataset, source_version, source_url, retrieval_date, sha256,
                    attribution, license, import_status, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'candidate', datetime('now'))""",
                (DATASET, RELEASE, SOURCE_URL, ACQUIRED_ON, summary["source_sha256"],
                 "International Monetary Fund, World Economic Outlook, October 2026",
                 "unclear_or_unverified"),
            )
            import_id = int(cur.lastrowid)

        inserted = 0
        unchanged = 0
        for row in rows:
            existing = connection.execute(
                """SELECT observation_id, value, unit, scale, value_status,
                          latest_actual_annual_data, reporting_year_months,
                          source_country_code, source_country_name, source_reference,
                          source_version, source_sha256, acquired_on,
                          acquisition_time_precision, import_id
                   FROM imf_weo_historical_observations
                   WHERE game_id=? AND indicator_code=? AND observation_year=? AND source_version=?""",
                (row["game_id"], row["indicator_code"], row["observation_year"], row["source_version"]),
            ).fetchone()
            expected = (
                row["value"], row["unit"], row["scale"], "unclassified",
                row["latest_actual_annual_data"], row["reporting_year_months"],
                row["source_country_code"], row["source_country_name"], row["source_reference"],
                row["source_version"], row["source_sha256"], row["acquired_on"],
                row["acquisition_time_precision"], import_id,
            )
            if existing:
                if tuple(existing)[1:] != expected:
                    raise WEOImportError(
                        "Existing WEO observation conflicts with candidate at "
                        f"{row['game_id']}/{row['indicator_code']}/{row['observation_year']}"
                    )
                unchanged += 1
                continue
            connection.execute(
                """INSERT INTO imf_weo_historical_observations (
                    game_id, source_country_code, source_country_name, indicator_code,
                    field_id, observation_year, value, unit, scale, value_status,
                    latest_actual_annual_data, reporting_year_months, source_reference,
                    source_version, source_sha256, acquired_on, acquisition_time_precision, import_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unclassified', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row["game_id"], row["source_country_code"], row["source_country_name"],
                 row["indicator_code"], row["field_id"], row["observation_year"], row["value"],
                 row["unit"], row["scale"], row["latest_actual_annual_data"],
                 row["reporting_year_months"], row["source_reference"], row["source_version"],
                 row["source_sha256"], row["acquired_on"], row["acquisition_time_precision"], import_id),
            )
            inserted += 1
        if inserted + unchanged != len(rows):
            raise WEOImportError("Internal WEO import accounting mismatch")
        issues = validate_database(connection)
        if issues:
            raise WEOImportError("Database validation failed: " + "; ".join(issues))
        record_application_applied(
            connection, approval_id=approval_id,
            application_id=f"imf-weo:{summary['source_sha256'][:16]}",
            details={"import_id": import_id, "inserted": inserted, "unchanged": unchanged,
                     "candidate_observations": len(rows)},
        )
        connection.commit()
        return {
            "dataset": DATASET, "release": "october_2026", "import_id": import_id,
            "candidate_observations": len(rows), "inserted": inserted, "unchanged": unchanged,
            "distinct_game_ids": len({row["game_id"] for row in rows}),
            "integrity": "ok", "foreign_keys": "ok", "approval_id": approval_id,
            "approval_status": "applied", "dataset_import_status": "candidate",
        }
    except (sqlite3.Error, ApplicationApprovalError):
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--identity-registry", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument("--migration", type=Path, default=DEFAULT_MIGRATION)
    parser.add_argument("--acquisition-record", type=Path, default=DEFAULT_ACQUISITION_RECORD)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true", help="Create a pending shared application approval")
    modes.add_argument("--decide", choices=("approved", "rejected"), help="Record an explicit human decision")
    modes.add_argument("--apply", action="store_true", help="Apply an already approved exact artifact")
    parser.add_argument("--approval-id")
    parser.add_argument("--actor")
    parser.add_argument("--note")
    args = parser.parse_args(argv)
    try:
        if args.prepare:
            result = prepare_application(args.candidate_dir, database_path=args.database,
                source_path=args.source, identity_path=args.identity_registry,
                migration_path=args.migration, acquisition_record_path=args.acquisition_record,
                approval_id=args.approval_id)
        elif args.decide:
            if not args.approval_id or not args.actor or not args.note:
                raise WEOImportError("--decide requires --approval-id, --actor and --note")
            result = decide_application_for_weo(args.approval_id, decision=args.decide,
                actor=args.actor, note=args.note, database_path=args.database)
        else:
            if not args.approval_id:
                raise WEOImportError("--apply requires --approval-id")
            result = apply_application(args.candidate_dir, args.approval_id,
                database_path=args.database, source_path=args.source,
                identity_path=args.identity_registry, migration_path=args.migration,
                acquisition_record_path=args.acquisition_record)
    except (WEOImportError, ApplicationApprovalError, OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"IMF WEO import failed: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
