from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tools.build_imf_weo_field15_identity_review import (
    DEFAULTS,
    ReviewBuildError,
    compile_review_register,
)


def _copy_seed(tmp_path: Path) -> tuple[Path, list[dict[str, str]], list[str]]:
    with DEFAULTS["seed"].open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    target = tmp_path / "seed.csv"
    return target, rows, fields


def _write_seed(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_compiles_all_field15_identity_proposals_without_approval():
    fields, rows, summary = compile_review_register()
    assert len(fields) == 22
    assert len(rows) == 196
    assert summary["proposal_count"] == 195
    assert summary["unique_proposed_game_ids"] == 195
    assert summary["held_source_ids"] == ["KOS"]
    assert summary["approved_game_ids"] == 0
    assert summary["database_written"] is False
    assert summary["registry_modified"] is False
    assert summary["crosswalk_modified"] is False


def test_rejects_proposed_game_id_missing_from_canonical_registry(tmp_path):
    path, rows, fields = _copy_seed(tmp_path)
    proposal = next(row for row in rows if row["review_outcome"] == "proposed_manual_review")
    proposal["reviewed_proposed_game_id"] = "tc_" + "f" * 32
    _write_seed(path, rows, fields)

    with pytest.raises(ReviewBuildError, match="targets unknown game_id"):
        compile_review_register(seed_path=path)


def test_rejects_owner_approval_hidden_in_proposal_seed(tmp_path):
    path, rows, fields = _copy_seed(tmp_path)
    proposal = next(row for row in rows if row["review_outcome"] == "proposed_manual_review")
    proposal["owner_decision"] = "approved"
    _write_seed(path, rows, fields)

    with pytest.raises(ReviewBuildError, match="not pending explicit owner approval"):
        compile_review_register(seed_path=path)


def test_rejects_changes_to_baseline_identity_inventory(tmp_path):
    path, rows, fields = _copy_seed(tmp_path)
    rows[0]["source_name"] = "Changed source name"
    _write_seed(path, rows, fields)

    with pytest.raises(ReviewBuildError, match="changed immutable baseline field"):
        compile_review_register(seed_path=path)


def test_kosovo_remains_held_without_mapping():
    _, rows, _ = compile_review_register()
    kos = next(row for row in rows if row["source_id"] == "KOS")
    assert kos["review_outcome"] == "hold_for_evidence"
    assert kos["reviewed_proposed_game_id"] == ""
    assert kos["proposed_registry_name"] == ""
    assert kos["un_m49_code"] == ""
    assert kos["approved_game_id"] == ""
