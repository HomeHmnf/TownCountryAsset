"""Transactional importer for normalized WP1.5 provider observations.

Provider-specific parsers must produce the normalized JSON contract documented
in docs/data-sources/wp1-5-sources.md. This module never parses raw provider
files and never infers country identities or missing values.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.connection import DEFAULT_DATABASE_PATH, connect_database
from tools.database.schema import apply_migrations, validate_database
from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "wp1_5_data_sources.json"


class StatisticsImportError(RuntimeError):
    """Raised when a normalized WP1.5 dataset cannot be safely imported."""


def _read_object(path: str | Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StatisticsImportError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StatisticsImportError(f"{label} must be a JSON object")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StatisticsImportError(f"{label} must be a non-empty string")
    return value


def _validate_manifest(manifest: dict[str, Any], source_key: str) -> tuple[str, str, str, str]:
    if manifest.get("manifest_schema_version") != 1 or manifest.get("work_package") != "WP1.5":
        raise StatisticsImportError("Unsupported WP1.5 source manifest")
    if manifest.get("source_key") != source_key:
        raise StatisticsImportError("Source manifest source_key does not match normalized dataset")
    release = _text(manifest.get("release"), "manifest.release")
    sha256 = _text(manifest.get("sha256"), "manifest.sha256")
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise StatisticsImportError("manifest.sha256 must be a lowercase SHA-256 digest")
    raw_path = _text(manifest.get("local_raw_path"), "manifest.local_raw_path")
    raw_file = Path(raw_path)
    try:
        actual_sha = hashlib.sha256(raw_file.read_bytes()).hexdigest()
    except OSError as exc:
        raise StatisticsImportError(f"Cannot read captured raw source file: {raw_file}") from exc
    if actual_sha != sha256:
        raise StatisticsImportError("Captured raw source checksum does not match its manifest")
    source_url = _text(manifest.get("final_url") or manifest.get("source_url"), "manifest source URL")
    if not source_url.startswith("https://"):
        raise StatisticsImportError("Source manifest URL must use HTTPS")
    retrieved_at = _text(manifest.get("retrieved_at"), "manifest.retrieved_at")
    try:
        retrieved_timestamp = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StatisticsImportError("manifest.retrieved_at must be an ISO-8601 timestamp") from exc
    if retrieved_timestamp.tzinfo is None or retrieved_timestamp.utcoffset() is None:
        raise StatisticsImportError("manifest.retrieved_at must include a timezone")
    for optional_key in ("attribution", "license_status"):
        optional_value = manifest.get(optional_key)
        if optional_value is not None and not isinstance(optional_value, str):
            raise StatisticsImportError(f"manifest.{optional_key} must be text when supplied")
    return release, sha256, source_url, retrieved_at


def _validate_observation(
    row: Any,
    *,
    index: int,
    field_by_id: dict[int, dict[str, Any]],
    source_key: str,
    crosswalk_by_game: dict[str, str],
) -> dict[str, Any]:
    label = f"observations[{index}]"
    if not isinstance(row, dict):
        raise StatisticsImportError(f"{label} must be an object")
    game_id = _text(row.get("game_id"), f"{label}.game_id")
    source_id = _text(row.get("source_id"), f"{label}.source_id")
    if crosswalk_by_game.get(game_id) != source_id:
        raise StatisticsImportError(f"{label} game_id/source_id pair is absent from the explicit crosswalk")
    field_id = row.get("field_id")
    if isinstance(field_id, bool) or not isinstance(field_id, int) or field_id not in field_by_id:
        raise StatisticsImportError(f"{label}.field_id is not in the approved 41-field contract")
    field = field_by_id[field_id]
    if field["primary_source"] != source_key:
        raise StatisticsImportError(
            f"{label} source {source_key!r} is not the contracted primary source for field {field_id}"
        )
    period = _text(row.get("observation_period"), f"{label}.observation_period")
    status = row.get("value_status", "observed")
    if not isinstance(status, str) or status not in {"observed", "estimated", "projected", "unavailable", "not_applicable"}:
        raise StatisticsImportError(f"{label}.value_status is invalid")
    value = row.get("value")
    unit = row.get("unit", field.get("unit"))
    if not isinstance(unit, str) or not unit.strip():
        raise StatisticsImportError(f"{label}.unit must be a non-empty string")
    if field["storage"] == "scalar":
        if value is None:
            if status not in {"unavailable", "not_applicable"}:
                raise StatisticsImportError(f"{label} NULL value requires unavailable/not_applicable status")
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise StatisticsImportError(f"{label} scalar value must be a finite number or explicit NULL")
            try:
                finite = math.isfinite(float(value))
            except (OverflowError, ValueError):
                finite = False
            if not finite:
                raise StatisticsImportError(f"{label} scalar value must be a finite number or explicit NULL")
            value = float(value)
            if status not in {"observed", "estimated", "projected"}:
                raise StatisticsImportError(f"{label} populated scalar requires observed/estimated/projected status")
    else:
        if value is None or not isinstance(value, (dict, list)):
            raise StatisticsImportError(f"{label} structured value must be a JSON object or array")
        if status not in {"observed", "estimated", "projected"}:
            raise StatisticsImportError(f"{label} structured value requires observed/estimated/projected status")
        try:
            _canonical_json(value)
        except (TypeError, ValueError) as exc:
            raise StatisticsImportError(f"{label} structured value is not valid finite JSON") from exc
    source_reference = row.get("source_reference")
    if source_reference is not None and (
        not isinstance(source_reference, str) or not source_reference.startswith("https://")
    ):
        raise StatisticsImportError(f"{label}.source_reference must be HTTPS when supplied")
    methodology = row.get("methodology")
    if methodology is not None and not isinstance(methodology, str):
        raise StatisticsImportError(f"{label}.methodology must be text when supplied")
    return {
        "game_id": game_id,
        "source_id": source_id,
        "field": field,
        "value": value,
        "unit": unit,
        "status": status,
        "period": period,
        "source_reference": source_reference,
        "methodology": methodology,
    }


def import_wp1_5_dataset(
    *,
    observations_path: str | Path,
    crosswalk_path: str | Path,
    manifest_path: str | Path,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    config_path: str | Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Import one normalized provider snapshot; repeated identical imports are idempotent."""
    normalized = _read_object(observations_path, "normalized observations")
    manifest = _read_object(manifest_path, "source manifest")
    config = _read_object(config_path, "WP1.5 field contract")
    if normalized.get("schema_version") != 1 or normalized.get("work_package") != "WP1.5":
        raise StatisticsImportError("Unsupported normalized observation schema")
    source_key = _text(normalized.get("source_key"), "normalized.source_key")
    if source_key not in config.get("sources", {}):
        raise StatisticsImportError(f"Unknown source key in WP1.5 contract: {source_key}")
    release, source_sha, source_url, retrieved_at = _validate_manifest(manifest, source_key)
    if normalized.get("source_key") != manifest.get("source_key"):
        raise StatisticsImportError("Normalized observations and source manifest do not match")
    if normalized.get("source_sha256") != source_sha or normalized.get("release") != release:
        raise StatisticsImportError("Normalized observations do not identify the captured source release/checksum")

    fields = config.get("fields")
    if not isinstance(fields, list):
        raise StatisticsImportError("WP1.5 contract fields must be an array")
    field_by_id = {item.get("id"): item for item in fields if isinstance(item, dict)}
    if len(field_by_id) != 41:
        raise StatisticsImportError("WP1.5 contract must enumerate exactly 41 distinct fields")

    try:
        crosswalk = load_crosswalk(
            crosswalk_path,
            expected_dataset=source_key,
        )
    except CrosswalkError as exc:
        raise StatisticsImportError(f"Invalid source crosswalk: {exc}") from exc
    if crosswalk.source_key != source_key:
        raise StatisticsImportError("Crosswalk source_key does not match source contract")
    crosswalk_by_game = {item.game_id: item.source_id for item in crosswalk.mappings}

    rows = normalized.get("observations")
    if not isinstance(rows, list) or not rows:
        raise StatisticsImportError("Normalized observations must be a non-empty array")
    validated = [
        _validate_observation(
            row,
            index=index,
            field_by_id=field_by_id,
            source_key=source_key,
            crosswalk_by_game=crosswalk_by_game,
        )
        for index, row in enumerate(rows)
    ]
    keys = [(row["game_id"], row["field"]["id"]) for row in validated]
    if len(keys) != len(set(keys)):
        raise StatisticsImportError("Duplicate country/field observations in normalized dataset")

    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        known = {
            str(row["game_id"])
            for row in connection.execute("SELECT game_id FROM countries").fetchall()
        }
        crosswalk_unknown = sorted({item.game_id for item in crosswalk.mappings} - known)
        if crosswalk_unknown:
            raise StatisticsImportError(
                "Crosswalk references game_id values absent from canonical database: "
                + ", ".join(crosswalk_unknown[:10])
            )
        unknown = sorted({row["game_id"] for row in validated} - known)
        if unknown:
            raise StatisticsImportError(
                "Normalized observations reference game_id values absent from canonical database: "
                + ", ".join(unknown[:10])
            )
        connection.execute("BEGIN IMMEDIATE")
        imported_at = _utc_now()
        existing_import = connection.execute(
            """SELECT import_id, source_version, source_url, retrieval_date
               FROM dataset_imports WHERE dataset = ? AND sha256 = ? ORDER BY import_id LIMIT 1""",
            (source_key, source_sha),
        ).fetchone()
        if existing_import is None:
            cursor = connection.execute(
                """INSERT INTO dataset_imports
                   (dataset, source_version, source_url, retrieval_date, sha256,
                    attribution, license, import_status, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'candidate', ?)""",
                (
                    source_key, release, source_url, retrieved_at, source_sha,
                    manifest.get("attribution"), manifest.get("license_status"), imported_at,
                ),
            )
            import_id = int(cursor.lastrowid)
        else:
            import_id = int(existing_import["import_id"])
            expected = (release, source_url, retrieved_at)
            actual = (
                existing_import["source_version"],
                existing_import["source_url"],
                existing_import["retrieval_date"],
            )
            if actual != expected:
                raise StatisticsImportError("Existing dataset import metadata conflicts with source manifest")

        # Persist explicit provider IDs as source provenance.
        # A changed mapping requires a separate identity-review operation.
        for mapping in crosswalk.mappings:
            existing_mapping = connection.execute(
                """SELECT game_id, is_current FROM country_sources
                   WHERE dataset = ? AND source_id = ?""",
                (source_key, mapping.source_id),
            ).fetchone()
            if existing_mapping is None:
                connection.execute(
                    """INSERT INTO country_sources
                       (game_id, dataset, source_id, is_current, import_id)
                       VALUES (?, ?, ?, 1, ?)""",
                    (mapping.game_id, source_key, mapping.source_id, import_id),
                )
            elif existing_mapping["game_id"] != mapping.game_id or existing_mapping["is_current"] != 1:
                raise StatisticsImportError(
                    f"Crosswalk conflicts with existing source mapping for {mapping.source_id}"
                )

        scalar_count = 0
        structured_count = 0
        for row in validated:
            field = row["field"]
            reference = row["source_reference"] or source_url
            if field["storage"] == "scalar":
                values = (
                    row["value"], row["unit"], None, row["period"],
                    row["status"], reference, release, row["methodology"], retrieved_at, import_id,
                )
                existing = connection.execute(
                    """SELECT value, unit, observed_at, observation_period, value_status,
                              source_reference, source_version, methodology, retrieved_at, import_id
                       FROM current_statistics WHERE game_id = ? AND statistic_key = ?""",
                    (row["game_id"], field["key"]),
                ).fetchone()
                if existing is not None and tuple(existing) != values:
                    old_import = connection.execute(
                        "SELECT dataset FROM dataset_imports WHERE import_id = ?",
                        (existing["import_id"],),
                    ).fetchone()
                    if old_import is None or old_import["dataset"] != source_key:
                        raise StatisticsImportError(
                            f"Existing statistic conflicts with a different source: {row['game_id']}/{field['key']}"
                        )
                    connection.execute(
                        """UPDATE current_statistics SET value=?, unit=?, observed_at=?, observation_period=?,
                                  value_status=?, source_reference=?, source_version=?, methodology=?,
                                  retrieved_at=?, import_id=?
                           WHERE game_id=? AND statistic_key=?""",
                        (*values, row["game_id"], field["key"]),
                    )
                elif existing is None:
                    connection.execute(
                        """INSERT INTO current_statistics
                           (value, unit, observed_at, observation_period, value_status,
                            source_reference, source_version, methodology, retrieved_at,
                            import_id, game_id, statistic_key)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (*values, row["game_id"], field["key"]),
                    )
                scalar_count += 1
            else:
                payload = _canonical_json({"value": row["value"], "unit": row["unit"]})
                values = (
                    payload, row["status"], row["period"], reference, release,
                    row["methodology"], retrieved_at, import_id,
                )
                existing = connection.execute(
                    """SELECT payload_json, value_status, observation_period, source_reference,
                              source_version, methodology, retrieved_at, import_id
                       FROM selected_game_data WHERE game_id = ? AND data_category = 'wp1_5'
                         AND data_key = ?""",
                    (row["game_id"], field["key"]),
                ).fetchone()
                if existing is not None and tuple(existing) != values:
                    old_import = connection.execute(
                        "SELECT dataset FROM dataset_imports WHERE import_id = ?",
                        (existing["import_id"],),
                    ).fetchone()
                    if old_import is None or old_import["dataset"] != source_key:
                        raise StatisticsImportError(
                            f"Existing structured data conflicts with a different source: {row['game_id']}/{field['key']}"
                        )
                    connection.execute(
                        """UPDATE selected_game_data SET payload_json=?, value_status=?, observation_period=?,
                                  source_reference=?, source_version=?, methodology=?, retrieved_at=?, import_id=?
                           WHERE game_id=? AND data_category='wp1_5' AND data_key=?""",
                        (*values, row["game_id"], field["key"]),
                    )
                elif existing is None:
                    connection.execute(
                        """INSERT INTO selected_game_data
                           (payload_json, value_status, observation_period, source_reference,
                            source_version, methodology, retrieved_at, import_id, game_id, data_category, data_key)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'wp1_5', ?)""",
                        (*values, row["game_id"], field["key"]),
                    )
                structured_count += 1

        issues = validate_database(connection)
        if issues:
            raise StatisticsImportError("Database validation failed: " + "; ".join(issues))
        connection.commit()
        return {
            "dataset": source_key,
            "release": release,
            "import_id": import_id,
            "observations": len(validated),
            "scalar_observations": scalar_count,
            "structured_observations": structured_count,
            "crosswalk_mappings": len(crosswalk.mappings),
            "integrity": "ok",
            "foreign_keys": "ok",
        }
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
