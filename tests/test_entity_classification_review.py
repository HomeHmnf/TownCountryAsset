from __future__ import annotations

from tools.audit_entity_classification import build_review, render_report
from tools.propose_iso_assignments import propose, render_report as render_iso_report
from tools.audit_iso_proposal_evidence import read_proposal_report


def sample_registry():
    return {
        "records": [
            {
                "game_id": "tc_alpha",
                "source": {"current_source_id": "AAA"},
                "names": {"en": "Alpha"},
                "entity_type": "unreviewed",
            },
            {
                "game_id": "tc_beta",
                "source": {"current_source_id": "BBB"},
                "names": {"en": "Beta"},
                "entity_type": "sovereign_state",
            },
        ]
    }


def sample_taxonomy():
    return {
        "unreviewed_value": "unreviewed",
        "types": {
            "sovereign_state": {
                "definition": "A reviewed sovereign state.",
                "evidence_required": ["authoritative status source", "project policy decision"],
            },
            "unreviewed": {
                "definition": "No approved classification.",
                "evidence_required": ["classification review required"],
            },
        },
        "policy": ["Do not infer from names alone."],
    }


def sample_proposals():
    registry = sample_registry()
    reference = [
        {"alpha2": "AA", "alpha3": "AAA", "english_name": "Alpha"},
        {"alpha2": "BB", "alpha3": "BBB", "english_name": "Beta"},
    ]
    report = render_iso_report(propose(registry, reference), "reference.csv")
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "proposals.md"
        path.write_text(report, encoding="utf-8")
        return read_proposal_report(path)


def test_review_worksheet_preserves_ids_and_does_not_infer_entity_types():
    registry = sample_registry()
    result = build_review(registry, sample_taxonomy(), sample_proposals())

    assert result["record_count"] == 2
    assert result["unique_registry_ids"] == 2
    assert result["unreviewed_count"] == 1
    assert result["issues"] == []
    assert [row["game_id"] for row in result["rows"]] == ["tc_alpha", "tc_beta"]
    assert result["rows"][0]["entity_type"] == "unreviewed"
    assert result["rows"][0]["alpha3"] == "AAA"
    assert "evidence/review status not represented" in result["rows"][1]["classification_status"]


def test_review_worksheet_flags_unknown_type_and_missing_or_stale_proposal():
    registry = sample_registry()
    registry["records"][0]["entity_type"] = "kingdom"
    proposals = sample_proposals()
    proposals = [row for row in proposals if row["game_id"] != "tc_alpha"]
    proposals.append({**proposals[0], "game_id": "tc_stale"})

    result = build_review(registry, sample_taxonomy(), proposals)
    joined = "\n".join(result["issues"])
    assert "entity_type 'kingdom' is not in config/entity_types.json" in joined
    assert "tc_alpha: no ISO proposal row found" in joined
    assert "Stale ISO proposal row for unknown registry game_id 'tc_stale'" in joined


def test_render_report_documents_taxonomy_and_review_safeguards():
    result = build_review(sample_registry(), sample_taxonomy(), sample_proposals())
    report = render_report(result, Path("registry.json"), Path("types.json"), Path("proposals.md"))

    assert "# Entity classification review worksheet" in report
    assert "Record-level review worksheet" in report
    assert "does not change the registry" in report
    assert "Do not infer from names alone." in report
