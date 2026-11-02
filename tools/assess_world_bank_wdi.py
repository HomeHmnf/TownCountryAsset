"""Read-only World Bank WDI indicator metadata and country coverage assessment.

This tool queries the public Indicators API and writes review reports only. It
never acquires immutable source snapshots, changes policy, or writes to SQLite.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.worldbank.org/v2"
START_YEAR = 2015
END_YEAR = 2025
INDICATORS = {
    "NY.GDP.MKTP.CD": {"field_id": 15, "key": "gdp", "unit_expected": "current_usd", "candidate": True},
    "NY.GDP.PCAP.CD": {"field_id": 16, "key": "gdp_per_capita", "unit_expected": "current_usd_per_person", "candidate": True},
    "NY.GDP.MKTP.PP.CD": {"field_id": 18, "key": "gdp_ppp", "unit_expected": "current_international_dollars", "candidate": True},
    "FP.CPI.TOTL.ZG": {"field_id": 20, "key": "inflation", "unit_expected": "percent_annual", "candidate": True},
    "SL.UEM.TOTL.ZS": {"field_id": 21, "key": "unemployment", "unit_expected": "percent_labour_force", "candidate": True},
    "EN.POP.DNST": {"field_id": 3, "key": "population_density", "unit_expected": "people_per_km2", "candidate": False},
    "AG.SRF.TOTL.K2": {"field_id": 33, "key": "total_area", "unit_expected": "km2", "candidate": False},
    "AG.LND.TOTL.K2": {"field_id": 34, "key": "land_area", "unit_expected": "km2", "candidate": False},
}


class AssessmentError(RuntimeError):
    """WDI API or response-contract failure."""


def _get_json(url: str, timeout: int = 45) -> Any:
    request = urllib.request.Request(url, headers={
        "User-Agent": "TownCountryAsset-WDI-Assessment/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise AssessmentError(f"HTTP {response.status} for {url}")
            return json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise AssessmentError(f"Cannot retrieve World Bank API response {url}: {exc}") from exc


def _url(path: str, params: dict[str, str]) -> str:
    return f"{API}/{path}?{urllib.parse.urlencode(params)}"


def fetch_indicator_metadata(code: str, get_json=_get_json) -> dict[str, Any]:
    payload = get_json(_url(f"indicator/{urllib.parse.quote(code, safe='.')}", {"format": "json"}))
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        raise AssessmentError(f"No metadata returned for indicator {code}")
    row = payload[1][0]
    if row.get("id") != code:
        raise AssessmentError(f"Indicator metadata identity mismatch for {code}")
    source = row.get("source") or {}
    return {
        "indicator_code": code,
        "name": row.get("name"),
        "unit": row.get("unit"),
        "source_note": row.get("sourceNote"),
        "source_organization": row.get("sourceOrganization"),
        "source_id": source.get("id"),
        "source_name": source.get("value"),
        "topics": [item.get("value") for item in row.get("topics", []) if item.get("value")],
        "metadata_url": f"https://api.worldbank.org/v2/indicator/{code}?format=json",
    }


def fetch_country_regions(get_json=_get_json) -> dict[str, dict[str, str]]:
    """Fetch the ISO3 country/aggregate catalogue and its authoritative region labels."""
    regions: dict[str, dict[str, str]] = {}
    page = 1
    while True:
        payload = get_json(_url(
            "country",
            {"format": "json", "per_page": "400", "page": str(page)},
        ))
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
            raise AssessmentError(f"Invalid country metadata response, page {page}")
        records = payload[1] or []
        if not isinstance(records, list):
            raise AssessmentError(f"Invalid country metadata page {page}")
        for row in records:
            iso3 = row.get("id")
            if not isinstance(iso3, str) or len(iso3) != 3:
                continue
            region = row.get("region") or {}
            regions[iso3] = {
                "region_id": str(region.get("id") or "").strip().upper(),
                "region_value": str(region.get("value") or "").strip(),
            }
        pages = int(payload[0].get("pages", 1))
        if page >= pages:
            break
        page += 1
        if page > 1000:
            raise AssessmentError("Unreasonable country metadata pagination count")
    if not regions:
        raise AssessmentError("World Bank country metadata catalogue is empty")
    return regions


def fetch_indicator_observations(
    code: str, start_year: int, end_year: int, get_json=_get_json
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = get_json(_url(
            f"country/all/indicator/{urllib.parse.quote(code, safe='.')}",
            {"format": "json", "date": f"{start_year}:{end_year}", "per_page": "20000", "page": str(page)},
        ))
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
            raise AssessmentError(f"Invalid observations response for {code}, page {page}")
        metadata, records = payload[0], payload[1] or []
        if not isinstance(records, list):
            raise AssessmentError(f"Invalid observations page for {code}, page {page}")
        rows.extend(records)
        pages = int(metadata.get("pages", 1))
        if page >= pages:
            break
        page += 1
        if page > 1000:
            raise AssessmentError(f"Unreasonable pagination count for {code}")
    return rows


def summarize_observations(
    code: str,
    records: list[dict[str, Any]],
    country_regions: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    by_country: dict[str, list[int]] = defaultdict(list)
    country_names: dict[str, str] = {}
    aggregate_rows = 0
    invalid_rows = 0
    for row in records:
        country = row.get("country") or {}
        # Observation records expose country.id as ISO2 and omit region
        # metadata. Join countryiso3code to the separate /country catalogue.
        iso3 = row.get("countryiso3code")
        if not isinstance(iso3, str) or len(iso3) != 3:
            aggregate_rows += 1
            continue
        if country_regions is None:
            # Retained for direct callers/tests; production assessment always
            # supplies the authoritative catalogue fetched by build_assessment.
            region = country.get("region") or {}
            region_id = str(region.get("id") or "").strip().upper()
            region_value = str(region.get("value") or "").strip().casefold()
        else:
            metadata = country_regions.get(iso3)
            if metadata is None:
                raise AssessmentError(
                    f"Observation {code}/{iso3} is absent from the World Bank country metadata catalogue"
                )
            region_id = metadata["region_id"]
            region_value = metadata["region_value"].casefold()
        if region_id == "NA" or region_value == "aggregates":
            aggregate_rows += 1
            continue
        year = row.get("date")
        value = row.get("value")
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            invalid_rows += 1
            continue
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            invalid_rows += 1
            continue
        if not (numeric == numeric and abs(numeric) != float("inf")):
            invalid_rows += 1
            continue
        by_country[iso3].append(year_int)
        country_names[iso3] = country.get("value") or iso3
    coverage = []
    for iso3, years in sorted(by_country.items()):
        unique = sorted(set(years))
        coverage.append({
            "iso3": iso3,
            "country_name": country_names[iso3],
            "non_null_observation_count": len(years),
            "first_observation_year": unique[0],
            "latest_observation_year": unique[-1],
            "observation_years": unique,
        })
    return {
        "indicator_code": code,
        "country_count": len(coverage),
        "non_null_observation_count": sum(item["non_null_observation_count"] for item in coverage),
        "aggregate_rows_excluded": aggregate_rows,
        "invalid_rows": invalid_rows,
        "countries": coverage,
    }


def build_assessment(start_year: int = START_YEAR, end_year: int = END_YEAR, get_json=_get_json) -> dict[str, Any]:
    if start_year < 1900 or end_year < start_year or end_year > 2100:
        raise AssessmentError("Invalid year range")
    results = []
    # Observation endpoint country objects omit region classification. Fetch
    # the provider's country catalogue once and join by ISO3 for every series.
    country_regions = fetch_country_regions(get_json)
    for code, contract in INDICATORS.items():
        metadata = fetch_indicator_metadata(code, get_json)
        summary = summarize_observations(
            code,
            fetch_indicator_observations(code, start_year, end_year, get_json),
            country_regions,
        )
        results.append({
            **contract,
            "metadata": metadata,
            "coverage": summary,
        })
    return {
        "schema_version": 1,
        "assessment": "world_bank_wdi_read_only_coverage",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start_year": start_year, "end_year": end_year},
        "api_base": API,
        "indicator_count": len(results),
        "imf_weo_comparison": {
            "status": "not_assessed",
            "reason": "No immutable IMF WEO comparison snapshot or normalized IMF observations are configured for this assessment. WDI coverage alone cannot establish definition or vintage equivalence.",
            "fields": [15, 16, 18, 20, 21],
        },
        "identity_mapping": {
            "status": "iso3_coverage_only",
            "reason": "This assessment does not infer game_id mappings from country names or assume ISO3 equivalence. A separately reviewed source crosswalk is required.",
        },
        "side_effects": {
            "immutable_snapshots_acquired": False,
            "source_registry_changed": False,
            "source_selection_policy_changed": False,
            "canonical_database_written": False,
        },
        "indicators": results,
    }


def write_reports(report: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    target.mkdir(parents=True, exist_ok=False)
    (target / "assessment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# World Bank WDI coverage assessment",
        "",
        f"- Checked: {report['checked_at']}",
        f"- Period: {report['period']['start_year']}–{report['period']['end_year']}",
        f"- Indicators: {report['indicator_count']}",
        "- Scope: read-only API assessment; no snapshots, policy changes, or database writes",
        "",
        "| Field | Indicator | Name | Unit | Source organization | Countries with observations | Latest year range |",
        "|---:|---|---|---|---|---:|---|",
    ]
    csv_rows = []
    for item in report["indicators"]:
        meta, coverage = item["metadata"], item["coverage"]
        years = [c["latest_observation_year"] for c in coverage["countries"]]
        year_range = f"{min(years)}–{max(years)}" if years else "none"
        lines.append(
            f"| {item['field_id']} | {meta['indicator_code']} | {meta.get('name') or ''} | "
            f"{meta.get('unit') or ''} | {meta.get('source_organization') or ''} | "
            f"{coverage['country_count']} | {year_range} |"
        )
        for country in coverage["countries"]:
            csv_rows.append({
                "field_id": item["field_id"], "field_key": item["key"],
                "indicator_code": meta["indicator_code"], "country_iso3": country["iso3"],
                "country_name": country["country_name"],
                "non_null_observation_count": country["non_null_observation_count"],
                "first_observation_year": country["first_observation_year"],
                "latest_observation_year": country["latest_observation_year"],
                "observation_years": ";".join(map(str, country["observation_years"])),
            })
    lines.extend([
        "",
        "## Comparability boundary",
        "",
        "IMF WEO comparability was not assessed because no immutable IMF WEO comparison snapshot or normalized IMF observations are configured. Do not infer equivalence from indicator labels.",
        "",
        "## Identity boundary",
        "",
        "Coverage is reported by provider ISO3 only. No game identity is inferred; a reviewed source crosswalk is required.",
        "",
        "## Indicator metadata notes",
        "",
    ])
    for item in report["indicators"]:
        meta = item["metadata"]
        lines.extend([
            f"### {meta['indicator_code']} — {meta.get('name') or 'Unnamed'}",
            "",
            f"- Unit: {meta.get('unit') or 'not supplied'}",
            f"- Source organization: {meta.get('source_organization') or 'not supplied'}",
            f"- Source note: {meta.get('source_note') or 'not supplied'}",
            f"- Metadata endpoint: {meta['metadata_url']}",
            "",
        ])
    (target / "assessment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (target / "country_coverage.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "field_id", "field_key", "indicator_code", "country_iso3", "country_name",
            "non_null_observation_count", "first_observation_year", "latest_observation_year",
            "observation_years",
        ])
        writer.writeheader()
        writer.writerows(csv_rows)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=START_YEAR)
    parser.add_argument("--end-year", type=int, default=END_YEAR)
    parser.add_argument("--output-root", type=Path, default=ROOT / "reports/sources/world-bank-wdi")
    args = parser.parse_args(argv)
    try:
        report = build_assessment(args.start_year, args.end_year)
        target = write_reports(report, args.output_root)
    except (AssessmentError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "assessment": report["assessment"],
        "indicators": report["indicator_count"],
        "period": report["period"],
        "report_directory": str(target),
        "imf_weo_comparison": report["imf_weo_comparison"]["status"],
        "snapshots_acquired": False,
        "database_written": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
