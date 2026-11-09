"""Inspect locally acquired World Bank ICP DataBank exports.

The inspector is intentionally format-tolerant: it accepts wide DataBank exports
(country/year/classification columns plus one column per indicator) and long
exports (one indicator/value per row). It preserves source file and sheet identity
and never imputes or carries values forward.
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
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = Path("raw_data/sources/world_bank_icp")
REPORT_ROOT = Path("reports/sources/world-bank-icp")
COUNTRY_NAMES = {"country", "country name", "economy", "economy name"}
COUNTRY_CODES = {"country code", "economy code", "iso3", "iso alpha 3", "country iso3"}
YEARS = {"time", "year", "reference year", "time code"}
CLASS_NAMES = {"classification", "classification name"}
CLASS_CODES = {"classification code"}
SERIES_NAMES = {"series", "indicator", "indicator name", "series name"}
SERIES_CODES = {"series code", "indicator code"}
VALUES = {"value", "observation value", "obs value"}
MISSING = {"", "..", "...", "na", "n/a", "n.a.", "null", "none", "-", "—"}


class ICPAssessmentError(RuntimeError):
    """Invalid or unsupported ICP export."""


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def year_value(value: Any) -> int | None:
    match = re.search(r"(?:19|20)\d{2}", str(value or ""))
    return int(match.group()) if match else None


def numeric(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text.lower() in MISSING:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_csv(path: Path) -> Iterable[tuple[str, list[str], list[list[Any]]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t|")
        except csv.Error:
            dialect = csv.excel
        rows = csv.reader(stream, dialect)
        try:
            header = next(rows)
        except StopIteration:
            return
        yield "csv", header, [row for row in rows]


def read_xlsx(path: Path) -> Iterable[tuple[str, list[str], list[list[Any]]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ICPAssessmentError("Install the project's Excel dependencies to inspect XLSX exports") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            iterator = sheet.iter_rows(values_only=True)
            header = next(iterator, None)
            if header is None:
                continue
            yield sheet.title, [str(x or "") for x in header], [list(row) for row in iterator]
    finally:
        workbook.close()


def column_index(headers: list[str], aliases: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if norm(header) in aliases:
            return index
    return None


def cell(row: list[Any], index: int | None) -> Any:
    return row[index] if index is not None and index < len(row) else None


def indicator_header(header: str) -> tuple[str, str]:
    value = header.strip()
    match = re.match(r"^([^:]+):\s*(.*?)\s*\[([^]]+)\]\s*$", value)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    match = re.match(r"^(.*?)\s*\[([^]]+)\]\s*$", value)
    if match:
        return match.group(2).strip(), match.group(1).strip()
    return value, value


def extract_rows(headers: list[str], rows: list[list[Any]], *, path: Path,
                 sheet: str) -> list[dict[str, Any]]:
    country_i = column_index(headers, COUNTRY_NAMES)
    code_i = column_index(headers, COUNTRY_CODES)
    year_i = column_index(headers, YEARS)
    class_i = column_index(headers, CLASS_NAMES)
    class_code_i = column_index(headers, CLASS_CODES)
    series_i = column_index(headers, SERIES_NAMES)
    series_code_i = column_index(headers, SERIES_CODES)
    value_i = column_index(headers, VALUES)
    if country_i is None or year_i is None:
        return []
    base = {i for i in (country_i, code_i, year_i, class_i, class_code_i,
                        series_i, series_code_i, value_i) if i is not None}
    output: list[dict[str, Any]] = []
    wide_indicators = [
        (i, *indicator_header(str(header)))
        for i, header in enumerate(headers) if i not in base and str(header).strip()
    ]
    for row_number, row in enumerate(rows, start=2):
        country = str(cell(row, country_i) or "").strip()
        year = year_value(cell(row, year_i))
        if not country or year is None:
            continue
        common = {
            "country_name": country,
            "country_code": str(cell(row, code_i) or "").strip(),
            "year": year,
            "classification_name": str(cell(row, class_i) or "").strip(),
            "classification_code": str(cell(row, class_code_i) or "").strip(),
            "source_file": path.as_posix(),
            "sheet": sheet,
            "source_row": row_number,
        }
        if series_i is not None and value_i is not None:
            value = numeric(cell(row, value_i))
            output.append({**common,
                "indicator_code": str(cell(row, series_code_i) or "").strip(),
                "indicator_name": str(cell(row, series_i) or "").strip(),
                "value": value,
                "observation_status": "missing" if value is None else "reported_value"})
        else:
            for index, indicator_code, indicator_name in wide_indicators:
                value = numeric(cell(row, index))
                output.append({**common, "indicator_code": indicator_code,
                    "indicator_name": indicator_name, "value": value,
                    "observation_status": "missing" if value is None else "reported_value"})
    return output


def inspect(root: str | Path = ROOT, retrieved_at: datetime | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    raw_root = root / RAW_ROOT
    if not raw_root.exists():
        raise ICPAssessmentError(f"ICP raw-data directory does not exist: {raw_root}")
    files = sorted(p for p in raw_root.rglob("*") if p.is_file()
                   and p.suffix.lower() in {".csv", ".xlsx"})
    if not files:
        raise ICPAssessmentError("No ICP CSV or XLSX exports found; acquire DataBank exports first")
    observations: list[dict[str, Any]] = []
    inspected: list[dict[str, Any]] = []
    unsupported: list[str] = []
    for path in files:
        readers = read_csv(path) if path.suffix.lower() == ".csv" else read_xlsx(path)
        file_count = 0
        for sheet, headers, rows in readers:
            extracted = extract_rows(headers, rows, path=path.relative_to(root), sheet=sheet)
            observations.extend(extracted)
            file_count += len(extracted)
        if file_count:
            inspected.append({"path": path.relative_to(root).as_posix(),
                              "observation_rows": file_count})
        else:
            unsupported.append(path.relative_to(root).as_posix())
    if not observations:
        raise ICPAssessmentError("No recognizable country/year/indicator observations found")
    coverage: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    latest_year: dict[tuple[str, str, str], int] = {}
    for item in observations:
        key = (item["country_code"] or item["country_name"],
               item["classification_code"] or item["classification_name"],
               item["indicator_code"] or item["indicator_name"])
        if item["value"] is not None:
            coverage[key].add(item["year"])
            latest_year[key] = max(latest_year.get(key, item["year"]), item["year"])
    # Preserve every source-vintage row tied at the latest year. Original and
    # revised benchmarks must never overwrite one another.
    latest_rows = []
    for item in observations:
        key = (item["country_code"] or item["country_name"],
               item["classification_code"] or item["classification_name"],
               item["indicator_code"] or item["indicator_name"])
        if item["value"] is not None and item["year"] == latest_year.get(key):
            latest_rows.append(item)
    coverage_rows = []
    for key, years in sorted(coverage.items()):
        coverage_rows.append({"country_code_or_name": key[0],
            "classification_code_or_name": key[1], "indicator_code": key[2],
            "first_available_year": min(years), "latest_available_year": max(years),
            "available_year_count": len(years),
            "observed_years": ";".join(map(str, sorted(years)))})
    stamp = retrieved_at or datetime.now(timezone.utc)
    report_id = "inspection_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = root / REPORT_ROOT / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    observation_fields = list(observations[0])
    def write_csv(name: str, rows: list[dict[str, Any]], fields: list[str]) -> None:
        with (report_dir / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    write_csv("observations_long.csv", observations, observation_fields)
    write_csv("latest_available_by_country_indicator.csv", latest_rows, observation_fields)
    write_csv("coverage_by_country_indicator.csv", coverage_rows,
              list(coverage_rows[0]) if coverage_rows else [])
    result = {
        "assessment": "world_bank_icp_multicycle_export_inspection",
        "report_id": report_id,
        "observation_count_including_missing": len(observations),
        "latest_available_series_count": len(latest_rows),
        "coverage_group_count": len(coverage_rows),
        "input_files_inspected": inspected,
        "input_files_unrecognized": unsupported,
        "latest_value_rule": "latest non-missing year independently by country, classification and indicator; all tied source-vintage records are retained",
        "missing_values": "preserved in observations_long.csv; excluded only from latest-value selection",
        "imputation_rule": "no imputation, interpolation, extrapolation or carry-forward performed",
        "outputs": {
            "observations": (report_dir / "observations_long.csv").relative_to(root).as_posix(),
            "latest_available": (report_dir / "latest_available_by_country_indicator.csv").relative_to(root).as_posix(),
            "coverage": (report_dir / "coverage_by_country_indicator.csv").relative_to(root).as_posix(),
        },
        "side_effects": {"raw_data_written": False, "project_database_written": False,
                         "game_database_written": False, "approval_created": False,
                         "source_selection_changed": False},
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
        result = inspect(args.root)
    except (ICPAssessmentError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
