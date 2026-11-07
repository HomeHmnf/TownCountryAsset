from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.build_imf_weo_wdi_decision_readiness import assess, write_report


def _rows() -> list[dict[str, str]]:
    rows = []
    for field_id in ("15", "16", "18", "20", "21"):
        rows.append({
            "game_id": "bhr",
            "country_name": "Bahrain",
            "field_id": field_id,
            "year": "2025",
            "identity_gate": "identity_review_required",
            "coverage_status": "both_sources_present",
            "imf_observation_status": "actual_per_weo_metadata",
            "wdi_observation_status": "wdi_actual_estimate_status_not_established",
            "year_evidence_scope": "no_country_case_year_scope",
            "country_case_id": ("bahrain_reference_period_settled" if field_id == "21" else "no_specific_country_case_recorded"),
        })
    return rows


def test_assessment_keeps_all_fields_blocked_by_identity_and_semantics(tmp_path: Path) -> None:
    source = tmp_path / "matrix.csv"
    rows = _rows()
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = assess(source)
    assert result["row_count"] == 5
    assert result["country_count"] == 1
    assert result["decision"] == "not_ready_for_source_policy_change_or_canonical_application"
    assert result["identity_gate_counts"] == {"identity_review_required": 5}
    assert len(result["field_assessments"]) == 5
    assert all(item["readiness"] == "blocked_semantic_and_identity_gates" for item in result["field_assessments"])
    assert result["approval_created"] is False
    assert result["policy_changed"] is False
    assert result["game_database_written"] is False


def test_report_writes_machine_and_human_decision_queues(tmp_path: Path) -> None:
    source = tmp_path / "matrix.csv"
    rows = _rows()
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = assess(source)
    target = write_report(result, tmp_path / "reports")
    payload = json.loads((target / "decision_readiness.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "not_ready_for_source_policy_change_or_canonical_application"
    assert (target / "decision_readiness.md").is_file()
    assert (target / "field_decision_queue.csv").is_file()
    case_queue = target / "country_case_decision_queue.csv"
    assert case_queue.is_file()
    with case_queue.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert "year_scopes" not in (reader.fieldnames or [])
        case_rows = list(reader)
    assert len(case_rows) == 1
    assert case_rows[0]["case_id"] == "bahrain_reference_period_settled"
    assert case_rows[0]["years_with_bounded_evidence"] == ""
