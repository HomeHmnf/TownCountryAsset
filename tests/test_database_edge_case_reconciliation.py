from __future__ import annotations

import json
from pathlib import Path

from tools.database.connection import connect_database
from tools.database.edge_case_reconciliation import apply_reconciliation
from tools.database.identity_import import _ensure_country
from tools.database.schema import apply_migrations

IDS = {
    "FLK": "tc_815eb2563fde4a4cb077173220e2a533",
    "TWN": "tc_98ab3dee1d554162b6bbd5dac6374fc8",
    "SOL": "tc_9a78f2eebcc24906a5c67581c0c3895e",
    "KOS": "tc_28aa17b84db24952b92fc51b421075e0",
    "CYN": "tc_d3e7f81572fd44ab920bfc066d592873",
    "IOA": "tc_7cd2130353a64e57bd3782773a8e12c7",
    "ATC": "tc_b61ca098adb74efc84564fd9fa800bf8",
    "KAS": "tc_644aaabf37604038996e34c1bc91c970",
}
NAMES = {
    "FLK": "Falkland Islands", "TWN": "Taiwan", "SOL": "Somaliland",
    "KOS": "Kosovo", "CYN": "Northern Cyprus",
    "IOA": "Indian Ocean Territories", "ATC": "Ashmore and Cartier Islands",
    "KAS": "Siachen Glacier",
}
TYPES = {
    "FLK": "dependent_territory", "TWN": "disputed_or_partially_recognized_entity",
    "SOL": "disputed_or_partially_recognized_entity", "KOS": "disputed_or_partially_recognized_entity",
    "CYN": "disputed_or_partially_recognized_entity", "IOA": "dependent_territory",
    "ATC": "dependent_territory", "KAS": "geographic_feature",
}
FLAGS = {"FLK": "fk", "TWN": "tw", "KOS": "xk"}


def fixture_data():
    registry = {"schema_version": 1, "dataset": "natural_earth_admin_0", "records": []}
    decisions = {"schema_version": 1, "policy_version": "identity-edge-case-reconciliation-2026-11-20", "records": []}
    flag_rows = []
    for source_id, gid in IDS.items():
        name = NAMES[source_id]
        registry["records"].append({
            "game_id": gid,
            "source": {"dataset": "natural_earth_admin_0", "current_source_id": source_id},
            "names": {
                "en": name, "fa": None, "aliases_en": [], "aliases_fa": [],
                "localization_status": "unreviewed",
            },
            "iso": {
                "alpha2": None,
                "alpha3": {"FLK": "FLK", "TWN": "TWN"}.get(source_id),
                "assignment_status": "unverified",
            },
            "entity_type": "unreviewed",
            "regions": [],
        })
        iso_verified = source_id in {"FLK", "TWN"}
        iso = {
            "alpha2": {"FLK": "FK", "TWN": "TW"}.get(source_id),
            "alpha3": {"FLK": "FLK", "TWN": "TWN"}.get(source_id),
            "assignment_status": "verified" if iso_verified else "not_applicable",
            "decision_code": "official_iso_assignment" if iso_verified else "no_official_iso_assignment",
            "reference_name": name,
            "evidence": [{"url": "https://example.org/iso", "note": "fixture evidence"}],
        }
        flag_status = "approved" if source_id in FLAGS else (
            "unresolved" if source_id in {"SOL", "CYN"} else "not_applicable"
        )
        flag = {
            "decision_status": flag_status,
            "decision_code": "source_flag_asset" if source_id in FLAGS else "no_flag_asset",
            "source_flag_code": FLAGS.get(source_id),
            "evidence": ["https://example.org/flags"],
        }
        if source_id == "ATC":
            flag.update({"decision_status": "approved", "decision_code": "parent_flag_fallback",
                         "parent_game_id": "tc_270a6ecb902d4ea1ac7373b3d1a3b2cc"})
        catalogue = {
            "decision_status": "excluded" if source_id == "KAS" else "approved",
            "decision_code": "retire_geographic_feature" if source_id == "KAS" else "retain_entity",
            "rationale": "fixture decision",
        }
        decisions["records"].append({
            "game_id": gid, "source_id": source_id, "name": name,
            "iso": iso,
            "entity": {"entity_type": TYPES[source_id], "evidence": [{"url": "https://example.org/entity"}]},
            "flag": flag,
            "catalogue": catalogue,
            "naming": {"decision_status": "approved", "decision_code": "retain_name", "aliases_en": []},
        })
        flag_rows.append({
            "game_id": gid, "source_flag_code": FLAGS.get(source_id),
            "status": "reviewed" if source_id in FLAGS else (
                "unreviewed" if source_id in {"SOL", "CYN"} else "rejected"
            ),
        })
    taxonomy = {"types": {name: {} for name in set(TYPES.values())}}
    flags_payload = {"records": flag_rows}
    return registry, decisions, taxonomy, flags_payload


