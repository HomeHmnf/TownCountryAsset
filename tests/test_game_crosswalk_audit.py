import json
from pathlib import Path

from tools.audit_game_country_crosswalk import audit, norm


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_norm_handles_persian_spacing_and_yeh_kaf():
    assert norm("هنگ‌کنگ") == norm(" هنگ کنگ ")
    assert norm("علي") == norm("علی")
    assert norm("كويت") == norm("کویت")


def test_audit_proposes_review_only_candidate_and_reports_catalog_mismatch(tmp_path):
    asset = tmp_path / "asset"
    game = tmp_path / "game"
    gd = game / "Asset" / "Data"
    asset.mkdir()
    gd.mkdir(parents=True)
    write_json(asset / "countries.json", {
        "count": 1,
        "countries": [{
            "id": "JPN", "name": "Japan", "iso3": "JPN", "regions": ["Asia"],
            "aliases": [], "source_attributes": {"ADMIN": "Japan", "NAME": "Japan", "NAME_LONG": "Japan"}
        }]
    })
    for region, prefix in (("asia", "MapAsia"), ("europe", "MapEurope"),
                           ("america", "MapAmerica"), ("africa", "MapAfrica")):
        write_json(gd / f"{prefix}_Countries.json", {"ژاپن": "ژاپن"})
        write_json(gd / f"{prefix}_ColorMap.json", {"abc123": ["ژاپن", [0, 0, 1, 1]], "def456": ["نام ناشناخته", [0, 0, 1, 1]]})
        write_json(gd / f"{prefix}_Questions.json", [{"question": "کجا؟", "answer": "نام ناشناخته"}])
    write_json(gd / "Flag_Data.json", {"easy": ["ژاپن"]})
    write_json(gd / "Flag_Translation.json", {"Japan": "ژاپن"})
    write_json(gd / "GeneralInfo_CountriesCapitals.json", {"آسیا": {"easy": [["ژاپن", "توکیو"]]}})
    write_json(gd / "GeneralInfo_Questions.json", [{"question": "پایتخت؟", "answer": "توکیو"}])
    write_json(gd / "Country_Aliases.json", {"_schema_version": 1, "asia": {"ژاپن قدیم": "ژاپن"}})

    report = audit(asset, game)
    assert report["asset_country_count"] == 1
    japan = next(row for row in report["game_labels"] if "ژاپن" in row["labels"])
    assert japan["asset_source_id_candidates"] == ["JPN"]
    assert japan["match_status"] == "candidate_needs_review"
    assert report["region_audits"]["asia"]["color_map_labels_missing_from_catalog"] == ["نامناشناخته"]
    assert report["region_audits"]["asia"]["question_answers_missing_from_catalog"] == ["نام ناشناخته"]
    assert report["asset_countries"][0]["review_status"] == "needs_human_review"
