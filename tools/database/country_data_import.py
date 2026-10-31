"""Transactional import of Natural Earth attributes and game-ID geometries."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from tools.database.connection import REPOSITORY_ROOT, connect_database
from tools.database.schema import validate_database

DEFAULT_CANDIDATE_DIR = REPOSITORY_ROOT / "generated" / "town_country_asset_candidate"
PROFILES = ("low", "medium", "high")
INPUT_FILES = (
    "countries.json",
    "geometry_game_id_low.json",
    "geometry_game_id_medium.json",
    "geometry_game_id_high.json",
)


class CountryDataImportError(RuntimeError):
    """Raised when candidate metadata or geometry cannot be imported safely."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CountryDataImportError(f"Cannot read JSON input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CountryDataImportError(f"Expected a JSON object in {path}")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _attribute_value(value: Any, label: str) -> tuple[str | None, str]:
    if value is None:
        return None, "null"
    if isinstance(value, bool):
        return ("true" if value else "false"), "boolean"
    if isinstance(value, int):
        return str(value), "integer"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CountryDataImportError(f"{label} contains a non-finite number")
        return repr(value), "real"
    if isinstance(value, str):
        return value, "text"
    if isinstance(value, (dict, list)):
        try:
            return _canonical_json(value), "json"
        except (TypeError, ValueError) as exc:
            raise CountryDataImportError(f"{label} is not valid JSON data: {exc}") from exc
    raise CountryDataImportError(f"{label} has unsupported value type {type(value).__name__}")


