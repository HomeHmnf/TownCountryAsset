from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools import build_imf_weo_field15_semantic_review as review


def test_integer_cutoff_is_inclusive():
    assert review.latest_actual_cutoff("2025") == (2025, "integer_latest_actual_year")


def test_zero_means_all_estimated():
    assert review.latest_actual_cutoff("0") == (0, "zero_means_all_estimated")


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ("FY2024/25", (2025, "fiscal_year_ending_year")),
        ("FY2025/26", (2026, "fiscal_year_ending_year")),
        ("FY2099/00", (2100, "fiscal_year_ending_year")),
    ],
)
def test_fiscal_year_uses_ending_year(metadata, expected):
    assert review.latest_actual_cutoff(metadata) == expected


@pytest.mark.parametrize("metadata", ["", "FY2024/2025", "FY2024/26", "n/a"])
def test_invalid_or_blank_metadata_fails_closed(metadata):
    with pytest.raises(review.SemanticReviewError):
        review.latest_actual_cutoff(metadata)


def _write_candidate(tmp_path: Path, source: Path, *, metadata: str = "FY2024/25",
                     candidate_value: str = "10") -> Path:
    source_hash = review.sha256(source)
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    observations = candidate / "observations.csv"
    fields = [
        "game_id", "source_country_code", "source_country_name", "indicator_code",
        "field_id", "observation_year", "value", "value_status",
        "latest_actual_annual_data", "reporting_year_months", "source_sha256",
    ]
    rows = [
        ["tc_" + "a" * 32, "AAA", "Example", "NGDPD", 15, 2024, candidate_value,
         "unclassified", metadata, "April/March", source_hash],
        ["tc_" + "a" * 32, "AAA", "Example", "NGDPD", 15, 2025, "11",
         "unclassified", metadata, "April/March", source_hash],
        ["tc_" + "a" * 32, "AAA", "Example", "NGDPD", 15, 2026, "12",
         "unclassified", metadata, "April/March", source_hash],
    ]
    with observations.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)
    (candidate / "candidate.json").write_text(json.dumps({
        "candidate_type": "imf_weo_annual_historical_observations",
        "field_ids": [15],
        "source_sha256": source_hash,
        "observations_sha256": review.sha256(observations),
        "observation_count": 3,
    }), encoding="utf-8")
    return candidate


def _write_source(path: Path, metadata: str = "FY2024/25") -> Path:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "SERIES_CODE", "COUNTRY", "FREQUENCY", "LATEST_ACTUAL_ANNUAL_DATA",
            "START_END_MONTHS_OF_REPORTING_YEAR", "2024", "2025", "2026",
        ])
        writer.writerow(["AAA.NGDPD.A", "Example", "Annual", metadata,
                         "April/March", "10", "11", "12"])
        for code in sorted(review.AGGREGATE_CODES):
            writer.writerow([f"{code}.NGDPD.A", code, "Annual", "2025",
                             "January/December", "1", "", ""])
    return path


def test_build_review_reconciles_source_and_candidate_and_never_projects(tmp_path, monkeypatch):
    source = _write_source(tmp_path / "source.csv")
    candidate = _write_candidate(tmp_path, source)
    monkeypatch.setattr(review, "EXPECTED_SERIES", 1)
    monkeypatch.setattr(review, "EXPECTED_OBSERVATIONS", 3)
    monkeypatch.setattr(review, "EXPECTED_AGGREGATE_VALUES", 13)
    proposals, report = review.build_review(source, candidate, verify_snapshot=False)
    assert [row["proposed_value_status"] for row in proposals] == [
        "observed", "observed", "estimated"
    ]
    assert [row["cutoff_year"] for row in proposals] == [2025, 2025, 2025]
    assert report["proposed_status_counts"] == {"estimated": 1, "observed": 2}
    assert report["projected_status_count"] == 0
    assert report["database_written"] is False
    assert report["approval_created"] is False
    assert report["complete"] is True


def test_build_review_rejects_candidate_value_mismatch(tmp_path, monkeypatch):
    source = _write_source(tmp_path / "source.csv")
    candidate = _write_candidate(tmp_path, source, candidate_value="999")
    monkeypatch.setattr(review, "EXPECTED_SERIES", 1)
    monkeypatch.setattr(review, "EXPECTED_OBSERVATIONS", 3)
    with pytest.raises(review.SemanticReviewError, match="Raw/candidate value mismatch"):
        review.build_review(source, candidate, verify_snapshot=False)


def test_build_review_rejects_non_unclassified_candidate_status(tmp_path, monkeypatch):
    source = _write_source(tmp_path / "source.csv")
    candidate = _write_candidate(tmp_path, source)
    observations = candidate / "observations.csv"
    text = observations.read_text(encoding="utf-8").replace("unclassified", "observed", 1)
    observations.write_text(text, encoding="utf-8")
    summary_path = candidate / "candidate.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["observations_sha256"] = review.sha256(observations)
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(review, "EXPECTED_SERIES", 1)
    monkeypatch.setattr(review, "EXPECTED_OBSERVATIONS", 3)
    with pytest.raises(review.SemanticReviewError, match="must remain unclassified"):
        review.build_review(source, candidate, verify_snapshot=False)
