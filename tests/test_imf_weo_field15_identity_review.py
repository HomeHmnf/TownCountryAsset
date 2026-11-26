from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.build_imf_weo_field15_identity_review import (
    REVIEW_FIELDS,
    IdentityReviewError,
    _registry_m49_name_index,
    _validate_m49_faq_html,
    _validate_wbg_crosswalk,
    parse_imf_appendix_codes,
    read_weo_ngdpd_inventory,
    write_outputs,
)


def test_inventory_is_derived_from_raw_weo_csv(tmp_path: Path):
    source = tmp_path / "weo.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["SERIES_CODE", "COUNTRY", "FREQUENCY", "LATEST_ACTUAL_ANNUAL_DATA", "1980", "1981"],
        )
        writer.writeheader()
        writer.writerow({
            "SERIES_CODE": "AAA.NGDPD.A", "COUNTRY": "Example A", "FREQUENCY": "Annual",
            "LATEST_ACTUAL_ANNUAL_DATA": "2025", "1980": "1.25", "1981": "",
        })
        writer.writerow({
            "SERIES_CODE": "G001.NGDPD.A", "COUNTRY": "World", "FREQUENCY": "Annual",
            "LATEST_ACTUAL_ANNUAL_DATA": "", "1980": "10", "1981": "11",
        })
        writer.writerow({
            "SERIES_CODE": "AAA.NGDPD.Q", "COUNTRY": "Example A", "FREQUENCY": "Quarterly",
            "LATEST_ACTUAL_ANNUAL_DATA": "", "1980": "1", "1981": "2",
        })

    rows = read_weo_ngdpd_inventory(source, expected_count=2)
    assert [row["source_id"] for row in rows] == ["AAA", "G001"]
    assert rows[0]["populated_year_count"] == "1"
    assert rows[0]["first_populated_year"] == "1980"
    assert rows[1]["populated_year_count"] == "2"


def test_appendix_parser_detects_official_codes_and_kosovo_discrepancy():
    pages = []
    for number in range(1, 15):
        body = ""
        if number == 10:
            body = (
                "ISO Code Country Currency\n"
                "AAA Example Land Example dollar\n"
                "TWN Taiwan Province of China New Taiwan dollar\n"
                "WBG West Bank and Gaza Israeli new shekel\n"
                "UVK Kosovo Euro\n"
            )
        pages.append(f"--- PAGE {number} ---\n{body}")
    text = "\n".join(pages)

    codes, parsed_pages = parse_imf_appendix_codes(
        text, {"AAA", "TWN", "WBG", "KOS", "G001"}, expected_count=4
    )
    assert {"AAA", "TWN", "WBG", "UVK"} <= codes
    assert "KOS" not in codes
    assert 10 in parsed_pages


def test_m49_faq_requires_statistical_codes_for_taiwan_and_kosovo():
    faq = (
        "<p>For strictly statistical purposes, the numerical code 158 can be used "
        "to represent this area.</p>"
        "<p>For strictly statistical purposes, the numerical code 412 can be used "
        "to represent this area.</p>"
    )
    _validate_m49_faq_html(faq)

    with pytest.raises(IdentityReviewError, match="code 412"):
        _validate_m49_faq_html(faq.replace("412", "413"))


def test_registry_targets_are_resolved_by_m49_names_not_registry_codes():
    registry = [{
        "game_id": "tc_" + "a" * 32,
        "source": {"current_source_id": "NOT_BHS"},
        "iso": {"alpha3": "NOT", "assignment_status": "unverified"},
        "names": {"en": "The Bahamas"},
    }]
    m49_rows = [{
        "Country or Area": "Bahamas",
        "M49 Code": "044",
        "ISO-alpha2 Code": "BS",
        "ISO-alpha3 Code": "BHS",
    }]

    resolved, ambiguous = _registry_m49_name_index(registry, m49_rows)
    assert not ambiguous
    assert resolved["044"][0]["game_id"] == "tc_" + "a" * 32
    assert resolved["044"][1]  # explicit reviewed name variant was used


def test_wbg_crosswalk_must_remain_the_only_approved_mapping():
    game_id = "tc_50c420df8b2c4c6eaae47d795f9a1ea2"
    registry = {game_id: {"game_id": game_id, "names": {"en": "Palestine"}}}
    crosswalk = {
        "review_approval": {"status": "approved", "scope": "Field 15 only"},
        "mappings": [{"source_id": "WBG", "game_id": game_id}],
    }
    assert _validate_wbg_crosswalk(crosswalk, registry) == game_id

    crosswalk["mappings"].append({"source_id": "AAA", "game_id": "tc_" + "b" * 32})
    with pytest.raises(IdentityReviewError, match="sole owner-approved"):
        _validate_wbg_crosswalk(crosswalk, registry)


