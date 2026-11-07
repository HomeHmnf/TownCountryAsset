from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.build_imf_weo_wdi_semantic_disposition import (
    DispositionError,
    build_matrix,
    write_outputs,
)


def _candidate(**overrides: str) -> dict[str, str]:
    row = {
        "game_id": "bhr", "country_name": "Bahrain",
        "identity_mapping_status": "mapped_review_required",
        "field_id": "21", "year": "2016", "coverage_status": "both_sources_present",
        "imf_value_canonical_unit": "3.9", "wdi_value_canonical_unit": "5.0",
        "imf_status_hint": "actual_per_weo_metadata",
        "imf_reporting_period_classification": "calendar_year",
        "wdi_status_classification": "not_classified_by_this_comparison",
        "wdi_observation_status": "",
    }
    return {**row, **overrides}


def test_build_matrix_preserves_bahrain_settled_case_and_identity_gate(tmp_path: Path) -> None:
    source = tmp_path / "candidate.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(_candidate()))
        writer.writeheader()
        writer.writerow(_candidate())
    rows, summary = build_matrix(source)
    row = rows[0]
    assert row["country_case_id"] == "bahrain_reference_period_settled"
    assert row["country_case_disposition"] == "settled_likely_reference_period_mismatch_do_not_reopen"
    assert row["identity_gate"] == "identity_review_required"
    assert row["semantic_disposition"] == "diagnostic_review_required_not_approved"
    assert summary["database_written"] is False


def test_build_matrix_keeps_blank_wdi_status_unclassified(tmp_path: Path) -> None:
    source = tmp_path / "candidate.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(_candidate()))
        writer.writeheader()
        writer.writerow(_candidate(field_id="15", country_name="Guinea"))
    rows, _ = build_matrix(source)
    assert rows[0]["wdi_observation_status"] == "wdi_actual_estimate_status_not_established"


def test_build_matrix_rejects_missing_contract_columns(tmp_path: Path) -> None:
    source = tmp_path / "candidate.csv"
    source.write_text("game_id,field_id\nbhr,21\n", encoding="utf-8")
    with pytest.raises(DispositionError, match="missing required columns"):
        build_matrix(source)


def test_write_outputs_creates_matrix_and_summary(tmp_path: Path) -> None:
    rows = [{**_candidate(), "identity_gate": "identity_review_required",
             "concept_disposition": "x", "period_disposition": "x",
             "methodology_disposition": "x", "imf_observation_status": "actual",
             "wdi_observation_status": "unclassified", "country_case_id": "case",
             "country_case_disposition": "open", "field_gate": "gate",
             "evidence_documents": "doc.md", "semantic_disposition": "diagnostic"}]
    summary = {"row_count": 1, "country_count": 1}
    target = write_outputs(rows, summary, tmp_path)
    assert (target / "semantic_disposition_matrix.csv").is_file()
    assert (target / "assessment.md").is_file()
    assert json.loads((target / "assessment.json").read_text())["row_count"] == 1
