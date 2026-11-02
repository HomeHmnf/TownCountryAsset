"""Investigate selected country-level IMF WEO/WDI discrepancies.

Consumes a previously generated comparison CSV. It does not fetch source data,
infer causes, modify source policy, or write to the canonical database.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports/sources/imf-wdi-discrepancy-investigation"
DEFAULT_INPUT = ROOT / "reports/sources/imf-wdi-comparison/20261102T091138Z/country_year_comparison.csv"

# Deliberately narrow, reviewable shortlist based on persistent country-level
# discrepancies in the initial comparison. This is diagnostic prioritization,
# not a claim that these countries have erroneous source observations.
TARGETS = {
    15: ("Turkmenistan", "Guinea", "Central African Republic"),
    16: ("Turkmenistan", "Guinea", "Central African Republic"),
    18: ("Guinea", "Central African Republic", "Zimbabwe"),
    20: ("Tonga", "Samoa", "Palau, Republic of"),
    21: ("Bahrain, Kingdom of", "Moldova, Republic of", "Philippines"),
}
REQUIRED_COLUMNS = {
    "field_id", "wdi_indicator", "imf_indicator", "game_id", "year",
    "imf_country", "wdi_country", "imf_source_code", "wdi_iso3",
    "imf_value_canonical_unit", "wdi_value_canonical_unit",
    "signed_difference", "absolute_difference", "relative_difference_percent",
    "absolute_relative_difference_percent", "imf_status_hint",
    "imf_latest_actual_annual_data", "imf_reporting_year_months",
    "imf_reporting_period_classification", "wdi_status",
}


class InvestigationError(RuntimeError):
    """Invalid comparison artifact or inconsistent row."""


def _number(row: dict[str, str], key: str, *, nullable: bool = False) -> float | None:
    raw = (row.get(key) or "").strip()
    if not raw and nullable:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise InvestigationError(f"Invalid numeric {key}: {raw!r}") from exc
    if not math.isfinite(value):
        raise InvestigationError(f"Non-finite {key}: {raw!r}")
    return value


def read_comparisons(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise InvestigationError(f"Comparison CSV does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise InvestigationError(f"Comparison CSV missing columns: {sorted(missing)}")
        rows: list[dict[str, Any]] = []
        seen: set[tuple[int, str, int]] = set()
        for raw in reader:
            try:
                field_id = int(raw["field_id"])
                year = int(raw["year"])
            except (TypeError, ValueError) as exc:
                raise InvestigationError("Invalid field_id or year") from exc
            key = (field_id, raw["game_id"], year)
            if key in seen:
                raise InvestigationError(f"Duplicate comparison key: {key}")
            seen.add(key)
            imf_value = _number(raw, "imf_value_canonical_unit")
            wdi_value = _number(raw, "wdi_value_canonical_unit")
            signed = _number(raw, "signed_difference")
            absolute = _number(raw, "absolute_difference")
            relative = _number(raw, "relative_difference_percent", nullable=True)
            absolute_relative = _number(raw, "absolute_relative_difference_percent", nullable=True)
            expected = imf_value - wdi_value
            if not math.isclose(signed, expected, rel_tol=1e-9, abs_tol=1e-6):
                raise InvestigationError(f"Signed difference mismatch for {key}")
            if not math.isclose(absolute, abs(expected), rel_tol=1e-9, abs_tol=1e-6):
                raise InvestigationError(f"Absolute difference mismatch for {key}")
            expected_relative = expected / wdi_value * 100 if wdi_value else None
            if expected_relative is None:
                if relative is not None or absolute_relative is not None:
                    raise InvestigationError(f"Zero-denominator relative value must be null for {key}")
            else:
                if relative is None or not math.isclose(relative, expected_relative, rel_tol=1e-7, abs_tol=1e-6):
                    raise InvestigationError(f"Relative difference mismatch for {key}")
                if absolute_relative is None or not math.isclose(absolute_relative, abs(expected_relative), rel_tol=1e-7, abs_tol=1e-6):
                    raise InvestigationError(f"Absolute relative difference mismatch for {key}")
            rows.append({
                **raw, "field_id": field_id, "year": year,
                "imf_value": imf_value, "wdi_value": wdi_value,
                "signed_difference": signed, "absolute_difference": absolute,
                "relative_difference_percent": relative,
                "absolute_relative_difference_percent": absolute_relative,
                "wdi_national_estimate_indicator": raw.get("wdi_national_estimate_indicator") or None,
                "wdi_national_estimate_value": _number(raw, "wdi_national_estimate_value", nullable=True),
                "wdi_national_estimate_country": raw.get("wdi_national_estimate_country") or None,
                "imf_unit": raw.get("imf_unit") or None,
                "imf_scale": raw.get("imf_scale") or None,
                "imf_reporting_period_type": raw.get("imf_reporting_period_type") or None,
                "imf_methodology": raw.get("imf_methodology") or None,
                "imf_methodology_notes": raw.get("imf_methodology_notes") or None,
                "imf_historical_data_source": raw.get("imf_historical_data_source") or None,
                "imf_labour_sector_employment_type": raw.get("imf_labour_sector_employment_type") or None,
                "imf_short_source_citation": raw.get("imf_short_source_citation") or None,
                "imf_country_update_date": raw.get("imf_country_update_date") or None,
            })
    return rows


def build_investigation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    targets = {(field, country) for field, countries in TARGETS.items() for country in countries}
    selected = [
        row for row in rows
        if (row["field_id"], row["imf_country"]) in targets
    ]
    missing = [
        {"field_id": field, "country": country}
        for field, countries in TARGETS.items()
        for country in countries
        if not any(r["field_id"] == field and r["imf_country"] == country for r in selected)
    ]
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        grouped[(row["field_id"], row["imf_country"])].append(row)

    investigations = []
    for (field_id, country), observations in sorted(grouped.items()):
        observations.sort(key=lambda row: row["year"])
        signed_values = [row["relative_difference_percent"] for row in observations if row["relative_difference_percent"] is not None]
        absolute_values = [row["absolute_relative_difference_percent"] for row in observations if row["absolute_relative_difference_percent"] is not None]
        signs = [1 if x > 0 else -1 if x < 0 else 0 for x in signed_values]
        nonzero_signs = [x for x in signs if x]
        direction = (
            "IMF consistently higher" if nonzero_signs and all(x > 0 for x in nonzero_signs)
            else "IMF consistently lower" if nonzero_signs and all(x < 0 for x in nonzero_signs)
            else "mixed direction" if nonzero_signs
            else "no nonzero relative differences"
        )
        investigations.append({
            "field_id": field_id,
            "imf_indicator": observations[0]["imf_indicator"],
            "wdi_indicator": observations[0]["wdi_indicator"],
            "country": country,
            "game_id": observations[0]["game_id"],
            "observation_count": len(observations),
            "first_year": observations[0]["year"],
            "last_year": observations[-1]["year"],
            "median_signed_relative_difference_percent": statistics.median(signed_values) if signed_values else None,
            "median_absolute_relative_difference_percent": statistics.median(absolute_values) if absolute_values else None,
            "max_absolute_relative_difference_percent": max(absolute_values) if absolute_values else None,
            "direction": direction,
            "imf_status_hints": dict(sorted({
                status: sum(row["imf_status_hint"] == status for row in observations)
                for status in {row["imf_status_hint"] for row in observations}
            }.items())),
            "imf_reporting_periods": dict(sorted({
                period: sum((row["imf_reporting_year_months"] or "unknown") == period for row in observations)
                for period in {(row["imf_reporting_year_months"] or "unknown") for row in observations}
            }.items())),
            "observations": [{
                "year": row["year"],
                "imf_value": row["imf_value"],
                "wdi_value": row["wdi_value"],
                "signed_difference": row["signed_difference"],
                "absolute_difference": row["absolute_difference"],
                "signed_relative_difference_percent": row["relative_difference_percent"],
                "absolute_relative_difference_percent": row["absolute_relative_difference_percent"],
                "imf_status_hint": row["imf_status_hint"],
                "imf_latest_actual_annual_data": row["imf_latest_actual_annual_data"] or None,
                "imf_reporting_year_months": row["imf_reporting_year_months"] or None,
                "imf_reporting_period_classification": row["imf_reporting_period_classification"],
                "wdi_status": row["wdi_status"],
                "wdi_national_estimate_indicator": row["wdi_national_estimate_indicator"],
                "wdi_national_estimate_value": row["wdi_national_estimate_value"],
                "wdi_national_estimate_country": row["wdi_national_estimate_country"],
                "imf_unit": row["imf_unit"],
                "imf_scale": row["imf_scale"],
                "imf_reporting_period_type": row["imf_reporting_period_type"],
                "imf_methodology": row["imf_methodology"],
                "imf_methodology_notes": row["imf_methodology_notes"],
                "imf_historical_data_source": row["imf_historical_data_source"],
                "imf_labour_sector_employment_type": row["imf_labour_sector_employment_type"],
                "imf_short_source_citation": row["imf_short_source_citation"],
                "imf_country_update_date": row["imf_country_update_date"],
            } for row in observations],
        })

    return {
        "assessment": "targeted_imf_weo_wdi_country_discrepancy_investigation",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "input_rows": len(rows),
        "selected_country_field_groups": len(investigations),
        "selected_observations": len(selected),
        "targets_not_found": missing,
        "targets": {str(field): list(countries) for field, countries in TARGETS.items()},
        "investigations": investigations,
        "interpretation_limits": [
            "This utility validates and summarizes the supplied comparison artifact; it does not retrieve original source records or source revision histories.",
            "A persistent discrepancy is a review priority, not proof that either provider is wrong.",
            "IMF actual status is only the comparison's hint from LATEST_ACTUAL_ANNUAL_DATA; WDI status is not classified.",
            "A same-numbered year may not represent the same reporting period; fiscal-year metadata is preserved but not shifted.",
            "Relative differences are unstable when the WDI denominator is close to zero; inspect absolute differences and source values as well.",
            "The live WDI API comparison is not vintage-aligned with the fixed IMF October 2026 export.",
            "No source policy, approval, release, or canonical database action is performed.",
        ],
        "side_effects": {
            "source_data_fetched": False, "source_registry_changed": False,
            "source_selection_policy_changed": False, "canonical_database_written": False,
            "release_promoted": False, "approval_created": False,
        },
    }


def write_reports(report: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    target.mkdir(parents=True, exist_ok=False)
    (target / "assessment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_rows = [
        {"field_id": item["field_id"], "country": item["country"], "game_id": item["game_id"], **obs}
        for item in report["investigations"] for obs in item["observations"]
    ]
    csv_path = target / "targeted_country_years.csv"
    fields = list(csv_rows[0]) if csv_rows else [
        "field_id", "country", "game_id", "year", "imf_value", "wdi_value",
        "signed_difference", "absolute_difference", "signed_relative_difference_percent",
        "absolute_relative_difference_percent", "imf_status_hint",
        "imf_latest_actual_annual_data", "imf_reporting_year_months",
        "imf_reporting_period_classification", "wdi_status",
        "wdi_national_estimate_indicator", "wdi_national_estimate_value",
        "wdi_national_estimate_country", "imf_unit", "imf_scale",
        "imf_reporting_period_type", "imf_methodology", "imf_methodology_notes",
        "imf_historical_data_source", "imf_labour_sector_employment_type",
        "imf_short_source_citation", "imf_country_update_date",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)

    lines = [
        "# Targeted IMF WEO/WDI country discrepancy investigation", "",
        f"- Checked: {report['checked_at']}",
        f"- Input comparison rows: {report['input_rows']}",
        f"- Selected country-field groups: {report['selected_country_field_groups']}",
        f"- Selected country-year observations: {report['selected_observations']}",
        "- Read-only analysis of the existing comparison CSV; no new source retrieval", "",
        "| Field | Country | Years | Median absolute relative difference | Direction |",
        "|---:|---|---:|---:|---|",
    ]
    for item in report["investigations"]:
        median = item["median_absolute_relative_difference_percent"]
        median_text = f"{median:.3f}%" if median is not None else "n/a"
        lines.append(f"| {item['field_id']} | {item['country']} | {item['observation_count']} | {median_text} | {item['direction']} |")
    if report["targets_not_found"]:
        lines.extend(["", "## Targets not found", ""])
        lines.extend(f"- Field {item['field_id']}: {item['country']}" for item in report["targets_not_found"])
    lines.extend(["", "## Country-level observations", ""])
    for item in report["investigations"]:
        lines.extend([
            f"### Field {item['field_id']}: {item['country']}", "",
            f"- Indicators: IMF {item['imf_indicator']}; WDI {item['wdi_indicator']}",
            f"- Median signed relative difference: {item['median_signed_relative_difference_percent']}",
            f"- Median absolute relative difference: {item['median_absolute_relative_difference_percent']}",
            f"- Maximum absolute relative difference: {item['max_absolute_relative_difference_percent']}",
            f"- Direction: {item['direction']}",
            f"- IMF status hints: {item['imf_status_hints']}",
            f"- IMF reporting periods: {item['imf_reporting_periods']}", "",
            "| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |",
            "|---:|---:|---:|---:|---:|---:|---|---|",
        ])
        for obs in item["observations"]:
            lines.append(
                f"| {obs['year']} | {obs['imf_value']} | {obs['wdi_value']} | "
                f"{obs['signed_difference']} | {obs['absolute_difference']} | "
                f"{obs['signed_relative_difference_percent']} | {obs['imf_status_hint']} | "
                f"{obs['imf_reporting_year_months'] or 'unknown'} |"
            )
        lines.append("")
    lines.extend(["## Interpretation limits", ""])
    lines.extend(f"- {note}" for note in report["interpretation_limits"])
    (target / "assessment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Existing country_year_comparison.csv")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        rows = read_comparisons(args.input)
        report = build_investigation(rows)
        target = write_reports(report, args.output_root)
    except (InvestigationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "assessment": report["assessment"], "input_rows": report["input_rows"],
        "selected_country_field_groups": report["selected_country_field_groups"],
        "selected_observations": report["selected_observations"],
        "targets_not_found": report["targets_not_found"],
        "report_directory": str(target), "database_written": False,
        "source_data_fetched": False, "policy_changed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
