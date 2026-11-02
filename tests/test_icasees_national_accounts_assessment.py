from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from tools.assess_icasees_national_accounts import (
    IcaseesAssessmentError,
    _cell_number,
    _extract_gdp_rows,
    verify_manifest,
)


def _add_table(workbook, name, headers, rows):
    sheet = workbook.create_sheet(name)
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    return sheet


def _workbook_fixture():
    workbook = Workbook()
    workbook.remove(workbook.active)
    revised_rows = [
        ["IND1", "SECTEUR PRIMAIRE", "millions de F CFA", "Units", 422.807, 462.537, 475.988],
        ["IND7", "SECTEUR SECONDAIRE", "millions de F CFA", "Units", 431.047, 431.564, 479.105],
        ["IND20", "SECTEUR TERTIAIRE", "millions de F CFA", "Units", 1022.856, 1074.753, 1108.461],
        ["IND33", "TOTAL VAB", "millions de F CFA", "Units", 1876.710, 1968.854, 2063.554],
        ["IND34", "IMPÔTS ET TAXES SUR LES PRODUITS", "millions de F CFA", "Units", 76.215, 87.181, 86.068],
        ["IND35", "PRODUIT INTERIEUR BRUT", "millions de F CFA", "Units", 1952.925, 2056.035, 2149.622],
    ]
    headers = ["Indicateur", "Indicateur Name", "Units", "Scale", 2019, 2020, 2021]
    _add_table(workbook, "Donnee", headers, revised_rows)
    _add_table(workbook, "Donnée nouvelle",
               ["Code", "Nom des indicateurs", "Units", "Scale", 2019, 2020, 2021],
               revised_rows)
    historical = [
        ["IND35", "PRODUIT INTERIEUR BRUT", "millions de F CFA", 887.5841, 1012.171, 1102.8569,
         1182.4962, 1276.8130, 1322.8826, 1431.9912],
    ]
    _add_table(workbook, "Donnee_2013-2019",
               ["Indicateur", "Nom", "Units", 2013, 2014, 2015, 2016, 2017, 2018, 2019],
               historical)
    combined_headers = [
        "Indicateur", "Nom des indicateurs", "Units", 2013, 2014, 2015, 2016, 2017, 2018, 2019,
        None, "Nom des indicateurs", "Units", "Scale", 2019, 2020, 2021,
    ]
    combined_rows = [
        ["IND33", "TOTAL VAB", "millions de F CFA", 800, 900, 1000, 1100, 1200, 1300, 1351.491,
         None, "TOTAL VAB", "millions de F CFA", "Units", 1876.710, 1968.854, 2063.554],
        ["IND34", "IMPÔTS ET TAXES SUR LES PRODUITS", "millions de F CFA", 40, 50, 60, 65, 70, 75, 80.500,
         None, "IMPÔTS ET TAXES SUR LES PRODUITS", "millions de F CFA", "Units", 76.215, 87.181, 86.068],
        ["IND35", "PRODUIT INTERIEUR BRUT", "millions de F CFA", 887.5841, 1012.171, 1102.8569, 1182.4962, 1276.8130, 1322.8826, 1431.9912,
         None, "PRODUIT INTERIEUR BRUT", "millions de F CFA", "Units", 1952.925, 2056.035, 2149.622],
    ]
    _add_table(workbook, "Donnée_SCN2008", combined_headers, combined_rows)
    return workbook


def test_extracts_old_and_revised_gdp_as_separate_series():
    series, checks = _extract_gdp_rows(_workbook_fixture())
    historical = [row for row in series if row["sheet"] == "Donnee_2013-2019"]
    revised = [row for row in series if row["sheet"] == "Donnée nouvelle"]
    assert [row["year"] for row in historical] == list(range(2013, 2020))
    assert [row["year"] for row in revised] == [2019, 2020, 2021]
    assert historical[-1]["value"] == pytest.approx(1431.9912)
    assert revised[0]["value"] == pytest.approx(1952.925)
    assert checks["gdp_2019_overlap"]["relative_difference_percent"] == pytest.approx(36.38, abs=0.01)


def test_gdp_row_lookup_matches_accented_french_label():
    workbook = _workbook_fixture()
    sheet = workbook["Donnée_SCN2008"]
    for row in range(2, sheet.max_row + 1):
        if sheet.cell(row, 13).value == "PRODUIT INTERIEUR BRUT":
            sheet.cell(row, 13).value = "PRODUIT INTÉRIEUR BRUT"
    series, _ = _extract_gdp_rows(workbook)
    revised = [row for row in series if row["sheet"] == "Donnée_SCN2008" and row["series_block"] == "revised"]
    assert len(revised) == 3


