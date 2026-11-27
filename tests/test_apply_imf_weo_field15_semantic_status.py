from __future__ import annotations

import sqlite3

import pytest

from tools import apply_imf_weo_field15_semantic_status as apply


def make_connection(*, status: str = "unclassified", source_sha: str = "b" * 64):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE imf_weo_historical_observations (
            observation_id INTEGER PRIMARY KEY,
            game_id TEXT NOT NULL,
            source_country_code TEXT NOT NULL,
            source_country_name TEXT NOT NULL,
            indicator_code TEXT NOT NULL,
            field_id INTEGER NOT NULL,
            observation_year INTEGER NOT NULL,
            value REAL NOT NULL,
            value_status TEXT NOT NULL,
            latest_actual_annual_data TEXT,
            reporting_year_months TEXT,
            source_version TEXT NOT NULL,
            source_sha256 TEXT NOT NULL
        );
        CREATE TABLE dataset_imports (
            import_id INTEGER PRIMARY KEY,
            dataset TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            import_status TEXT NOT NULL
        );
        """
    )
    connection.execute(
        """INSERT INTO imf_weo_historical_observations VALUES
           (1, ?, 'AAA', 'Example', 'NGDPD', 15, 2025, 1.5, ?, '2025',
            'January/December', ?, ?)""",
        ("tc_" + "a" * 32, status, apply.SOURCE_VERSION, source_sha),
    )
    connection.execute(
        "INSERT INTO dataset_imports VALUES (3, 'world_economic_outlook', ?, 'candidate')",
        (apply.DEFAULT_SOURCE_SHA256,),
    )
    return connection


def proposal_row():
    return {
        "game_id": "tc_" + "a" * 32,
        "source_country_code": "AAA",
        "source_country_name": "Example",
        "indicator_code": "NGDPD",
        "field_id": 15,
        "observation_year": 2025,
        "value": 1.5,
        "current_value_status": "unclassified",
        "proposed_value_status": "observed",
        "latest_actual_annual_data": "2025",
        "reporting_year_months": "January/December",
        "cutoff_year": 2025,
        "classification_rule": "integer_latest_actual_year",
        "source_sha256": apply.DEFAULT_SOURCE_SHA256,
    }


def test_database_preflight_accepts_exact_unclassified_row(monkeypatch):
    monkeypatch.setattr(apply, "EXPECTED_ROWS", 1)
    monkeypatch.setattr(apply, "DEFAULT_SOURCE_SHA256", "b" * 64)
    connection = make_connection()
    try:
        result = apply.verify_database(connection, [proposal_row()])
        assert result["rows"] == 1
        assert result["all_unclassified"] is True
        assert result["dataset_import_status"] == "candidate"
        assert result["integrity"] == "ok"
        assert result["foreign_keys"] == "ok"
    finally:
        connection.close()


def test_database_preflight_rejects_already_classified_row(monkeypatch):
    monkeypatch.setattr(apply, "EXPECTED_ROWS", 1)
    monkeypatch.setattr(apply, "DEFAULT_SOURCE_SHA256", "b" * 64)
    connection = make_connection(status="observed")
    try:
        with pytest.raises(apply.SemanticApplyError, match="not unclassified"):
            apply.verify_database(connection, [proposal_row()])
    finally:
        connection.close()


def test_database_preflight_rejects_source_checksum_mismatch(monkeypatch):
    monkeypatch.setattr(apply, "EXPECTED_ROWS", 1)
    monkeypatch.setattr(apply, "DEFAULT_SOURCE_SHA256", "b" * 64)
    connection = make_connection(source_sha="c" * 64)
    try:
        with pytest.raises(apply.SemanticApplyError, match="coverage mismatch"):
            apply.verify_database(connection, [proposal_row()])
    finally:
        connection.close()


def test_database_preflight_rejects_extra_release_rows(monkeypatch):
    monkeypatch.setattr(apply, "EXPECTED_ROWS", 1)
    monkeypatch.setattr(apply, "DEFAULT_SOURCE_SHA256", "b" * 64)
    connection = make_connection()
    connection.execute(
        """INSERT INTO imf_weo_historical_observations VALUES
           (2, ?, 'BBB', 'Other', 'NGDPD', 15, 2024, 2.5, 'unclassified',
            '2024', 'January/December', ?, ?)""",
        ("tc_" + "c" * 32, apply.SOURCE_VERSION, "c" * 64),
    )
    try:
        with pytest.raises(apply.SemanticApplyError, match="release row count"):
            apply.verify_database(connection, [proposal_row()])
    finally:
        connection.close()


def test_proposal_loader_rejects_unapproved_fingerprint(tmp_path):
    (tmp_path / "classification_proposals.csv").write_text("not,the,approved,proposal\n")
    (tmp_path / "summary.json").write_text("{}")
    (tmp_path / "owner_semantic_approval.md").write_text("APPROVED")
    with pytest.raises(apply.SemanticApplyError, match="SHA-256"):
        apply.load_approved_proposal(tmp_path)
