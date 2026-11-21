from __future__ import annotations

import json

from tools.database.connection import connect_database
from tools.database.schema import apply_migrations


def test_country_iso_identity_separates_official_and_proposed_codes(tmp_path):
    database = tmp_path / "canonical.sqlite"
    connection = connect_database(database)
    try:
        apply_migrations(connection)
        now = "2026-11-21T00:00:00Z"
        candidate_id = "tc_" + "1" * 32
        verified_id = "tc_" + "2" * 32
        connection.execute(
            """INSERT INTO countries (
                game_id, entity_type, record_status, iso_alpha2, iso_alpha3,
                iso_assignment_status, localization_status, created_at, updated_at
            ) VALUES (?, 'unreviewed', 'approved', 'PS', 'PSE',
                      'unverified', 'unreviewed', ?, ?)""",
            (candidate_id, now, now),
        )
        connection.execute(
            """INSERT INTO review_proposals (
                game_id, proposal_type, proposal_fingerprint, proposed_json,
                evidence_json, review_status, created_at
            ) VALUES (?, 'iso', ?, ?, '{}', 'candidate', ?)""",
            (
                candidate_id, "a" * 64,
                json.dumps({"alpha2": "PS", "alpha3": "PSE"}),
                now,
            ),
        )
        connection.execute(
            """INSERT INTO countries (
                game_id, entity_type, record_status, iso_alpha2, iso_alpha3,
                iso_assignment_status, localization_status, created_at, updated_at
            ) VALUES (?, 'unreviewed', 'approved', 'TW', 'TWN',
                      'verified', 'unreviewed', ?, ?)""",
            (verified_id, now, now),
        )
        connection.commit()

        candidate = connection.execute(
            "SELECT * FROM country_iso_identity WHERE game_id=?", (candidate_id,)
        ).fetchone()
        assert candidate["official_iso_alpha2"] is None
        assert candidate["official_iso_alpha3"] is None
        assert candidate["proposed_iso_alpha2"] == "PS"
        assert candidate["proposed_iso_alpha3"] == "PSE"
        assert candidate["iso_proposal_status"] == "candidate"

        verified = connection.execute(
            "SELECT * FROM country_iso_identity WHERE game_id=?", (verified_id,)
        ).fetchone()
        assert verified["official_iso_alpha2"] == "TW"
        assert verified["official_iso_alpha3"] == "TWN"
        assert verified["iso_proposal_id"] is None
    finally:
        connection.close()
