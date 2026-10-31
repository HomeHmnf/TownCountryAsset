"""Transactional importer for normalized WP1.5 observations.

Provider-specific parsers must produce the normalized batch format documented in
docs/data-sources/wp1-5-sources.md. This module never matches identities itself.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.schema import validate_database
from tools.database.source_crosswalk import CrosswalkError, load_crosswalk


class GameDataImportError(ValueError):
    """Raised when a normalized WP1.5 batch fails validation or import."""


@dataclass(frozen=True)
class ImportResult:
    import_id: int
    dataset: str
    source_version: str
    scalar_rows: int
    structured_rows: int
    idempotent: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GameDataImportError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GameDataImportError(f"{label} must contain a JSON object")
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise GameDataImportError(f"Value is not finite JSON data: {exc}") from exc


def _load_field_contract(config_path: str | Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    config = _read_json(config_path, "WP1.5 source contract")
    if config.get("work_package") != "WP1.5" or not isinstance(config.get("fields"), list):
        raise GameDataImportError("Unsupported WP1.5 field contract")
    fields: dict[str, dict[str, Any]] = {}
    for field in config["fields"]:
        if not isinstance(field, dict) or not isinstance(field.get("key"), str):
            raise GameDataImportError("Every field contract entry must have a key")
        key = field["key"]
        if key in fields:
            raise GameDataImportError(f"Duplicate field key in contract: {key}")
        if field.get("storage") not in {"scalar", "structured"}:
            raise GameDataImportError(f"Unsupported storage type for {key}")
        fields[key] = field
    return fields, config


def _verify_manifest(manifest: dict[str, Any], manifest_path: str | Path) -> tuple[Path, str]:
    required = ("source_key", "release", "sha256", "retrieved_at", "final_url", "filename", "local_raw_path")
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        raise GameDataImportError(f"Source manifest is missing required fields: {', '.join(missing)}")
    digest = manifest["sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise GameDataImportError("Source manifest has an invalid SHA-256")
    raw_path = Path(manifest["local_raw_path"])
    if not raw_path.is_absolute():
        raw_path = Path(manifest_path).resolve().parents[3] / raw_path
    if not raw_path.is_file():
        raise GameDataImportError(f"Raw source snapshot is missing: {raw_path}")
    hasher = hashlib.sha256()
    with raw_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    actual = hasher.hexdigest()
    if actual != digest:
        raise GameDataImportError(
            f"Raw source checksum does not match manifest: expected {digest}, received {actual}"
        )
    return raw_path, digest


def _validate_batch_rows(
    rows: Any,
    *,
    fields: dict[str, dict[str, Any]],
    source_key: str,
    source_ids: dict[str, str],
    retrieved_at: str,
) -> tuple[list[dict[str, Any]], int, int]:
    if not isinstance(rows, list) or not rows:
        raise GameDataImportError("Normalized batch observations must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    unique: set[tuple[str, str]] = set()
    scalar_count = structured_count = 0
    statuses = {"observed", "estimated", "projected", "unavailable", "not_applicable"}
    for index, row in enumerate(rows):
        label = f"observations[{index}]"
        if not isinstance(row, dict):
            raise GameDataImportError(f"{label} must be an object")
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or source_id not in source_ids:
            raise GameDataImportError(f"{label}.source_id has no explicit crosswalk mapping")
        game_id = source_ids[source_id]
        field_key = row.get("field_key")
        field = fields.get(field_key) if isinstance(field_key, str) else None
        if field is None:
            raise GameDataImportError(f"{label}.field_key is not in the WP1.5 field contract")
        if field.get("primary_source") != source_key:
            raise GameDataImportError(
                f"{label}.field_key {field_key!r} is assigned to {field.get('primary_source')!r}, not {source_key!r}"
            )
        identity = (game_id, field_key)
        if identity in unique:
            raise GameDataImportError(f"Duplicate observation for game_id={game_id}, field={field_key}")
        unique.add(identity)
        status = row.get("value_status")
        if not isinstance(status, str) or status not in statuses:
            raise GameDataImportError(f"{label}.value_status is invalid")
        unit = row.get("unit")
        if not isinstance(unit, str) or not unit.strip():
            raise GameDataImportError(f"{label}.unit must be a non-empty canonical unit")
        period = row.get("observation_period")
        if not isinstance(period, str) or not period.strip():
            raise GameDataImportError(f"{label}.observation_period is required")
        reference = row.get("source_reference")
        if not isinstance(reference, str) or not reference.strip():
            raise GameDataImportError(f"{label}.source_reference is required")
        methodology = row.get("methodology")
        if not isinstance(methodology, str) or not methodology.strip():
            raise GameDataImportError(f"{label}.methodology is required")
        value = row.get("value")
        record = {
            "game_id": game_id,
            "field_key": field_key,
            "storage": field["storage"],
            "value": value,
            "value_status": status,
            "unit": unit,
            "observation_period": period,
            "source_reference": reference,
            "source_version": None,
            "methodology": methodology,
            "retrieved_at": retrieved_at,
        }
        if field["storage"] == "scalar":
            if value is None:
                if status not in {"unavailable", "not_applicable"}:
                    raise GameDataImportError(f"{label}: NULL scalar requires unavailable/not_applicable status")
            else:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    raise GameDataImportError(f"{label}.value must be a finite number or explicit NULL")
                if status not in {"observed", "estimated", "projected"}:
                    raise GameDataImportError(f"{label}: populated scalar requires observed/estimated/projected status")
            scalar_count += 1
        else:
            if value is None or status not in {"observed", "estimated", "projected"}:
                raise GameDataImportError(f"{label}: structured values must be non-NULL and observed/estimated/projected")
            _canonical_json(value)
            structured_count += 1
        normalized.append(record)
    return normalized, scalar_count, structured_count


def _row_matches(connection: sqlite3.Connection, row: dict[str, Any], import_id: int) -> bool:
    if row["storage"] == "scalar":
        existing = connection.execute(
            """SELECT value, unit, observation_period, value_status, source_reference,
                      source_version, methodology, retrieved_at, import_id
               FROM current_statistics WHERE game_id = ? AND statistic_key = ?""",
            (row["game_id"], row["field_key"]),
        ).fetchone()
        if existing is None:
            return False
        return (
            existing["value"] == row["value"]
            and existing["unit"] == row["unit"]
            and existing["observation_period"] == row["observation_period"]
            and existing["value_status"] == row["value_status"]
            and existing["source_reference"] == row["source_reference"]
            and existing["source_version"] == row["source_version"]
            and existing["methodology"] == row["methodology"]
            and existing["retrieved_at"] == row["retrieved_at"]
            and existing["import_id"] == import_id
        )
    existing = connection.execute(
        """SELECT payload_json, observation_period, value_status, source_reference,
                  source_version, methodology, retrieved_at, import_id
           FROM selected_game_data WHERE game_id = ? AND data_category = 'wp1_5'
             AND data_key = ?""",
        (row["game_id"], row["field_key"]),
    ).fetchone()
    if existing is None:
        return False
    return (
        existing["payload_json"] == _canonical_json(row["value"])
        and existing["observation_period"] == row["observation_period"]
        and existing["value_status"] == row["value_status"]
        and existing["source_reference"] == row["source_reference"]
        and existing["source_version"] == row["source_version"]
        and existing["methodology"] == row["methodology"]
        and existing["retrieved_at"] == row["retrieved_at"]
        and existing["import_id"] == import_id
    )


def import_normalized_batch(
    connection: sqlite3.Connection,
    *,
    batch_path: str | Path,
    manifest_path: str | Path,
    crosswalk_path: str | Path,
    config_path: str | Path,
) -> ImportResult:
    """Validate provenance, crosswalk and normalized observations, then import atomically."""
    batch = _read_json(batch_path, "normalized observation batch")
    manifest = _read_json(manifest_path, "source manifest")
    _, digest = _verify_manifest(manifest, manifest_path)
    source_key = batch.get("source_key")
    release = batch.get("release")
    if source_key != manifest.get("source_key") or release != manifest.get("release"):
        raise GameDataImportError("Batch source_key/release does not match the captured source manifest")
    if batch.get("schema_version") != 1:
        raise GameDataImportError("Unsupported normalized batch schema version")
    try:
        known_ids = [row["game_id"] for row in connection.execute("SELECT game_id FROM countries")]
        crosswalk = load_crosswalk(
            crosswalk_path, expected_dataset=source_key, known_game_ids=known_ids
        )
    except CrosswalkError as exc:
        raise GameDataImportError(f"Invalid source crosswalk: {exc}") from exc
    if crosswalk.source_key != source_key:
        raise GameDataImportError("Crosswalk source_key does not match source manifest")
    source_ids = {item.source_id: item.game_id for item in crosswalk.mappings}
    fields, _ = _load_field_contract(config_path)
    normalized, scalar_count, structured_count = _validate_batch_rows(
        batch.get("observations"),
        fields=fields,
        source_key=source_key,
        source_ids=source_ids,
        retrieved_at=manifest["retrieved_at"],
    )
    for row in normalized:
        row["source_version"] = release

    dataset = source_key
    existing_imports = connection.execute(
        "SELECT * FROM dataset_imports WHERE dataset = ? AND source_version = ? AND sha256 = ?",
        (dataset, release, digest),
    ).fetchall()
    if len(existing_imports) > 1:
        raise GameDataImportError("Multiple dataset_imports rows match the same source release and checksum")
    if existing_imports:
        import_id = int(existing_imports[0]["import_id"])
        if not all(_row_matches(connection, row, import_id) for row in normalized):
            raise GameDataImportError("Existing import rows conflict with this normalized batch")
        expected_scalar = sum(row["storage"] == "scalar" for row in normalized)
        expected_structured = len(normalized) - expected_scalar
        actual_scalar = connection.execute(
            "SELECT COUNT(*) FROM current_statistics WHERE import_id = ?", (import_id,)
        ).fetchone()[0]
        actual_structured = connection.execute(
            "SELECT COUNT(*) FROM selected_game_data WHERE import_id = ?", (import_id,)
        ).fetchone()[0]
        if actual_scalar != expected_scalar or actual_structured != expected_structured:
            raise GameDataImportError("Existing import row counts differ from normalized batch")
        return ImportResult(import_id, dataset, release, scalar_count, structured_count, True)

    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """INSERT INTO dataset_imports (
                   dataset, source_version, source_url, retrieval_date, sha256,
                   attribution, license, import_status, imported_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, 'candidate', ?)""",
            (
                dataset, release, manifest.get("final_url"), manifest.get("retrieved_at"),
                digest, manifest.get("attribution"), manifest.get("license_status"), _utc_now(),
            ),
        )
        import_id = int(cursor.lastrowid)
        for row in normalized:
            if row["storage"] == "scalar":
                connection.execute(
                    """INSERT INTO current_statistics (
                           game_id, statistic_key, value, unit, observed_at,
                           observation_period, value_status, source_reference,
                           source_version, methodology, retrieved_at, import_id
                       ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row["game_id"], row["field_key"], row["value"], row["unit"],
                        row["observation_period"], row["value_status"], row["source_reference"],
                        row["source_version"], row["methodology"], row["retrieved_at"], import_id,
                    ),
                )
            else:
                connection.execute(
                    """INSERT INTO selected_game_data (
                           game_id, data_category, data_key, payload_json, import_id,
                           value_status, observation_period, source_reference,
                           source_version, methodology, retrieved_at
                       ) VALUES (?, 'wp1_5', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row["game_id"], row["field_key"], _canonical_json(row["value"]), import_id,
                        row["value_status"], row["observation_period"], row["source_reference"],
                        row["source_version"], row["methodology"], row["retrieved_at"],
                    ),
                )
        issues = validate_database(connection)
        if issues:
            raise GameDataImportError("Database integrity validation failed: " + "; ".join(issues))
        connection.commit()
    except Exception as exc:
        if connection.in_transaction:
            connection.rollback()
        if isinstance(exc, GameDataImportError):
            raise
        if isinstance(exc, sqlite3.IntegrityError):
            raise GameDataImportError(f"Database rejected WP1.5 import: {exc}") from exc
        raise
    return ImportResult(import_id, dataset, release, scalar_count, structured_count, False)
