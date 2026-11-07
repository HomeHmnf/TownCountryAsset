"""Build a read-only WDI macro-series decomposition from a frozen API snapshot.

The output tests arithmetic relationships between published WDI series. It does
not prove that a provider uses a particular input series or conversion method.
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
from tools import compare_imf_weo_wdi as comparison
from tools import acquire_world_bank_wdi_snapshot as wdi_snapshot

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/sources/wdi-macro-decomposition"
SUPPORTING = (
    "NY.GDP.MKTP.CN", "PA.NUS.FCRF", "PA.NUS.ATLS",
    "PA.NUS.PPP", "SP.POP.TOTL", "FP.CPI.TOTL",
)
BASE_CODES = tuple(comparison.PAIRS)


class DecompositionError(RuntimeError):
    """Invalid snapshot or decomposition input."""


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _relative_difference(reported: float | None, implied: float | None) -> float | None:
    if reported is None or implied in (None, 0):
        return None
    return (reported - implied) / abs(implied) * 100


def _index_observations(snapshot: dict[str, Any]) -> dict[str, dict[tuple[str, int], dict[str, Any]]]:
    result: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    regions = snapshot["country_regions"]
    for code, records in snapshot["observations"].items():
        indexed: dict[tuple[str, int], dict[str, Any]] = {}
        for record in records:
            iso3 = record.get("countryiso3code")
            if not isinstance(iso3, str) or len(iso3) != 3:
                continue
            region = regions.get(iso3)
            if region is None:
                raise DecompositionError(f"WDI country {iso3} missing from captured country catalogue")
            if region.get("region_id") == "NA" or region.get("region_value", "").casefold() == "aggregates":
                continue
            try:
                year = int(record.get("date"))
            except (TypeError, ValueError):
                continue
            key = (iso3, year)
            if key in indexed:
                raise DecompositionError(f"Duplicate WDI observation: {code}/{iso3}/{year}")
            indexed[key] = record
        result[code] = indexed
    return result


def assess_snapshot(
    snapshot: dict[str, Any],
    imf_data: dict[str, dict[tuple[str, int], dict[str, Any]]],
    countries: list[dict[str, Any]],
    *, start_year: int, end_year: int,
) -> dict[str, Any]:
    missing = set(SUPPORTING) - set(snapshot.get("observations", {}))
    if missing:
        raise DecompositionError(f"Snapshot lacks supporting indicators: {sorted(missing)}")
    indexed = _index_observations(snapshot)
    rows: list[dict[str, Any]] = []
    country_by_id = {item["game_id"]: item for item in countries}

    def observation(code: str, iso3: str | None, year: int) -> dict[str, Any] | None:
        if not iso3:
            return None
        return indexed.get(code, {}).get((iso3, year))

    def value(code: str, iso3: str | None, year: int) -> float | None:
        record = observation(code, iso3, year)
        return _number(record.get("value")) if record else None

    for game_id, country in sorted(country_by_id.items()):
        iso3 = country.get("source_lookup_code")
        country_meta = snapshot["country_regions"].get(iso3 or "", {})
        for year in range(start_year, end_year + 1):
            current = {
                code: value(code, iso3, year)
                for code in (*BASE_CODES, *SUPPORTING)
            }
            previous_cpi = value("FP.CPI.TOTL", iso3, year - 1)
            gdp_lcu = current["NY.GDP.MKTP.CN"]
            official_fx = current["PA.NUS.FCRF"]
            alternative_fx = current["PA.NUS.ATLS"]
            ppp_factor = current["PA.NUS.PPP"]
            population = current["SP.POP.TOTL"]
            gdp_usd = current["NY.GDP.MKTP.CD"]
            gdp_ppp = current["NY.GDP.MKTP.PP.CD"]
            gdp_pc = current["NY.GDP.PCAP.CD"]
            cpi_index = current["FP.CPI.TOTL"]

            official_implied = _ratio(gdp_lcu, official_fx)
            alternative_implied = _ratio(gdp_lcu, alternative_fx)
            ppp_implied = _ratio(gdp_lcu, ppp_factor)
            per_capita_implied = _ratio(gdp_usd, population)
            cpi_yoy = (
                (cpi_index / previous_cpi - 1) * 100
                if cpi_index is not None and previous_cpi not in (None, 0) else None
            )
            imf_values = {
                "imf_ngdpd_current_usd": (imf_data.get("NGDPD", {}).get((game_id, year)) or {}).get("value"),
                "imf_ngdpdpc_current_usd_per_person": (imf_data.get("NGDPDPC", {}).get((game_id, year)) or {}).get("value"),
                "imf_pppgdp_current_international_dollars": (imf_data.get("PPPGDP", {}).get((game_id, year)) or {}).get("value"),
                "imf_pcpipch_percent": (imf_data.get("PCPIPCH", {}).get((game_id, year)) or {}).get("value"),
            }
            row = {
                "game_id": game_id, "country_name": country.get("country_name"),
                "source_lookup_code": iso3, "identity_mapping_status": country.get("identity_mapping_status"),
                "identity_gate": "passed" if country.get("identity_mapping_status") == "mapped_verified" else "blocking",
                "year": year,
                "wdi_country_special_notes": country_meta.get("special_notes"),
                "wdi_gdp_current_lcu": gdp_lcu,
                "wdi_official_exchange_rate_lcu_per_usd": official_fx,
                "wdi_alternative_conversion_factor_lcu_per_usd": alternative_fx,
                "wdi_gdp_ppp_conversion_factor_lcu_per_intl_dollar": ppp_factor,
                "wdi_population_total": population,
                "wdi_cpi_index": cpi_index,
                "wdi_cpi_index_previous_year": previous_cpi,
                "wdi_gdp_current_usd_reported": gdp_usd,
                "wdi_gdp_current_ppp_reported": gdp_ppp,
                "wdi_gdp_per_capita_current_usd_reported": gdp_pc,
                "wdi_inflation_annual_percent_reported": current["FP.CPI.TOTL.ZG"],
                "wdi_gdp_current_usd_implied_official_fx": official_implied,
                "wdi_gdp_current_usd_implied_alternative_factor": alternative_implied,
                "wdi_gdp_current_ppp_implied_from_lcu": ppp_implied,
                "wdi_gdp_per_capita_implied_from_usd_and_population": per_capita_implied,
                "wdi_cpi_index_yoy_percent_diagnostic": cpi_yoy,
                "wdi_gdp_usd_vs_official_fx_implied_relative_difference_percent": _relative_difference(gdp_usd, official_implied),
                "wdi_gdp_usd_vs_alternative_factor_implied_relative_difference_percent": _relative_difference(gdp_usd, alternative_implied),
                "wdi_ppp_vs_lcu_factor_implied_relative_difference_percent": _relative_difference(gdp_ppp, ppp_implied),
                "wdi_gdp_per_capita_vs_gdp_population_implied_relative_difference_percent": _relative_difference(gdp_pc, per_capita_implied),
                "wdi_inflation_vs_cpi_index_yoy_difference_percentage_points": (
                    current["FP.CPI.TOTL.ZG"] - cpi_yoy
                    if current["FP.CPI.TOTL.ZG"] is not None and cpi_yoy is not None else None
                ),
                **imf_values,
            }
            for code in SUPPORTING:
                record = observation(code, iso3, year)
                row[f"status_{code}"] = record.get("obs_status") if record else None
            rows.append(row)

    return {
        "assessment": "wdi_macro_series_decomposition",
        "row_count": len(rows),
        "country_count": len(country_by_id),
        "period": {"start_year": start_year, "end_year": end_year},
        "snapshot_id": snapshot["manifest"].get("snapshot_id"),
        "snapshot_retrieved_at": snapshot["manifest"].get("retrieved_at"),
        "snapshot_manifest_sha256": snapshot.get("manifest_sha256"),
        "supporting_indicators": {
            code: {
                "name": snapshot["indicator_metadata"][code].get("name"),
                "unit": snapshot["indicator_metadata"][code].get("unit"),
                "source_note": snapshot["indicator_metadata"][code].get("sourceNote"),
                "source_organization": snapshot["indicator_metadata"][code].get("sourceOrganization"),
                "api_last_updated": (snapshot.get("indicator_metadata_api_metadata", {}).get(code) or {}).get("lastupdated"),
            }
            for code in SUPPORTING
        },
        "identity_gate_counts": dict(sorted(Counter(row["identity_gate"] for row in rows).items())),
        "side_effects": {
            "source_data_fetched": False, "database_written": False,
            "source_selection_changed": False, "approval_created": False,
            "release_promoted": False, "game_database_written": False,
        },
        "limitations": [
            "WDI arithmetic relationships are diagnostics, not proof of the provider's internal construction pipeline.",
            "PA.NUS.ATLS is the DEC alternative conversion factor used in the Atlas method; its presence does not prove it converts NY.GDP.MKTP.CD.",
            "Official exchange rates, alternative conversion factors and PPP factors may use different reference periods and vintages from national accounts.",
            "Population division is an arithmetic check; the reference date and population universe may differ from the GDP-per-capita denominator.",
            "CPI-index year-on-year growth is a diagnostic only; the annual index convention and inflation-series source vintage require confirmation.",
            "All identity mappings remain subject to the separate country-identity governance gate.",
            "The WDI capture is a rolling API snapshot, not a provider-declared vintage aligned to the October 2026 IMF WEO export.",
            "Observation status is preserved verbatim and not interpreted as actual, estimate or projection.",
        ],
        "rows": rows,
    }


def write_report(result: dict[str, Any], output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir()
    rows = result.pop("rows")
    result["report_directory"] = str(target)
    fields = list(rows[0]) if rows else ["game_id", "country_name", "source_lookup_code", "identity_mapping_status", "year"]
    with (target / "decomposition_matrix.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    result["row_count"] = len(rows)
    (target / "assessment.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# WDI macro-series decomposition assessment", "",
        f"- Snapshot: {result.get('snapshot_id')}",
        f"- Retrieval time: {result.get('snapshot_retrieved_at')}",
        f"- Countries: {result['country_count']}; country-year rows: {result['row_count']}",
        f"- Decision boundary: diagnostic only; no source policy or database change.", "",
        "## Supporting indicators", "",
        "| Code | Name | Unit | Source organization | API last updated |",
        "|---|---|---|---|---|",
    ]
    for code, item in result["supporting_indicators"].items():
        lines.append(f"| {code} | {item['name']} | {item['unit']} | {item['source_organization']} | {item['api_last_updated']} |")
    lines += ["", "## Interpretation limits", ""] + [f"- {item}" for item in result["limitations"]]
    lines += ["", "## Side effects", "", "- No new source responses fetched by this assessment.",
              "- No SQLite database, source-selection policy, approval, release or Game DB state changed.", ""]
    (target / "assessment.md").write_text("\n".join(lines), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--imf-csv", type=Path, default=imf.CSV_PATH)
    parser.add_argument("--identity-registry", type=Path, default=imf.IDENTITY)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        snapshot = wdi_snapshot.load_snapshot(args.snapshot_manifest)
        if snapshot["start_year"] > args.start_year - 1 or snapshot["end_year"] < args.end_year:
            raise DecompositionError("Snapshot must include the requested period and prior-year CPI index")
        if args.start_year < 1901 or args.end_year < args.start_year:
            raise DecompositionError("Invalid assessment period")
        imf_data, _ = comparison.read_imf_observations(
            args.imf_csv, args.identity_registry, args.start_year, args.end_year
        )
        code_to_game = comparison._identity_by_code(args.identity_registry)
        countries = comparison._identity_country_rows(args.identity_registry, code_to_game)
        result = assess_snapshot(
            snapshot, imf_data, countries,
            start_year=args.start_year, end_year=args.end_year,
        )
        target = write_report(result, args.output_root)
    except (DecompositionError, wdi_snapshot.SnapshotError, comparison.ComparisonError,
            OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({key: value for key, value in result.items()}, ensure_ascii=False, indent=2))
    print(f"report_directory: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
