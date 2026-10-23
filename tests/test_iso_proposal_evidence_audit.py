from __future__ import annotations

from tools.audit_iso_proposal_evidence import audit_evidence, read_proposal_report
from tools.propose_iso_assignments import propose, render_report


def registry():
    return {
        "records": [
            {"game_id": "tc_alpha", "names": {"en": "Alpha"}, "iso": {"assignment_status": "unverified"}},
            {"game_id": "tc_beta", "names": {"en": "Beta"}, "iso": {"assignment_status": "unverified"}},
        ]
    }


def reference():
    return [
        {"alpha2": "AA", "alpha3": "AAA", "english_name": "Alpha"},
        {"alpha2": "BB", "alpha3": "BBB", "english_name": "Beta"},
    ]


def report_rows(data=None, refs=None):
    result = propose(data or registry(), refs or reference())
    report = render_report(result, "reference.csv", "https://example.invalid/reference.csv", "2026-10-22")
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "proposals.md"
        path.write_text(report, encoding="utf-8")
        return read_proposal_report(path)


def test_clean_proposals_pass_registry_and_reference_consistency_audit():
    result = audit_evidence(registry(), reference(), report_rows())
    assert result["registry_count"] == 2
    assert result["unique_registry_ids"] == 2
    assert result["proposal_row_count"] == 2
    assert result["candidate_count"] == 2
    assert result["issues"] == []


def test_audit_detects_missing_stale_and_duplicate_proposal_rows():
    rows = report_rows()
    rows[1] = dict(rows[0])
    rows.append({**rows[0], "game_id": "tc_stale"})
    result = audit_evidence(registry(), reference(), rows)
    joined = "\n".join(result["issues"])
    assert "occurs 2 times" in joined
    assert "Missing proposal row for registry game_id 'tc_beta'" in joined
    assert "Stale proposal row for unknown game_id 'tc_stale'" in joined


def test_audit_detects_edited_candidate_codes_and_reference_label():
    rows = report_rows()
    rows[0]["Candidate alpha-2"] = "ZZ"
    rows[0]["Candidate alpha-3"] = "ZZZ"
    rows[0]["Reference English name"] = "Not Alpha"
    result = audit_evidence(registry(), reference(), rows)
    joined = "\n".join(result["issues"])
    assert "stale or edited proposal field 'Candidate alpha-2'" in joined
    assert "candidate code pair ZZ/ZZZ is absent from captured reference" in joined


def test_audit_detects_candidate_code_conflicts_between_records():
    rows = report_rows()
    rows[1]["Candidate alpha-2"] = "AA"
    rows[1]["Candidate alpha-3"] = "AAA"
    rows[1]["Reference English name"] = "Alpha"
    result = audit_evidence(registry(), reference(), rows)
    joined = "\n".join(result["issues"])
    assert "Candidate code pair AA/AAA is proposed for multiple game_ids" in joined
    assert "Candidate alpha-2 AA is proposed for multiple game_ids" in joined
    assert "Candidate alpha-3 AAA is proposed for multiple game_ids" in joined
