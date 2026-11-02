"""Read-only country-year comparison of IMF WEO and World Bank WDI.

Uses the recorded October 2026 IMF CSV and live WDI API observations. The WDI
API is rolling rather than an immutable release, so results are exploratory
comparison evidence and are not suitable for approval or source promotion.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import assess_imf_weo as imf
from tools import assess_world_bank_wdi as wdi

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/sources/imf-wdi-comparison"
START_YEAR = 2015
END_YEAR = 2025

PAIRS = {
    "NY.GDP.MKTP.CD": {
        "field_id": 15, "imf_code": "NGDPD", "imf_multiplier": 1_000_000_000,
        "unit": "current_usd", "comparison": "nominal GDP at current prices",
    },
    "NY.GDP.PCAP.CD": {
        "field_id": 16, "imf_code": "NGDPDPC", "imf_multiplier": 1,
        "unit": "current_usd_per_person", "comparison": "GDP per capita at current prices",
    },
    "NY.GDP.MKTP.PP.CD": {
        "field_id": 18, "imf_code": "PPPGDP", "imf_multiplier": 1_000_000_000,
        "unit": "current_international_dollars", "comparison": "GDP at current PPP prices; benchmark compatibility requires review",
    },
    "FP.CPI.TOTL.ZG": {
        "field_id": 20, "imf_code": "PCPIPCH", "imf_multiplier": 1,
        "unit": "percent_annual", "comparison": "annual CPI inflation; period-average convention requires review",
    },
    "SL.UEM.TOTL.ZS": {
        "field_id": 21, "imf_code": "LUR", "imf_multiplier": 1,
        "unit": "percent_labour_force", "comparison": "unemployment rate; methodology and IMF unit require review",
    },
}


class ComparisonError(RuntimeError):
    """Input, identity, or provider response contract failure."""


def _identity_by_code(path: Path) -> dict[str, str]:
    index = imf.identity_index(path)
    result: dict[str, str] = {}
    for code, records in index.items():
        game_ids = {r.get("game_id") for r in records if r.get("game_id")}
        if len(game_ids) == 1:
            result[code] = next(iter(game_ids))
    return result


def read_imf_observations(
    csv_path: Path, identity_path: Path, start_year: int, end_year: int
) -> tuple[dict[str, dict[tuple[str, int], dict[str, Any]]], dict[str, set[str]]]:
    imf.fingerprint(csv_path, imf.EXPECTED["csv"])
    code_to_game = _identity_by_code(identity_path)
    output: dict[str, dict[tuple[str, int], dict[str, Any]]] = {
        code: {} for code in PAIRS
    }
    seen_series: set[tuple[str, str]] = set()
    unmatched_codes: dict[str, set[str]] = defaultdict(set)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"SERIES_CODE", "COUNTRY", "FREQUENCY", "UNIT", "SCALE", "LATEST_ACTUAL_ANNUAL_DATA"}
        if required - set(reader.fieldnames or []):
            raise ComparisonError(f"IMF CSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            parts = (row.get("SERIES_CODE") or "").split(".")
            if len(parts) != 3 or parts[1] not in output or parts[2] != "A":
                continue
            indicator, source_code = parts[1], parts[0]
            if row.get("FREQUENCY") != "Annual":
                continue
            game_id = code_to_game.get(source_code)
            if not game_id:
                unmatched_codes[indicator].add(source_code)
                continue
            series_key = (indicator, source_code)
            if series_key in seen_series:
                raise ComparisonError(f"Duplicate IMF country series: {indicator}/{source_code}")
            seen_series.add(series_key)
            contract = PAIRS[next(k for k, v in PAIRS.items() if v["imf_code"] == indicator)]
            if indicator in {"NGDPD", "NGDPDPC"} and row.get("UNIT") != "US dollar":
                raise ComparisonError(f"Unexpected IMF unit for {indicator}/{source_code}: {row.get('UNIT')!r}")
            if indicator in {"NGDPD", "PPPGDP"} and row.get("SCALE") != "Billions":
                raise ComparisonError(f"Unexpected IMF scale for {indicator}/{source_code}: {row.get('SCALE')!r}")
            actual_text = (row.get("LATEST_ACTUAL_ANNUAL_DATA") or "").strip()
            actual_match = re.fullmatch(r"(\\d{4})", actual_text)
            latest_actual_year = int(actual_match.group(1)) if actual_match else None
            for year in range(start_year, end_year + 1):
                raw = (row.get(str(year)) or "").strip()
                if not raw:
                    continue
                try:
                    value = float(raw) * contract["imf_multiplier"]
                except ValueError as exc:
                    raise ComparisonError(f"Non-numeric IMF value {indicator}/{source_code}/{year}") from exc
                if not math.isfinite(value):
                    raise ComparisonError(f"Non-finite IMF value {indicator}/{source_code}/{year}")
                status = (
                    "actual_per_weo_metadata" if latest_actual_year is not None and year <= latest_actual_year
                    else "after_latest_actual" if latest_actual_year is not None
                    else "status_unclassified"
                )
                output[indicator][(game_id, year)] = {
                    "value": value, "game_id": game_id, "source_code": source_code,
                    "country_name": row.get("COUNTRY") or source_code,
                    "latest_actual_annual_data": actual_text or None,
                    "status_hint": status,
                    "reporting_year_months": row.get("START_END_MONTHS_OF_REPORTING_YEAR") or None,
                }
    return output, unmatched_codes


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1)]


def build_comparison(
    csv_path: Path = imf.CSV_PATH,
    identity_path: Path = imf.IDENTITY,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    get_json=wdi._get_json,
) -> dict[str, Any]:
    if start_year < 1900 or end_year < start_year or end_year > 2100:
        raise ComparisonError("Invalid comparison year range")
    imf_data, unmatched_imf_codes = read_imf_observations(csv_path, identity_path, start_year, end_year)
    code_to_game = _identity_by_code(identity_path)
    country_regions = wdi.fetch_country_regions(get_json)
    indicators: list[dict[str, Any]] = []
    all_pairs: list[dict[str, Any]] = []

    for wdi_code, contract in PAIRS.items():
        metadata = wdi.fetch_indicator_metadata(wdi_code, get_json)
        records = wdi.fetch_indicator_observations(wdi_code, start_year, end_year, get_json)
        wdi_values: dict[tuple[str, int], dict[str, Any]] = {}
        unmatched_wdi_codes: set[str] = set()
        for row in records:
            source_code = row.get("countryiso3code")
            if not isinstance(source_code, str) or len(source_code) != 3:
                continue
            region = country_regions.get(source_code)
            if region is None:
                raise ComparisonError(f"WDI country {source_code} missing from country catalogue")
            if region["region_id"] == "NA" or region["region_value"].casefold() == "aggregates":
                continue
            game_id = code_to_game.get(source_code)
            if not game_id:
                unmatched_wdi_codes.add(source_code)
                continue
            try:
                year = int(row.get("date"))
            except (TypeError, ValueError):
                continue
            if row.get("value") is None:
                continue
            try:
                value = float(row["value"])
            except (TypeError, ValueError) as exc:
                raise ComparisonError(f"Invalid WDI value {wdi_code}/{source_code}/{year}") from exc
            if not math.isfinite(value):
                raise ComparisonError(f"Non-finite WDI value {wdi_code}/{source_code}/{year}")
            key = (game_id, year)
            if key in wdi_values:
                raise ComparisonError(f"Duplicate WDI country-year: {wdi_code}/{source_code}/{year}")
            wdi_values[key] = {
                "value": value, "source_code": source_code,
                "country_name": (row.get("country") or {}).get("value") or source_code,
            }

        imf_code = contract["imf_code"]
        left = imf_data[imf_code]
        shared = sorted(set(left) & set(wdi_values))
        imf_only = sorted(set(left) - set(wdi_values))
        wdi_only = sorted(set(wdi_values) - set(left))
        comparisons = []
        abs_pct: list[float] = []
        abs_pp: list[float] = []
        over_five = 0
        for key in shared:
            a, b = left[key], wdi_values[key]
            difference = a["value"] - b["value"]
            relative = difference / b["value"] * 100 if b["value"] != 0 else None
            if relative is not None:
                abs_pct.append(abs(relative))
                if abs(relative) > 5:
                    over_five += 1
            if contract["field_id"] in {20, 21}:
                abs_pp.append(abs(difference))
            item = {
                "field_id": contract["field_id"], "wdi_indicator": wdi_code,
                "imf_indicator": imf_code, "game_id": key[0], "year": key[1],
                "imf_country": a["country_name"], "wdi_country": b["country_name"],
                "imf_source_code": a["source_code"], "wdi_iso3": b["source_code"],
                "imf_value_canonical_unit": a["value"], "wdi_value_canonical_unit": b["value"],
                "absolute_difference": difference, "relative_difference_percent": relative,
                "imf_status_hint": a["status_hint"],
                "imf_latest_actual_annual_data": a["latest_actual_annual_data"],
                "imf_reporting_year_months": a["reporting_year_months"],
                "wdi_status": "not_classified_by_this_comparison",
            }
            comparisons.append(item)
            all_pairs.append(item)

        indicators.append({
            **contract, "wdi_indicator": wdi_code, "imf_indicator": imf_code,
            "wdi_metadata": metadata,
            "imf_country_count": len({k[0] for k in left}),
            "wdi_country_count": len({k[0] for k in wdi_values}),
            "matched_country_count": len({k[0] for k in shared}),
            "matched_country_year_count": len(shared),
            "unmatched_imf_source_codes": sorted(unmatched_imf_codes[imf_code]),
            "unmatched_wdi_iso3_codes": sorted(unmatched_wdi_codes),
            "imf_only_country_year_count": len(imf_only),
            "wdi_only_country_year_count": len(wdi_only),
            "mean_absolute_relative_difference_percent": statistics.mean(abs_pct) if abs_pct else None,
            "median_absolute_relative_difference_percent": statistics.median(abs_pct) if abs_pct else None,
            "p95_absolute_relative_difference_percent": _percentile(abs_pct, 0.95),
            "country_years_over_5_percent_difference": over_five,
            "mean_absolute_difference_percentage_points": statistics.mean(abs_pp) if abs_pp else None,
            "comparability_notes": {
                "definition": contract["comparison"],
                "wdi_source_organization": metadata.get("source_organization"),
                "wdi_source_note": metadata.get("source_note"),
                "wdi_api_last_updated": metadata.get("api_last_updated"),
                "imf_status": "latest-actual metadata used only as a hint; fiscal-year labels and PPPGDP remain unclassified",
                "vintage": "IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned",
            },
            "country_year_comparisons": comparisons,
        })

    return {
        "schema_version": 1,
        "assessment": "imf_weo_world_bank_wdi_country_year_comparison",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start_year": start_year, "end_year": end_year},
        "imf_snapshot": imf.fingerprint(csv_path, imf.EXPECTED["csv"]),
        "identity_registry": imf.fingerprint(identity_path),
        "wdi_api_base": wdi.API,
        "wdi_retrieval_model": "live_rolling_api_not_immutable_snapshot",
        "identity_join": "IMF source code and WDI ISO3 are mapped through the existing project identity registry to game_id; no new crosswalk assignments are made.",
        "indicators": indicators,
        "side_effects": {
            "immutable_snapshots_acquired": False, "source_registry_changed": False,
            "source_selection_policy_changed": False, "canonical_database_written": False,
            "release_promoted": False, "approval_created": False,
        },
    }


def write_reports(report: dict[str, Any], output_root: Path = OUTPUT) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    target.mkdir(parents=True, exist_ok=False)
    (target / "assessment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# IMF WEO and World Bank WDI country-year comparison", "",
        f"- Checked: {report['checked_at']}",
        f"- Period: {report['period']['start_year']}–{report['period']['end_year']}",
        "- Read-only; IMF snapshot fixed, WDI API live/rolling; no policy or database changes", "",
        "| Field | IMF | WDI | Matched countries | Matched country-years | IMF-only years | WDI-only years | Median absolute difference |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in report["indicators"]:
        median = item["median_absolute_relative_difference_percent"]
        median_text = f"{median:.2f}%" if median is not None else "n/a"
        lines.append(
            f"| {item['field_id']} | {item['imf_indicator']} | {item['wdi_indicator']} | "
            f"{item['matched_country_count']} | {item['matched_country_year_count']} | "
            f"{item['imf_only_country_year_count']} | {item['wdi_only_country_year_count']} | {median_text} |"
        )
    for item in report["indicators"]:
        notes = item["comparability_notes"]
        lines.extend(["", f"## Field {item['field_id']}: {item['imf_indicator']} vs {item['wdi_indicator']}", "",
            f"- Definition: {notes['definition']}",
            f"- WDI originating organization: {notes['wdi_source_organization'] or 'not supplied'}",
            f"- WDI source note: {notes['wdi_source_note'] or 'not supplied'}",
            f"- WDI API last updated: {notes['wdi_api_last_updated'] or 'not supplied'}",
            f"- Mean absolute relative difference: {item['mean_absolute_relative_difference_percent']}",
            f"- Median absolute relative difference: {item['median_absolute_relative_difference_percent']}",
            f"- 95th percentile absolute relative difference: {item['p95_absolute_relative_difference_percent']}",
            f"- Country-years with >5% relative difference: {item['country_years_over_5_percent_difference']}",
            f"- Mean absolute difference (percentage points, fields 20/21): {item['mean_absolute_difference_percentage_points']}",
            f"- Vintage caveat: {notes['vintage']}"])
    lines.extend(["", "## Interpretation limits", "",
        "- A shared country-year is a numerical comparison, not proof of semantic equivalence.",
        "- IMF values in Billions are converted to absolute dollars; GDP per capita and percentage series are not rescaled.",
        "- IMF actual/estimate classification is only a hint from LATEST_ACTUAL_ANNUAL_DATA; fiscal-year labels and PPPGDP are unclassified.",
        "- WDI observation status is not inferred. WDI is retrieved live and may change between runs.",
        "- Fields 18, 20 and 21 require explicit definition review before a policy decision; PPP benchmark, CPI period convention and unemployment methodology/unit remain material caveats.",
        "- No source-selection, release, approval, or database action is performed."])
    (target / "assessment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows = [row for item in report["indicators"] for row in item["country_year_comparisons"]]
    fields = list(rows[0]) if rows else [
        "field_id", "wdi_indicator", "imf_indicator", "game_id", "year",
        "imf_country", "wdi_country", "imf_source_code", "wdi_iso3",
        "imf_value_canonical_unit", "wdi_value_canonical_unit",
        "absolute_difference", "relative_difference_percent", "imf_status_hint",
        "imf_latest_actual_annual_data", "imf_reporting_year_months", "wdi_status",
    ]
    with (target / "country_year_comparison.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=START_YEAR)
    parser.add_argument("--end-year", type=int, default=END_YEAR)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = build_comparison(start_year=args.start_year, end_year=args.end_year)
        target = write_reports(report, args.output_root)
    except (ComparisonError, imf.AssessmentError, wdi.AssessmentError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "assessment": report["assessment"], "indicators": len(report["indicators"]),
        "period": report["period"], "report_directory": str(target),
        "matched_country_years": {str(x["field_id"]): x["matched_country_year_count"] for x in report["indicators"]},
        "database_written": False, "policy_changed": False, "release_promoted": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