def _review_row(source_id: str, index: int, *, held: bool = False) -> dict[str, str]:
    row = {field: "" for field in REVIEW_FIELDS}
    row.update({
        "field_id": "15",
        "indicator_code": "NGDPD",
        "source_id": source_id,
        "source_name": source_id,
        "series_code": source_id + ".NGDPD.A",
        "populated_year_count": "52",
        "first_populated_year": "1980",
        "last_populated_year": "2031",
        "exact_normalized_name_match": "false",
        "review_outcome": "hold_for_evidence" if held else "proposed_manual_review",
        "owner_decision": "" if held else "pending_explicit_owner_approval",
        "reviewed_proposed_game_id": "" if held else "tc_" + f"{index:032x}",
        "proposed_registry_name": "" if held else "Proposed " + source_id,
        "un_m49_code": "" if held else "001",
    })
    return row


def test_one_run_writes_all_ten_cumulative_batches_and_final_register(tmp_path: Path):
    before = [f"AA{i:03d}" for i in range(85)]
    after = [f"ZZ{i:03d}" for i in range(110)]
    source_ids = sorted(before + ["KOS"] + after)
    rows = [_review_row(code, index, held=(code == "KOS")) for index, code in enumerate(source_ids)]
    inventory = [{
        "source_id": row["source_id"], "source_name": row["source_name"],
        "series_code": row["series_code"], "populated_year_count": "52",
        "first_populated_year": "1980", "last_populated_year": "2031",
        "classification": "hold_for_evidence" if row["source_id"] == "KOS" else "proposal",
        "proposed_game_id": row["reviewed_proposed_game_id"],
    } for row in rows]
    aggregate = [{
        "source_country_code": "G001", "series_code": "G001.NGDPD.A",
        "source_country_name": "World", "indicator_code": "NGDPD", "field_id": "15",
        "disposition": "excluded", "rationale": "WEO aggregate",
        "populated_year_count": "52", "first_populated_year": "1980",
        "last_populated_year": "2031", "latest_actual_annual_data": "",
        "release": "october_2026", "source_sha256": "a" * 64,
    }]
    exceptions = [{
        "source_country_code": "KOS", "source_country_name": "Kosovo",
        "series_code": "KOS.NGDPD.A", "exception": "imf_appendix_code_discrepancy",
        "candidate_game_ids": "", "disposition": "hold_for_evidence",
        "rationale": "KOS versus UVK", "evidence_reference": "imf;un",
    }]
    result = {
        "inventory": inventory,
        "aggregates": aggregate,
        "exceptions": exceptions,
        "review_rows": rows,
        "fingerprints": {},
        "m49_faq_html": "<html>official FAQ snapshot</html>",
        "m49_faq_provenance": {
            "source_url": "https://unstats.un.org/unsd/methodology/m49/",
            "final_url": "https://unstats.un.org/unsd/methodology/m49/",
            "retrieved_at_utc": "2026-11-26T00:00:00+00:00",
            "content_type": "text/html; charset=utf-8",
            "byte_count": 30,
            "sha256": "a" * 64,
            "validation": "test",
        },
        "summary": {
            "source_identity_count": 210, "aggregate_exclusion_count": 13,
            "individual_economy_count": 197, "existing_approved_crosswalk_count": 1,
            "proposal_count": 195, "held_identity_count": 1,
            "owner_approved_proposal_count": 0, "batch_size": 20,
            "batch_count": 10, "batch_sizes": [20] * 9 + [16],
            "database_written": False, "approval_created": False,
            "registry_modified": False, "crosswalk_modified": False,
            "manual_batch_registers_read": False,
            "manual_inventory_or_exclusion_registers_read": False,
        },
    }

    output = write_outputs(result, tmp_path)
    assert (output / "field_15_identity_review_register_final.csv").is_file()
    assert (output / "field_15_identity_inventory.csv").is_file()
    assert (output / "field_15_exclusion_register.csv").is_file()
    assert (output / "identity_exceptions.csv").is_file()
    assert len(list(output.glob("field_15_identity_review_register_batch*.csv"))) == 10

    def read_register(path: Path):
        with path.open("r", encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    batch1 = read_register(output / "field_15_identity_review_register_batch01.csv")
    batch5 = read_register(output / "field_15_identity_review_register_batch05.csv")
    final = read_register(output / "field_15_identity_review_register_final.csv")
    assert len(batch1) == len(batch5) == len(final) == 196
    assert sum(row["reviewed_proposed_game_id"] != "" for row in batch1) == 20
    assert sum(row["review_outcome"] == "hold_for_evidence" for row in batch5) == 1
    assert sum(row["reviewed_proposed_game_id"] != "" for row in batch5) == 99
    assert sum(row["reviewed_proposed_game_id"] != "" for row in final) == 195
    assert sum(row["review_outcome"] == "pending_review" for row in final) == 0
    kos = next(row for row in final if row["source_id"] == "KOS")
    assert kos["review_outcome"] == "hold_for_evidence"
    assert kos["reviewed_proposed_game_id"] == ""
    assert all(row["owner_decision"] == "pending_explicit_owner_approval" for row in final if row["reviewed_proposed_game_id"])



def test_cli_runs_directly_without_pythonpath_from_outside_repository(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "tools/build_imf_weo_field15_identity_review.py"
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
    assert "Generate all IMF WEO field-15 identity-review batches" in completed.stdout