def _load_and_validate(candidate_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    countries_path = candidate_dir / "countries.json"
    manifest = _read_json(candidate_dir / "manifest.json")
    countries_payload = _read_json(countries_path)
    if countries_payload.get("schema_version") != 1:
        raise CountryDataImportError("Unsupported countries.json schema_version")
    countries = countries_payload.get("countries")
    if not isinstance(countries, list) or countries_payload.get("count") != len(countries):
        raise CountryDataImportError("Candidate countries count does not match its countries array")

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise CountryDataImportError("manifest.json files must be an object")
    payloads: dict[str, dict[str, Any]] = {"countries.json": countries_payload}
    for filename in INPUT_FILES:
        path = candidate_dir / filename
        entry = files.get(filename)
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            raise CountryDataImportError(f"manifest.json has no checksum for {filename}")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise CountryDataImportError(f"Cannot read candidate input {path}: {exc}") from exc
        if _sha256_bytes(raw) != entry["sha256"]:
            raise CountryDataImportError(f"Candidate {filename} checksum does not match manifest.json")
        if filename != "countries.json":
            try:
                decoded = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CountryDataImportError(f"Invalid JSON in {filename}: {exc}") from exc
            if not isinstance(decoded, dict):
                raise CountryDataImportError(f"{filename} must contain a JSON object")
            payloads[filename] = decoded

    if manifest.get("schema_version") != 1:
        raise CountryDataImportError("Unsupported candidate manifest schema_version")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise CountryDataImportError("Candidate manifest source metadata is missing")
    archive_sha = source.get("archive_sha256")
    if not isinstance(archive_sha, str) or len(archive_sha) != 64 or any(
        char not in "0123456789abcdef" for char in archive_sha
    ):
        raise CountryDataImportError("Manifest source archive_sha256 must be a lowercase SHA-256")

    by_game_id: dict[str, dict[str, Any]] = {}
    by_source_id: set[str] = set()
    for country in countries:
        if not isinstance(country, dict):
            raise CountryDataImportError("Candidate contains a non-object country")
        game_id = country.get("game_id")
        source_id = country.get("id")
        if not isinstance(game_id, str) or len(game_id) != 35 or not game_id.startswith("tc_") or any(
            char not in "0123456789abcdef" for char in game_id[3:]
        ):
            raise CountryDataImportError(f"Invalid or missing candidate game_id: {game_id!r}")
        if not isinstance(source_id, str) or not source_id.strip():
            raise CountryDataImportError(f"Invalid or missing source ID for {game_id}")
        if game_id in by_game_id:
            raise CountryDataImportError(f"Duplicate candidate game_id: {game_id}")
        if source_id in by_source_id:
            raise CountryDataImportError(f"Duplicate candidate source ID: {source_id}")
        if not isinstance(country.get("source_attributes"), dict):
            raise CountryDataImportError(f"Missing source_attributes object for {game_id}")
        if not isinstance(country.get("source_geometry_type"), str) or not country["source_geometry_type"]:
            raise CountryDataImportError(f"Missing source_geometry_type for {game_id}")
        by_game_id[game_id] = country
        by_source_id.add(source_id)

    for profile in PROFILES:
        filename = f"geometry_game_id_{profile}.json"
        payload = payloads[filename]
        if payload.get("schema_version") != 1 or payload.get("profile") != profile or payload.get("key") != "game_id":
            raise CountryDataImportError(f"{filename} has an unexpected schema, profile, or key mode")
        geometries = payload.get("geometries")
        if not isinstance(geometries, dict):
            raise CountryDataImportError(f"{filename} geometries must be an object")
        if set(geometries) != set(by_game_id):
            missing = sorted(set(by_game_id) - set(geometries))
            extra = sorted(set(geometries) - set(by_game_id))
            raise CountryDataImportError(
                f"{filename} game_id coverage mismatch; missing={missing}, extra={extra}"
            )
        for game_id, geometry in geometries.items():
            if not isinstance(geometry, dict) or geometry.get("type") not in {
                "Point", "MultiPoint", "LineString", "MultiLineString",
                "Polygon", "MultiPolygon", "GeometryCollection",
            }:
                raise CountryDataImportError(f"{filename} has invalid GeoJSON geometry for {game_id}")
            try:
                _canonical_json(geometry)
            except (TypeError, ValueError) as exc:
                raise CountryDataImportError(f"{filename} has invalid geometry JSON for {game_id}: {exc}") from exc

    return manifest, countries_payload, payloads


def import_country_data(
    database_path: str | Path,
    candidate_dir: str | Path = DEFAULT_CANDIDATE_DIR,
) -> dict[str, int | str]:
    """Import all source attributes and low/medium/high geometries without promotion."""
    candidate_dir = Path(candidate_dir)
    manifest, countries_payload, payloads = _load_and_validate(candidate_dir)
    source = manifest["source"]
    archive_sha = source["archive_sha256"]
    dataset = source.get("dataset") or "natural_earth_admin_0"
    if not isinstance(dataset, str) or not dataset.strip():
        raise CountryDataImportError("Manifest dataset must be a non-empty string")

    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        imports = connection.execute(
            "SELECT * FROM dataset_imports WHERE dataset = ? AND sha256 = ?",
            (dataset, archive_sha),
        ).fetchall()
        if len(imports) != 1:
            raise CountryDataImportError(
                f"Expected exactly one WP1.2 dataset_imports row for {dataset}/{archive_sha}; found {len(imports)}"
            )
        import_row = imports[0]
        expected_provenance = (
            source.get("source_version"), source.get("url"), source.get("retrieval_date"),
            source.get("attribution"), source.get("license"),
        )
        actual_provenance = tuple(import_row[key] for key in (
            "source_version", "source_url", "retrieval_date", "attribution", "license"
        ))
        if actual_provenance != expected_provenance:
            raise CountryDataImportError("Manifest source provenance conflicts with the WP1.2 dataset import")
        import_id = int(import_row["import_id"])

        current_sources = connection.execute(
            "SELECT game_id, source_id FROM country_sources WHERE dataset = ? AND is_current = 1",
            (dataset,),
        ).fetchall()
        source_to_game = {row["source_id"]: row["game_id"] for row in current_sources}
        if len(source_to_game) != len(current_sources):
            raise CountryDataImportError(f"Database has duplicate current source IDs for {dataset}")

        countries = countries_payload["countries"]
        candidate_source_to_game = {country["id"]: country["game_id"] for country in countries}
        if candidate_source_to_game != source_to_game:
            missing = sorted(set(source_to_game) - set(candidate_source_to_game))
            extra = sorted(set(candidate_source_to_game) - set(source_to_game))
            conflicts = sorted(
                source_id for source_id in set(source_to_game) & set(candidate_source_to_game)
                if source_to_game[source_id] != candidate_source_to_game[source_id]
            )
            raise CountryDataImportError(
                f"Candidate/database identity coverage mismatch; missing={missing}, extra={extra}, conflicts={conflicts}"
            )

        attribute_count = 0
        geometry_count = 0
        for game_id, country in sorted(
            ((item["game_id"], item) for item in countries), key=lambda pair: pair[0]
        ):
            attributes = dict(country["source_attributes"])
            if "source_geometry_type" in attributes:
                raise CountryDataImportError(
                    f"Reserved attribute key source_geometry_type is present in source attributes for {game_id}"
                )
            attributes["source_geometry_type"] = country["source_geometry_type"]
            for key, value in sorted(attributes.items()):
                if not isinstance(key, str) or not key.strip():
                    raise CountryDataImportError(f"Invalid attribute key for {game_id}: {key!r}")
                stored_value, value_type = _attribute_value(value, f"{game_id}.{key}")
                existing = connection.execute(
                    "SELECT attribute_value, value_type FROM country_attributes WHERE game_id = ? AND attribute_key = ?",
                    (game_id, key),
                ).fetchone()
                expected = (stored_value, value_type)
                if existing is None:
                    connection.execute(
                        """INSERT INTO country_attributes (game_id, attribute_key, attribute_value, value_type)
                           VALUES (?, ?, ?, ?)""",
                        (game_id, key, stored_value, value_type),
                    )
                elif tuple(existing) != expected:
                    raise CountryDataImportError(f"Existing country attribute conflicts for {game_id}/{key}")
                attribute_count += 1

            for profile in PROFILES:
                geometry = payloads[f"geometry_game_id_{profile}.json"]["geometries"][game_id]
                geometry_json = _canonical_json(geometry)
                geometry_sha = _sha256_bytes(geometry_json.encode("utf-8"))
                existing = connection.execute(
                    "SELECT geometry_json, sha256, import_id FROM country_geometries WHERE game_id = ? AND profile = ?",
                    (game_id, profile),
                ).fetchone()
                expected = (geometry_json, geometry_sha, import_id)
                if existing is None:
                    connection.execute(
                        """INSERT INTO country_geometries (game_id, profile, geometry_json, sha256, import_id)
                           VALUES (?, ?, ?, ?, ?)""",
                        (game_id, profile, geometry_json, geometry_sha, import_id),
                    )
                elif tuple(existing) != expected:
                    raise CountryDataImportError(f"Existing geometry conflicts for {game_id}/{profile}")
                geometry_count += 1

        issues = validate_database(connection)
        if issues:
            raise CountryDataImportError("Database validation failed: " + "; ".join(issues))
        connection.commit()
        return {
            "dataset": dataset,
            "import_id": import_id,
            "countries": len(countries),
            "attributes": attribute_count,
            "geometry_profiles": len(PROFILES),
            "geometries": geometry_count,
        }
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
