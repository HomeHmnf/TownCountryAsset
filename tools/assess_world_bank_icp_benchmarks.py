"""Extract semantic ICP 2011 table observations and compare captured benchmarks.

This is a research/reporting layer only. It preserves table, column, unit and
release identity; only exact country-name matches are assigned an ISO3 code.
Cross-release comparisons are emitted only for explicitly aligned measures.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from tools.assess_world_bank_icp_exports import (
    ICPAssessmentError,
    decode_csv,
    is_icp2011_original_workbook,
    norm,
    read_csv,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = Path("raw_data/sources/world_bank_icp")
INSPECTION_ROOT = Path("reports/sources/world-bank-icp")
REPORT_ROOT = Path("reports/sources/world-bank-icp-benchmarks")

TABLES: dict[str, dict[str, str]] = {
    "R1": {"name": "GDP", "family": "summary_results", "unit": "column_specific"},
    "R2": {"name": "Actual individual consumption", "family": "summary_results", "unit": "column_specific"},
    "R3": {"name": "Individual consumption expenditure by households", "family": "summary_results", "unit": "column_specific"},
    "R4": {"name": "Individual consumption expenditure by government", "family": "summary_results", "unit": "column_specific"},
    "R5": {"name": "Collective consumption expenditure by government", "family": "summary_results", "unit": "column_specific"},
    "R6": {"name": "Gross fixed capital formation", "family": "summary_results", "unit": "column_specific"},
    "R7": {"name": "Domestic absorption", "family": "summary_results", "unit": "column_specific"},
    "D1": {"name": "Expenditures", "family": "national_currency_expenditure", "unit": "national currency units, billions"},
    "D2": {"name": "Expenditure shares", "family": "expenditure_share", "unit": "percent of GDP"},
    "D3": {"name": "PPPs", "family": "ppp_conversion_factor", "unit": "local currency units per international dollar (US$=1)"},
    "D4": {"name": "Real expenditures", "family": "real_expenditure", "unit": "US dollars, billions"},
    "D5": {"name": "Real expenditure country and regional shares", "family": "real_expenditure_share", "unit": "percent of world real expenditure"},
    "D6": {"name": "Real expenditures per capita", "family": "real_expenditure_per_capita", "unit": "US dollars per person"},
    "D7": {"name": "Index of real expenditures per capita", "family": "real_expenditure_per_capita_index", "unit": "world equals 100"},
    "D8": {"name": "Price level index", "family": "price_level_index", "unit": "world equals 100"},
    "D9": {"name": "Nominal expenditures", "family": "nominal_expenditure", "unit": "US dollars, billions"},
    "D10": {"name": "Nominal expenditures per capita", "family": "nominal_expenditure_per_capita", "unit": "US dollars per person"},
    "S1": {"name": "Main results and reference data, Pacific Islands", "family": "supplementary_results", "unit": "column_specific"},
    "S2": {"name": "Estimated results and reference data, nonbenchmark economies", "family": "supplementary_results", "unit": "column_specific"},
}

SUMMARY_COLUMN_DEFINITIONS = {
    "00": ("Economy", "entity_label"),
    "01": ("Expenditure based on PPPs", "US dollars, billions"),
    "02": ("Expenditure based on exchange rates", "US dollars, billions"),
    "03": ("Expenditure per capita based on PPPs", "US dollars per person"),
    "04": ("Expenditure per capita based on exchange rates", "US dollars per person"),
    "05": ("Price level index", "world equals 100"),
    "06": ("Expenditure per capita index based on PPPs", "world equals 100"),
    "07": ("Expenditure per capita index based on exchange rates", "world equals 100"),
    "08": ("Expenditure per capita index based on PPPs", "United States equals 100"),
    "09": ("Expenditure per capita index based on exchange rates", "United States equals 100"),
    "10": ("Share of PPP-based world expenditure", "percent"),
    "11": ("Share of exchange-rate-based world expenditure", "percent"),
    "12": ("Share of world population", "percent"),
    "13": ("PPP with US dollar equal to 1", "local currency units per international dollar (US$=1)"),
    "14": ("Exchange rate with US dollar equal to 1", "national currency units per US dollar"),
    "15": ("Population", "millions of persons"),
    "16": ("Expenditure in national currency units", "national currency units; table-specific scale"),
}

REGION_NAMES = {
    "africa", "asia and the pacific", "commonwealth of independent states",
    "eurostat oecd", "latin america", "caribbean", "western asia",
    "pacific islands", "world",
}
MISSING = {"", "..", "...", "…", "na", "n/a", "n.a.", "null", "none", "-", "—"}

def normalized_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()

def number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text.casefold() in MISSING:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None

def column_code(value: Any) -> str | None:
    match = re.fullmatch(r"\s*\(?\s*(\d{1,2})\s*\)?\s*[a-z]?\s*", str(value or ""), re.I)
    return match.group(1).zfill(2) if match else None

def canonical_aggregate(value: Any) -> str:
    text = normalized_name(value)
    aliases = (
        ("gross domestic product", "GDP"),
        ("actual individual consumption", "AIC"),
        ("household and npish consumption", "HOUSEHOLD_CONSUMPTION"),
        ("individual consumption expenditure by households", "HOUSEHOLD_CONSUMPTION"),
        ("individual consumption expenditure by government", "GOVERNMENT_INDIVIDUAL_CONSUMPTION"),
        ("collective consumption expenditure by government", "GOVERNMENT_COLLECTIVE_CONSUMPTION"),
        ("gross fixed capital formation", "GFCF"),
        ("domestic absorption", "DOMESTIC_ABSORPTION"),
    )
    for phrase, key in aliases:
        if phrase in text:
            return key
    # Short labels occur in the workbook's summary tables.
    if re.search(r"\bgdp\b", text):
        return "GDP"
    if re.search(r"\baic\b", text):
        return "AIC"
    return ""

def benchmark_role(release: str, year: int, indicator_name: str = "") -> str:
    if release == "icp_2017_cycle":
        if year == 2011:
            return "revised_2011_benchmark"
        if year == 2017:
            return "original_2017_benchmark"
        return "annual_series_role_not_inferred"
    if release == "icp_2021_saved_report":
        if year == 2017:
            return "revised_2017_benchmark"
        if year == 2021:
            return "2021_benchmark"
        if year in {2018, 2019, 2020}:
            return "interpolation_per_ICP_2021_publication"
        if year in {2022, 2023} and canonical_aggregate(indicator_name) == "GDP":
            return "GDP_PPP_extrapolation_per_ICP_2021_publication"
        return "annual_series_role_not_inferred"
    return "role_not_inferred"

# Workbook spellings that differ from common ICP country-metadata labels.
# An alias is accepted only when its target is present as one unique source-
# reported metadata name; no ISO3 code is assigned from this table alone.
COUNTRY_NAME_ALIAS_TARGETS = {
    "egypt arab rep a": ("egypt arab rep", "egypt arab republic"),
    "sudanb": ("sudan",),
    "russian federationd": ("russian federation",),
    "cape verde": ("cabo verde",),
    "swaziland": ("eswatini",),
    "gambia the": ("gambia",),
}


def country_name_index(root: Path) -> dict[str, list[str]]:
    """Index source-reported country names using the inspector's CSV dialect reader."""
    index: dict[str, list[str]] = defaultdict(list)
    for path in sorted((root / RAW_ROOT).rglob("*.csv")):
        if "country" not in norm(path.stem) or "metadata" not in norm(path.stem):
            continue
        # read_csv detects comma, semicolon, tab and pipe delimiters. Using a
        # default comma reader here silently collapsed non-comma metadata rows.
        for _sheet, headers, rows in read_csv(path):
            positions = {norm(name): i for i, name in enumerate(headers)}
            code_i = next((positions[k] for k in (
                "code", "country code", "economy code", "iso3", "iso3 code",
                "iso alpha 3", "country iso3",
            ) if k in positions), None)
            name_keys = (
                "long name", "country name", "economy name", "economy",
                "name", "short name", "country",
            )
            name_indices = [positions[k] for k in name_keys if k in positions]
            if code_i is None or not name_indices:
                continue
            for row in rows:
                if code_i >= len(row):
                    continue
                code = str(row[code_i] or "").strip().upper()
                if not code:
                    continue
                for name_i in name_indices:
                    if name_i >= len(row):
                        continue
                    key = normalized_name(row[name_i])
                    if key and code not in index[key]:
                        index[key].append(code)
    # Add only explicit, reviewable workbook-to-metadata aliases, and only
    # where the metadata target resolves to one code.
    for alias, targets in COUNTRY_NAME_ALIAS_TARGETS.items():
        codes = {code for target in targets for code in index.get(target, [])}
        if len(codes) == 1:
            index[alias] = [next(iter(codes))]
    return index

