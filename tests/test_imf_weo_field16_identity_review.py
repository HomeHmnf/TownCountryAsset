from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.build_imf_weo_field16_identity_review import ReviewBuildError, build_review


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_fixture(tmp_path: Path) -> tuple[Path, Path]:
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    source_path = tmp_path / "weo.csv"
    registry_path = tmp_path / "registry.json"
    codes = [f"C{i:03d}" for i in range(195)] + ["SSD", "WBG"]
    with source_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["SERIES_CODE", "COUNTRY", "1999", "2000"])
        writer.writeheader()
        for code in codes:
            writer.writerow({"SERIES_CODE": f"{code}.NGDPDPC.A", "COUNTRY": f"Country {code}", "1999": "1.0", "2000": ""})
    registry_records = [
        {
            "game_id": f"game-{i:03d}",
            "source": {"current_source_id": f"C{i:03d}"},
            "status": "proposed",
            "entity_type": "unreviewed",
            "names": {"en": f"Country C{i:03d}"},
        }
        for i in range(242)
    ]
    registry_path.write_text(json.dumps({"records": registry_records}), encoding="utf-8")
    exceptions = [
        {
            "line_number": str(i + 2),
            "series_code": f"{code}.NGDPDPC.A",
            "source_country_code": code,
            "exception": "unmapped_or_ambiguous_identity",
            "candidate_game_ids": "",
        }
        for i, code in enumerate(codes)
    ]
    write_csv(candidate_dir / "identity_exceptions.csv", exceptions)
    (candidate_dir / "observations.csv").write_text("\n", encoding="utf-8")
    candidate = {
        "field_ids": [16],
        "observation_count": 0,
        "exception_count": len(exceptions),
        "database_written": False,
        "approval_created": False,
        "release": "october_2026",
        "source_path": source_path.name,
        "source_sha256": digest(source_path),
        "observations_sha256": digest(candidate_dir / "observations.csv"),
        "exceptions_sha256": digest(candidate_dir / "identity_exceptions.csv"),
    }
    (candidate_dir / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")
    # The builder resolves source_path relative to the repository root. Put the
    # fixture source beside the candidate and temporarily use an absolute path
    # rejected by the production relative-path contract; instead patch ROOT below.
    candidate["source_path"] = str(source_path)
    (candidate_dir / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")
    return candidate_dir, registry_path


def test_field16_review_proposes_only_exact_unique_registry_source_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.build_imf_weo_field16_identity_review as module

    candidate_dir, registry_path = make_fixture(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    proposals, unresolved, metadata = build_review(candidate_dir, registry_path)

    assert len(proposals) == 195
    assert len(unresolved) == 2
    assert {row["source_id"] for row in unresolved} == {"SSD", "WBG"}
    assert all(row["decision"] == "PENDING" for row in proposals)
    assert all(row["approved_game_id"] == "-" for row in proposals)
    assert all(row["proposal_basis"] == "exact_unique_registry_current_source_id_match_only" for row in proposals)
    assert all(row["registry_status"] == "proposed" for row in proposals)
    assert [sum(row["batch"] == f"{n:02d}" for row in proposals) for n in range(1, 11)] == [20] * 9 + [15]
    assert all(row["source_name"] and row["populated_year_count"] == 1 for row in proposals)
    assert metadata["database_written"] is False
    assert metadata["approval_created"] is False


def test_field16_review_rejects_candidate_checksum_tampering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.build_imf_weo_field16_identity_review as module

    candidate_dir, registry_path = make_fixture(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    with (candidate_dir / "observations.csv").open("a", encoding="utf-8") as stream:
        stream.write("tampered\n")
    with pytest.raises(ReviewBuildError, match="observations checksum"):
        build_review(candidate_dir, registry_path)
