from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.database import imf_weo_import as importer
from tools.database.application_approval import build_application_artifact
from tools.database.connection import connect_database
from tools.database.schema import apply_migrations


def _package(root: Path):
    candidate = root / "candidate"
    candidate.mkdir()
    source = root / "weo.csv"
    source.write_text("immutable test source", encoding="utf-8")
    identity = root / "identity.json"
    identity.write_text("{}", encoding="utf-8")
    migration = root / "008.sql"
    migration.write_text("-- test migration dependency", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    headers = [
        "game_id", "source_country_code", "source_country_name", "indicator_code",
        "field_id", "observation_year", "value", "unit", "scale", "value_status",
        "latest_actual_annual_data", "reporting_year_months", "source_reference",
        "source_version", "source_sha256", "acquired_on", "acquisition_time_precision",
    ]
    row = [
        "tc_" + "a" * 32, "AAA", "Example", "NGDPD", "15", "2024", "12.5",
        "US dollar", "Billions", "unclassified", "2023", "January/December",
        importer.SOURCE_URL, importer.RELEASE, source_hash, importer.ACQUIRED_ON, "day",
    ]
    observations = candidate / "observations.csv"
    with observations.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerow(row)
    exceptions = candidate / "identity_exceptions.csv"
    exceptions.write_text("line_number,exception\n", encoding="utf-8")
    summary = {
        "candidate_type": "imf_weo_annual_historical_observations",
        "source_sha256": source_hash,
        "source_byte_count": source.stat().st_size,
        "source_path": "weo.csv",
        "identity_registry_path": "identity.json",
        "observations_sha256": hashlib.sha256(observations.read_bytes()).hexdigest(),
        "exceptions_sha256": hashlib.sha256(exceptions.read_bytes()).hexdigest(),
        "observation_count": 1,
    }
    (candidate / "candidate.json").write_text(json.dumps(summary), encoding="utf-8")
    return candidate, source, identity, migration


def test_candidate_package_checksums_and_provenance(tmp_path, monkeypatch):
    candidate, source, identity, migration = _package(tmp_path)
    monkeypatch.setattr(importer, "REPOSITORY_ROOT", tmp_path)
    rows, summary, inputs = importer._load_candidate(candidate, source, identity, migration)
    assert len(rows) == 1
    assert rows[0]["value_status"] == "unclassified"
    assert rows[0]["unit"] == "US dollar"
    assert len(inputs) == 6
    (candidate / "observations.csv").write_text("changed", encoding="utf-8")
    with pytest.raises(importer.WEOImportError, match="observations.csv checksum"):
        importer._load_candidate(candidate, source, identity, migration)


def test_candidate_package_rejects_missing_units_only_if_not_preserved(tmp_path, monkeypatch):
    candidate, source, identity, migration = _package(tmp_path)
    monkeypatch.setattr(importer, "REPOSITORY_ROOT", tmp_path)
    path = candidate / "observations.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    rows[0]["unit"] = ""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    exceptions = candidate / "identity_exceptions.csv"
    summary = json.loads((candidate / "candidate.json").read_text())
    summary["observations_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (candidate / "candidate.json").write_text(json.dumps(summary))
    result, _, _ = importer._load_candidate(candidate, source, identity, migration)
    assert result[0]["unit"] is None


def test_migration_allows_multiple_release_vintages():
    connection = connect_database(":memory:")
    try:
        apply_migrations(connection)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(imf_weo_historical_observations)")}
        assert {"source_version", "value_status", "unit", "import_id"} <= columns
        indexes = connection.execute("PRAGMA index_list(imf_weo_historical_observations)").fetchall()
        unique_indexes = [row["name"] for row in indexes if row["unique"]]
        assert unique_indexes
        for name in unique_indexes:
            cols = [row["name"] for row in connection.execute(f'PRAGMA index_info("{name}")')]
            if cols:
                assert "source_version" in cols
    finally:
        connection.close()
