from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.database import application_approval
from tools.database.connection import connect_database
from tools.database.schema import apply_migrations
from tools import bulk_approve_country_reviews as bulk


GAME_ID = "tc_" + "a" * 32
OTHER_ID = "tc_" + "b" * 32


@pytest.fixture
def review_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(application_approval, "REPOSITORY_ROOT", tmp_path)
    registry = tmp_path / "registry.json"
    registry.write_text('{"schema_version":1,"dataset":"natural_earth_admin_0","records":[]}', encoding="utf-8")
    database = tmp_path / "canonical.sqlite"
    connection = connect_database(database)
    apply_migrations(connection)
    connection.execute(
        """INSERT INTO dataset_imports(dataset, sha256, import_status, imported_at)
           VALUES ('natural_earth_admin_0', ?, 'candidate', '2026-11-01T00:00:00Z')""",
        ("c" * 64,),
    )
    import_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    for gid, source_id, name in ((GAME_ID, "AAA", "Alpha"), (OTHER_ID, "BBB", "Beta")):
        connection.execute(
            """INSERT INTO countries(game_id, entity_type, record_status, created_at, updated_at)
               VALUES (?, 'unreviewed', 'candidate', 'now', 'now')""",
            (gid,),
        )
        connection.execute(
            """INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id)
               VALUES (?, 'natural_earth_admin_0', ?, 1, ?)""",
            (gid, source_id, import_id),
        )
        connection.execute(
            """INSERT INTO country_names(game_id, language, name, name_type)
               VALUES (?, 'en', ?, 'canonical')""",
            (gid, name),
        )
    connection.execute(
        """INSERT INTO review_proposals
           (game_id, proposal_type, proposal_fingerprint, proposed_json, evidence_json,
            review_status, created_at)
           VALUES (?, 'iso', ?, ?, ?, 'candidate', 'now')""",
        (GAME_ID, "1" * 64, json.dumps({"alpha2": "AA", "alpha3": "AAA"}),
         json.dumps({"source_url": "https://example.test/iso.csv", "evidence": ["reviewed"]})),
    )
    connection.commit()
    connection.close()
    return database, registry


def test_bulk_approval_dry_run_does_not_write(review_db):
    database, registry = review_db
    result = bulk.bulk_approve(
        database, registry, approve_records=True, proposal_types={"iso"}
    )
    assert result["status"] == "dry_run"
    assert result["record_candidates_eligible"] == 2
    assert result["proposal_candidates_eligible"] == 1
    assert result["database_written"] is False
    connection = connect_database(database)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM countries WHERE record_status='candidate'"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT review_status FROM review_proposals WHERE proposal_type='iso'"
        ).fetchone()[0] == "candidate"
    finally:
        connection.close()


def test_bulk_approval_applies_records_and_iso_atomically(review_db):
    database, registry = review_db
    result = bulk.bulk_approve(
        database, registry, approve_records=True, proposal_types={"iso"},
        actor="owner", note="Previously reviewed country identities and ISO assignments.",
        apply=True, confirm_reviewed=True,
    )
    assert result["status"] == "applied"
    assert result["approved_record_count"] == 2
    assert result["approved_proposal_counts"] == {"iso": 1}
    connection = connect_database(database)
    try:
        rows = connection.execute(
            "SELECT record_status, iso_alpha2, iso_alpha3, iso_assignment_status FROM countries WHERE game_id=?",
            (GAME_ID,),
        ).fetchone()
        assert tuple(rows) == ("approved", "AA", "AAA", "verified")
        assert connection.execute(
            "SELECT record_status FROM countries WHERE game_id=?", (OTHER_ID,)
        ).fetchone()[0] == "approved"
        assert connection.execute(
            "SELECT review_status, reviewed_at FROM review_proposals WHERE proposal_type='iso'"
        ).fetchone()[0] == "approved"
        events = connection.execute(
            "SELECT event_type FROM database_application_events ORDER BY event_id"
        ).fetchall()
        assert [row[0] for row in events] == ["proposed", "approved", "applied"]
    finally:
        connection.close()


def test_apply_requires_explicit_attestation_and_reviewer(review_db):
    database, registry = review_db
    with pytest.raises(bulk.BulkApprovalError, match="--confirm-reviewed"):
        bulk.bulk_approve(
            database, registry, approve_records=True, apply=True,
            actor="owner", note="Reviewed",
        )


def test_iso_candidate_without_pair_remains_unapproved(review_db):
    database, registry = review_db
    connection = connect_database(database)
    connection.execute(
        """INSERT INTO review_proposals
           (game_id, proposal_type, proposal_fingerprint, proposed_json, evidence_json,
            review_status, created_at)
           VALUES (?, 'iso', ?, ?, '{}', 'candidate', 'now')""",
        (OTHER_ID, "2" * 64, json.dumps({"alpha2": None, "alpha3": None})),
    )
    connection.commit()
    connection.close()
    result = bulk.bulk_approve(
        database, registry, proposal_types={"iso"},
        actor="owner", note="Reviewed ISO candidates.",
        apply=True, confirm_reviewed=True,
    )
    assert result["approved_proposal_counts"] == {"iso": 1}
    assert result["skipped"]["iso_missing_or_invalid_iso_pair"] == 1
    connection = connect_database(database)
    try:
        assert connection.execute(
            "SELECT iso_assignment_status FROM countries WHERE game_id=?", (OTHER_ID,)
        ).fetchone()[0] == "unverified"
        assert connection.execute(
            "SELECT review_status FROM review_proposals WHERE game_id=?", (OTHER_ID,)
        ).fetchone()[0] == "candidate"
    finally:
        connection.close()