def _merged_value(sheet: Any, row: int, col: int, merged_ranges: list[Any]) -> Any:
    value = sheet.cell(row, col).value
    if value is not None:
        return value
    for merged in merged_ranges:
        if merged.min_row <= row <= merged.max_row and merged.min_col <= col <= merged.max_col:
            return sheet.cell(merged.min_row, merged.min_col).value
    return None

def _header_path(sheet: Any, code_row: int, col: int, merged_ranges: list[Any]) -> str:
    parts: list[str] = []
    for row in range(max(1, code_row - 9), code_row):
        value = _merged_value(sheet, row, col, merged_ranges)
        if value is None:
            continue
        label = " ".join(str(value).split())
        if label and label not in parts and not re.match(r"^(table|notes?|source)\b", label, re.I):
            parts.append(label)
    return " | ".join(parts)

def extract_workbook_semantics(path: Path, country_index: dict[str, list[str]],
                               source_file: str | None = None) -> list[dict[str, Any]]:
    workbook = load_workbook(path, read_only=False, data_only=True)
    source_path = source_file or path.name
    output: list[dict[str, Any]] = []
    try:
        for sheet in workbook.worksheets:
            match = re.search(r"\b([RDS])\s*0*(\d+)\b", sheet.title, re.I)
            if not match:
                continue
            table_id = f"{match.group(1).upper()}{int(match.group(2))}"
            definition = TABLES.get(table_id)
            if not definition:
                continue
            merged_ranges = list(sheet.merged_cells.ranges)
            code_rows: list[tuple[int, dict[int, str]]] = []
            for row_no in range(1, sheet.max_row + 1):
                codes = {
                    col: code for col in range(1, sheet.max_column + 1)
                    if (code := column_code(sheet.cell(row_no, col).value)) is not None
                }
                if len(codes) >= 2 and "00" in codes.values():
                    code_rows.append((row_no, codes))
            for code_row, code_columns in code_rows:
                country_col = next(col for col, code in code_columns.items() if code == "00")
                header_paths = {
                    code: _header_path(sheet, code_row, col, merged_ranges)
                    for col, code in code_columns.items()
                }
                next_code_row = next((r for r, _ in code_rows if r > code_row), sheet.max_row + 1)
                for row_no in range(code_row + 1, next_code_row):
                    label_value = sheet.cell(row_no, country_col).value
                    if not isinstance(label_value, str) or not label_value.strip():
                        continue
                    country_name = " ".join(label_value.split())
                    row_values = {
                        code: sheet.cell(row_no, col).value
                        for col, code in code_columns.items() if code != "00"
                    }
                    if not any(number(value) is not None for value in row_values.values()):
                        continue
                    entity_norm = normalized_name(country_name)
                    is_total = entity_norm.startswith("total")
                    is_region = entity_norm in REGION_NAMES
                    matches = country_index.get(entity_norm, [])
                    country_code = matches[0] if len(matches) == 1 and not (is_total or is_region) else ""
                    identity_status = (
                        "aggregate_or_region" if is_total or is_region else
                        "exact_unique_country_name_match" if len(matches) == 1
                        and entity_norm not in COUNTRY_NAME_ALIAS_TARGETS else
                        "explicit_country_name_alias_match" if len(matches) == 1 else
                        "ambiguous_exact_country_name" if len(matches) > 1 else
                        "no_exact_country_name_match"
                    )
                    for code, raw_value in row_values.items():
                        summary = SUMMARY_COLUMN_DEFINITIONS.get(code)
                        header = header_paths.get(code, "")
                        measure_name = summary[0] if definition["family"] in {"summary_results", "supplementary_results"} and summary else header
                        unit = summary[1] if definition["family"] in {"summary_results", "supplementary_results"} and summary else definition["unit"]
                        if code == "16" and table_id.startswith("R"):
                            unit = "national currency units, billions"
                        elif code == "16" and table_id == "S1":
                            unit = "national currency units, millions"
                        parsed = number(raw_value)
                        output.append({
                            "source_release": "icp_2011_cycle",
                            "source_file": source_path,
                            "sheet": sheet.title,
                            "table_id": table_id,
                            "table_name": definition["name"],
                            "table_family": definition["family"],
                            "reference_year": 2011,
                            "country_name_raw": country_name,
                            "country_code": country_code,
                            "country_identity_status": identity_status,
                            "entity_type": "total" if is_total else "region" if is_region else "country_candidate",
                            "column_code": code,
                            "column_header_path": header,
                            "measure_name": measure_name,
                            "unit": unit,
                            "unit_status": "table_or_column_labelled",
                            "value_raw": "" if raw_value is None else str(raw_value),
                            "value": parsed,
                            "observation_status": "missing" if parsed is None else "reported_value",
                            "source_row": row_no,
                            "source_column": code_columns[next(c for c, v in code_columns.items() if v == code)],
                            "source_cell": sheet.cell(row_no, next(c for c, v in code_columns.items() if v == code)).coordinate,
                            "aggregate_key": (
                                canonical_aggregate(definition["name"])
                                if definition["family"] == "summary_results"
                                else canonical_aggregate(measure_name + " " + header)
                            ),
                            "direct_ppp_comparison_candidate": table_id == "D3" and not (is_total or is_region),
                        })
    finally:
        workbook.close()
    return output

