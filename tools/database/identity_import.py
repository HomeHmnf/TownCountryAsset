"""Transactional import of the persistent identity registry and source provenance."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.connection import REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database

DEFAULT_REGISTRY_PATH = REPOSITORY_ROOT / "config" / "country_identity_registry.json"
DEFAULT_CANDIDATE_DIR = REPOSITORY_ROOT / "generated" / "town_country_asset_candidate"


class IdentityImportError(RuntimeError):
    """Raised when identity inputs cannot be imported without ambiguity."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityImportError(f"Cannot read JSON input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise IdentityImportError(f"Expected a JSON object in {path}")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdentityImportError(f"{label} must be a non-empty string")
    return value


def _validate_inputs(
    registry: dict[str, Any],
    candidate: dict[str, Any],
    source_manifest: dict[str, Any],
    countries_path: Path,
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    if registry.get("schema_version") != 1:
        raise IdentityImportError("Unsupported identity registry schema_version")
    dataset = _require_text(registry.get("dataset"), "registry.dataset")
    if registry.get("status") not in {"proposal", "candidate", "approved"}:
        raise IdentityImportError("Unsupported identity registry status")
    source = candidate.get("source")
    if not isinstance(source, dict):
        raise IdentityImportError("Candidate countries.json has no source metadata")
    if source_manifest.get("source") != source:
        raise IdentityImportError("Candidate source metadata does not match manifest.json")
    if source.get("archive_sha256") is None:
        raise IdentityImportError("Candidate source archive_sha256 is missing")
    archive_sha = _require_text(source.get("archive_sha256"), "source.archive_sha256")
    if len(archive_sha) != 64 or any(c not in "0123456789abcdef" for c in archive_sha):
        raise IdentityImportError("source.archive_sha256 must be a lowercase SHA-256")
    if candidate.get("schema_version") != 1:
        raise IdentityImportError("Unsupported candidate countries schema_version")
    records = registry.get("records")
    countries = candidate.get("countries")
    if not isinstance(records, list) or not isinstance(countries, list):
        raise IdentityImportError("Registry records and candidate countries must be arrays")
    if candidate.get("count") != len(countries):
        raise IdentityImportError("Candidate count does not match its countries array")
    manifest_files = source_manifest.get("files")
    country_manifest = manifest_files.get("countries.json") if isinstance(manifest_files, dict) else None
    expected_hash = country_manifest.get("sha256") if isinstance(country_manifest, dict) else None
    actual_hash = hashlib.sha256(countries_path.read_bytes()).hexdigest()
    if expected_hash != actual_hash:
        raise IdentityImportError("Candidate countries.json checksum does not match manifest.json")
    if len(records) != len(countries):
        raise IdentityImportError(
            f"Registry/candidate record count mismatch: {len(records)} != {len(countries)}"
        )

    by_source: dict[str, dict[str, Any]] = {}
    game_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise IdentityImportError("Registry contains a non-object record")
        game_id = _require_text(record.get("game_id"), "record.game_id")
        if len(game_id) != 35 or not game_id.startswith("tc_") or any(
            c not in "0123456789abcdef" for c in game_id[3:]
        ):
            raise IdentityImportError(f"Invalid persistent game_id: {game_id!r}")
        if game_id in game_ids:
            raise IdentityImportError(f"Duplicate game_id in registry: {game_id}")
        game_ids.add(game_id)
        record_source = record.get("source")
        if not isinstance(record_source, dict) or record_source.get("dataset") != dataset:
            raise IdentityImportError(f"Invalid source dataset for {game_id}")
        source_id = _require_text(record_source.get("current_source_id"), f"{game_id}.current_source_id")
        if source_id in by_source:
            raise IdentityImportError(f"Duplicate current source ID in registry: {source_id}")
        previous = record_source.get("previous_source_ids")
        if not isinstance(previous, list) or any(not isinstance(x, str) or not x.strip() for x in previous):
            raise IdentityImportError(f"Invalid previous_source_ids for {game_id}")
        if source_id in previous or len(previous) != len(set(previous)):
            raise IdentityImportError(f"Duplicate current/historical source ID for {game_id}")
        names = record.get("names")
        if not isinstance(names, dict):
            raise IdentityImportError(f"Missing names object for {game_id}")
        _require_text(names.get("en"), f"{game_id}.names.en")
        if not isinstance(names.get("aliases_en"), list) or any(
            not isinstance(x, str) or not x.strip() for x in names["aliases_en"]
        ):
            raise IdentityImportError(f"Invalid English aliases for {game_id}")
        if not isinstance(record.get("regions"), list) or any(
            not isinstance(x, str) or not x.strip() for x in record["regions"]
        ):
            raise IdentityImportError(f"Invalid regions for {game_id}")
        iso = record.get("iso")
        if not isinstance(iso, dict):
            raise IdentityImportError(f"Missing ISO object for {game_id}")
        by_source[source_id] = record

    candidate_by_source: dict[str, dict[str, Any]] = {}
    for country in countries:
        if not isinstance(country, dict):
            raise IdentityImportError("Candidate contains a non-object country")
        source_id = _require_text(country.get("id"), "candidate country.id")
        if source_id in candidate_by_source:
            raise IdentityImportError(f"Duplicate candidate source ID: {source_id}")
        candidate_by_source[source_id] = country
    if set(by_source) != set(candidate_by_source):
        missing = sorted(set(by_source) - set(candidate_by_source))
        extra = sorted(set(candidate_by_source) - set(by_source))
        raise IdentityImportError(f"Registry/candidate source coverage mismatch; missing={missing}, extra={extra}")

    for source_id, record in by_source.items():
        country = candidate_by_source[source_id]
        if country.get("game_id") != record["game_id"]:
            raise IdentityImportError(f"game_id mismatch for source ID {source_id}")
        if country.get("name") != record["names"]["en"]:
            raise IdentityImportError(f"English canonical name mismatch for source ID {source_id}")
        if country.get("aliases", []) != record["names"]["aliases_en"]:
            raise IdentityImportError(f"English alias mismatch for source ID {source_id}")
        if country.get("regions", []) != record["regions"]:
            raise IdentityImportError(f"Region membership mismatch for source ID {source_id}")
        if country.get("iso3") != record["iso"].get("alpha3"):
            raise IdentityImportError(f"ISO alpha-3 candidate mismatch for source ID {source_id}")

    return dataset, records, source


def _ensure_country(connection: sqlite3.Connection, record: dict[str, Any], now: str) -> None:
    game_id = record["game_id"]
    iso = record["iso"]
    names = record["names"]
    expected = (
        record.get("entity_type") or "unreviewed",
        "candidate",
        iso.get("alpha2"),
        iso.get("alpha3"),
        iso.get("assignment_status", "unverified"),
        names.get("localization_status", "unreviewed"),
    )
    existing = connection.execute(
        """SELECT entity_type, record_status, iso_alpha2, iso_alpha3,
                  iso_assignment_status, localization_status
           FROM countries WHERE game_id = ?""",
        (game_id,),
    ).fetchone()
    if existing is None:
        connection.execute(
            """INSERT INTO countries (
                game_id, entity_type, record_status, iso_alpha2, iso_alpha3,
                iso_assignment_status, localization_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (game_id, *expected, now, now),
        )
    elif tuple(existing) != expected:
        raise IdentityImportError(f"Existing country record conflicts with registry for {game_id}")


def _ensure_source(
    connection: sqlite3.Connection,
    game_id: str,
    dataset: str,
    source_id: str,
    is_current: int,
    import_id: int,
) -> None:
    existing = connection.execute(
        """SELECT is_current, import_id FROM country_sources
           WHERE game_id = ? AND dataset = ? AND source_id = ?""",
        (game_id, dataset, source_id),
    ).fetchone()
    expected = (is_current, import_id)
    if existing is None:
        connection.execute(
            """INSERT INTO country_sources (game_id, dataset, source_id, is_current, import_id)
               VALUES (?, ?, ?, ?, ?)""",
            (game_id, dataset, source_id, is_current, import_id),
        )
    elif tuple(existing) != expected:
        raise IdentityImportError(
            f"Existing source mapping conflicts for {game_id}/{dataset}/{source_id}"
        )


def _ensure_name(
    connection: sqlite3.Connection, game_id: str, language: str, name: str, name_type: str
) -> None:
    existing = connection.execute(
        """SELECT name FROM country_names
           WHERE game_id = ? AND language = ? AND name_type = ?""",
        (game_id, language, name_type),
    ).fetchall()
    if name_type == "canonical" and existing and existing[0]["name"] != name:
        raise IdentityImportError(f"Canonical {language} name conflicts for {game_id}")
    match = connection.execute(
        """SELECT 1 FROM country_names
           WHERE game_id = ? AND language = ? AND name = ? AND name_type = ?""",
        (game_id, language, name, name_type),
    ).fetchone()
    if match is None:
        connection.execute(
            """INSERT INTO country_names (game_id, language, name, name_type)
               VALUES (?, ?, ?, ?)""",
            (game_id, language, name, name_type),
        )


def import_identity_registry(
    database_path: str | Path,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    candidate_dir: str | Path = DEFAULT_CANDIDATE_DIR,
) -> dict[str, int | str]:
    """Import registry identity and source provenance; never approve or infer data."""
    registry_path = Path(registry_path)
    candidate_dir = Path(candidate_dir)
    countries_path = candidate_dir / "countries.json"
    registry = _read_json(registry_path)
    candidate = _read_json(countries_path)
    manifest = _read_json(candidate_dir / "manifest.json")
    dataset, records, source = _validate_inputs(registry, candidate, manifest, countries_path)
    now = _utc_now()
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        archive_sha = source["archive_sha256"]
        imports = connection.execute(
            "SELECT * FROM dataset_imports WHERE dataset = ? AND sha256 = ?",
            (dataset, archive_sha),
        ).fetchall()
        if len(imports) > 1:
            raise IdentityImportError("Multiple dataset_imports rows already exist for this dataset/checksum")
        metadata = (
            source.get("source_version"),
            source.get("url"),
            source.get("retrieval_date"),
            source.get("attribution"),
            source.get("license"),
            "candidate",
        )
        if imports:
            import_id = int(imports[0]["import_id"])
            actual = tuple(imports[0][key] for key in (
                "source_version", "source_url", "retrieval_date", "attribution", "license", "import_status"
            ))
            if actual != metadata:
                raise IdentityImportError("Existing dataset provenance conflicts with candidate manifest")
        else:
            cursor = connection.execute(
                """INSERT INTO dataset_imports (
                    dataset, source_version, source_url, retrieval_date, sha256,
                    attribution, license, import_status, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (dataset, *metadata[:4], archive_sha, metadata[4], metadata[5], now),
            )
            import_id = int(cursor.lastrowid)

        source_count = 0
        name_count = 0
        region_count = 0
        for record in records:
            _ensure_country(connection, record, now)
            current_id = record["source"]["current_source_id"]
            _ensure_source(connection, record["game_id"], dataset, current_id, 1, import_id)
            source_count += 1
            for previous_id in record["source"]["previous_source_ids"]:
                _ensure_source(connection, record["game_id"], dataset, previous_id, 0, import_id)
                source_count += 1
            _ensure_name(connection, record["game_id"], "en", record["names"]["en"], "canonical")
            name_count += 1
            for alias in dict.fromkeys(record["names"]["aliases_en"]):
                _ensure_name(connection, record["game_id"], "en", alias, "alias")
                name_count += 1
            for region in dict.fromkeys(record["regions"]):
                connection.execute(
                    """INSERT OR IGNORE INTO country_regions (game_id, region, classification_source)
                       VALUES (?, ?, 'config/regions.json')""",
                    (record["game_id"], region),
                )
                region_count += 1

        issues = validate_database(connection)
        if issues:
            raise IdentityImportError("Database validation failed: " + "; ".join(issues))
        connection.commit()
        return {
            "dataset": dataset,
            "import_id": import_id,
            "countries": len(records),
            "source_mappings": source_count,
            "names": name_count,
            "region_memberships": region_count,
        }
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
