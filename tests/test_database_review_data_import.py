from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.database.connection import connect_database
from tools.database.review_data_import import ReviewDataImportError, import_review_data
from tools.database.schema import apply_migrations
from tools.propose_iso_assignments import propose, read_reference, render_report


GAME_ID = "tc_" + "a" * 32


def write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def fixture_inputs(tmp_path: Path) -> dict[str, Path]:
    registry = {
        "schema_version": 1,
        "dataset": "natural_earth_admin_0",
        "status": "candidate",
        "records": [{
            "game_id": GAME_ID,
            "source": {
                "dataset": "natural_earth_admin_0",
                "current_source_id": "AAA",
                "previous_source_ids": [],
            },
            "names": {
                "en": "Alpha",
                "fa": None,
                "aliases_en": [],
                "aliases_fa": [],
                "localization_status": "unreviewed",
            },
            "iso": {"alpha2": None, "alpha3": None, "assignment_status": "unverified"},
            "entity_type": "unreviewed",
            "regions": [],
        }],
    }
    registry_path = write_json(tmp_path / "registry.json", registry)
    taxonomy_path = write_json(tmp_path / "entity_types.json", {
        "schema_version": 1,
        "unreviewed_value": "unreviewed",
        "types": {
            "unreviewed": {
                "definition": "No classification has been approved.",
                "evidence_required": ["classification review required"],
            },
            "sovereign_state": {
                "definition": "Reviewed sovereign state.",
                "evidence_required": ["authoritative status source"],
            },
        },
    })
    reference_path = tmp_path / "iso.csv"
    reference_path.write_text("alpha2,alpha3,english_name\nAA,AAA,Alpha\n", encoding="utf-8")
    reference = read_reference(reference_path)
    report_path = tmp_path / "iso-proposals.md"
    report_path.write_text(render_report(propose(registry, reference), str(reference_path)), encoding="utf-8")
    iso_provenance_path = write_json(tmp_path / "iso-provenance.json", {
        "source_url": "https://example.invalid/iso.csv",
        "source_repository": "example/iso",
        "retrieved_at_utc": "2026-10-01T00:00:00+00:00",
        "raw_sha256": "b" * 64,
        "normalized_reference": str(reference_path),
        "normalized_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "reference_row_count": len(reference),
    })
    persian_path = write_json(tmp_path / "persian-candidates.json", {
        "record_count": 1,
        "candidate_count": 1,
        "rows": [{
            "game_id": GAME_ID, "source_id": "AAA", "english_name": "Alpha",
            "current_persian_name": "", "wikidata_qid": "Q30",
            "candidate_persian_name": "آلفا",
            "candidate_status": "candidate available; human review required",
            "review_status": "unreviewed",
        }],
    })
    persian_provenance_path = write_json(tmp_path / "persian-provenance.json", {
        "source_url": "https://query.wikidata.org/sparql",
        "retrieved_at_utc": "2026-10-01T00:00:00+00:00",
        "raw_sha256": "c" * 64,
        "candidate_snapshot": str(persian_path),
        "candidate_count": 1,
    })
    flag_path = write_json(tmp_path / "flags.json", {
        "schema_version": 1,
        "source": {"repository_url": "https://example.invalid/flags", "license": "MIT"},
        "records": [{
            "game_id": GAME_ID, "source_flag_code": None,
            "status": "unreviewed", "decision_note": None, "evidence": [],
        }],
    })
    return {
        "registry": registry_path, "taxonomy": taxonomy_path,
        "iso_reference": reference_path, "iso_provenance": iso_provenance_path,
        "iso_proposals": report_path, "persian_candidates": persian_path,
        "persian_provenance": persian_provenance_path, "flags": flag_path,
    }


def make_database(path: Path) -> None:
    connection = connect_database(path)
    try:
        apply_migrations(connection)
        connection.execute(
            """INSERT INTO dataset_imports
               (dataset, sha256, import_status, imported_at)
               VALUES ('natural_earth_admin_0', ?, 'candidate', '2026-10-01T00:00:00Z')""",
            ("d" * 64,),
        )
        import_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """INSERT INTO countries
               (game_id, entity_type, record_status, iso_assignment_status,
                localization_status, created_at, updated_at)
               VALUES (?, 'unreviewed', 'candidate', 'unverified', 'unreviewed',
                       '2026-10-01T00:00:00Z', '2026-10-01T00:00:00Z')""",
            (GAME_ID,),
        )
        connection.execute(
            """INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id)
               VALUES (?, 'natural_earth_admin_0', 'AAA', 1, ?)""",
            (GAME_ID, import_id),
        )
        connection.execute(
            """INSERT INTO country_attributes(game_id, attribute_key, attribute_value, value_type)
               VALUES (?, 'WIKIDATAID', 'Q30', 'text')""",
            (GAME_ID,),
        )
    finally:
        connection.close()


def run_import(database: Path, inputs: dict[str, Path]):
    return import_review_data(
        database, inputs["registry"], inputs["iso_reference"],
        inputs["iso_provenance"], inputs["iso_proposals"],
        inputs["persian_candidates"], inputs["persian_provenance"],
        inputs["taxonomy"], inputs["flags"],
    )


