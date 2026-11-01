from __future__ import annotations

from tools.database.identity_reconciliation import reconcile_identities
from tools.database.reporting import emit_terminal_report, write_report_bundle
from tools.propose_iso_assignments import REVIEWED_NAME_VARIANTS, propose


FIELDS = {
    "game_id": "game_id",
    "registry_name": "names.en",
    "source_id": "source.current_source_id",
    "existing_alpha2": "iso.alpha2",
    "existing_alpha3": "iso.alpha3",
    "reference_name": "name",
    "reference_id": "m49",
    "reference_alpha2": "a2",
    "reference_alpha3": "a3",
}


def _record(game_id, name, source_id="", a2=None, a3=None):
    return {
        "game_id": game_id, "names": {"en": name},
        "source": {"current_source_id": source_id},
        "iso": {"alpha2": a2, "alpha3": a3},
    }


def test_reconciles_codes_independently_and_keeps_source_id_separate():
    registry = {"records": [
        _record("tc_a", "Alpha", "AAA", None, "AAA"),
        _record("tc_b", "Beta", "BEE", "BB", "OLD"),
        _record("tc_c", "Gamma", "GAM", "GC", "GAM"),
        _record("tc_d", "Missing", "MIS"),
        _record("tc_e", "Variant", "VAA"),
        _record("tc_f", "Delta", "DEL", "DD", None),
    ]}
    refs = [
        {"name": "Alpha", "m49": "001", "a2": "AA", "a3": "AAA"},
        {"name": "Beta", "m49": "002", "a2": "BB", "a3": "BBB"},
        {"name": "Gamma", "m49": "003", "a2": "GG", "a3": "GAM"},
        {"name": "Variant Formal", "m49": "004", "a2": "VV", "a3": "VVA"},
        {"name": "Reference only", "m49": "005", "a2": "", "a3": ""},
        {"name": "Delta", "m49": "006", "a2": "DD", "a3": "DDD"},
    ]
    before = repr(registry)
    result = reconcile_identities(
        registry, refs, fields=FIELDS,
        name_variants={"variant": ("Variant Formal", "Explicit reviewed variant.")},
    )
    rows = {row["game_id"]: row for row in result["records"]}
    assert rows["tc_a"]["alpha3_comparison"] == "match"
    assert rows["tc_a"]["name_comparison"] == "exact"
    assert rows["tc_a"]["alpha2_comparison"] == "missing_existing"
    assert rows["tc_a"]["code_pair_classification"] == "alpha3_only_agreement"
    assert rows["tc_b"]["code_pair_classification"] == "genuine_code_mismatch"
    assert rows["tc_c"]["code_pair_classification"] == "genuine_code_mismatch"
    assert rows["tc_f"]["code_pair_classification"] == "alpha2_only_agreement"
    assert rows["tc_f"]["source_id_vs_reference_alpha3"] == "different"
    assert rows["tc_d"]["match_type"] == "unmatched"
    assert rows["tc_e"]["match_type"] == "explicit_variant"
    assert rows["tc_e"]["name_comparison"] == "explicit_variant"
    assert rows["tc_a"]["source_id_vs_reference_alpha3"] == "same"
    assert result["summary"]["unmatched_reference_count"] == 1
    assert repr(registry) == before


def test_ambiguous_names_are_not_forced_and_all_reference_rows_remain_accounted():
    registry = {"records": [_record("tc_a", "Same Name"), _record("tc_b", "Same Name")]}
    refs = [
        {"name": "Same Name", "m49": "001", "a2": "AA", "a3": "AAA"},
        {"name": "Other", "m49": "002", "a2": "", "a3": ""},
    ]
    result = reconcile_identities(registry, refs, fields=FIELDS)
    assert all(row["match_type"] == "ambiguous" for row in result["records"])
    assert result["summary"]["ambiguous_registry_count"] == 2
    assert result["summary"]["unmatched_reference_count"] == 2


def test_duplicate_registry_names_cannot_claim_the_same_reference_row():
    registry = {"records": [_record("tc_a", "Same Name"), _record("tc_b", "Same Name")]}
    refs = [{"name": "Same Name", "m49": "001", "a2": "AA", "a3": "AAA"}]
    result = reconcile_identities(registry, refs, fields=FIELDS)
    assert all(row["match_type"] == "ambiguous" for row in result["records"])
    assert result["summary"]["matched_count"] == 0
    assert result["summary"]["ambiguous_registry_count"] == 2
    assert result["summary"]["unmatched_reference_count"] == 1


