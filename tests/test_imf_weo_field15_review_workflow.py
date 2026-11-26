from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.manage_imf_weo_field15_review import (
    HEADER,
    SEPARATOR,
    META_OPEN,
    META_CLOSE,
    ReviewError,
    parse_review,
)


def make_review(tmp_path: Path, *, decision: str = "PENDING", approved: str = "-") -> Path:
    metadata = {
        "schema_version": 1,
        "field_id": 15,
        "indicator_code": "NGDPD",
        "automatic_review_directory": "reports/sources/example",
        "input_fingerprints": {},
    }
    lines = [
        "# IMF WEO October 2026 — field 15 / NGDPD owner review",
        "",
        "- Owner actor: PENDING",
        "- Approval date (YYYY-MM-DD): PENDING",
        "- Approval statement: PENDING",
        "",
        HEADER,
        SEPARATOR,
    ]
    for index in range(196):
        source_id = "KOS" if index == 100 else f"X{index:03d}"
        batch = index // 20 + 1
        if source_id == "KOS":
            values = [f"{batch:02d}", source_id, "Kosovo", "KOS.NGDPD.A", "52",
                      "-", "-", "-", "IMF;UN", "HOLD", "-", "Retain the established evidence hold."]
        else:
            row_decision = decision if index == 0 else "PENDING"
            approved_id = approved if index == 0 else "-"
            values = [f"{batch:02d}", source_id, source_id, source_id + ".NGDPD.A", "52",
                      "tc_" + f"{index:032x}", "Registry " + source_id, "001", "https://example.org/evidence",
                      row_decision, approved_id,
                      "Owner reviewed the independent identity evidence and recorded this disposition."
                      if row_decision != "PENDING" else ""]
        lines.append("| " + " | ".join(values) + " |")
    lines += ["", META_OPEN, __import__("json").dumps(metadata), META_CLOSE]
    path = tmp_path / "review.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_parser_accepts_initial_pending_review(tmp_path: Path):
    path = make_review(tmp_path)
    metadata, rows, _ = parse_review(path, complete=False)
    assert metadata["field_id"] == 15
    assert len(rows) == 196
    assert sum(row["source_id"] != "KOS" for row in rows) == 195


def test_parser_rejects_pending_decisions_for_application(tmp_path: Path):
    path = make_review(tmp_path)
    with pytest.raises(ReviewError, match="Decision pending"):
        parse_review(path, complete=True)


def test_parser_rejects_approved_target_different_from_proposal(tmp_path: Path):
    path = make_review(tmp_path, decision="APPROVE", approved="tc_" + "f" * 32)
    with pytest.raises(ReviewError, match="Approved target differs"):
        parse_review(path, complete=False)


def test_parser_rejects_missing_owner_approval_metadata(tmp_path: Path):
    path = make_review(tmp_path)
    text = path.read_text(encoding="utf-8")
    text = text.replace("- Owner actor: PENDING", "- Owner actor: project-owner")
    text = text.replace("- Approval date (YYYY-MM-DD): PENDING", "- Approval date (YYYY-MM-DD): 2026-11-26")
    text = text.replace("- Approval statement: PENDING", "- Approval statement: I approve this complete field 15 review.")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ReviewError, match="Decision pending"):
        parse_review(path, complete=True)


def test_cli_help_works_from_outside_repository(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "tools/manage_imf_weo_field15_review.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "generate-review" in result.stdout
    assert "apply-reviewed" in result.stdout
