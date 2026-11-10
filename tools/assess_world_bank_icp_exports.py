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
import io
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
TIME_CODES = {"time code", "year code"}
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


def decode_csv(path: Path) -> tuple[str, str]:
    """Decode a DataBank CSV with deterministic, strict encoding fallbacks."""
    raw = path.read_bytes()
    if raw.startswith((b"\\xff\\xfe", b"\\xfe\\xff")):
        return raw.decode("utf-16"), "utf-16"
    if raw.startswith(b"\\xef\\xbb\\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        # DataBank CSV exports can contain Windows-1252 punctuation.
        try:
            return raw.decode("cp1252"), "cp1252"
        except UnicodeDecodeError:
            return raw.decode("latin-1"), "latin-1"


def read_csv(path: Path) -> Iterable[tuple[str, list[str], list[list[Any]]]]:
    text, encoding = decode_csv(path)
    stream = io.StringIO(text, newline="")
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
    yield f"csv ({encoding})", header, [row for row in rows]


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


def source_release_for(path: Path) -> str:
    """Return the source release identity encoded by the acquisition path."""
    parts = path.parts
    for part in parts:
        match = re.fullmatch(r"icp_(20\d{2})_cycle", part)
        if match:
            return f"icp_{match.group(1)}_cycle"
    if "databank_exports" in parts:
        return "icp_2021_saved_report"
    return "unclassified_source_release"


def is_series_metadata_file(path: Path) -> bool:
    return "series" in norm(path.stem) and "metadata" in norm(path.stem)


def extract_series_metadata(headers: list[str], rows: list[list[Any]], *,
                            path: Path, source_release: str) -> list[dict[str, Any]]:
    country_i = column_index(headers, COUNTRY_NAMES)
    year_i = column_index(headers, YEARS)
    if len(headers) < 2:
        return []
    result = []
    for row_number, row in enumerate(rows, start=2):
        if str(cell(row, country_i) or "").strip() or year_value(cell(row, year_i)):
            continue
        # DataBank appends a small two-column Code / Indicator Name
        # dictionary after the repeated observation block, under the same
        # original wide-export header.
        code = str(cell(row, 0) or "").strip()
        description = str(cell(row, 1) or "").strip()
        if not re.fullmatch(r"\d{4,}", code) or not description:
            continue
        result.append({
            "source_release": source_release,
            "source_file": path.as_posix(),
            "indicator_code": code,
            "indicator_name": "",
            "indicator_definition": description,
            "source_row": row_number,
        })
    return result


def extract_rows(headers: list[str], rows: list[list[Any]], *, path: Path,
                 sheet: str, source_release: str) -> list[dict[str, Any]]:
    country_i = column_index(headers, COUNTRY_NAMES)
    code_i = column_index(headers, COUNTRY_CODES)
    year_i = column_index(headers, YEARS)
    time_code_i = column_index(headers, TIME_CODES)
    class_i = column_index(headers, CLASS_NAMES)
    class_code_i = column_index(headers, CLASS_CODES)
    series_i = column_index(headers, SERIES_NAMES)
    series_code_i = column_index(headers, SERIES_CODES)
    value_i = column_index(headers, VALUES)
    year_columns = [(i, int(str(header).strip())) for i, header in enumerate(headers)
                    if re.fullmatch(r"(?:19|20)\d{2}", str(header).strip())]
    wide_year_layout = year_i is None and bool(year_columns)
    if country_i is None or (year_i is None and not wide_year_layout):
        return []
    base = {i for i in (country_i, code_i, year_i, time_code_i, class_i, class_code_i,
                        series_i, series_code_i, value_i) if i is not None}
    wide_indicators = [
        (i, *indicator_header(str(header)))
        for i, header in enumerate(headers) if i not in base and str(header).strip()
    ]
    output: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        country = str(cell(row, country_i) or "").strip()
        if not country:
            continue
        common = {
            "source_release": source_release,
            "country_name": country,
            "country_code": str(cell(row, code_i) or "").strip(),
            "classification_name": str(cell(row, class_i) or "").strip(),
            "classification_code": str(cell(row, class_code_i) or "").strip(),
            "source_file": path.as_posix(),
            "sheet": sheet,
            "source_row": row_number,
        }
        if wide_year_layout:
            series_code = str(cell(row, series_code_i) or "").strip()
            series_name = str(cell(row, series_i) or "").strip()
            if not series_code and not series_name:
                continue
            for index, year in year_columns:
                value = numeric(cell(row, index))
                output.append({**common, "year": year,
                    "source_year_column": str(headers[index]),
                    "indicator_code": series_code,
                    "indicator_name": series_name,
                    "value": value,
                    "observation_status": "missing" if value is None else "reported_value"})
        else:
            year = year_value(cell(row, year_i))
            if year is None:
                continue
            common["year"] = year
            common["source_year_column"] = str(cell(row, time_code_i) or "")
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


def extract_country_metadata(headers: list[str], rows: list[list[Any]], *,
                             path: Path, source_release: str) -> list[dict[str, Any]]:
    result = []
    for row_number, row in enumerate(rows, start=2):
        if not any(str(value or "").strip() for value in row):
            continue
        record = {"source_release": source_release, "source_file": path.as_posix(),
                  "source_row": row_number}
        for index, header in enumerate(headers):
            key = norm(header).replace(" ", "_") or f"column_{index + 1}"
            record[key] = cell(row, index)
        result.append(record)
    return result



def is_icp2011_original_workbook(path: Path) -> bool:
    """Identify the specifically acquired original ICP 2011 results workbook."""
    return (path.suffix.lower() == ".xlsx"
            and path.name == "2011-International-Comparison-Program-results.xlsx"
            and "icp_2011_cycle" in path.parts)


def inspect_icp2011_workbook(path: Path, *, relative_path: Path,
                             source_release: str) -> tuple[list[dict[str, Any]],
                                                            list[dict[str, Any]],
                                                            list[dict[str, Any]]]:
    """Capture the original ICP 2011 workbook's sheet and cell structure.

    The 23 R/D/S tables have heterogeneous measures and units. Until each table's
    row/column semantics are mapped from its own labels, this function deliberately
    preserves source cells rather than manufacturing harmonized observations.
    """
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ICPAssessmentError("Install the project's Excel dependencies to inspect XLSX exports") from exc
    workbook = load_workbook(path, read_only=False, data_only=False)
    inventory: list[dict[str, Any]] = []
    cells: list[dict[str, Any]] = []
    rows_out: list[dict[str, Any]] = []
    try:
        for sheet in workbook.worksheets:
            match = re.match(r"^\\s*([RDS])\\s*0*(\\d+)\\b", sheet.title, re.IGNORECASE)
            table_prefix = match.group(1).upper() if match else ""
            table_number = int(match.group(2)) if match else None
            table_id = f"{table_prefix}{table_number}" if match else ""
            table_category = {
                "R": "summary_results", "D": "detailed_results",
                "S": "supplementary_results",
            }.get(table_prefix, "unclassified_sheet")
            nonempty_count = 0
            last_row = 0
            last_column = 0
            for row_number in range(1, sheet.max_row + 1):
                values = [sheet.cell(row_number, col).value
                          for col in range(1, sheet.max_column + 1)]
                if not any(value is not None for value in values):
                    continue
                last_row = row_number
                last_column = max((i + 1 for i, value in enumerate(values)
                                   if value is not None), default=0)
                nonempty_count += sum(value is not None for value in values)
                rows_out.append({
                    "source_release": source_release,
                    "source_file": relative_path.as_posix(),
                    "sheet": sheet.title, "table_id": table_id,
                    "table_category": table_category, "source_row": row_number,
                    "row_values_json": json.dumps(values[:last_column],
                                                   ensure_ascii=False, default=str),
                })
                for column_number, value in enumerate(values, start=1):
                    if value is None:
                        continue
                    coordinate = sheet.cell(row_number, column_number).coordinate
                    cells.append({
                        "source_release": source_release,
                        "source_file": relative_path.as_posix(),
                        "sheet": sheet.title, "table_id": table_id,
                        "table_category": table_category,
                        "cell": coordinate, "source_row": row_number,
                        "source_column": column_number,
                        "column_letter": sheet.cell(row_number, column_number).column_letter,
                        "value": value.isoformat() if hasattr(value, "isoformat") else value,
                        "cell_data_type": sheet.cell(row_number, column_number).data_type,
                        "number_format": sheet.cell(row_number, column_number).number_format,
                    })
            inventory.append({
                "source_release": source_release,
                "source_file": relative_path.as_posix(),
                "sheet": sheet.title, "table_id": table_id,
                "table_category": table_category,
                "max_row": sheet.max_row, "max_column": sheet.max_column,
                "last_nonempty_row": last_row, "last_nonempty_column": last_column,
                "nonempty_cell_count": nonempty_count,
                "merged_range_count": len(sheet.merged_cells.ranges),
            })
    finally:
        workbook.close()
    if not inventory:
        raise ICPAssessmentError(f"Original ICP 2011 workbook has no worksheets: {path}")
    return inventory, cells, rows_out


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
    series_metadata: list[dict[str, Any]] = []
    country_metadata: list[dict[str, Any]] = []
    observed_series: dict[tuple[str, str], dict[str, Any]] = {}
    workbook_inventory: list[dict[str, Any]] = []
    workbook_cells: list[dict[str, Any]] = []
    workbook_rows: list[dict[str, Any]] = []
    for path in files:
        relative_path = path.relative_to(root)
        release = source_release_for(relative_path)
        if is_icp2011_original_workbook(relative_path):
            inventory, cells, table_rows = inspect_icp2011_workbook(
                path, relative_path=relative_path, source_release=release)
            workbook_inventory.extend(inventory)
            workbook_cells.extend(cells)
            workbook_rows.extend(table_rows)
            inspected.append({
                "path": relative_path.as_posix(),
                "artifact_role": "original_benchmark_workbook_structure",
                "observation_rows": 0,
                "metadata_rows": len(inventory),
                "workbook_nonempty_cells": len(cells),
                "workbook_nonempty_rows": len(table_rows),
            })
            continue
        readers = read_csv(path) if path.suffix.lower() == ".csv" else read_xlsx(path)
        file_count = 0
        metadata_count = 0
        for sheet, headers, rows in readers:
            if "country" in norm(path.stem) and "metadata" in norm(path.stem):
                extracted_countries = extract_country_metadata(
                    headers, rows, path=relative_path, source_release=release)
                country_metadata.extend(extracted_countries)
                metadata_count += len(extracted_countries)
                continue
            if is_series_metadata_file(path):
                extracted_metadata = extract_series_metadata(
                    headers, rows, path=relative_path, source_release=release)
                series_metadata.extend(extracted_metadata)
                metadata_count += len(extracted_metadata)
                continue
            extracted = extract_rows(headers, rows, path=relative_path, sheet=sheet,
                                     source_release=release)
            observations.extend(extracted)
            file_count += len(extracted)
            for item in extracted:
                code = str(item.get("indicator_code") or "").strip()
                name = str(item.get("indicator_name") or "").strip()
                if code or name:
                    observed_series[(release, code or name)] = {
                        "source_release": release, "source_file": relative_path.as_posix(),
                        "indicator_code": code, "indicator_name": name,
                        "indicator_definition": "", "source_row": item["source_row"]}
        if file_count or metadata_count:
            if "country" in norm(path.stem) and "metadata" in norm(path.stem):
                artifact_role = "country_metadata"
            elif is_series_metadata_file(path):
                artifact_role = "series_metadata"
            else:
                artifact_role = "observations"
            inspected.append({"path": relative_path.as_posix(),
                              "artifact_role": artifact_role,
                              "observation_rows": file_count,
                              "metadata_rows": metadata_count})
        else:
            unsupported.append(relative_path.as_posix())
    if not observations and not workbook_inventory:
        raise ICPAssessmentError("No recognizable country/year/indicator observations or supported ICP 2011 workbook found")
    series_catalogue = dict(observed_series)
    for item in series_metadata:
        key = (item["source_release"], item["indicator_code"] or item["indicator_name"])
        if key in series_catalogue:
            if item["indicator_definition"]:
                series_catalogue[key]["indicator_definition"] = item["indicator_definition"]
        else:
            series_catalogue[key] = item
    series_metadata = list(series_catalogue.values())
    coverage: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    latest_year: dict[tuple[str, str, str], int] = {}
    for item in observations:
        key = (item["source_release"],
               item["country_code"] or item["country_name"],
               item["classification_code"] or item["classification_name"],
               item["indicator_code"] or item["indicator_name"])
        if item["value"] is not None:
            coverage[key].add(item["year"])
            latest_year[key] = max(latest_year.get(key, item["year"]), item["year"])
    # Preserve every source-vintage row tied at the latest year. Original and
    # revised benchmarks must never overwrite one another.
    latest_rows = []
    for item in observations:
        key = (item["source_release"],
               item["country_code"] or item["country_name"],
               item["classification_code"] or item["classification_name"],
               item["indicator_code"] or item["indicator_name"])
        if item["value"] is not None and item["year"] == latest_year.get(key):
            latest_rows.append(item)
    coverage_rows = []
    for key, years in sorted(coverage.items()):
        coverage_rows.append({"source_release": key[0],
            "country_code_or_name": key[1],
            "classification_code_or_name": key[2], "indicator_code": key[3],
            "first_available_year": min(years), "latest_available_year": max(years),
            "available_year_count": len(years),
            "observed_years": ";".join(map(str, sorted(years)))})
    stamp = retrieved_at or datetime.now(timezone.utc)
    report_id = "inspection_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = root / REPORT_ROOT / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    observation_fields = list(observations[0]) if observations else [\n        "source_release", "country_name", "country_code", "classification_name",\n        "classification_code", "source_file", "sheet", "source_row", "year",\n        "source_year_column", "indicator_code", "indicator_name", "value",\n        "observation_status"]
    def write_csv(name: str, rows: list[dict[str, Any]], fields: list[str]) -> None:
        with (report_dir / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    write_csv("observations_long.csv", observations, observation_fields)
    write_csv("latest_available_by_country_indicator.csv", latest_rows, observation_fields)
    write_csv("coverage_by_country_indicator.csv", coverage_rows,
              list(coverage_rows[0]) if coverage_rows else [])
    metadata_fields = list(series_metadata[0]) if series_metadata else [
        "source_release", "source_file", "indicator_code", "indicator_name",
        "indicator_definition", "source_row"]
    write_csv("series_metadata.csv", series_metadata, metadata_fields)
    country_fields = list(country_metadata[0]) if country_metadata else [
        "source_release", "source_file", "source_row"]
    write_csv("country_metadata.csv", country_metadata, country_fields)
    workbook_inventory_fields = list(workbook_inventory[0]) if workbook_inventory else [
        "source_release", "source_file", "sheet", "table_id", "table_category",
        "max_row", "max_column", "last_nonempty_row", "last_nonempty_column",
        "nonempty_cell_count", "merged_range_count"]
    workbook_cell_fields = list(workbook_cells[0]) if workbook_cells else [
        "source_release", "source_file", "sheet", "table_id", "table_category",
        "cell", "source_row", "source_column", "column_letter", "value",
        "cell_data_type", "number_format"]
    workbook_row_fields = list(workbook_rows[0]) if workbook_rows else [
        "source_release", "source_file", "sheet", "table_id", "table_category",
        "source_row", "row_values_json"]
    write_csv("icp_2011_workbook_sheets.csv", workbook_inventory, workbook_inventory_fields)
    write_csv("icp_2011_workbook_cells.csv", workbook_cells, workbook_cell_fields)
    write_csv("icp_2011_workbook_rows.csv", workbook_rows, workbook_row_fields)
    result = {
        "assessment": "world_bank_icp_multicycle_export_inspection",
        "report_id": report_id,
        "observation_count_including_missing": len(observations),
        "series_metadata_definition_count": sum(bool(item["indicator_definition"]) for item in series_metadata),
        "observed_series_count": len(observed_series),
        "country_metadata_row_count": len(country_metadata),
        "source_release_count": len({item["source_release"] for item in observations}
                                    | {item["source_release"] for item in workbook_inventory}),
        "icp_2011_workbook_sheet_count": len(workbook_inventory),
        "icp_2011_workbook_nonempty_cell_count": len(workbook_cells),
        "icp_2011_workbook_nonempty_row_count": len(workbook_rows),
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
            "series_metadata": (report_dir / "series_metadata.csv").relative_to(root).as_posix(),
            "country_metadata": (report_dir / "country_metadata.csv").relative_to(root).as_posix(),
            "icp_2011_workbook_sheets": (report_dir / "icp_2011_workbook_sheets.csv").relative_to(root).as_posix(),
            "icp_2011_workbook_cells": (report_dir / "icp_2011_workbook_cells.csv").relative_to(root).as_posix(),
            "icp_2011_workbook_rows": (report_dir / "icp_2011_workbook_rows.csv").relative_to(root).as_posix(),
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
