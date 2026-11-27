from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.manage_imf_weo_field16_owner_review import (
    OwnerReviewError,
    build_owner_review,
    validate_owner_decisions,
    write_owner_review,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture(tmp_path: Path) -> tuple[Path, Path]:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    registry_path = tmp_path / "registry.json"
    registry_records = []
    proposals = []
    for index in range(242):
        code = f"C{index:03d}"
        record = {
            "game_id": f"game-{index:03d}",
            "source": {"current_source_id": code, "previous_source_ids": []},
            "status": "proposed",
            "entity_type": "unreviewed",
            "iso": {"alpha2": None, "alpha3": code, "assignment_status": "unverified"},
            "names": {"en": f"Country {code}", "aliases_en": []},
            "regions": ["Test Region"],
            "geometry_key": code,
        }
        registry_records.append(record)
        if index < 195:
            proposals.append({
                "source_id": code,
                "source_name": f"Country {code}" if index != 0 else "Different Source Name",
                "series_code": f"{code}.NGDPDPC.A",
                "populated_year_count": "52",
                "first_populated_year": "1980",
                "last_populated_year": "2031",
                "candidate_line_number": str(index + 2),
                "candidate_exception": "unmapped_or_ambiguous_identity",
                "proposed_game_id": record["game_id"],
                "registry_name": record["names"]["en"],
                "registry_status": record["status"],
                "registry_entity_type": record["entity_type"],
                "proposal_basis": "exact_unique_registry_current_source_id_match_only",
                "decision": "PENDING",
                "approved_game_id": "-",
                "owner_rationale": "",
                "batch": f"{index // 20 + 1:02d}",
            })
    registry_path.write_text(json.dumps({"records": registry_records}), encoding="utf-8")
    proposals_path = input_dir / "identity_proposals.csv"
    write_csv(proposals_path, proposals)
    unresolved_path = input_dir / "unresolved_identities.csv"
    write_csv(unresolved_path, [{"source_id": "SSD", "decision": "HOLD"}, {"source_id": "WBG", "decision": "HOLD"}])
    manifest = {
        "field_id": 16,
        "indicator_code": "NGDPDPC",
        "source_release": "october_2026",
        "review_directory": "input",
        "identity_proposals_sha256": digest(proposals_path),
        "unresolved_identities_sha256": digest(unresolved_path),
        "registry_sha256": digest(registry_path),
        "database_written": False,
        "approval_created": False,
    }
    (input_dir / "review_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return input_dir, registry_path


def test_build_enriches_identity_evidence_and_flags_review_risks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.manage_imf_weo_field16_owner_review as module

    input_dir, registry_path = fixture(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    rows, metadata = build_owner_review(input_dir, registry_path)

    assert len(rows) == 195
    assert rows[0]["name_comparison"] == "name_difference_requires_review"
    assert "source_registry_name_difference" in rows[0]["manual_review_flags"]
    assert "registry_status_not_approved" in rows[0]["manual_review_flags"]
    assert rows[1]["name_comparison"] == "exact_normalized_match"
    assert rows[1]["registry_iso_assignment_status"] == "unverified"
    assert rows[0]["owner_decision"] == ""
    assert metadata["approval_created"] is False
    assert metadata["database_written"] is False


def test_decision_validator_requires_complete_evidence_and_keeps_no_write_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.manage_imf_weo_field16_owner_review as module

    input_dir, registry_path = fixture(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    rows, metadata = build_owner_review(input_dir, registry_path)
    review_dir = write_owner_review(rows, metadata, tmp_path / "owner-review")
    path = review_dir / "owner_review.csv"

    with pytest.raises(OwnerReviewError, match="Missing or invalid owner decision"):
        validate_owner_decisions(review_dir)

    edited = list(rows)
    for row in edited:
        row["owner_decision"] = "APPROVE"
        row["approved_game_id"] = row["proposed_game_id"]
        row["owner_rationale"] = "Reviewed against cited primary identity evidence"
        row["owner_evidence_reference"] = "https://example.invalid/source"
    write_csv(path, edited)
    payload = validate_owner_decisions(review_dir)
    assert payload["decision_counts"] == {"APPROVE": 195, "REJECT": 0, "HOLD": 0}
    assert payload["approval_created"] is False
    assert payload["database_written"] is False

    edited[0]["proposed_game_id"] = "tampered-game-id"
    write_csv(path, edited)
    with pytest.raises(OwnerReviewError, match="Immutable identity evidence changed"):
        validate_owner_decisions(review_dir)


def test_approve_requires_exact_target_and_evidence_reference(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.manage_imf_weo_field16_owner_review as module

    input_dir, registry_path = fixture(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    rows, metadata = build_owner_review(input_dir, registry_path)
    review_dir = write_owner_review(rows, metadata, tmp_path / "owner-review")
    edited = list(rows)
    for row in edited:
        row["owner_decision"] = "APPROVE"
        row["approved_game_id"] = row["proposed_game_id"]
        row["owner_rationale"] = "Identity evidence reviewed"
        row["owner_evidence_reference"] = "primary source"
    edited[0]["owner_evidence_reference"] = ""
    write_csv(review_dir / "owner_review.csv", edited)
    with pytest.raises(OwnerReviewError, match="requires an evidence reference"):
        validate_owner_decisions(review_dir)


def test_build_includes_existing_source_scoped_mappings_and_identity_decisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.manage_imf_weo_field16_owner_review as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    input_dir, registry_path = fixture(tmp_path)
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    payloads = {
        "wdi": {
            "dataset": "world_bank_wdi",
            "review_approval": {"status": "approved", "scope": "WDI crosswalk only", "approval_record": "wdi-review.md"},
            "mappings": [{"source_id": "C000", "game_id": "game-000", "source_name": "Country C000", "match_method": "reviewed_manual", "evidence_url": "https://example.invalid/wdi"}],
        },
        "wpp": {
            "dataset": "un_wpp",
            "review_approval": {"status": "approved", "scope": "UN WPP crosswalk only", "approval_record": "wpp-review.md"},
            "mappings": [{"source_id": "999", "game_id": "game-000", "source_name": "Country C000", "match_method": "reviewed_manual", "evidence_url": "https://example.invalid/wpp"}],
            "mapping_policy": {},
        },
        "icp": {
            "dataset": "world_bank_icp",
            "review_approval": {"status": "pending", "scope": "ICP candidate only"},
            "mappings": [{"source_country_code": "C000", "game_id": "game-000", "source_country_name": "Country C000", "review_status": "pending", "match_method": "candidate"}],
        },
        "imf_weo": {
            "dataset": "imf_weo",
            "review_approval": {"status": "approved", "scope": "Field 15 NGDPD only", "approval_record": "imf-field15.md"},
            "mappings": [
                {"source_id": "C000", "game_id": "game-000", "source_name": "Country C000", "match_method": "reviewed_manual"},
                {"source_id": "WBG", "game_id": "game-999", "source_name": "West Bank and Gaza", "match_method": "reviewed_manual"},
            ],
        },
        "edge_cases": {
            "policy_version": "identity-edge-review-v1",
            "reviewed_at": "2026-11-20T00:00:00Z",
            "records": [{
                "source_id": "C000", "game_id": "game-000", "name": "Country C000",
                "iso": {"assignment_status": "verified"},
                "entity": {"entity_type": "country"},
                "catalogue": {"decision_status": "approved"},
                "naming": {"decision_status": "approved", "aliases_en": ["C000"]},
            }],
        },
    }
    paths = {}
    for key, payload in payloads.items():
        path = history_dir / f"{key}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[key] = path

    rows, metadata = build_owner_review(input_dir, registry_path, paths)
    first = rows[0]
    mappings = json.loads(first["existing_project_source_mappings"])
    decisions = json.loads(first["prior_project_identity_decision"])

    assert {item["dataset"] for item in mappings} == {"world_bank_wdi", "un_wpp", "world_bank_icp", "imf_weo"}
    imf = next(item for item in mappings if item["dataset"] == "imf_weo")
    assert imf["approval_status"] == "approved"
    assert imf["approval_scope"] == "Field 15 NGDPD only"
    assert imf["proposal_game_id_match"] == "same_game_id"
    assert next(item for item in mappings if item["dataset"] == "world_bank_icp")["approval_status"] == "pending"
    assert decisions["catalogue"]["decision_status"] == "approved"
    assert decisions["proposal_game_id_match"] == "same_game_id"
    assert metadata["crosswalk_game_id_conflict_rows"] == 0
    wbg = next(item for item in metadata["unresolved_identity_history_rows"] if item["source_id"] == "WBG")
    wbg_mapping = json.loads(wbg["existing_project_source_mappings"])[0]
    assert wbg_mapping["approval_scope"] == "Field 15 NGDPD only"
    assert metadata["unresolved_identity_count"] == 2

    review_dir = write_owner_review(rows, metadata, tmp_path / "owner-review")
    unresolved_csv = list(csv.DictReader((review_dir / "unresolved_identity_history.csv").open(encoding="utf-8")))
    assert len(unresolved_csv) == 2
    assert json.loads(next(item for item in unresolved_csv if item["source_id"] == "WBG")["existing_project_source_mappings"])[0]["approval_scope"] == "Field 15 NGDPD only"
    assert metadata["identity_history_policy"].startswith("source-scoped review evidence only")
    with (review_dir / "unresolved_identity_history.csv").open("a", encoding="utf-8") as stream:
        stream.write("tampered\\n")
    with pytest.raises(OwnerReviewError, match="Unresolved identity history checksum mismatch"):
        validate_owner_decisions(review_dir)
    assert set(metadata["identity_history_files"]) == set(paths)
    assert metadata["approval_created"] is False
    assert metadata["database_written"] is False
