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
        match = re.fullmatch(r"icp_(20\\d{2})_cycle", part)
        if match:
            return f"icp_{match.group(1)}_cycle"
    if "databank_exports" in parts:
        return "icp_2021_saved_report"
    return "unclassified_source_release"


def is_series_metadata_file(path: Path) -> bool:
    return "series" in norm(path.stem) and "metadata" in norm(path.stem)


def extract_series_metadata(headers: list[str], rows: list[list[Any]], *,
                            path: Path, source_release: str) -> list[dict[str, Any]]:
    name_i = column_index(headers, CLASS_NAMES)
    description_i = column_index(headers, CLASS_CODES)
    country_i = column_index(headers, COUNTRY_NAMES)
    year_i = column_index(headers, YEARS)
    if name_i is None or description_i is None:
        return []
    result = []
    for row_number, row in enumerate(rows, start=2):
        if str(cell(row, country_i) or "").strip() or year_value(cell(row, year_i)):
            continue
        code = str(cell(row, name_i) or "").strip()
        description = str(cell(row, description_i) or "").strip()
        if not re.fullmatch(r"\\d{4,}", code) or not description:
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
    if country_i is None or year_i is None:
        return []
    base = {i for i in (country_i, code_i, year_i, time_code_i, class_i, class_code_i,
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
            "source_release": source_release,
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
    series_metadata: list[dict[str, Any]] = []
    for path in files:
        relative_path = path.relative_to(root)
        release = source_release_for(relative_path)
        readers = read_csv(path) if path.suffix.lower() == ".csv" else read_xlsx(path)
        file_count = 0
        metadata_count = 0
        for sheet, headers, rows in readers:
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
        if file_count or metadata_count:
            inspected.append({"path": relative_path.as_posix(),
                              "artifact_role": "series_metadata" if metadata_count else "observations",
                              "observation_rows": file_count,
                              "series_metadata_rows": metadata_count})
        else:
            unsupported.append(relative_path.as_posix())
    if not observations:
        raise ICPAssessmentError("No recognizable country/year/indicator observations found")
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
        key = (item["country_code"] or item["country_name"],
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
    metadata_fields = list(series_metadata[0]) if series_metadata else [
        "source_release", "source_file", "indicator_code", "indicator_name",
        "indicator_definition", "source_row"]
    write_csv("series_metadata.csv", series_metadata, metadata_fields)
    result = {
        "assessment": "world_bank_icp_multicycle_export_inspection",
        "report_id": report_id,
        "observation_count_including_missing": len(observations),
        "series_metadata_definition_count": len(series_metadata),
        "source_release_count": len({item["source_release"] for item in observations}),
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
