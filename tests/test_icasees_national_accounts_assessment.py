from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from tools.assess_icasees_national_accounts import (
    IcaseesAssessmentError,
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
        ["IND35", "PRODUIT INTERIEUR BRUT", "millions de F CFA", 840, 950, 1060, 1165, 1270, 1375, 1431.9912,
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
    definitions = module.FILES
    entries = []
    for item in definitions:
        path = tmp_path / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("payload-" + item["file_id"]).encode())
        entries.append({**item, "repository_path": item["path"],
                        "byte_count": path.stat().st_size, "sha256": module._sha256(path)})
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
