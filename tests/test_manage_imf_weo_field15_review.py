from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tools.manage_imf_weo_field15_review import (
    HEADER,
    META_CLOSE,
    META_OPEN,
    SEPARATOR,
    ReviewError,
    parse_review,
    verify_existing_observations_are_candidate_subset,
)


FIXED_DECISIONS = {
    "WBG": "Reuse existing owner-approved WBG to Palestine mapping; field 15 only.",
    "aggregates": "Reuse 13 owner-approved excluded dispositions; 665 populated values.",
    "KOS": "Preserve hold_for_evidence; no identity mapping.",
}


def _review_text(*, first_decision: str = "PENDING", first_approved_id: str = "-") -> str:
    metadata = {
        "schema_version": 1,
        "field_id": 15,
        "indicator_code": "NGDPD",
        "fixed_decisions": FIXED_DECISIONS,
    }
    lines = [
        "# IMF WEO October 2026 — field 15 / NGDPD owner review",
        "WBG maps to tc_50c420df8b2c4c6eaae47d795f9a1ea2 (Palestine).",
        "Total: 13 aggregate series and 665 populated annual values.",
        META_OPEN,
        json.dumps(metadata),
        META_CLOSE,
        HEADER,
        SEPARATOR,
    ]
    sources = []
    for i in range(196):
        if i == 80:
            source_id = "KOS"
        else:
            n = i if i < 80 else i - 1
            source_id = f"X{n:02d}"
        sources.append(source_id)
    for i, source_id in enumerate(sources):
        batch = f"{i // 20 + 1:02d}"
        if source_id == "KOS":
            values = [
                batch, source_id, "Kosovo", "KOS.NGDPD.A", "52 (1980–2031)",
                "-", "-", "-", "IMF Appendix; UN M49", "KOS / UVK discrepancy",
                "HOLD", "-", "KOS and UVK source codes remain unresolved.",
            ]
        else:
            proposed = "tc_" + f"{i:032x}"
            decision = first_decision if i == 0 else "PENDING"
            approved = first_approved_id if i == 0 else "-"
            rationale = "Owner-reviewed identity rationale." if i == 0 and decision != "PENDING" else ""
            values = [
                batch, source_id, f"Example {source_id}", f"{source_id}.NGDPD.A",
                "52 (1980–2031)", proposed, f"Registry {source_id}", "001",
                "https://example.org/imf;https://example.org/m49",
                "IMF Appendix to M49 to canonical registry", decision, approved, rationale,
            ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def test_parse_review_accepts_pending_195_identity_register(tmp_path: Path):
    path = tmp_path / "review.md"
    path.write_text(_review_text(), encoding="utf-8")

    metadata, rows, _ = parse_review(path, complete=False)

    assert metadata["field_id"] == 15
    assert metadata["indicator_code"] == "NGDPD"
    assert len(rows) == 196
    assert sum(row["source_id"] == "KOS" for row in rows) == 1
    assert sum(row["decision"] == "PENDING" for row in rows) == 195


def test_parse_review_rejects_approved_game_id_that_differs_from_proposal(tmp_path: Path):
    path = tmp_path / "review.md"
    path.write_text(
        _review_text(first_decision="APPROVE", first_approved_id="tc_" + "f" * 32),
        encoding="utf-8",
    )

    with pytest.raises(ReviewError, match="Approved target differs"):
        parse_review(path, complete=False)


def test_parse_review_rejects_pending_decisions_when_complete(tmp_path: Path):
    path = tmp_path / "review.md"
    path.write_text(_review_text(), encoding="utf-8")

    with pytest.raises(ReviewError, match="Decision pending"):
        parse_review(path, complete=True)


def test_cli_help_runs_outside_repository_without_pythonpath(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "tools/manage_imf_weo_field15_review.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "generate-review" in completed.stdout
    assert "validate-review" in completed.stdout
    assert "apply-reviewed" in completed.stdout



def _write_candidate_fixture(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "observations.csv").write_text(
        "game_id,indicator_code,observation_year\n"
        "tc_" + "a" * 32 + ",NGDPD,2000\n",
        encoding="utf-8",
    )
    (directory / "candidate.json").write_text(
        json.dumps({"source_sha256": "a" * 64}),
        encoding="utf-8",
    )


def _write_existing_observations_db(path: Path, *, extra_kos: bool) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """CREATE TABLE imf_weo_historical_observations (
                game_id TEXT, source_country_code TEXT, indicator_code TEXT,
                observation_year INTEGER, source_version TEXT, source_sha256 TEXT,
                field_id INTEGER
            )"""
        )
        connection.execute(
            """INSERT INTO imf_weo_historical_observations VALUES
               (?, ?, ?, ?, ?, ?, ?)""",
            (
                "tc_" + "a" * 32, "AAA", "NGDPD", 2000,
                "October 2026 / IMF.RES_WEO_9.0.0", "a" * 64, 15,
            ),
        )
        if extra_kos:
            connection.execute(
                """INSERT INTO imf_weo_historical_observations VALUES
                   (?, ?, ?, ?, ?, ?, ?)""",
                (
                    "tc_" + "b" * 32, "KOS", "NGDPD", 2001,
                    "October 2026 / IMF.RES_WEO_9.0.0", "a" * 64, 15,
                ),
            )
        connection.commit()
    finally:
        connection.close()


def test_existing_legacy_rows_outside_candidate_block_before_application(tmp_path: Path):
    candidate = tmp_path / "candidate"
    database = tmp_path / "game.sqlite"
    _write_candidate_fixture(candidate)
    _write_existing_observations_db(database, extra_kos=True)

    with pytest.raises(ReviewError, match="KOS:1"):
        verify_existing_observations_are_candidate_subset(candidate, database)


def test_existing_rows_that_are_candidate_subset_pass_preflight(tmp_path: Path):
    candidate = tmp_path / "candidate"
    database = tmp_path / "game.sqlite"
    _write_candidate_fixture(candidate)
    _write_existing_observations_db(database, extra_kos=False)

    result = verify_existing_observations_are_candidate_subset(candidate, database)

    assert result["existing_observation_rows"] == 1
    assert result["existing_rows_outside_candidate"] == 0
    assert result["preflight_passed"] is True
