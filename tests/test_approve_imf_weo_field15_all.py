from __future__ import annotations

import pytest

from tools.manage_imf_weo_field15_review import HEADER, ReviewError
from tools.approve_imf_weo_field15_all import build_bulk_approved_document


def _document() -> str:
    lines = [
        "# IMF WEO October 2026 — field 15 / NGDPD owner review",
        "",
        "- Owner actor: PENDING",
        "- Approval date (YYYY-MM-DD): PENDING",
        "- Approval statement: PENDING",
        "",
        HEADER,
        "|---:|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for index in range(195):
        source = f"S{index:03d}"
        game_id = "tc_" + f"{index:032x}"
        values = [
            "01", source, f"Source {index}", f"{source}.NGDPD.A", "52 (1980–2031)",
            game_id, f"Registry {index}", f"{index % 999:03d}", "IMF; UN M49",
            "Evidence-backed source proposal", "PENDING", "-", "",
        ]
        lines.append("| " + " | ".join(values) + " |")
    kos = ["10", "KOS", "Kosovo", "KOS.NGDPD.A", "52 (1980–2031)", "-", "-", "-", "IMF appendix",
           "Code discrepancy", "HOLD", "-", "Retain evidence hold"]
    lines.append("| " + " | ".join(kos) + " |")
    return "\n".join(lines) + "\n"


def test_bulk_builder_approves_every_proposal_and_preserves_kos_hold():
    note = "Owner confirms the complete generated identity proposal set for field 15."
    result, count = build_bulk_approved_document(
        _document(), actor="project-owner", note=note, approval_date="2026-11-26"
    )
    assert count == 195
    assert "- Owner actor: project-owner" in result
    assert "- Approval date (YYYY-MM-DD): 2026-11-26" in result
    assert result.count("| APPROVE |") == 195
    assert result.count("| HOLD |") == 1
    assert result.count("| tc_") == 390
    assert note in result


def test_bulk_builder_rejects_wrong_proposal_count():
    document = _document().replace("S194", "KOS")
    with pytest.raises(ReviewError):
        build_bulk_approved_document(
            document, actor="project-owner",
            note="Owner approves the complete generated identity proposal set.",
            approval_date="2026-11-26",
        )


def test_bulk_builder_requires_explicit_rationale():
    with pytest.raises(ReviewError):
        build_bulk_approved_document(
            _document(), actor="project-owner", note="too short", approval_date="2026-11-26"
        )
