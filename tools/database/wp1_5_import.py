"""Transactional import framework for normalized WP1.5 source observations.

Provider-specific adapters produce normalized JSON observations. This module
validates the acquisition manifest, raw checksum, field contract and explicit
country crosswalk before writing candidate observations to canonical SQLite.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.connection import DEFAULT_DATABASE_PATH, REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database
from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

DEFAULT_CONFIG = REPOSITORY_ROOT / "config" / "wp1_5_data_sources.json"
ALLOWED_STATUSES = {"observed", "estimated", "projected"}
NULL_STATUSES = {"unavailable", "not_applicable"}


class WP15ImportError(RuntimeError):
    """Raised when normalized WP1.5 observations fail validation or import."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WP15ImportError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WP15ImportError(f"{label} must contain a JSON object")
    return payload


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WP15ImportError(f"{label} must be a non-empty string")
    return value


def _aware_timestamp(value: Any, label: str) -> str:
    text = _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WP15ImportError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WP15ImportError(f"{label} must include a timezone")
    return text


def _load_inputs(*, manifest_path: Path, crosswalk_path: Path, observations_path: Path, config_path: Path):
    manifest = _read_json(manifest_path, "source manifest")
    observations = _read_json(observations_path, "normalized observations")
    config = _read_json(config_path, "WP1.5 source contract")
    if manifest.get("manifest_schema_version") != 1 or manifest.get("work_package") != "WP1.5":
        raise WP15ImportError("Unsupported WP1.5 source manifest")
    if observations.get("schema_version") != 1:
        raise WP15ImportError("Unsupported normalized observation schema_version")
    dataset = _require_text(manifest.get("source_key"), "manifest.source_key")
    if observations.get("dataset") != dataset:
        raise WP15ImportError("Observation dataset does not match source manifest")
    release = _require_text(manifest.get("release"), "manifest.release")
    if observations.get("release") != release:
        raise WP15ImportError("Observation release does not match source manifest")
    sources = config.get("sources")
    if not isinstance(sources, dict) or dataset not in sources:
        raise WP15ImportError(f"Dataset is not declared in WP1.5 source contract: {dataset}")
    raw_fields = config.get("fields")
    if not isinstance(raw_fields, list):
        raise WP15ImportError("WP1.5 field contract must be an array")
    fields = {item.get("key"): item for item in raw_fields if isinstance(item, dict) and isinstance(item.get("key"), str)}
    source_path_text = _require_text(manifest.get("local_raw_path"), "manifest.local_raw_path")
    source_path = Path(source_path_text)
    resolved = source_path.resolve() if source_path.is_absolute() else (REPOSITORY_ROOT / source_path).resolve()
    raw_root = (REPOSITORY_ROOT / "raw_data" / "wp1_5").resolve()
    if not resolved.is_relative_to(raw_root):
        raise WP15ImportError("Manifest raw path must resolve inside raw_data/wp1_5")
    try:
        raw_bytes = resolved.read_bytes()
    except OSError as exc:
        raise WP15ImportError(f"Cannot read captured source bytes {resolved}: {exc}") from exc
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    expected_sha = _require_text(manifest.get("sha256"), "manifest.sha256")
    if len(expected_sha) != 64 or actual_sha != expected_sha:
        raise WP15ImportError("Captured source SHA-256 does not match manifest")
    if manifest.get("byte_count") != len(raw_bytes):
        raise WP15ImportError("Captured source byte_count does not match manifest")
    retrieved_at = _aware_timestamp(manifest.get("retrieved_at"), "manifest.retrieved_at")
    source_url = _require_text(manifest.get("final_url") or manifest.get("source_url"), "manifest.final_url")
    if not source_url.startswith("https://"):
        raise WP15ImportError("Manifest source URL must use HTTPS")
    try:
        crosswalk = load_crosswalk(crosswalk_path, expected_dataset=dataset)
    except CrosswalkError as exc:
        raise WP15ImportError(str(exc)) from exc
    return manifest, observations, fields, crosswalk, {
        "dataset": dataset, "release": release, "sha256": actual_sha,
        "retrieved_at": retrieved_at, "source_url": source_url,
    }


