from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.build_imf_weo_wdi_review_package import (
    ReviewPackageError,
    build_package,
    write_package,
)


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "game_id": "tc_bahrain", "country_name": "Bahrain", "field_id": "21",
        "year": "2016", "identity_gate": "identity_review_required",
        "semantic_disposition": "diagnostic_review_required_not_approved",
        "field_gate": "confirm_imf_unit_population_reference_period_and_method",
        "country_case_id": "bahrain_reference_period_settled",
        "country_case_disposition": "settled_likely_reference_period_mismatch_do_not_reopen",
        "evidence_documents": "docs/data-sources/bahrain-unemployment-series-assessment.md",
        "imf_observation_status": "actual_per_weo_metadata",
        "wdi_observation_status": "wdi_actual_estimate_status_not_established",
    }
    return {**row, **overrides}


def _input(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_build_package_has_one_decision_surface_and_linked_edge_cases(tmp_path: Path) -> None:
    source = tmp_path / "semantic.csv"
    _input(source, [_row(), _row(game_id="tc_bahrain2", country_name="Bahrain II")])
    rows, cases, summary = build_package(source)

    assert len(rows) == 2
    assert all(row["review_decision"] == "pending" for row in rows)
    assert all(row["review_row_id"] and row["edge_case_ids"] for row in rows)
    assert {case["category"] for case in cases} >= {
        "identity", "field_semantics", "country_case", "comparison_status",
    }
    assert all(case["affected_row_ids"] for case in cases)
    assert summary["review_authority"] == "review_register.csv"
    assert summary["edge_case_role"] == "linked_work_queue_not_a_separate_decision_surface"
    assert summary["approval_created"] is False
    assert summary["database_written"] is False


def test_build_package_rejects_duplicate_country_field_year(tmp_path: Path) -> None:
    source = tmp_path / "semantic.csv"
    _input(source, [_row(), _row()])
    with pytest.raises(ReviewPackageError, match="Duplicate"):
        build_package(source)


def test_write_package_writes_fingerprinted_review_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "semantic.csv"
    _input(source, [_row()])
    rows, cases, summary = build_package(source)
    target = write_package(rows, cases, summary, tmp_path / "out")
    payload = json.loads((target / "package.json").read_text(encoding="utf-8"))
    assert payload["candidate_is_approved"] is False
    assert payload["review_register_sha256"]
    with (target / "review_register.csv").open(encoding="utf-8", newline="") as stream:
        reviewed = list(csv.DictReader(stream))
    assert reviewed[0]["review_decision"] == "pending"
    assert (target / "edge_cases.csv").is_file()
    assert (target / "README.md").is_file()


def test_build_package_rejects_missing_contract_columns(tmp_path: Path) -> None:
    source = tmp_path / "semantic.csv"
    source.write_text("game_id,field_id\nx,21\n", encoding="utf-8")
    with pytest.raises(ReviewPackageError, match="missing required columns"):
        build_package(source)