def test_imports_review_candidates_without_promoting_or_filling_values(tmp_path: Path):
    inputs = fixture_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    make_database(database)

    result = run_import(database, inputs)
    assert result == {
        "countries": 1, "iso_proposals": 1, "localization_proposals": 1,
        "entity_type_proposals": 0, "flag_proposals": 1, "flag_mappings": 1,
    }
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM review_proposals").fetchone()[0] == 3
        statuses = connection.execute(
            "SELECT proposal_type, review_status FROM review_proposals ORDER BY proposal_type"
        ).fetchall()
        assert [(row[0], row[1]) for row in statuses] == [
            ("flag", "candidate"), ("iso", "candidate"), ("localization", "candidate")
        ]
        country = connection.execute(
            "SELECT iso_assignment_status, localization_status, entity_type_status FROM countries"
        ).fetchone()
        assert tuple(country) == ("unverified", "unreviewed", "unreviewed")
        assert connection.execute("SELECT COUNT(*) FROM country_names WHERE language='fa'").fetchone()[0] == 0
        flag = connection.execute("SELECT source_flag_code, mapping_status FROM country_flags").fetchone()
        assert tuple(flag) == (None, "candidate")
    finally:
        connection.close()


def test_repeat_import_is_idempotent(tmp_path: Path):
    inputs = fixture_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    make_database(database)
    run_import(database, inputs)
    run_import(database, inputs)
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM review_proposals").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM country_flags").fetchone()[0] == 1
    finally:
        connection.close()


def test_rejects_stale_iso_reference_checksum_before_database_write(tmp_path: Path):
    inputs = fixture_inputs(tmp_path)
    inputs["iso_reference"].write_text("alpha2,alpha3,english_name\nBB,BBB,Beta\n", encoding="utf-8")
    database = tmp_path / "canonical.sqlite"
    make_database(database)
    with pytest.raises(ReviewDataImportError, match="checksum"):
        run_import(database, inputs)
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM review_proposals").fetchone()[0] == 0
    finally:
        connection.close()


def test_rejects_persian_identity_mismatch_before_database_write(tmp_path: Path):
    inputs = fixture_inputs(tmp_path)
    payload = json.loads(inputs["persian_candidates"].read_text(encoding="utf-8"))
    payload["rows"][0]["source_id"] = "BBB"
    write_json(inputs["persian_candidates"], payload)
    database = tmp_path / "canonical.sqlite"
    make_database(database)
    with pytest.raises(ReviewDataImportError, match="identity/source mapping mismatch"):
        run_import(database, inputs)
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM review_proposals").fetchone()[0] == 0
    finally:
        connection.close()


def test_rejects_flag_mapping_with_unapproved_reviewed_status(tmp_path: Path):
    inputs = fixture_inputs(tmp_path)
    payload = json.loads(inputs["flags"].read_text(encoding="utf-8"))
    payload["records"][0]["status"] = "reviewed"
    write_json(inputs["flags"], payload)
    database = tmp_path / "canonical.sqlite"
    make_database(database)
    with pytest.raises(ReviewDataImportError, match="reviewed flag mapping requires"):
        run_import(database, inputs)


def test_review_status_triggers_require_matching_approved_proposals(tmp_path: Path):
    database = tmp_path / "schema.sqlite"
    connection = connect_database(database)
    try:
        apply_migrations(connection)
        connection.execute(
            """INSERT INTO countries
               (game_id, entity_type, iso_assignment_status, localization_status,
                created_at, updated_at)
               VALUES (?, 'sovereign_state', 'unverified', 'unreviewed', 'now', 'now')""",
            (GAME_ID,),
        )
        with pytest.raises(sqlite3.IntegrityError, match="approved entity_type proposal"):
            connection.execute(
                "UPDATE countries SET entity_type_status='reviewed' WHERE game_id=?", (GAME_ID,)
            )
        with pytest.raises(sqlite3.IntegrityError, match="approved Persian localization proposal"):
            connection.execute(
                "UPDATE countries SET localization_status='reviewed' WHERE game_id=?", (GAME_ID,)
            )
        with pytest.raises(sqlite3.IntegrityError, match="approved ISO proposal"):
            connection.execute(
                """UPDATE countries SET iso_alpha2='AA', iso_alpha3='AAA',
                   iso_assignment_status='verified' WHERE game_id=?""", (GAME_ID,)
            )
    finally:
        connection.close()


def test_non_unreviewed_entity_type_is_recorded_as_candidate_not_approved(tmp_path: Path):
    inputs = fixture_inputs(tmp_path)
    registry = json.loads(inputs["registry"].read_text(encoding="utf-8"))
    registry["records"][0]["entity_type"] = "sovereign_state"
    write_json(inputs["registry"], registry)
    database = tmp_path / "canonical.sqlite"
    make_database(database)
    connection = connect_database(database)
    try:
        connection.execute("UPDATE countries SET entity_type='sovereign_state' WHERE game_id=?", (GAME_ID,))
    finally:
        connection.close()

    result = run_import(database, inputs)
    assert result["entity_type_proposals"] == 1
    connection = connect_database(database)
    try:
        proposal = connection.execute(
            "SELECT review_status, evidence_json FROM review_proposals WHERE proposal_type='entity_type'"
        ).fetchone()
        assert proposal["review_status"] == "candidate"
        evidence = json.loads(proposal["evidence_json"])
        assert evidence["evidence"] == []
        assert evidence["evidence_required"] == ["authoritative status source"]
        assert connection.execute(
            "SELECT entity_type_status FROM countries WHERE game_id=?", (GAME_ID,)
        ).fetchone()[0] == "unreviewed"
    finally:
        connection.close()