def latest_inspection_observations(root: Path) -> tuple[Path, list[dict[str, str]]]:
    candidates = sorted((root / INSPECTION_ROOT).glob("inspection_*/observations_long.csv"))
    if not candidates:
        raise ICPAssessmentError("Run tools.assess_world_bank_icp_exports before benchmark comparison")
    path = candidates[-1]
    with path.open(encoding="utf-8", newline="") as stream:
        return path, list(csv.DictReader(stream))

def compare(root: str | Path = ROOT, retrieved_at: datetime | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    raw_root = root / RAW_ROOT
    workbook_paths = [p for p in raw_root.rglob("*.xlsx") if is_icp2011_original_workbook(p)]
    if not workbook_paths:
        raise ICPAssessmentError("Original ICP 2011 results workbook is not present")
    if len(workbook_paths) != 1:
        raise ICPAssessmentError(f"Expected one original ICP 2011 workbook, found {len(workbook_paths)}")
    country_index = country_name_index(root)
    semantic_rows = extract_workbook_semantics(
        workbook_paths[0], country_index,
        source_file=workbook_paths[0].relative_to(root).as_posix(),
    )
    if not semantic_rows:
        raise ICPAssessmentError(
            "No semantic table rows were recognized; inspect workbook column-code rows before comparison"
        )
    inspection_path, observations = latest_inspection_observations(root)

    # Original ICP 2011 D3 PPP factors versus the ICP 2017 cycle's revised 2011 PPP factors.
    revised_2011: dict[tuple[str, str], dict[str, str]] = {}
    for item in observations:
        if (item.get("source_release") != "icp_2017_cycle"
                or item.get("year") != "2011"
                or item.get("classification_code") != "PPPGlob"
                or not item.get("country_code")
                or not item.get("value")):
            continue
        aggregate = canonical_aggregate(item.get("indicator_name", ""))
        if aggregate:
            revised_2011[(item["country_code"], aggregate)] = item

    comparisons: list[dict[str, Any]] = []
    comparison_coverage: list[dict[str, Any]] = []
    d3_rows = [r for r in semantic_rows if r["table_id"] == "D3"]
    matched_2011_keys: set[tuple[str, str]] = set()
    for item in d3_rows:
        if not item["country_code"]:
            match_status = "country_identity_unresolved"
            revised = None
        elif not item["aggregate_key"]:
            match_status = "aggregate_identity_unresolved"
            revised = None
        else:
            revised = revised_2011.get((item["country_code"], item["aggregate_key"]))
            match_status = "matched" if revised is not None and item["value"] is not None else (
                "missing_original_2011_value" if item["value"] is None else
                "missing_revised_2011_observation"
            )
        comparison_coverage.append({
            "comparison_type": "original_2011_vs_revised_2011",
            "country_code": item["country_code"],
            "country_name": item["country_name_raw"],
            "aggregate_key": item["aggregate_key"],
            "classification_code": "PPPGlob",
            "indicator_code": revised.get("indicator_code", "") if revised else "",
            "match_status": match_status,
            "source_a_value": item["value"],
            "source_b_value": revised.get("value", "") if revised else "",
        })
        if not item["country_code"] or not item["aggregate_key"] or revised is None or item["value"] is None:
            continue
        matched_2011_keys.add((item["country_code"], item["aggregate_key"]))
        old_value = float(item["value"])
        new_value = float(revised["value"])
        comparisons.append({
            "comparison_type": "original_2011_vs_revised_2011",
            "source_a_release": "icp_2011_cycle",
            "source_a_year": 2011,
            "source_a_role": "original_2011_benchmark",
            "source_b_release": "icp_2017_cycle",
            "source_b_year": 2011,
            "source_b_role": "revised_2011_benchmark",
            "country_code": item["country_code"],
            "country_name": item["country_name_raw"],
            "aggregate_key": item["aggregate_key"],
            "classification_code": "PPPGlob",
            "indicator_code": revised.get("indicator_code", ""),
            "source_a_value": old_value,
            "source_b_value": new_value,
            "absolute_difference": new_value - old_value,
            "percent_difference": ((new_value / old_value) - 1.0) * 100 if old_value else None,
            "unit": "local currency units per international dollar (US$=1)",
            "comparability_status": "direct_measure_match_exact_country_and_aggregate",
            "source_a_file": item["source_file"],
            "source_a_sheet": item["sheet"],
            "source_a_cell": item["source_cell"],
            "source_b_file": revised.get("source_file", ""),
            "source_b_row": revised.get("source_row", ""),
        })

    for key, revised in revised_2011.items():
        if key not in matched_2011_keys:
            comparison_coverage.append({
                "comparison_type": "original_2011_vs_revised_2011",
                "country_code": key[0], "country_name": revised.get("country_name", ""),
                "aggregate_key": key[1], "classification_code": "PPPGlob",
                "indicator_code": revised.get("indicator_code", ""),
                "match_status": "missing_original_2011_observation",
                "source_a_value": "", "source_b_value": revised.get("value", ""),
            })

    # Original 2017 benchmark versus revised 2017 benchmark, using exact source keys.
    original_2017: dict[tuple[str, str, str], dict[str, str]] = {}
    revised_2017: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in observations:
        if item.get("year") != "2017" or not item.get("country_code"):
            continue
        key = (item["country_code"], item.get("classification_code", ""),
               item.get("indicator_code", ""))
        if item.get("source_release") == "icp_2017_cycle":
            original_2017[key] = item
        elif item.get("source_release") == "icp_2021_saved_report":
            revised_2017[key] = item
    original_scope = {
        "countries": {item.get("country_code", "") for item in observations
                      if item.get("source_release") == "icp_2017_cycle"},
        "classifications": {item.get("classification_code", "") for item in observations
                            if item.get("source_release") == "icp_2017_cycle"},
        "indicators": {item.get("indicator_code", "") for item in observations
                       if item.get("source_release") == "icp_2017_cycle"},
    }
    revised_scope = {
        "countries": {item.get("country_code", "") for item in observations
                      if item.get("source_release") == "icp_2021_saved_report"},
        "classifications": {item.get("classification_code", "") for item in observations
                            if item.get("source_release") == "icp_2021_saved_report"},
        "indicators": {item.get("indicator_code", "") for item in observations
                       if item.get("source_release") == "icp_2021_saved_report"},
    }
    for key in sorted(set(original_2017) | set(revised_2017)):
        old = original_2017.get(key)
        new = revised_2017.get(key)
        if old is None:
            if key[0] not in original_scope["countries"]:
                match_status = "country_not_in_original_export_scope"
            elif key[1] not in original_scope["classifications"]:
                match_status = "classification_not_in_original_export_scope"
            elif key[2] not in original_scope["indicators"]:
                match_status = "indicator_not_in_original_export_scope"
            else:
                match_status = "no_original_2017_observation_in_selected_scope"
        elif new is None:
            if key[0] not in revised_scope["countries"]:
                match_status = "country_not_in_revised_export_scope"
            elif key[1] not in revised_scope["classifications"]:
                match_status = "classification_not_in_revised_export_scope"
            elif key[2] not in revised_scope["indicators"]:
                match_status = "indicator_not_in_revised_export_scope"
            else:
                match_status = "no_revised_2017_observation_in_selected_scope"
        elif not old.get("value"):
            match_status = "missing_original_2017_value"
        elif not new.get("value"):
            match_status = "missing_revised_2017_value"
        else:
            match_status = "matched"
        comparison_coverage.append({
            "comparison_type": "original_2017_vs_revised_2017",
            "country_code": key[0],
            "country_name": (old or new or {}).get("country_name", ""),
            "aggregate_key": canonical_aggregate((old or new or {}).get("indicator_name", "")),
            "classification_code": key[1],
            "indicator_code": key[2],
            "match_status": match_status,
            "source_a_value": old.get("value", "") if old else "",
            "source_b_value": new.get("value", "") if new else "",
        })
        if old is None or new is None or not old.get("value") or not new.get("value"):
            continue
        old_value, new_value = float(old["value"]), float(new["value"])
        comparisons.append({
            "comparison_type": "original_2017_vs_revised_2017",
            "source_a_release": "icp_2017_cycle",
            "source_a_year": 2017,
            "source_a_role": "original_2017_benchmark",
            "source_b_release": "icp_2021_saved_report",
            "source_b_year": 2017,
            "source_b_role": "revised_2017_benchmark",
            "country_code": key[0],
            "country_name": old.get("country_name", ""),
            "aggregate_key": canonical_aggregate(old.get("indicator_name", "")),
            "classification_code": key[1],
            "indicator_code": key[2],
            "source_a_value": old_value,
            "source_b_value": new_value,
            "absolute_difference": new_value - old_value,
            "percent_difference": ((new_value / old_value) - 1.0) * 100 if old_value else None,
            "unit": "source-reported; classification and indicator keys identical",
            "comparability_status": "exact_country_classification_indicator_key_match",
            "source_a_file": old.get("source_file", ""),
            "source_a_sheet": old.get("sheet", ""),
            "source_a_cell": "",
            "source_b_file": new.get("source_file", ""),
            "source_b_row": new.get("source_row", ""),
        })

    coverage_counts: dict[tuple[str, int, str, str, str, str], dict[str, int]] = {}
    for item in observations:
        release = item.get("source_release", "")
        year = int(item["year"]) if item.get("year", "").isdigit() else 0
        key = (release, year, item.get("country_code") or item.get("country_name", ""),
               item.get("classification_code", ""), item.get("indicator_code", ""),
               item.get("indicator_name", ""))
        counts = coverage_counts.setdefault(key, {"reported": 0, "missing": 0})
        counts["missing" if not item.get("value") else "reported"] += 1
    coverage_rows = [{
        "source_release": key[0], "year": key[1],
        "benchmark_role": benchmark_role(key[0], key[1], key[5]),
        "country_code_or_name": key[2], "classification_code": key[3],
        "indicator_code": key[4], "indicator_name": key[5],
        "reported_observation_count": counts["reported"],
        "missing_observation_count": counts["missing"],
    } for key, counts in sorted(coverage_counts.items())]

    stamp = retrieved_at or datetime.now(timezone.utc)
    report_id = "benchmark_assessment_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = root / REPORT_ROOT / report_id
    report_dir.mkdir(parents=True, exist_ok=False)

    def write_csv(name: str, rows: list[dict[str, Any]], fields: list[str]) -> None:
        with (report_dir / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    semantic_fields = list(semantic_rows[0]) if semantic_rows else [
        "source_release", "source_file", "sheet", "table_id", "table_name",
        "table_family", "reference_year", "country_name_raw", "country_code",
        "country_identity_status", "entity_type", "column_code", "column_header_path",
        "measure_name", "unit", "unit_status", "value_raw", "value",
        "observation_status", "source_row", "source_column", "source_cell",
        "aggregate_key", "direct_ppp_comparison_candidate"]
    comparison_fields = list(comparisons[0]) if comparisons else [
        "comparison_type", "source_a_release", "source_a_year", "source_a_role",
        "source_b_release", "source_b_year", "source_b_role", "country_code",
        "country_name", "aggregate_key", "classification_code", "indicator_code",
        "source_a_value", "source_b_value", "absolute_difference",
        "percent_difference", "unit", "comparability_status", "source_a_file",
        "source_a_sheet", "source_a_cell", "source_b_file", "source_b_row"]
    coverage_fields = list(coverage_rows[0]) if coverage_rows else [
        "source_release", "year", "benchmark_role", "country_code_or_name",
        "classification_code", "indicator_code", "indicator_name",
        "reported_observation_count", "missing_observation_count"]
    comparison_coverage_fields = list(comparison_coverage[0]) if comparison_coverage else [
        "comparison_type", "country_code", "country_name", "aggregate_key",
        "classification_code", "indicator_code", "match_status",
        "source_a_value", "source_b_value"]
    write_csv("icp_2011_workbook_semantic_observations.csv", semantic_rows, semantic_fields)
    write_csv("benchmark_comparisons.csv", comparisons, comparison_fields)
    write_csv("benchmark_comparison_coverage.csv", comparison_coverage, comparison_coverage_fields)
    write_csv("benchmark_coverage.csv", coverage_rows, coverage_fields)

    result = {
        "assessment": "world_bank_icp_benchmark_semantic_extraction_and_comparison",
        "report_id": report_id,
        "workbook_semantic_observation_count": len(semantic_rows),
        "workbook_table_count": len({row["table_id"] for row in semantic_rows}),
        "workbook_missing_expected_tables": sorted(
            set(TABLES) - {row["table_id"] for row in semantic_rows}
        ),
        "workbook_exact_country_name_match_count": sum(
            row["country_identity_status"] == "exact_unique_country_name_match"
            for row in semantic_rows),
        "workbook_unmatched_country_candidate_count": sum(
            row["entity_type"] == "country_candidate" and not row["country_code"]
            for row in semantic_rows),
        "original_2011_vs_revised_2011_comparison_count": sum(
            row["comparison_type"] == "original_2011_vs_revised_2011" for row in comparisons),
        "original_2017_vs_revised_2017_comparison_count": sum(
            row["comparison_type"] == "original_2017_vs_revised_2017" for row in comparisons),
        "comparison_count": len(comparisons),
        "comparison_coverage_row_count": len(comparison_coverage),
        "comparison_coverage_matched_count": sum(
            row["match_status"] == "matched" for row in comparison_coverage
        ),
        "comparison_coverage_unmatched_count": sum(
            row["match_status"] != "matched" for row in comparison_coverage
        ),
        "comparison_coverage_status_counts": {
            status: sum(row["match_status"] == status for row in comparison_coverage)
            for status in sorted({row["match_status"] for row in comparison_coverage})
        },
        "inspection_observations_source": inspection_path.relative_to(root).as_posix(),
        "outputs": {
            "workbook_semantic_observations": (report_dir / "icp_2011_workbook_semantic_observations.csv").relative_to(root).as_posix(),
            "benchmark_comparisons": (report_dir / "benchmark_comparisons.csv").relative_to(root).as_posix(),
            "benchmark_comparison_coverage": (report_dir / "benchmark_comparison_coverage.csv").relative_to(root).as_posix(),
            "benchmark_coverage": (report_dir / "benchmark_coverage.csv").relative_to(root).as_posix(),
        },
        "interpretation": {
            "country_identity": "unique exact normalized matches across source-reported country metadata name fields receive a code; a small explicit workbook-name alias list is applied only when its target resolves to one unique metadata code",
            "2011_comparison": "original workbook D3 PPP factors compared only with ICP 2017-cycle 2011 PPPGlob observations for the same country and aggregate",
            "2017_comparison": "original and revised 2017 values compared only on exact country, classification and indicator code keys",
            "annual_roles": "only roles explicitly documented for ICP 2021 are assigned; other annual-series roles remain unclassified",
            "units": "table and column units remain explicit; unlike measures are not compared",
            "missingness": "missing values remain in semantic extracts and coverage; comparisons require two reported values; 2017 coverage distinguishes country, classification and indicator exclusions from absent observations inside the selected export scope",
        },
        "side_effects": {
            "raw_data_written": False, "project_database_written": False,
            "game_database_written": False, "approval_created": False,
            "source_selection_changed": False, "canonical_data_promoted": False,
        },
    }
    with (report_dir / "assessment.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        result = compare(args.root)
    except (ICPAssessmentError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