def seed_database(path: Path, registry):
    connection = connect_database(path)
    try:
        apply_migrations(connection)
        connection.execute(
            """INSERT INTO dataset_imports(dataset, sha256, import_status, imported_at)
               VALUES ('natural_earth_admin_0', ?, 'candidate', '2026-11-20T00:00:00Z')""",
            ("a" * 64,),
        )
        import_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """INSERT INTO application_approvals
               (approval_id, domain, artifact_sha256, artifact_json, status, created_at,
                approved_by, approved_at)
               VALUES ('edge-case-test-001', 'test', ?, '{}', 'approved',
                       '2026-11-20T00:00:00Z', 'project-owner', '2026-11-20T00:00:00Z')""",
            ("b" * 64,),
        )
        for record in registry["records"]:
            gid = record["game_id"]
            source_id = record["source"]["current_source_id"]
            connection.execute(
                """INSERT INTO countries
                   (game_id, entity_type, record_status, iso_assignment_status,
                    localization_status, created_at, updated_at)
                   VALUES (?, 'unreviewed', 'approved', 'unverified', 'unreviewed',
                           '2026-11-20T00:00:00Z', '2026-11-20T00:00:00Z')""",
                (gid,),
            )
            connection.execute(
                """INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id)
                   VALUES (?, 'natural_earth_admin_0', ?, 1, ?)""",
                (gid, source_id, import_id),
            )
            connection.execute(
                """INSERT INTO country_flags(game_id, source_flag_code, mapping_status)
                   VALUES (?, NULL, 'candidate')""", (gid,)
            )
            for kind in ("iso", "entity_type", "flag"):
                connection.execute(
                    """INSERT INTO review_proposals
                       (game_id, proposal_type, proposal_fingerprint, proposed_json,
                        evidence_json, review_status, created_at)
                       VALUES (?, ?, ?, '{}', '[]', 'candidate', '2026-11-20T00:00:00Z')""",
                    (gid, kind, (str(len(kind)) * 64)[:64]),
                )
        # The reviewed source-code mappings already have approved proposals,
        # as they would after the WP1.4 review-data import.
        for source_id in FLAGS:
            gid = IDS[source_id]
            connection.execute(
                """INSERT INTO review_proposals
                   (game_id, proposal_type, proposal_fingerprint, proposed_json,
                    evidence_json, review_status, created_at, reviewed_at)
                   VALUES (?, 'flag', ?, ?, '{}', 'approved',
                           '2026-11-20T00:00:00Z', '2026-11-20T00:00:00Z')""",
                (gid, ("c" * 64), json.dumps({"source_flag_code": FLAGS[source_id]})),
            )
            connection.execute(
                "UPDATE country_flags SET source_flag_code=?, mapping_status='reviewed' WHERE game_id=?",
                (FLAGS[source_id], gid),
            )
        for source_id in ("IOA", "ATC", "KAS"):
            connection.execute(
                "UPDATE country_flags SET mapping_status='rejected' WHERE game_id=?",
                (IDS[source_id],),
            )
        connection.commit()
    finally:
        connection.close()


