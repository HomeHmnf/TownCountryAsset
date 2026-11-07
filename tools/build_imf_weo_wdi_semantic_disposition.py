"""Build a country × field × year semantic disposition matrix.

This is a read-only evidence-indexing step. It never approves identities, assigns
provider equivalence, changes source policy, or writes either SQLite database.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/sources/imf-wdi-comparison/20261107T144614Z/candidate_matrix.csv"
DEFAULT_OUTPUT = ROOT / "reports/sources/imf-wdi-semantic-disposition"

FIELD_RULES: dict[str, dict[str, str]] = {
    "15": {
        "concept": "qualified_comparability_nominal_gdp_current_usd",
        "period": "annual_period_requires_source_vintage_confirmation",
        "method": "national_accounts_vintage_and_exchange_rate_conversion",
        "gate": "reconcile_national_accounts_vintage_and_usd_conversion",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    "16": {
        "concept": "qualified_comparability_nominal_gdp_per_capita",
        "period": "annual_period_requires_source_vintage_confirmation",
        "method": "field_15_numerator_plus_population_denominator_vintage_and_universe",
        "gate": "reconcile_gdp_numerator_population_denominator_and_population_universe",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    "18": {
        "concept": "not_demonstrated_comparable_current_ppp_dollars",
        "period": "unknown_or_unverified",
        "method": "icp_benchmark_linking_extrapolation_and_woe_construction",
        "gate": "reconcile_icp_benchmark_ppp_factor_and_nominal_gdp_input",
        "evidence": "docs/data-sources/field-18-ppp-gdp-comparability-assessment.md",
    },
    "20": {
        "concept": "not_demonstrated_comparable_annual_cpi_inflation",
        "period": "annual_average_and_reference_period_alignment_required",
        "method": "annual_average_vs_calendar_or_fiscal_year_and_cpi_vintage",
        "gate": "confirm_provider_reference_period_and_annual_average_convention",
        "evidence": "docs/data-sources/field-20-inflation-comparability-assessment.md",
    },
    "21": {
        "concept": "non_equivalent_products_in_general_case",
        "period": "reference_population_and_annual_aggregation_require_country_review",
        "method": "ilo_modelled_vs_national_or_country_desk_series",
        "gate": "confirm_imf_unit_population_reference_period_and_method",
        "evidence": "docs/data-sources/field-21-unemployment-comparability-assessment.md",
    },
}

# These are bounded evidence dispositions, not inferred numeric corrections.
COUNTRY_CASES: dict[tuple[str, str], dict[str, str]] = {
    ("central african republic", "15"): {
        "case": "car_national_accounts_rebasing",
        "disposition": "newer_2019_base_sna2008_accounts_require_vintage_alignment",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md;docs/data-sources/icasees-central-african-republic-national-accounts.md",
    },
    ("central african republic", "16"): {
        "case": "car_gdp_population_denominator",
        "disposition": "field_15_national_accounts_and_population_vintage_reconciliation_required",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md;docs/data-sources/icasees-central-african-republic-national-accounts.md",
    },
    ("central african republic", "18"): {
        "case": "car_ppp_decomposition",
        "disposition": "nominal_gdp_and_ppp_factor_decomposition_open",
        "evidence": "docs/data-sources/field-18-ppp-gdp-comparability-assessment.md",
    },
    ("guinea", "15"): {
        "case": "guinea_sna2008_2018_base_rebasing",
        "disposition": "rebased_national_accounts_support_woe_direction_but_vintage_alignment_open",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    ("guinea", "16"): {
        "case": "guinea_gdp_population_denominator",
        "disposition": "field_15_rebasing_and_population_denominator_vintage_review_required",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    ("guinea", "18"): {
        "case": "guinea_ppp_decomposition",
        "disposition": "nominal_gdp_and_ppp_factor_decomposition_open",
        "evidence": "docs/data-sources/field-18-ppp-gdp-comparability-assessment.md",
    },
    ("turkmenistan", "15"): {
        "case": "turkmenistan_exchange_rate_regime",
        "disposition": "dual_exchange_rate_and_conversion_factor_require_reconciliation",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    ("turkmenistan", "16"): {
        "case": "turkmenistan_gdp_population_denominator",
        "disposition": "exchange_rate_conversion_and_population_denominator_review_required",
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    ("zimbabwe", "18"): {
        "case": "zimbabwe_icp_2017_benchmark",
        "disposition": "2017_ppp_benchmark_and_woe_special_conversion_need_reconciliation",
        "evidence": "docs/data-sources/field-18-ppp-gdp-comparability-assessment.md",
    },
    ("samoa", "20"): {
        "case": "samoa_fiscal_year_july_june",
        "disposition": "fiscal_year_ending_year_correspondence_supported_2021_2024_2025_residual_open",
        "evidence": "docs/data-sources/field-20-inflation-comparability-assessment.md",
    },
    ("tonga", "20"): {
        "case": "tonga_fiscal_year_july_start_and_cpi_rebase",
        "disposition": "fiscal_year_correspondence_supported_2022_2025_historical_vintage_open",
        "evidence": "docs/data-sources/field-20-inflation-comparability-assessment.md",
    },
    ("palau", "20"): {
        "case": "palau_fiscal_year_september_end",
        "disposition": "fiscal_year_correspondence_supported_2023_2025_earlier_years_open",
        "evidence": "docs/data-sources/field-20-inflation-comparability-assessment.md",
    },
    ("bahrain", "21"): {
        "case": "bahrain_reference_period_settled",
        "disposition": "settled_likely_reference_period_mismatch_do_not_reopen",
        "evidence": "docs/data-sources/bahrain-unemployment-series-assessment.md;docs/data-sources/field-21-unemployment-comparability-assessment.md",
    },
    ("moldova", "21"): {
        "case": "moldova_2025_lfs_redesign",
        "disposition": "national_lfs_corroborates_2024_2025_preserve_2025_break_in_series",
        "evidence": "docs/data-sources/field-21-unemployment-comparability-assessment.md",
    },
    ("philippines", "21"): {
        "case": "philippines_annualized_lfs",
        "disposition": "psa_annual_lfs_corroborates_2023_2025_preserve_2025_preliminary_status",
        "evidence": "docs/data-sources/field-21-unemployment-comparability-assessment.md",
    },
}

REQUIRED = {
    "game_id", "country_name", "identity_mapping_status", "field_id", "year",
    "coverage_status", "imf_value_canonical_unit", "wdi_value_canonical_unit",
    "imf_status_hint", "imf_reporting_period_classification",
    "wdi_status_classification", "wdi_observation_status",
}


class DispositionError(RuntimeError):
    """Invalid candidate matrix or output contract."""


def _country_key(value: str) -> str:
    return re.sub(r"[^a-z]+", " ", (value or "").casefold()).strip()



# Explicit year scopes are evidence boundaries, not automatic approval.
COUNTRY_YEAR_SCOPES = {
    ("central african republic", "15"): {"ranges": [(2019, 2021, "primary_national_accounts_and_weo_crosscheck")], "note": "ICASEES definitive 2019–2021 accounts; surrounding years require vintage reconciliation."},
    ("central african republic", "16"): {"ranges": [(2019, 2021, "gdp_evidence_population_denominator_open")], "note": "GDP evidence for 2019–2021; population denominator is not independently reconstructed."},
    ("central african republic", "18"): {"ranges": [], "note": "Nominal-account evidence is contextual; no year-specific PPP factor decomposition is complete."},
    ("guinea", "15"): {"ranges": [(2018, 2024, "rebased_national_accounts_vintage_corroboration")], "note": "2018-base SNA 2008 series and 2024 UNSD profile; not independent validation of every annual row."},
    ("guinea", "16"): {"ranges": [(2018, 2024, "gdp_rebase_population_denominator_open")], "note": "GDP rebase evidence; population denominator and vintage remain open."},
    ("guinea", "18"): {"ranges": [], "note": "Nominal-account evidence is contextual; PPP factor decomposition remains open."},
    ("turkmenistan", "15"): {"ranges": [(2019, 2025, "alternative_conversion_factor_period_documented")], "note": "Alternative conversion factor documented for 2019–2025; 2018 divergence onset remains unexplained."},
    ("turkmenistan", "16"): {"ranges": [(2019, 2025, "exchange_rate_warning_population_denominator_open")], "note": "Conversion warning applies; population denominator and exact contribution remain unresolved."},
    ("zimbabwe", "18"): {"ranges": [(2017, 2017, "country_specific_icp_factor_conversion_documented")], "note": "IMF special 2017 PPP-factor conversion documented; current WDI benchmark reconciliation remains open."},
    ("samoa", "20"): {"ranges": [(2021, 2024, "fiscal_year_correspondence_supported"), (2025, 2025, "residual_discrepancy_open")], "note": "July–June correspondence documented for 2021–2024; 2025 residual remains open."},
    ("tonga", "20"): {"ranges": [(2022, 2025, "fiscal_year_correspondence_supported_vintage_open")], "note": "Fiscal-year correspondence supported for 2022–2025; historical CPI vintage remains open."},
    ("palau", "20"): {"ranges": [(2023, 2025, "fiscal_year_correspondence_supported")], "note": "September fiscal-year correspondence supported for 2023–2025; earlier years remain open."},
    ("bahrain", "21"): {"ranges": [(2016, 2016, "official_year_end_vs_annual_reference_period_conflict"), (2017, 2025, "official_total_rate_exactly_matches_weo")], "note": "Official annual data verify 2016–2025; 2016 is a likely year-end/annual mismatch. 2015 is outside coverage."},
    ("moldova", "21"): {"ranges": [(2024, 2024, "national_lfs_corroborates_weo"), (2025, 2025, "national_lfs_corroborates_weo_break_in_series")], "note": "NBS LFS corroborates 2024–2025; preserve redesign and 2025 comparability caveat."},
    ("philippines", "21"): {"ranges": [(2023, 2025, "psa_annual_lfs_corroborates_weo_2025_preliminary")], "note": "PSA annualized LFS corroborates 2023–2025; 2025 remains preliminary."},
}


def _year_scope(country: str, field_id: str, year: int) -> tuple[str, str]:
    scope = COUNTRY_YEAR_SCOPES.get((_country_key(country), field_id))
    if not scope:
        return "no_country_case_year_scope", "No country-specific year scope is recorded."
    for start, end, label in scope["ranges"]:
        if start <= year <= end:
            return label, scope["note"]
    return "case_context_only_no_year_specific_support", scope["note"]


def _build_review_queues(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["game_id"], row["country_name"], row["field_id"])].append(row)
    country_queue = []
    for (game_id, country, field_id), items in sorted(groups.items()):
        country_queue.append({
            "game_id": game_id,
            "country_name": country,
            "field_id": field_id,
            "country_case_id": items[0]["country_case_id"],
            "year_count": len(items),
            "year_scope_counts": dict(sorted(Counter(r["year_evidence_scope"] for r in items).items())),
            "coverage_counts": dict(sorted(Counter(r["coverage_status"] for r in items).items())),
            "imf_status_counts": dict(sorted(Counter(r["imf_observation_status"] for r in items).items())),
            "wdi_status_counts": dict(sorted(Counter(r["wdi_observation_status"] for r in items).items())),
            "required_field_gate": items[0]["field_gate"],
            "review_status": "requires_country_field_review_not_approved",
        })
    field_queue = []
    for field_id in sorted(FIELD_RULES, key=int):
        subset = [r for r in rows if r["field_id"] == field_id]
        field_queue.append({
            "field_id": field_id,
            "row_count": len(subset),
            "coverage_counts": dict(sorted(Counter(r["coverage_status"] for r in subset).items())),
            "identity_gate_counts": dict(sorted(Counter(r["identity_gate"] for r in subset).items())),
            "imf_status_counts": dict(sorted(Counter(r["imf_observation_status"] for r in subset).items())),
            "wdi_status_counts": dict(sorted(Counter(r["wdi_observation_status"] for r in subset).items())),
            "year_evidence_scope_counts": dict(sorted(Counter(r["year_evidence_scope"] for r in subset).items())),
            "required_gate": FIELD_RULES[field_id]["gate"],
            "review_status": "field_semantics_open_not_approved",
        })
    return country_queue, field_queue


def _disposition(row: dict[str, str]) -> dict[str, str]:
    field_id = row["field_id"]
    if field_id not in FIELD_RULES:
        raise DispositionError(f"Unsupported field_id: {field_id}")
    field = FIELD_RULES[field_id]
    case = COUNTRY_CASES.get((_country_key(row["country_name"]), field_id), {})
    wdi_status = row.get("wdi_status_classification") or "not_available_in_input"
    if wdi_status == "missing":
        wdi_status_detail = "no_wdi_observation"
    elif wdi_status == "forecast":
        wdi_status_detail = "explicit_wdi_forecast_status"
    else:
        wdi_status_detail = "wdi_actual_estimate_status_not_established"
    imf_status = row.get("imf_status_hint") or "status_unclassified"
    period = row.get("imf_reporting_period_classification") or "unknown"
    if field_id == "20" and case:
        period = case["disposition"]
    elif field_id == "21" and case:
        period = case["disposition"]
    elif field_id in {"15", "16"} and period == "calendar_year":
        period = "imf_calendar_year_metadata_wdi_annual_period_not_vintage_aligned"
    elif field_id in {"15", "16"} and period == "non_calendar_fiscal_year":
        period = "imf_non_calendar_fiscal_year_wdi_annual_period_alignment_unverified"
    year_scope, year_scope_note = _year_scope(row["country_name"], field_id, int(row["year"]))
    return {
        "year_evidence_scope": year_scope,
        "year_evidence_note": year_scope_note,
        "identity_gate": (
            "identity_review_required"
            if row["identity_mapping_status"] != "mapped_verified"
            else "identity_verified"
        ),
        "concept_disposition": field["concept"],
        "period_disposition": period,
        "methodology_disposition": field["method"],
        "imf_observation_status": imf_status,
        "wdi_observation_status": wdi_status_detail,
        "country_case_id": case.get("case", "no_specific_country_case_recorded"),
        "country_case_disposition": case.get("disposition", "field_level_review_only_no_country_resolution"),
        "field_gate": field["gate"],
        "evidence_documents": case.get("evidence", field["evidence"]),
        "semantic_disposition": "diagnostic_review_required_not_approved",
    }


def build_matrix(input_path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    with input_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise DispositionError(f"Candidate matrix missing required columns: {sorted(missing)}")
        output: list[dict[str, str]] = []
        for row in reader:
            output.append({**row, **_disposition(row)})
    if not output:
        raise DispositionError("Candidate matrix contains no rows")
    country_queue, field_queue = _build_review_queues(output)
    summary: dict[str, Any] = {
        "assessment": "imf_weo_wdi_semantic_disposition_matrix",
        "input": str(input_path),
        "row_count": len(output),
        "country_count": len({r["game_id"] for r in output}),
        "field_counts": dict(sorted(Counter(r["field_id"] for r in output).items())),
        "identity_gate_counts": dict(sorted(Counter(r["identity_gate"] for r in output).items())),
        "semantic_disposition_counts": dict(sorted(Counter(r["semantic_disposition"] for r in output).items())),
        "country_case_counts": dict(sorted(Counter(r["country_case_id"] for r in output).items())),
        "wdi_observation_status_counts": dict(sorted(Counter(r["wdi_observation_status"] for r in output).items())),
        "imf_status_hint_counts": dict(sorted(Counter(r["imf_observation_status"] for r in output).items())),
        "year_evidence_scope_counts": dict(sorted(Counter(r["year_evidence_scope"] for r in output).items())),
        "country_field_review_group_count": len(country_queue),
        "field_review_count": len(field_queue),
        "database_written": False,
        "policy_changed": False,
        "approval_created": False,
        "release_promoted": False,
        "game_database_written": False,
    }
    summary["_country_queue"] = country_queue
    summary["_field_queue"] = field_queue
    return output, summary


def write_outputs(rows: list[dict[str, str]], summary: dict[str, Any], output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir()
    matrix_path = target / "semantic_disposition_matrix.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    country_queue = summary.pop("_country_queue", [])
    field_queue = summary.pop("_field_queue", [])
    summary["report_directory"] = str(target)
    (target / "assessment.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# IMF WEO–WDI semantic disposition matrix",
        "",
        f"- Rows: {summary['row_count']}",
        f"- Project identities: {summary['country_count']}",
        "- All rows remain diagnostic and not approved.",
        "- Identity review remains a separate gate.",
        "- Unknown observation status is preserved; no estimate/projection inference is made.",
        "",
        "## Field-level gates",
        "",
        "| Field | Concept disposition | Required gate |",
        "|---:|---|---|",
    ]
    for field_id, rule in FIELD_RULES.items():
        lines.append(f"| {field_id} | {rule['concept']} | {rule['gate']} |")
    lines += [
        "",
        "## Country evidence cases",
        "",
        "| Country | Field | Case | Disposition |",
        "|---|---:|---|---|",
    ]
    for (country, field_id), case in sorted(COUNTRY_CASES.items()):
        lines.append(f"| {country.title()} | {field_id} | {case['case']} | {case['disposition']} |")
    lines += [
        "",
        "## Coverage and interpretation",
        "",
        "This artifact enriches the supplied candidate matrix; it does not recompute observations or differences. Country cases are bounded to the evidence recorded in the linked assessment documents. A case disposition does not automatically validate every year in that country-field series.",
        "",
        "The IMF latest-actual metadata remains a hint; years after that boundary are not automatically separated into estimates and projections. WDI blank observation status remains unclassified. Missing WDI observations are labelled missing, not estimated.",
        "",
        "No identity was promoted, no source policy changed, no approval was created, no release was promoted, and neither database was written.",
        "",
    ]
    (target / "assessment.md").write_text("\n".join(lines), encoding="utf-8")
    (target / "country_field_review_queue.json").write_text(json.dumps(country_queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "field_review_summary.json").write_text(json.dumps(field_queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if country_queue:
        with (target / "country_field_review_queue.csv").open("w", encoding="utf-8", newline="") as stream:
            fields = list(country_queue[0])
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in country_queue:
                writer.writerow({**item, "year_scope_counts": json.dumps(item["year_scope_counts"], sort_keys=True), "coverage_counts": json.dumps(item["coverage_counts"], sort_keys=True), "imf_status_counts": json.dumps(item["imf_status_counts"], sort_keys=True), "wdi_status_counts": json.dumps(item["wdi_status_counts"], sort_keys=True)})
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        rows, summary = build_matrix(args.input)
        target = write_outputs(rows, summary, args.output_root)
    except (DispositionError, OSError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**summary, "report_directory": str(target)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
