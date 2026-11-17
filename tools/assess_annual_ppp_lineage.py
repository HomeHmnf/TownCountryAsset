"""Assess annual PPP lineage across captured ICP, WDI and IMF WEO sources.

Read-only research output. Source releases and annual roles remain separate;
cross-source arithmetic is diagnostic unless currency/unit lineage is verified.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import assess_imf_weo as imf
from tools import assess_world_bank_icp_benchmarks as icp_benchmarks
from tools import acquire_world_bank_wdi_snapshot as wdi_snapshot

ROOT = Path(__file__).resolve().parents[1]
ICP_INSPECTION = Path("reports/sources/world-bank-icp")
ICP_BENCHMARKS = Path("reports/sources/world-bank-icp-benchmarks")
WDI_MANIFESTS = Path("data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators")
OUTPUT = ROOT / "reports/sources/annual-ppp-lineage"
WEO_CSV = imf.CSV_PATH
IDENTITY = imf.IDENTITY


class LineageError(RuntimeError):
    """Invalid, missing or ambiguous source evidence."""


def _number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _latest_file(pattern: str, directory: Path, label: str) -> Path:
    candidates = sorted(directory.glob(pattern))
    if not candidates:
        raise LineageError(f"No {label} found under {directory}")
    return candidates[-1]


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise LineageError(f"Cannot read {path}: {exc}") from exc


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_weo(path: Path, allowed_country_codes: set[str] | None = None) -> dict[tuple[str, int], dict[str, Any]]:
    imf.fingerprint(path, imf.EXPECTED["csv"])
    output: dict[tuple[str, int], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"SERIES_CODE", "COUNTRY", "UNIT", "SCALE"}
        if required - set(reader.fieldnames or []):
            raise LineageError(f"WEO CSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            parts = (row.get("SERIES_CODE") or "").split(".")
            if len(parts) != 3 or parts[1] not in {"NGDP", "PPPGDP"} or parts[2] != "A":
                continue
            code = parts[0]
            if len(code) != 3 or not code.isalpha():
                continue
            if allowed_country_codes is not None and code not in allowed_country_codes:
                continue
            for year_text in row:
                if not (len(year_text) == 4 and year_text.isdigit()):
                    continue
                value = _number(row.get(year_text))
                key = (code, int(year_text))
                item = output.setdefault(key, {"country_name": row.get("COUNTRY", "")})
                item[parts[1]] = value
                item[f"{parts[1]}_unit"] = row.get("UNIT", "")
                item[f"{parts[1]}_scale"] = row.get("SCALE", "")
                item[f"{parts[1]}_series_code"] = row.get("SERIES_CODE", "")
    return output


def _load_icp_rows(inspection: Path, benchmark_report: Path) -> list[dict[str, Any]]:
    observations = _read_csv(inspection / "observations_long.csv")
    rows: list[dict[str, Any]] = []
    for item in observations:
        if (item.get("indicator_code") != "1000000"
                or item.get("classification_code") != "PPPGlob"
                or not item.get("country_code")
                or not item.get("year", "").isdigit()):
            continue
        year = int(item["year"])
        release = item.get("source_release", "")
        role = icp_benchmarks.benchmark_role(release, year, item.get("indicator_name", ""))
        rows.append({
            "country_code": item["country_code"], "country_name": item.get("country_name", ""),
            "year": year, "source": "ICP", "source_release": release,
            "lineage_role": role, "metric": "GDP_PPP_conversion_factor",
            "value": _number(item.get("value")),
            "unit": "source-reported ICP PPPGlob GDP factor; currency denomination retained from release",
            "source_file": item.get("source_file", ""), "source_row": item.get("source_row", ""),
            "classification_code": item.get("classification_code", ""),
            "indicator_code": item.get("indicator_code", ""),
            "observation_status": item.get("observation_status", ""),
            "comparability_status": "not_cross_release_normalized_currency_unit_review_required",
        })

    # The original 2011 workbook D3 GDP PPP is a separate original benchmark.
    semantic_path = benchmark_report / "icp_2011_workbook_semantic_observations.csv"
    if semantic_path.is_file():
        for item in _read_csv(semantic_path):
            if (item.get("table_id") != "D3" or item.get("aggregate_key") != "GDP"
                    or not item.get("country_code")):
                continue
            rows.append({
                "country_code": item["country_code"], "country_name": item.get("country_name_raw", ""),
                "year": 2011, "source": "ICP", "source_release": "icp_2011_cycle",
                "lineage_role": "original_2011_benchmark", "metric": "GDP_PPP_conversion_factor",
                "value": _number(item.get("value")), "unit": item.get("unit", ""),
                "source_file": item.get("source_file", ""), "source_row": item.get("source_row", ""),
                "classification_code": "", "indicator_code": "D3_GDP",
                "observation_status": item.get("observation_status", ""),
                "comparability_status": "not_cross_release_normalized_currency_unit_review_required",
            })
    return rows


def assess(
    *, repository_root: str | Path = ROOT, wdi_manifest: str | Path | None = None,
    weo_csv: str | Path = WEO_CSV,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    inspection = _latest_file("inspection_*/observations_long.csv", root / ICP_INSPECTION,
                              "ICP export-inspection observation file").parent
    benchmark_report = _latest_file("benchmark_assessment_*/icp_2011_workbook_semantic_observations.csv",
                                    root / ICP_BENCHMARKS, "ICP benchmark semantic report").parent
    manifest = Path(wdi_manifest) if wdi_manifest else _latest_file("*.json", root / WDI_MANIFESTS,
                                                                    "WDI immutable snapshot manifest")
    snapshot = wdi_snapshot.load_snapshot(manifest, repository_root=root)
    if snapshot["start_year"] > 2014 or snapshot["end_year"] < 2015:
        raise LineageError("WDI snapshot must include the annual PPP comparison period and 2014 start")
    weo_country_codes = set(imf.identity_index(IDENTITY))
    weo = _load_weo(Path(weo_csv), allowed_country_codes=weo_country_codes)
    icp_rows = _load_icp_rows(inspection, benchmark_report)

    lineage_rows = list(icp_rows)
    wdi_index: dict[tuple[str, int], dict[str, Any]] = {}
    for code in ("PA.NUS.PPP", "NY.GDP.MKTP.PP.CD", "NY.GDP.MKTP.CN"):
        if code not in snapshot["observations"]:
            raise LineageError(f"WDI snapshot is missing required indicator {code}")
    for code in ("PA.NUS.PPP", "NY.GDP.MKTP.PP.CD", "NY.GDP.MKTP.CN"):
        for item in snapshot["observations"][code]:
            iso3 = item.get("countryiso3code")
            year = _number(item.get("date"))
            if not isinstance(iso3, str) or len(iso3) != 3 or year is None:
                continue
            region = snapshot["country_regions"].get(iso3)
            if (region is None or region.get("region_id") == "NA"
                    or region.get("region_value", "").casefold() == "aggregates"):
                continue
            key = (iso3, int(year))
            target = wdi_index.setdefault(key, {"country_name": item.get("country", {}).get("value", "")})
            target[code] = _number(item.get("value"))
            target[f"{code}_status"] = item.get("obs_status", "")
    for (code, year), item in sorted(wdi_index.items()):
        if item.get("PA.NUS.PPP") is not None:
            lineage_rows.append({
                "country_code": code, "country_name": item.get("country_name", ""), "year": year,
                "source": "WDI", "source_release": snapshot["manifest"].get("snapshot_id", ""),
                "lineage_role": "rolling_annual_api_series_lineage_not_benchmark_classified",
                "metric": "GDP_PPP_conversion_factor", "value": item["PA.NUS.PPP"],
                "unit": snapshot["indicator_metadata"]["PA.NUS.PPP"].get("unit", "LCU per international dollar"),
                "source_file": snapshot["manifest_path"].relative_to(root).as_posix(),
                "source_row": "", "classification_code": "", "indicator_code": "PA.NUS.PPP",
                "observation_status": item.get("PA.NUS.PPP_status", ""),
                "comparability_status": "WDI_source_metadata_unit; benchmark_or_extrapolation_role_not_observation_level",
            })
        if item.get("NY.GDP.MKTP.PP.CD") is not None:
            lineage_rows.append({
                "country_code": code, "country_name": item.get("country_name", ""), "year": year,
                "source": "WDI", "source_release": snapshot["manifest"].get("snapshot_id", ""),
                "lineage_role": "rolling_annual_api_series_not_ICP_benchmark",
                "metric": "GDP_current_PPP", "value": item["NY.GDP.MKTP.PP.CD"],
                "unit": snapshot["indicator_metadata"]["NY.GDP.MKTP.PP.CD"].get("unit", ""),
                "source_file": snapshot["manifest_path"].relative_to(root).as_posix(),
                "source_row": "", "classification_code": "", "indicator_code": "NY.GDP.MKTP.PP.CD",
                "observation_status": item.get("NY.GDP.MKTP.PP.CD_status", ""),
                "comparability_status": "reported_WDI_PPP_GDP_not_a_conversion_factor",
            })

    diagnostic_rows: list[dict[str, Any]] = []
    for key in sorted(set(wdi_index) | set(weo)):
        code, year = key
        wdi_item = wdi_index.get(key, {})
        weo_item = weo.get(key, {})
        wdi_factor = wdi_item.get("PA.NUS.PPP")
        wdi_ppp_gdp = wdi_item.get("NY.GDP.MKTP.PP.CD")
        wdi_lcu_gdp = wdi_item.get("NY.GDP.MKTP.CN")
        weo_lcu_gdp = weo_item.get("NGDP")
        weo_ppp_gdp = weo_item.get("PPPGDP")
        weo_implied_factor = (
            weo_lcu_gdp / weo_ppp_gdp
            if weo_lcu_gdp is not None and weo_ppp_gdp not in (None, 0) else None
        )
        weo_ppp_scale = str(weo_item.get("PPPGDP_scale", "")).strip().casefold()
        weo_ppp_multiplier = 1_000_000_000 if weo_ppp_scale == "billions" else (
            1 if weo_ppp_scale in {"units", "unit"} else None
        )
        weo_ppp_gdp_absolute = (
            weo_ppp_gdp * weo_ppp_multiplier
            if weo_ppp_gdp is not None and weo_ppp_multiplier is not None else None
        )
        wdi_implied_ppp_gdp = (
            wdi_lcu_gdp / wdi_factor
            if wdi_lcu_gdp is not None and wdi_factor not in (None, 0) else None
        )
        ratio = (
            wdi_factor / weo_implied_factor
            if wdi_factor is not None and weo_implied_factor not in (None, 0) else None
        )
        diagnostic_rows.append({
            "country_code": code, "country_name": wdi_item.get("country_name") or weo_item.get("country_name", ""),
            "year": year,
            "wdi_ppp_factor_lcu_per_intl_dollar": wdi_factor,
            "wdi_ppp_factor_obs_status": wdi_item.get("PA.NUS.PPP_status", ""),
            "wdi_gdp_current_lcu": wdi_lcu_gdp,
            "wdi_gdp_current_ppp_reported": wdi_ppp_gdp,
            "wdi_gdp_current_ppp_implied_from_lcu_factor": wdi_implied_ppp_gdp,
            "wdi_ppp_gdp_arithmetic_ratio_reported_to_implied": (
                wdi_ppp_gdp / wdi_implied_ppp_gdp
                if wdi_ppp_gdp is not None and wdi_implied_ppp_gdp not in (None, 0) else None
            ),
            "weo_ngdp_current_lcu": weo_lcu_gdp,
            "weo_pppgdp_current_intl_dollars_source_scale": weo_ppp_gdp,
            "weo_pppgdp_scale_multiplier_to_units": weo_ppp_multiplier,
            "weo_pppgdp_current_intl_dollars_absolute": weo_ppp_gdp_absolute,
            "wdi_to_weo_pppgdp_ratio_arithmetic_only": (
                wdi_ppp_gdp / weo_ppp_gdp_absolute
                if wdi_ppp_gdp is not None and weo_ppp_gdp_absolute not in (None, 0) else None
            ),
            "wdi_vs_weo_pppgdp_relative_difference_percent_arithmetic_only": (
                (wdi_ppp_gdp / weo_ppp_gdp_absolute - 1) * 100
                if wdi_ppp_gdp is not None and weo_ppp_gdp_absolute not in (None, 0) else None
            ),
            "weo_ngdp_unit": weo_item.get("NGDP_unit", ""),
            "weo_ngdp_scale": weo_item.get("NGDP_scale", ""),
            "weo_pppgdp_unit": weo_item.get("PPPGDP_unit", ""),
            "weo_pppgdp_scale": weo_item.get("PPPGDP_scale", ""),
            "weo_implied_ppp_factor_lcu_per_intl_dollar": weo_implied_factor,
            "wdi_factor_to_weo_implied_factor_ratio_arithmetic_only": ratio,
            "factor_comparability_status": (
                "not_established_currency_denomination_and_vintage_review_required"
                if ratio is not None else "insufficient_overlap"
            ),
            "wdi_snapshot_id": snapshot["manifest"].get("snapshot_id"),
            "weo_release": "imf_weo_october_2026",
        })
        if weo_ppp_gdp is not None:
            lineage_rows.append({
                "country_code": code, "country_name": diagnostic_rows[-1]["country_name"], "year": year,
                "source": "IMF_WEO", "source_release": "imf_weo_october_2026",
                "lineage_role": "WEO_reported_PPP_GDP; PPP_factor_derived_only_as_diagnostic",
                "metric": "GDP_current_PPP", "value": weo_ppp_gdp,
                "unit": "current international dollars; source scale " + str(weo_item.get("PPPGDP_scale", "")),
                "source_file": Path(weo_csv).resolve().relative_to(root).as_posix(),
                "source_row": "", "classification_code": "", "indicator_code": "PPPGDP",
                "observation_status": "source_value; actual_estimate_projection_status_unclassified",
                "comparability_status": "WEO_PPPGDP_reported_value; not a direct ICP factor",
            })
        if weo_implied_factor is not None:
            lineage_rows.append({
                "country_code": code, "country_name": diagnostic_rows[-1]["country_name"], "year": year,
                "source": "IMF_WEO", "source_release": "imf_weo_october_2026",
                "lineage_role": "derived_ratio_NGDP_divided_by_PPPGDP_not_provider_PPP_factor",
                "metric": "GDP_PPP_conversion_factor_derived", "value": weo_implied_factor,
                "unit": "WEO current LCU per current international dollar (ratio of reported series)",
                "source_file": Path(weo_csv).resolve().relative_to(root).as_posix(),
                "source_row": "", "classification_code": "", "indicator_code": "NGDP/PPPGDP",
                "observation_status": "derived", "comparability_status": "arithmetic_only_currency_unit_review_required",
            })

    lineage_rows.sort(key=lambda row: (row["country_code"], row["year"], row["source"], row["source_release"], row["metric"]))
    diagnostic_rows.sort(key=lambda row: (row["country_code"], row["year"]))
    countries = {row["country_code"] for row in lineage_rows}
    years = [row["year"] for row in lineage_rows]
    return {
        "assessment": "annual_ppp_lineage_across_icp_wdi_imf_weo",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "country_count": len(countries),
        "lineage_row_count": len(lineage_rows),
        "country_year_diagnostic_row_count": len(diagnostic_rows),
        "year_range": {"minimum": min(years) if years else None, "maximum": max(years) if years else None},
        "source_coverage": {
            "icp_releases": dict(sorted(Counter(row["source_release"] for row in icp_rows).items())),
            "not_captured_icp_releases": ["icp_2005_cycle"],
            "wdi_snapshot_id": snapshot["manifest"].get("snapshot_id"),
            "wdi_snapshot_retrieved_at": snapshot["manifest"].get("retrieved_at"),
            "wdi_snapshot_manifest_sha256": snapshot.get("manifest_sha256"),
            "weo_release": "imf_weo_october_2026",
            "weo_csv_fingerprint": imf.fingerprint(Path(weo_csv), imf.EXPECTED["csv"]),
        },
        "interpretation": [
            "ICP original and revised benchmark releases remain distinct. Annual roles are assigned only where the ICP publication explicitly documents them.",
            "ICP 2017 archive years other than its original 2017 and revised 2011 benchmark roles remain unclassified; year columns alone do not prove interpolation or extrapolation.",
            "WDI PA.NUS.PPP is a rolling annual API series. Its observation-level benchmark/interpolation/extrapolation lineage is not supplied by this capture.",
            "WEO PPPGDP is reported current-PPP GDP. Where its source scale is Billions, it is rescaled to absolute international dollars before the WDI/WEO PPP-GDP arithmetic comparison. NGDP divided by PPPGDP is a derived arithmetic factor, not the provider's PPPEX field or a published conversion-factor series.",
            "WEO PPPEX is not used because its captured precision is rounded and unsuitable for exact factor reconciliation.",
            "Numerical WDI/WEO factor ratios are diagnostics only; currency redenomination, national-accounts vintage and reference-unit compatibility remain unverified.",
            "ICP PPP factor values are retained per source release and not normalized across currency denominations or vintages.",
            "The original ICP 2005 release is not present in the captured inputs and is not represented as zero or missing country observations.",
            "No source observations are filled, interpolated, extrapolated or imputed by this assessment.",
        ],
        "side_effects": {
            "raw_data_written": False, "project_database_written": False,
            "game_database_written": False, "approval_created": False,
            "source_selection_changed": False, "canonical_data_promoted": False,
            "retention_applied": False,
        },
    }, lineage_rows, diagnostic_rows


def write_report(result: dict[str, Any], lineage_rows: list[dict[str, Any]],
                 diagnostic_rows: list[dict[str, Any]], output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / ("annual_ppp_lineage_" + stamp)
    suffix = 1
    while target.exists():
        target = output_root / ("annual_ppp_lineage_" + stamp + f"-{suffix}")
        suffix += 1
    target.mkdir()
    result["report_directory"] = str(target)
    lineage_fields = list(lineage_rows[0]) if lineage_rows else [
        "country_code", "country_name", "year", "source", "source_release",
        "lineage_role", "metric", "value", "unit", "source_file", "source_row",
        "classification_code", "indicator_code", "observation_status", "comparability_status"]
    diagnostic_fields = list(diagnostic_rows[0]) if diagnostic_rows else [
        "country_code", "country_name", "year", "wdi_ppp_factor_lcu_per_intl_dollar",
        "weo_implied_ppp_factor_lcu_per_intl_dollar"]
    _write_csv(target / "annual_ppp_lineage.csv", lineage_rows, lineage_fields)
    _write_csv(target / "country_year_diagnostics.csv", diagnostic_rows, diagnostic_fields)
    (target / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zw = [row for row in diagnostic_rows if row["country_code"] == "ZWE"]
    lines = [
        "# Annual PPP lineage assessment", "",
        f"- Checked: {result['checked_at']}",
        f"- Countries: {result['country_count']}; lineage rows: {result['lineage_row_count']}",
        f"- Country-year diagnostics: {result['country_year_diagnostic_row_count']}",
        f"- WDI snapshot: {result['source_coverage']['wdi_snapshot_id']}",
        "- Read-only; no source selection, approval, database or canonical-data changes.", "",
        "## Zimbabwe diagnostic", "",
        "| Year | WDI PPP factor | WDI PPP GDP reported | WDI PPP GDP from LCU/factor | WEO PPP GDP | WDI/WEO PPP GDP difference | WEO implied factor | WDI/WEO factor ratio (arithmetic only) |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in zw:
        fmt = lambda value: "" if value is None else f"{value:.10g}"
        lines.append("| " + " | ".join([
            str(row["year"]), fmt(row["wdi_ppp_factor_lcu_per_intl_dollar"]),
            fmt(row["wdi_gdp_current_ppp_reported"]), fmt(row["wdi_gdp_current_ppp_implied_from_lcu_factor"]),
            fmt(row["weo_pppgdp_current_intl_dollars_absolute"]),
            fmt(row["wdi_vs_weo_pppgdp_relative_difference_percent_arithmetic_only"]),
            fmt(row["weo_implied_ppp_factor_lcu_per_intl_dollar"]),
            fmt(row["wdi_factor_to_weo_implied_factor_ratio_arithmetic_only"]),
        ]) + " |")
    lines += ["", "## Interpretation limits", ""] + [f"- {item}" for item in result["interpretation"]]
    lines += ["", "## Side effects", "", "- No raw source files or manifests written.",
              "- No Project DB or Game DB writes; no approval, source-selection, promotion or retention.", ""]
    (target / "assessment.md").write_text("\n".join(lines), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--wdi-manifest", type=Path)
    parser.add_argument("--weo-csv", type=Path, default=WEO_CSV)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        result, lineage_rows, diagnostic_rows = assess(
            repository_root=args.root, wdi_manifest=args.wdi_manifest, weo_csv=args.weo_csv)
        target = write_report(result, lineage_rows, diagnostic_rows, args.output_root)
    except (LineageError, wdi_snapshot.SnapshotError, imf.AssessmentError,
            icp_benchmarks.ICPAssessmentError, OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"interpretation"}}, ensure_ascii=False, indent=2))
    print(f"report_directory: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
