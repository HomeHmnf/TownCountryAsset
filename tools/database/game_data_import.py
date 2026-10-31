"""Transactional writer for normalized WP1.5 observations."""
from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

_SHA = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"observed", "estimated", "projected", "unavailable", "not_applicable"}


class GameDataImportError(RuntimeError):
    """Invalid, conflicting, or unsafe normalized WP1.5 data."""


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GameDataImportError(f"{label} must be non-empty text")
    return value


def _timestamp(value: Any, label: str) -> str:
    value = _text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GameDataImportError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GameDataImportError(f"{label} must include a timezone")
    return value


def _import_wp1_5_data(
    connection: sqlite3.Connection,
    *,
    dataset: str,
    source_version: str,
    source_url: str,
    sha256: str,
    retrieved_at: str,
    crosswalk_path: str | Path,
    observations: Iterable[dict[str, Any]],
    contract_path: str | Path,
    attribution: str | None = None,
    license_text: str | None = None,
) -> dict[str, int | bool]:
    """Import one candidate snapshot; never replace a different snapshot."""
    dataset = _text(dataset, "dataset")
    source_version = _text(source_version, "source_version")
    source_url = _text(source_url, "source_url")
    if not source_url.startswith("https://") or not _SHA.fullmatch(sha256 or ""):
        raise GameDataImportError("source_url must be HTTPS and sha256 a lowercase SHA-256")
    retrieved_at = _timestamp(retrieved_at, "retrieved_at")
    try:
        contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GameDataImportError(f"Cannot read source contract: {exc}") from exc
    if not isinstance(contract, dict) or contract.get("schema_version") != 1:
        raise GameDataImportError("Unsupported WP1.5 source contract")
    if dataset not in contract.get("sources", {}):
        raise GameDataImportError(f"Undeclared WP1.5 source: {dataset}")
    fields = {
        row["key"]: row for row in contract.get("fields", [])
        if isinstance(row, dict) and isinstance(row.get("key"), str)
    }
    try:
        crosswalk = load_crosswalk(
            crosswalk_path, expected_dataset=dataset,
            known_game_ids=(r[0] for r in connection.execute("SELECT game_id FROM countries")),
        )
    except CrosswalkError as exc:
        raise GameDataImportError(str(exc)) from exc
    game_by_source = {m.source_id: m.game_id for m in crosswalk.mappings}

    normalized = []
    seen = set()
    for i, row in enumerate(observations):
        label = f"observations[{i}]"
        if not isinstance(row, dict):
            raise GameDataImportError(f"{label} must be an object")
        source_id = _text(row.get("source_id"), f"{label}.source_id")
        game_id = game_by_source.get(source_id)
        if game_id is None:
            raise GameDataImportError(f"{label}.source_id is absent from explicit crosswalk")
        key = _text(row.get("field_key"), f"{label}.field_key")
        field = fields.get(key)
        if field is None:
            raise GameDataImportError(f"{label}.field_key is not a selected WP1.5 field")
        if field.get("primary_source") != dataset:
            raise GameDataImportError(f"{label}.field_key is assigned to another source")
        status = row.get("value_status", "observed")
        if status not in _STATUSES:
            raise GameDataImportError(f"{label}.value_status is invalid")
        period = _text(row.get("observation_period"), f"{label}.observation_period")
        reference = _text(row.get("source_reference", source_url), f"{label}.source_reference")
        if not reference.startswith("https://"):
            raise GameDataImportError(f"{label}.source_reference must be HTTPS")
        methodology = row.get("methodology")
        if methodology is not None and (not isinstance(methodology, str) or not methodology.strip()):
            raise GameDataImportError(f"{label}.methodology must be non-empty text")
        unit = row.get("unit", field.get("unit"))
        if unit is not None and (not isinstance(unit, str) or not unit.strip()):
            raise GameDataImportError(f"{label}.unit must be non-empty text")
        observed_at = row.get("observed_at")
        if observed_at is not None:
            observed_at = _timestamp(observed_at, f"{label}.observed_at")
        value = row.get("value")
        storage = field.get("storage")
        if storage == "scalar":
            if value is None:
                if status not in {"unavailable", "not_applicable"}:
                    raise GameDataImportError(f"{label}.null scalar requires unavailable/not_applicable")
            elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise GameDataImportError(f"{label}.value must be finite numeric data or null")
            elif status not in {"observed", "estimated", "projected"}:
                raise GameDataImportError(f"{label}.non-null scalar has invalid status")
            payload = None
            numeric = float(value) if value is not None else None
        elif storage == "structured":
            if value is None or status not in {"observed", "estimated", "projected"}:
                raise GameDataImportError(f"{label}.structured value must be present and non-null")
            try:
                payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise GameDataImportError(f"{label}.value is not valid JSON data") from exc
            numeric = None
        else:
            raise GameDataImportError(f"{label}.unsupported storage type {storage!r}")
        identity = (game_id, key)
        if identity in seen:
            raise GameDataImportError(f"Duplicate observation for {game_id}/{key}")
        seen.add(identity)
        normalized.append((game_id, source_id, key, storage, numeric, payload,
                           unit, status, period, reference, methodology, observed_at))
    if not normalized:
        raise GameDataImportError("At least one observation is required")

    connection.execute("BEGIN IMMEDIATE")
    try:
        prior = connection.execute(
            "SELECT import_id, source_version, source_url FROM dataset_imports WHERE dataset=? AND sha256=?",
            (dataset, sha256),
        ).fetchone()
        other = connection.execute(
            "SELECT 1 FROM dataset_imports WHERE dataset=? AND sha256<>? LIMIT 1",
            (dataset, sha256),
        ).fetchone()
        if other:
            raise GameDataImportError("A different snapshot is already imported for this dataset; replacement is not supported")
        if prior:
            import_id = prior["import_id"]
            if (prior["source_version"], prior["source_url"]) != (source_version, source_url):
                raise GameDataImportError("Existing snapshot metadata conflicts")
        else:
            import_id = connection.execute(
                """INSERT INTO dataset_imports
                   (dataset,source_version,source_url,retrieval_date,sha256,attribution,license,import_status,imported_at)
                   VALUES (?,?,?,?,?,?,?,'candidate',?)""",
                (dataset, source_version, source_url, retrieved_at, sha256,
                 attribution, license_text, retrieved_at),
            ).lastrowid

        for mapping in crosswalk.mappings:
            old = connection.execute(
                "SELECT game_id,is_current,import_id FROM country_sources WHERE dataset=? AND source_id=?",
                (dataset, mapping.source_id),
            ).fetchone()
            expected = (mapping.game_id, 1, import_id)
            if old is None:
                connection.execute(
                    "INSERT INTO country_sources(game_id,dataset,source_id,is_current,import_id) VALUES(?,?,?,1,?)",
                    (mapping.game_id, dataset, mapping.source_id, import_id),
                )
            elif tuple(old) != expected:
                raise GameDataImportError(f"Conflicting source crosswalk mapping for {mapping.source_id}")

        inserted = 0
        for (gid, source_id, key, storage, number, payload, unit, status,
             period, reference, methodology, observed_at) in normalized:
            if storage == "scalar":
                old = connection.execute(
                    """SELECT value,unit,observation_period,value_status,source_reference,
                              source_version,methodology,retrieved_at,import_id
                       FROM current_statistics WHERE game_id=? AND statistic_key=?""", (gid, key)
                ).fetchone()
                expected = (number, unit, period, status, reference, source_version,
                            methodology, retrieved_at, import_id)
                if old is not None:
                    if tuple(old) != expected:
                        raise GameDataImportError(f"Conflicting scalar observation for {gid}/{key}")
                    continue
                connection.execute(
                    """INSERT INTO current_statistics
                       (game_id,statistic_key,value,unit,observed_at,observation_period,value_status,
                        source_reference,source_version,methodology,retrieved_at,import_id)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (gid,key,number,unit,observed_at,period,status,reference,source_version,
                     methodology,retrieved_at,import_id),
                )
            else:
                old = connection.execute(
                    """SELECT payload_json,observation_period,value_status,source_reference,
                              source_version,methodology,retrieved_at,import_id
                       FROM selected_game_data WHERE game_id=? AND data_category='wp1_5' AND data_key=?""",
                    (gid,key),
                ).fetchone()
                expected = (payload,period,status,reference,source_version,methodology,retrieved_at,import_id)
                if old is not None:
                    if tuple(old) != expected:
                        raise GameDataImportError(f"Conflicting structured observation for {gid}/{key}")
                    continue
                connection.execute(
                    """INSERT INTO selected_game_data
                       (game_id,data_category,data_key,payload_json,import_id,value_status,observation_period,
                        source_reference,source_version,methodology,retrieved_at)
                       VALUES(?,'wp1_5',?,?,?,?,?,?,?,?,?)""",
                    (gid,key,payload,import_id,status,period,reference,source_version,methodology,retrieved_at),
                )
            inserted += 1
        connection.commit()
        return {"import_id": int(import_id), "country_mappings": len(crosswalk.mappings),
                "observations": len(normalized), "inserted_observations": inserted,
                "idempotent": inserted == 0}
    except Exception:
        connection.rollback()
        raise



def import_wp1_5_snapshot(
    connection: sqlite3.Connection,
    *,
    manifest_path: str | Path,
    crosswalk_path: str | Path,
    observations: Iterable[dict[str, Any]],
    contract_path: str | Path,
) -> dict[str, int | bool]:
    """Verify captured raw bytes against their acquisition manifest, then import."""
    import hashlib

    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GameDataImportError(f"Cannot read acquisition manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("manifest_schema_version") != 1:
        raise GameDataImportError("Unsupported source acquisition manifest")
    if manifest.get("work_package") != "WP1.5":
        raise GameDataImportError("Acquisition manifest is not a WP1.5 snapshot")
    dataset = _text(manifest.get("source_key"), "manifest.source_key")
    source_version = _text(manifest.get("release"), "manifest.release")
    source_url = _text(manifest.get("final_url") or manifest.get("source_url"), "manifest.final_url")
    retrieved_at = _timestamp(manifest.get("retrieved_at"), "manifest.retrieved_at")
    sha256 = manifest.get("sha256")
    if not isinstance(sha256, str) or not _SHA.fullmatch(sha256):
        raise GameDataImportError("manifest.sha256 must be a lowercase SHA-256")
    raw_path_value = _text(manifest.get("local_raw_path"), "manifest.local_raw_path")
    raw_path = Path(raw_path_value)
    try:
        digest = hashlib.sha256()
        byte_count = 0
        with raw_path.open("rb") as raw_file:
            while chunk := raw_file.read(1024 * 1024):
                digest.update(chunk)
                byte_count += len(chunk)
    except OSError as exc:
        raise GameDataImportError(f"Cannot read acquired raw snapshot: {exc}") from exc
    if digest.hexdigest() != sha256:
        raise GameDataImportError("Raw snapshot SHA-256 does not match acquisition manifest")
    if manifest.get("byte_count") != byte_count:
        raise GameDataImportError("Raw snapshot byte count does not match acquisition manifest")
    return _import_wp1_5_data(
        connection,
        dataset=dataset,
        source_version=source_version,
        source_url=source_url,
        sha256=sha256,
        retrieved_at=retrieved_at,
        crosswalk_path=crosswalk_path,
        observations=observations,
        contract_path=contract_path,
        attribution=manifest.get("attribution"),
        license_text=manifest.get("license_status"),
    )
