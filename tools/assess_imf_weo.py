"""Read-only coverage and identity assessment for the manually acquired IMF WEO CSV."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_data/sources/imf_weo/october_2026"
CSV_PATH = RAW / "dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv"
PDF_PATH = RAW / "October 2026 WEO Database Appendix.pdf"
IDENTITY = ROOT / "config/country_identity_registry.json"
POLICY = ROOT / "config/source_selection.json"
REGISTRY = ROOT / "config/data_sources.json"
OUTPUT = ROOT / "reports/sources/imf-weo"
EXPECTED = {
    "csv": ("a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d", 26692032),
    "appendix": ("cd4e2829d7e621d43134728bfc128547f776e909e08ef1d38b837e2d39e5ae2a", 985701),
}
INDICATORS = {
    "NGDPD": (15, "gdp", "US dollar", "Billions"),
    "NGDPDPC": (16, "gdp_per_capita", "US dollar", "Units"),
    "PPPGDP": (18, "gdp_ppp", None, "Billions"),
    "PCPIPCH": (20, "inflation", "Percent", "Units"),
    "LUR": (21, "unemployment", None, "Units"),
}
YEAR = re.compile(r"^\d{4}$")


class AssessmentError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(path: Path, expected: tuple[str, int] | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise AssessmentError(f"Missing required input: {path}")
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise AssessmentError(f"Input must be inside repository: {path}") from exc
    result = {"path": relative, "sha256": digest(path), "byte_count": path.stat().st_size}
    if expected:
        result["matches_recorded_snapshot"] = result["sha256"] == expected[0] and result["byte_count"] == expected[1]
        if not result["matches_recorded_snapshot"]:
            raise AssessmentError(f"Input differs from recorded manual snapshot: {path}")
    return result


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def identity_index(path: Path) -> dict[str, list[dict[str, Any]]]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssessmentError(f"Cannot read identity registry: {exc}") from exc
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in doc.get("records", []):
        iso, source = record.get("iso") or {}, record.get("source") or {}
        for code in {iso.get("alpha3"), source.get("current_source_id")}:
            if isinstance(code, str) and re.fullmatch(r"[A-Z]{3}", code):
                result[code].append(record)
    return dict(result)


def build_assessment(csv_path: Path = CSV_PATH, appendix_path: Path = PDF_PATH,
                     start_year: int = 1980, end_year: int = 2031,
                     identity_path: Path = IDENTITY) -> dict[str, Any]:
    if start_year < 1900 or end_year < start_year or end_year > 2100:
        raise AssessmentError("Invalid year range")
    inputs = {
        "csv": fingerprint(csv_path, EXPECTED["csv"]),
        "appendix": fingerprint(appendix_path, EXPECTED["appendix"]),
        "identity_registry": fingerprint(identity_path),
        "source_selection_policy": fingerprint(POLICY),
        "source_registry": fingerprint(REGISTRY),
    }
    identities = identity_index(identity_path)
    year_columns = [str(y) for y in range(start_year, end_year + 1)]
    grouped = {code: [] for code in INDICATORS}
    invalid_frequency = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = list(reader.fieldnames or [])
        required = {"SERIES_CODE", "COUNTRY", "INDICATOR", "FREQUENCY", "UNIT", "SCALE", "LATEST_ACTUAL_ANNUAL_DATA"}
        if required - set(headers):
            raise AssessmentError(f"Missing CSV columns: {sorted(required - set(headers))}")
        for row in reader:
            parts = (row.get("SERIES_CODE") or "").split(".")
            if len(parts) != 3 or parts[1] not in grouped:
                continue
            if parts[2] != "A" or row.get("FREQUENCY", "").strip() != "Annual":
                invalid_frequency.append(row.get("SERIES_CODE"))
                continue
            grouped[parts[1]].append(row)

    indicators, country_rows, series_rows = [], [], []
    for code, (field_id, key, expected_unit, expected_scale) in INDICATORS.items():
        rows = grouped[code]
        prefixes, latest, units, scales, months = Counter(), Counter(), Counter(), Counter(), Counter()
        populated, duplicates, seen = Counter(), [], set()
        aggregate_prefixes, unmatched, name_mismatches = set(), set(), set()
        registry_matches, name_matches, non_null, invalid = set(), set(), 0, 0
        for row in rows:
            series_code = row["SERIES_CODE"]
            prefix = series_code.split(".")[0]
            if series_code in seen:
                duplicates.append(series_code)
            seen.add(series_code)
            prefixes[prefix] += 1
            latest[(row.get("LATEST_ACTUAL_ANNUAL_DATA") or "").strip() or "(blank)"] += 1
            units[(row.get("UNIT") or "").strip() or "(blank)"] += 1
            scales[(row.get("SCALE") or "").strip() or "(blank)"] += 1
            months[(row.get("START_END_MONTHS_OF_REPORTING_YEAR") or "").strip() or "(blank)"] += 1

            matches = identities.get(prefix, []) if re.fullmatch(r"[A-Z]{3}", prefix) else []
            game_ids = {m.get("game_id") for m in matches if m.get("game_id")}
            if len(prefix) != 3:
                aggregate_prefixes.add(prefix)
                status, game_id, name_match = "non_iso_aggregate_code", None, False
            elif len(game_ids) == 1:
                status, game_id = "registry_code_match_review_iso_status", next(iter(game_ids))
                registry_matches.add(prefix)
                rec = next(m for m in matches if m.get("game_id") == game_id)
                aliases = [rec.get("names", {}).get("en"), *(rec.get("names", {}).get("aliases_en") or [])]
                name_match = norm(row.get("COUNTRY")) in {norm(v) for v in aliases if v}
                if name_match:
                    name_matches.add(prefix)
                else:
                    name_mismatches.add(prefix)
            elif len(game_ids) > 1:
                status, game_id, name_match = "ambiguous_registry_code", None, False
                unmatched.add(prefix)
            else:
                status, game_id, name_match = "unmatched_three_letter_source_code", None, False
                unmatched.add(prefix)

            values = []
            for year in year_columns:
                raw = (row.get(year) or "").strip()
                if not raw:
                    continue
                try:
                    number = float(raw)
                except ValueError:
                    invalid += 1
                    continue
                if not math.isfinite(number):
                    invalid += 1
                    continue
                populated[year] += 1
                non_null += 1
                values.append(int(year))
            item = {
                "field_id": field_id, "indicator_code": code, "series_code": series_code,
                "source_country_code": prefix, "country_name": row.get("COUNTRY", ""),
                "identity_status": status, "game_id": game_id, "registry_name_match": name_match,
                "latest_actual_annual_data": (row.get("LATEST_ACTUAL_ANNUAL_DATA") or "").strip() or None,
                "unit": (row.get("UNIT") or "").strip() or None,
                "scale": (row.get("SCALE") or "").strip() or None,
                "reporting_year_months": (row.get("START_END_MONTHS_OF_REPORTING_YEAR") or "").strip() or None,
                "non_null_observation_count": len(values),
                "first_populated_year": min(values) if values else None,
                "latest_populated_year": max(values) if values else None,
            }
            series_rows.append(item)
            if status != "non_iso_aggregate_code":
                country_rows.append(item.copy())

        if not rows:
            raise AssessmentError(f"Required indicator series are absent: {code}")
        indicators.append({
            "field_id": field_id, "key": key, "indicator_code": code, "series_count": len(rows),
            "unique_series_count": len(seen), "duplicate_series_codes": sorted(duplicates),
            "prefix_lengths": dict(Counter(len(p) for p in prefixes)),
            "non_iso_aggregate_prefixes": sorted(aggregate_prefixes),
            "unmatched_or_ambiguous_three_letter_prefixes": sorted(unmatched),
            "registry_code_match_count": len(registry_matches), "registry_name_match_count": len(name_matches),
            "registry_name_mismatch_prefixes": sorted(name_mismatches),
            "unit_distribution": dict(units), "scale_distribution": dict(scales),
            "latest_actual_annual_data_distribution": dict(latest),
            "reporting_year_month_distribution": dict(months),
            "populated_observations_by_year": dict(sorted(populated.items())),
            "non_null_observation_count": non_null, "invalid_numeric_observation_count": invalid,
            "unit_contract": "matches_expected" if expected_unit and set(units) == {expected_unit} else (
                "not_supplied_requires_review" if expected_unit is None else "unexpected_values"),
            "scale_contract": "matches_expected" if set(scales) == {expected_scale} else "unexpected_values",
        })

    return {
        "schema_version": 1, "assessment": "imf_weo_manual_snapshot_coverage_and_identity",
        "source_id": "imf_weo", "release": "october_2026",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start_year": start_year, "end_year": end_year},
        "input_fingerprints": inputs,
        "csv_structure": {"encoding": "UTF-8 with optional BOM", "delimiter": "comma",
                          "column_count": len(headers), "year_columns_detected": [h for h in headers if YEAR.fullmatch(h)],
                          "invalid_frequency_series_codes": invalid_frequency},
        "indicator_count": len(indicators), "indicators": indicators,
        "country_series": country_rows, "series": series_rows,
        "wdi_comparison": {"status": "not_assessed",
            "reason": "WDI currently has API coverage evidence only; a normalized WDI snapshot is required for country-year definition and value comparison.",
            "fields": [15, 16, 18, 20, 21]},
        "semantic_limitations": [
            "Latest-actual metadata is retained verbatim; fiscal-year labels are not coerced to calendar years.",
            "PPPGDP has no latest-actual metadata; its actual/estimate/projected status remains unresolved.",
            "LUR UNIT is blank; do not normalize to percent until the series definition is verified.",
            "Three-letter IMF codes are candidate identity keys only; registry matches do not approve ISO assignments.",
            "Non-three-letter prefixes are excluded from country identity matching as aggregate/group codes.",
            "Missing annual values remain missing; a series row does not imply complete year coverage.",
        ],
        "side_effects": {"immutable_snapshots_acquired": False, "source_registry_changed": False,
                         "source_selection_policy_changed": False, "canonical_database_written": False,
                         "release_promoted": False},
    }


def write_reports(report: dict[str, Any], output_root: Path = OUTPUT) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    target.mkdir(parents=True, exist_ok=False)
    (target / "assessment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# IMF WEO October 2026 coverage and identity assessment", "",
             f"- Checked: {report['checked_at']}",
             f"- Period: {report['period']['start_year']}–{report['period']['end_year']}",
             "- Read-only; no acquisition, policy changes, database writes or promotion", "",
             "| Field | Series | Rows | Registry code matches | Name matches | Aggregate prefixes | Non-null observations |",
             "|---:|---|---:|---:|---:|---:|---:|"]
    for item in report["indicators"]:
        lines.append(f"| {item['field_id']} | {item['indicator_code']} | {item['series_count']} | {item['registry_code_match_count']} | {item['registry_name_match_count']} | {len(item['non_iso_aggregate_prefixes'])} | {item['non_null_observation_count']} |")
    for item in report["indicators"]:
        lines.extend(["", f"## {item['indicator_code']} — field {item['field_id']}", "",
                      f"- Prefix lengths: {json.dumps(item['prefix_lengths'], sort_keys=True)}",
                      f"- Aggregate prefixes: {', '.join(item['non_iso_aggregate_prefixes']) or 'none'}",
                      f"- Unmatched/ambiguous codes: {', '.join(item['unmatched_or_ambiguous_three_letter_prefixes']) or 'none'}",
                      f"- Units: {json.dumps(item['unit_distribution'], ensure_ascii=False, sort_keys=True)}",
                      f"- Scales: {json.dumps(item['scale_distribution'], sort_keys=True)}",
                      f"- Latest actual metadata: {json.dumps(item['latest_actual_annual_data_distribution'], ensure_ascii=False, sort_keys=True)}",
                      f"- Reporting-year months: {json.dumps(item['reporting_year_month_distribution'], sort_keys=True)}",
                      f"- Populated by year: {json.dumps(item['populated_observations_by_year'], sort_keys=True)}"])
    lines.extend(["", "## Semantic limitations", "", *[f"- {x}" for x in report["semantic_limitations"]],
                  "", "## WDI comparison", "", report["wdi_comparison"]["reason"], "",
                  "## Input fingerprints", "",
                  "| Input | Bytes | SHA-256 | Recorded snapshot match |", "|---|---:|---|---|"])
    for label in ("csv", "appendix"):
        item = report["input_fingerprints"][label]
        lines.append(f"| {label} | {item['byte_count']} | {item['sha256']} | {item['matches_recorded_snapshot']} |")
    (target / "assessment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for filename, records in (("country_coverage.csv", report["country_series"]), ("series_rows.csv", report["series"])):
        fields = list(records[0]) if records else []
        with (target / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    parser.add_argument("--appendix", type=Path, default=PDF_PATH)
    parser.add_argument("--start-year", type=int, default=1980)
    parser.add_argument("--end-year", type=int, default=2031)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = build_assessment(args.csv, args.appendix, args.start_year, args.end_year)
        target = write_reports(report, args.output_root)
    except (AssessmentError, OSError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"assessment": report["assessment"], "indicators": report["indicator_count"],
                      "period": report["period"], "report_directory": str(target),
                      "wdi_comparison": report["wdi_comparison"]["status"],
                      "snapshots_acquired": False, "database_written": False, "release_promoted": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