def test_reconciliation_records_explicit_decisions_and_retires_siachen(tmp_path: Path):
    registry, decisions, taxonomy, flags_payload = fixture_data()
    database = tmp_path / "canonical.sqlite"
    seed_database(database, registry)

    connection = connect_database(database)
    try:
        result = apply_reconciliation(
            connection, registry, decisions, taxonomy, flags_payload,
            actor="project-owner", approval_id="edge-case-test-001",
            now="2026-11-20T12:00:00Z",
        )
        connection.commit()
        assert result == {
            "records": 8, "decisions": 40, "iso_verified": 2,
            "iso_not_applicable": 6, "entity_types_approved": 8,
            "flags_resolved": 6, "flags_unresolved": 2, "retired": 1,
        }
        assert connection.execute("SELECT COUNT(*) FROM country_review_decisions").fetchone()[0] == 40
        assert tuple(connection.execute(
            "SELECT iso_alpha2, iso_alpha3, iso_assignment_status FROM countries WHERE game_id=?",
            (IDS["TWN"],),
        ).fetchone()) == ("TW", "TWN", "verified")
        assert tuple(connection.execute(
            "SELECT iso_alpha2, iso_alpha3, iso_assignment_status FROM countries WHERE game_id=?",
            (IDS["KOS"],),
        ).fetchone()) == (None, None, "not_applicable")
        assert tuple(connection.execute(
            "SELECT entity_type, record_status, entity_type_status FROM countries WHERE game_id=?",
            (IDS["KAS"],),
        ).fetchone()) == ("geographic_feature", "retired", "reviewed")
        assert tuple(connection.execute(
            "SELECT source_flag_code, mapping_status FROM country_flags WHERE game_id=?",
            (IDS["KOS"],),
        ).fetchone()) == ("xk", "reviewed")
        assert tuple(connection.execute(
            "SELECT source_flag_code, mapping_status FROM country_flags WHERE game_id=?",
            (IDS["SOL"],),
        ).fetchone()) == (None, "candidate")
        assert connection.execute(
            "SELECT COUNT(*) FROM country_review_decisions WHERE decision_status='unresolved'"
        ).fetchone()[0] == 2
        # A later identity-registry re-import must preserve approved edge decisions.
        for record in registry["records"]:
            _ensure_country(connection, record, "2026-11-20T12:00:00Z")
    finally:
        connection.close()



def test_reconciliation_ignores_current_source_mappings_from_other_datasets(tmp_path: Path):
    registry, decisions, taxonomy, flags_payload = fixture_data()
    database = tmp_path / "canonical.sqlite"
    seed_database(database, registry)

    connection = connect_database(database)
    try:
        connection.execute(
            """INSERT INTO dataset_imports(dataset, sha256, import_status, imported_at)
               VALUES ('un_wpp', ?, 'candidate', '2026-11-20T00:00:00Z')""",
            ("d" * 64,),
        )
        wpp_import_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id)
               VALUES (?, 'un_wpp', '158', 1, ?)""",
            (IDS["TWN"], wpp_import_id),
        )

        result = apply_reconciliation(
            connection, registry, decisions, taxonomy, flags_payload,
            actor="project-owner", approval_id="edge-case-test-001",
            now="2026-11-20T12:00:00Z",
        )
        assert result["records"] == 8
    finally:
        connection.close()

def test_reconciliation_is_idempotent_for_the_same_decisions(tmp_path: Path):
    registry, decisions, taxonomy, flags_payload = fixture_data()
    database = tmp_path / "canonical.sqlite"
    seed_database(database, registry)
    connection = connect_database(database)
    try:
        kwargs = {
            "actor": "project-owner", "approval_id": "edge-case-test-001",
            "now": "2026-11-20T12:00:00Z",
        }
        apply_reconciliation(connection, registry, decisions, taxonomy, flags_payload, **kwargs)
        apply_reconciliation(connection, registry, decisions, taxonomy, flags_payload, **kwargs)
        assert connection.execute("SELECT COUNT(*) FROM country_review_decisions").fetchone()[0] == 40
    finally:
        connection.close()