def test_repeated_2019_header_does_not_replace_historical_value():
    series, _ = _extract_gdp_rows(_workbook_fixture())
    combined_old = [row for row in series if row["sheet"] == "Donnée_SCN2008"
                    and row["series_block"] == "historical"]
    assert combined_old[-1]["year"] == 2019
    assert combined_old[-1]["value"] == pytest.approx(1431.9912)


def test_gdp_arithmetic_is_validated_in_both_revised_sheets():
    _, checks = _extract_gdp_rows(_workbook_fixture())
    assert checks["Donnee_2019_gdp_equals_vab_plus_taxes"] is True
    assert checks["Donnee_2020_gdp_equals_vab_plus_taxes"] is True
    assert checks["Donnée nouvelle_2021_gdp_equals_vab_plus_taxes"] is True
    assert checks["Donnée_SCN2008_2019_gdp_equals_vab_plus_taxes"] is True


def test_manifest_verification_rejects_changed_snapshot(tmp_path, monkeypatch):
    import tools.assess_icasees_national_accounts as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    definitions = []
    entries = []
    for original in module.FILES:
        item = dict(original)
        path = tmp_path / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("payload-" + item["file_id"]).encode())
        item["expected_byte_count"] = path.stat().st_size
        item["expected_sha256"] = module._sha256(path)
        definitions.append(item)
        entries.append({**item, "repository_path": item["path"],
                        "byte_count": path.stat().st_size, "sha256": module._sha256(path)})
    monkeypatch.setattr(module, "FILES", definitions)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"manifest_schema_version": 1, "source_id": module.SOURCE_ID,
                                    "files": entries}), encoding="utf-8")
    _, checks = verify_manifest(manifest)
    assert all(row["status"] == "valid" for row in checks)
    (tmp_path / definitions[0]["path"]).write_text("changed", encoding="utf-8")
    with pytest.raises(IcaseesAssessmentError, match="differ from the manifest"):
        verify_manifest(manifest)


def test_manifest_verification_requires_exact_file_set(tmp_path, monkeypatch):
    import tools.assess_icasees_national_accounts as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"manifest_schema_version": 1, "source_id": module.SOURCE_ID,
                                    "files": []}), encoding="utf-8")
    with pytest.raises(IcaseesAssessmentError, match="exact three"):
        verify_manifest(manifest)


def test_sector_and_duplicate_table_consistency_checks_pass():
    _, checks = _extract_gdp_rows(_workbook_fixture())
    for year in (2019, 2020, 2021):
        assert checks[f"Donnee_{year}_sector_vab_equals_total_vab"] is True
        assert checks[f"Donnée nouvelle_{year}_sector_vab_equals_total_vab"] is True
        assert checks[f"revised_gdp_presentations_agree_{year}"] is True
    for year in range(2013, 2020):
        assert checks[f"historical_gdp_presentations_agree_{year}"] is True


def test_simple_arithmetic_formula_is_evaluated_without_excel_cache():
    workbook = _workbook_fixture()
    sheet = workbook["Donnee"]
    sheet["E7"] = "=E5+E6"
    series, checks = _extract_gdp_rows(workbook)
    row = next(item for item in series if item["sheet"] == "Donnee" and item["year"] == 2019)
    assert row["value"] == pytest.approx(1952.925)
    assert checks["Donnee_2019_gdp_equals_vab_plus_taxes"] is True


def test_chained_arithmetic_formula_is_evaluated():
    workbook = _workbook_fixture()
    sheet = workbook["Donnee"]
    sheet["E5"] = 100.0
    sheet["E6"] = 200.0
    sheet["E7"] = 300.0
    sheet["E8"] = "=E5+E6+E7"
    assert _cell_number(sheet, 8, 5) == pytest.approx(600.0)


def test_sum_range_formula_is_evaluated_without_excel_cache():
    workbook = _workbook_fixture()
    sheet = workbook["Donnee"]
    sheet["E3"] = 10.0
    sheet["E4"] = 20.0
    sheet["E5"] = 30.0
    sheet["E6"] = 40.0
    sheet["E7"] = 50.0
    sheet["E2"] = "=SUM(E3:E7)"
    assert _cell_number(sheet, 2, 5) == pytest.approx(150.0)


def test_unsupported_formula_fails_explicitly():
    workbook = _workbook_fixture()
    workbook["Donnee"]["E7"] = "=AVERAGE(E5:E6)"
    with pytest.raises(IcaseesAssessmentError, match="Unsupported workbook formula"):
        _extract_gdp_rows(workbook)