def _validate_observations(observations: dict[str, Any], fields: dict[str, Any], dataset: str, crosswalk):
    rows = observations.get("observations")
    if not isinstance(rows, list) or not rows:
        raise WP15ImportError("observations must be a non-empty array")
    mapping = {item.source_id: item.game_id for item in crosswalk.mappings}
    seen: set[tuple[str, str]] = set()
    normalized = []
    for index, row in enumerate(rows):
        label = f"observations[{index}]"
        if not isinstance(row, dict):
            raise WP15ImportError(f"{label} must be an object")
        source_id = _require_text(row.get("source_id"), f"{label}.source_id")
        if source_id not in mapping:
            raise WP15ImportError(f"{label}.source_id is absent from the explicit crosswalk: {source_id}")
        field_key = _require_text(row.get("field_key"), f"{label}.field_key")
        field = fields.get(field_key)
        if field is None:
            raise WP15ImportError(f"{label}.field_key is not a selected WP1.5 field: {field_key}")
        if field.get("primary_source") != dataset:
            raise WP15ImportError(f"{label}.field_key {field_key} is assigned to {field.get('primary_source')}, not {dataset}")
        game_id = mapping[source_id]
        identity = (game_id, field_key)
        if identity in seen:
            raise WP15ImportError(f"Duplicate country/field observation: {identity}")
        seen.add(identity)
        storage = field.get("storage")
        period = _require_text(row.get("observation_period"), f"{label}.observation_period")
        status = row.get("value_status", "observed")
        unit = _require_text(row.get("unit"), f"{label}.unit")
        if storage == "scalar":
            value = row.get("value")
            if value is None:
                if status not in NULL_STATUSES:
                    raise WP15ImportError(f"{label}: null scalar requires unavailable/not_applicable status")
            elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise WP15ImportError(f"{label}.value must be a finite number or null")
            elif status not in ALLOWED_STATUSES:
                raise WP15ImportError(f"{label}: populated scalar requires observed/estimated/projected status")
            payload = None
        elif storage == "structured":
            payload = row.get("payload")
            if not isinstance(payload, (dict, list)):
                raise WP15ImportError(f"{label}.payload must be a JSON object or array")
            if status not in ALLOWED_STATUSES:
                raise WP15ImportError(f"{label}: structured value requires observed/estimated/projected status")
            value = None
        else:
            raise WP15ImportError(f"Unsupported storage contract for field {field_key}")
        methodology = row.get("methodology") or field.get("method")
        methodology = _require_text(methodology, f"{label}.methodology")
        source_reference = row.get("source_reference")
        if source_reference is not None:
            source_reference = _require_text(source_reference, f"{label}.source_reference")
        normalized.append({
            "game_id": game_id, "source_id": source_id, "field_key": field_key,
            "storage": storage, "value": value, "payload": payload, "unit": unit,
            "observation_period": period, "value_status": status,
            "methodology": methodology, "source_reference": source_reference,
        })
    return normalized


