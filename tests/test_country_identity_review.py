from tools.audit_country_identity_registry import audit_registry, render_report


def sample_registry():
    return {
        "status": "proposal",
        "records": [
            {
                "game_id": "tc_alpha",
                "source": {"current_source_id": "AAA", "previous_source_ids": []},
                "geometry_key": "AAA",
                "status": "proposed",
                "iso": {"alpha2": None, "alpha3": "AAA", "assignment_status": "unverified"},
                "names": {"en": "Alpha", "fa": None, "aliases_en": [], "aliases_fa": [], "localization_status": "unreviewed"},
                "entity_type": "unreviewed",
                "regions": ["Asia"],
            }
        ],
    }


def test_audit_reports_review_gaps_without_mutating_registry():
    registry = sample_registry()
    before = repr(registry)
    result = audit_registry(registry)
    assert result["record_count"] == 1
    assert result["unique_game_ids"] == 1
    assert result["structural_issues"] == []
    assert result["review_counts"]["entity type unreviewed"] == 1
    assert result["review_counts"]["ISO status unverified"] == 1
    assert result["review_counts"]["Persian name missing"] == 1
    assert repr(registry) == before


def test_audit_detects_duplicate_ids_and_geometry_mismatch():
    registry = sample_registry()
    duplicate = dict(registry["records"][0])
    duplicate["source"] = {"current_source_id": "BBB", "previous_source_ids": []}
    duplicate["geometry_key"] = "WRONG"
    registry["records"].append(duplicate)
    result = audit_registry(registry)
    assert any("duplicate game_id" in issue for issue in result["structural_issues"])
    assert any("geometry_key differs" in issue for issue in result["structural_issues"])


def test_report_includes_record_level_review_reasons_and_safety_guidance():
    report = render_report(audit_registry(sample_registry()))
    assert "| tc_alpha | AAA | Alpha |" in report
    assert "does not approve or change any record" in report
    assert "Do not regenerate, replace, or derive canonical game IDs" in report