def test_rejects_duplicate_game_ids():
    registry = {"records": [_record("tc_a", "A"), _record("tc_a", "B")]}
    try:
        reconcile_identities(registry, [], fields=FIELDS)
    except ValueError as exc:
        assert "duplicate game_id" in str(exc)
    else:
        raise AssertionError("duplicate game_id was accepted")


def test_standard_report_bundle_and_terminal_modes(tmp_path, capsys):
    result = reconcile_identities(
        {"records": [_record("tc_a", "Alpha", a2="AA", a3="AAA")]},
        [{"name": "Alpha", "m49": "001", "a2": "AA", "a3": "AAA"}],
        fields=FIELDS,
    )
    paths = write_report_bundle(
        tmp_path, database_id="test_database", domain="identity",
        report_id="reconciliation", summary_markdown="# Summary",
        records=result["records"], unmatched_registry=result["unmatched_registry"],
        unmatched_reference=result["unmatched_reference"], provenance={"read_only": True},
    )
    assert (tmp_path / "database/test_database/identity/reconciliation/summary.md").is_file()
    assert (tmp_path / "database/test_database/identity/reconciliation/records.csv").is_file()
    assert (tmp_path / "database/test_database/identity/reconciliation/provenance.json").is_file()
    emit_terminal_report(result, paths, quiet=True)
    assert capsys.readouterr().out == ""
    emit_terminal_report(result, paths)
    assert "Registry records: 1" in capsys.readouterr().out
    emit_terminal_report(result, paths, verbose=True)
    verbose_output = capsys.readouterr().out
    assert "Code-pair classifications:" in verbose_output
    assert "tc_a" in verbose_output


def test_report_path_segments_are_validated(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="unsafe report path segment"):
        write_report_bundle(
            tmp_path, database_id="../escape", domain="identity",
            report_id="report", summary_markdown="", records=[],
            unmatched_registry=[], unmatched_reference=[], provenance={},
        )



def test_ten_owner_approved_m49_name_variants_match_without_assigning_codes():
    pairs = [
        ("Falkland Islands", "Falkland Islands (the) [Malvinas]"),
        ("South Korea", "Republic of Korea"),
        ("North Korea", "Democratic People's Republic of Korea"),
        ("Netherlands", "Netherlands (Kingdom of the)"),
        ("Nauru", "Naoero"),
        ("Moldova", "Republic of Moldova"),
        ("Palestine", "State of Palestine"),
        ("Wallis and Futuna", "Wallis and Futuna Islands"),
        ("Macao S.A.R", "China, Macao Special Administrative Region"),
        ("Hong Kong S.A.R.", "China, Hong Kong Special Administrative Region"),
    ]
    records = [
        _record(f"tc_variant_{index}", registry_name)
        for index, (registry_name, _) in enumerate(pairs)
    ]
    references = [
        {"name": reference_name, "m49": f"{index + 1:03}", "a2": "", "a3": ""}
        for index, (_, reference_name) in enumerate(pairs)
    ]

    result = reconcile_identities(
        {"records": records}, references, fields=FIELDS,
        name_variants=REVIEWED_NAME_VARIANTS,
    )
    assert result["summary"]["matched_count"] == 10
    assert result["summary"]["unmatched_registry_count"] == 0
    assert result["summary"]["unmatched_reference_count"] == 0
    assert result["summary"]["name_comparisons"]["explicit_variant"] == 10
    assert all(row["match_type"] == "explicit_variant" for row in result["records"])
    assert all(row["existing_alpha2"] == "" and row["existing_alpha3"] == ""
               for row in result["records"])

    proposal = propose(
        {"records": records},
        [
            {"english_name": row["name"], "alpha2": "AA", "alpha3": "AAA"}
            for row in references
        ],
    )
    assert proposal["candidate_count"] == 10
    assert proposal["explicit_variant_count"] == 10
    assert all(row["match_type"] == "explicit name variant"
               for row in proposal["proposals"])