def import_wp1_5_dataset(*, manifest_path: str | Path, crosswalk_path: str | Path,
                         observations_path: str | Path, database_path: str | Path = DEFAULT_DATABASE_PATH,
                         config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Validate and transactionally import one normalized provider snapshot."""
    manifest, observations, fields, crosswalk, metadata = _load_inputs(
        manifest_path=Path(manifest_path), crosswalk_path=Path(crosswalk_path),
        observations_path=Path(observations_path), config_path=Path(config_path),
    )
    rows = _validate_observations(observations, fields, metadata["dataset"], crosswalk)
    dataset, release = metadata["dataset"], metadata["release"]
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        validate_database(connection)
        known_ids = {row["game_id"] for row in connection.execute("SELECT game_id FROM countries")}
        for mapping in crosswalk.mappings:
            if mapping.game_id not in known_ids:
                raise WP15ImportError(f"Crosswalk game_id is absent from canonical database: {mapping.game_id}")
        connection.execute("BEGIN IMMEDIATE")
        existing_import = connection.execute(
            "SELECT import_id, source_version, source_url FROM dataset_imports WHERE dataset = ? AND sha256 = ?",
            (dataset, metadata["sha256"]),
        ).fetchone()
        if existing_import is not None:
            if existing_import["source_version"] != release or existing_import["source_url"] != metadata["source_url"]:
                raise WP15ImportError("Existing dataset checksum is associated with conflicting release metadata")
            import_id = int(existing_import["import_id"])
            connection.execute("COMMIT")
            return {"dataset": dataset, "release": release, "import_id": import_id,
                    "observations": len(rows), "idempotent": True,
                    "scalar_rows": sum(r["storage"] == "scalar" for r in rows),
                    "structured_rows": sum(r["storage"] == "structured" for r in rows)}
        cursor = connection.execute(
            """INSERT INTO dataset_imports
               (dataset, source_version, source_url, retrieval_date, sha256, attribution, license, import_status, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'candidate', ?)""",
            (dataset, release, metadata["source_url"], metadata["retrieved_at"], metadata["sha256"],
             manifest.get("attribution"), manifest.get("license_status"), _utc_now()),
        )
        import_id = int(cursor.lastrowid)
        for mapping in crosswalk.mappings:
            existing = connection.execute(
                "SELECT game_id, is_current FROM country_sources WHERE dataset = ? AND source_id = ?",
                (dataset, mapping.source_id),
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id) VALUES (?, ?, ?, 1, ?)",
                    (mapping.game_id, dataset, mapping.source_id, import_id),
                )
            elif existing["game_id"] != mapping.game_id or existing["is_current"] != 1:
                raise WP15ImportError(f"Crosswalk conflicts with existing source identity mapping for {mapping.source_id}")
        for row in rows:
            if row["storage"] == "scalar":
                existing = connection.execute(
                    """SELECT s.import_id, d.dataset FROM current_statistics s
                       LEFT JOIN dataset_imports d ON d.import_id = s.import_id
                       WHERE s.game_id = ? AND s.statistic_key = ?""",
                    (row["game_id"], row["field_key"]),
                ).fetchone()
                if existing is not None and existing["dataset"] != dataset:
                    raise WP15ImportError(f"Current statistic {row['field_key']} for {row['game_id']} belongs to another source")
                values = (row["value"], row["unit"], row["observation_period"], row["observation_period"],
                          row["value_status"], row["source_reference"] or metadata["source_url"], release,
                          row["methodology"], metadata["retrieved_at"], import_id)
                if existing is None:
                    connection.execute(
                        """INSERT INTO current_statistics
                           (game_id, statistic_key, value, unit, observed_at, observation_period, value_status,
                            source_reference, source_version, methodology, retrieved_at, import_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (row["game_id"], row["field_key"], *values),
                    )
                else:
                    connection.execute(
                        """UPDATE current_statistics SET value=?, unit=?, observed_at=?, observation_period=?,
                           value_status=?, source_reference=?, source_version=?, methodology=?, retrieved_at=?, import_id=?
                           WHERE game_id=? AND statistic_key=?""",
                        (*values, row["game_id"], row["field_key"]),
                    )
            else:
                payload_json = json.dumps(row["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
                existing = connection.execute(
                    """SELECT g.import_id, d.dataset FROM selected_game_data g
                       LEFT JOIN dataset_imports d ON d.import_id = g.import_id
                       WHERE g.game_id = ? AND g.data_category = 'wp1_5' AND g.data_key = ?""",
                    (row["game_id"], row["field_key"]),
                ).fetchone()
                if existing is not None and existing["dataset"] != dataset:
                    raise WP15ImportError(f"Current structured field {row['field_key']} for {row['game_id']} belongs to another source")
                values = (payload_json, import_id, row["value_status"], row["observation_period"],
                          row["source_reference"] or metadata["source_url"], release, row["methodology"], metadata["retrieved_at"])
                if existing is None:
                    connection.execute(
                        """INSERT INTO selected_game_data
                           (game_id, data_category, data_key, payload_json, import_id, value_status, observation_period,
                            source_reference, source_version, methodology, retrieved_at)
                           VALUES (?, 'wp1_5', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (row["game_id"], row["field_key"], *values),
                    )
                else:
                    connection.execute(
                        """UPDATE selected_game_data SET payload_json=?, import_id=?, value_status=?, observation_period=?,
                           source_reference=?, source_version=?, methodology=?, retrieved_at=?
                           WHERE game_id=? AND data_category='wp1_5' AND data_key=?""",
                        (*values, row["game_id"], row["field_key"]),
                    )
        validate_database(connection)
        connection.execute("COMMIT")
        return {"dataset": dataset, "release": release, "import_id": import_id,
                "observations": len(rows), "idempotent": False,
                "scalar_rows": sum(r["storage"] == "scalar" for r in rows),
                "structured_rows": sum(r["storage"] == "structured" for r in rows)}
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()