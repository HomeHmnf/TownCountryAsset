"""Read-only ICASEES CAR national-accounts snapshot and comparability assessment.

The manifest command records the already-committed source files without copying or
modifying them. The assess command verifies those fingerprints, inventories the
workbook/PDFs, validates internal GDP arithmetic, and reports the 2019 series break.
No database or source-selection policy writes are performed.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from tools.sources.registry import ROOT, SourceError, load_registry
from tools.sources.reporting import write_source_report_bundle

SOURCE_ID = "icasees_national_accounts"
MANIFEST = ROOT / "data_manifests/sources/icasees_national_accounts/manual_publication_bundle/2026-07-16.json"
OUTPUT_ROOT = ROOT / "reports/sources/icasees-national-accounts"
EXPECTED_COMMIT = "ed62810037abdc2975a51b0677e3b3d7c6a57bdb"

FILES = [
    {"file_id": "national_accounts_dataset", "path": "raw_data/sources/icasees/national_accounts_dataset/2026-07-16/11-Comptes nationaux_16-07-2026.xlsx", "expected_byte_count": 59054, "expected_sha256": "7d6f764f1eba87c5df53ffedbbf0a90a48061098509cd67f9070501737b63dce", "provider_url": "https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/jeux-de-donnees-des-comptes-nationaux-de-2005-2019-et-2019-2021-paru-en-2026", "published_date": "2026-07-16", "format": "xlsx"},
    {"file_id": "definitive_accounts_2019_2021", "path": "raw_data/sources/icasees/national_accounts_2019_2021/2026-07-30/COMPTES-NATIONAUX-2019_2021.pdf", "expected_byte_count": 2071097, "expected_sha256": "e419508a82e9d09421405880c7a8212376d60776cc809ed942241bd231e6d173", "provider_url": "https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/comptes-nationaux-definitifs-2019-2021-de-la-republique-centrafricaine", "published_date": "2026-07-30", "format": "pdf"},
    {"file_id": "gdp_rebasing_memo_2019", "path": "raw_data/sources/icasees/gdp_rebasing_2019/2026-08-07/2026-08_Aide-memoire_Rebasage_PIB_Base2019_SCN2008_RCA.pdf", "expected_byte_count": 298873, "expected_sha256": "403bae60e88c7d8701bc0d1498228a6a49e96bc90cf2cdc4de6be8d451f29bc5", "provider_url": "https://www.icasees.org/index.php/actualites/399-icasees-publication-de-laide-memoire-sur-les-travaux-de-rebasage-du-pib-base-2019-selon-le-scn-2008", "published_date": "2026-08-07", "format": "pdf"},
]
GDP_LABEL = "PRODUIT INTERIEUR BRUT"
TOLERANCE = 1e-7


class IcaseesAssessmentError(RuntimeError):
    """ICASEES snapshot, workbook, or assessment contract failure."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_contract() -> dict[str, Any]:
    registry = load_registry()
    source = registry["sources"].get(SOURCE_ID)
    if not source:
        raise IcaseesAssessmentError(f"{SOURCE_ID} is missing from the central source registry")
    if source.get("license_status") != "CC BY 4.0":
        raise IcaseesAssessmentError("ICASEES license classification differs from the registered contract")
    return source


def build_manifest(recorded_at: datetime | None = None) -> dict[str, Any]:
    source = _source_contract()
    timestamp = recorded_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise IcaseesAssessmentError("Manifest recorded_at must be timezone-aware")
    entries = []
    for item in FILES:
        path = ROOT / item["path"]
        if not path.is_file():
            raise IcaseesAssessmentError(f"Committed ICASEES file is missing: {item['path']}")
        digest, size = _sha256(path), path.stat().st_size
        if digest != item["expected_sha256"] or size != item["expected_byte_count"]:
            raise IcaseesAssessmentError(
                f"Committed file fingerprint differs from the reviewed inventory: {item['path']}"
            )
        entries.append({**item, "byte_count": size, "sha256": digest, "repository_path": item["path"]})
    return {
        "manifest_schema_version": 1, "source_id": SOURCE_ID, "source_name": source["name"],
        "download_id": "manual_publication_bundle", "release": "2026-07-16",
        "release_kind": "edition_or_snapshot",
        "snapshot_id": "manual_2026-07-16", "snapshot_kind": "committed_manual_publication_bundle",
        "repository_commit": EXPECTED_COMMIT, "recorded_at": timestamp.astimezone(timezone.utc).isoformat(),
        "license_status": source["license_status"], "terms_url": source["terms_url"],
        "attribution": source["attribution"], "files": entries,
        "side_effects": {"raw_files_copied": False, "database_written": False,
                         "source_selection_policy_changed": False, "release_promoted": False,
                         "observations_normalized": False},
    }


def write_manifest(path: Path = MANIFEST, recorded_at: datetime | None = None) -> dict[str, Any]:
    if path.exists():
        raise IcaseesAssessmentError(f"Refusing to overwrite existing immutable manifest: {path}")
    manifest = build_manifest(recorded_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_manifest(path: Path = MANIFEST) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IcaseesAssessmentError(f"Cannot read ICASEES manifest {path}: {exc}") from exc
    if manifest.get("manifest_schema_version") != 1 or manifest.get("source_id") != SOURCE_ID:
        raise IcaseesAssessmentError("ICASEES manifest schema/source identity mismatch")
    expected = {item["file_id"]: item for item in FILES}
    actual = {item.get("file_id"): item for item in manifest.get("files", [])}
    if set(actual) != set(expected):
        raise IcaseesAssessmentError("ICASEES manifest does not contain the exact three registered source files")
    checks = []
    for file_id, definition in expected.items():
        entry = actual[file_id]
        path_on_disk = ROOT / definition["path"]
        if entry.get("path") != definition["path"] or entry.get("repository_path") != definition["path"]:
            raise IcaseesAssessmentError(f"Manifest path mismatch for {file_id}")
        if not path_on_disk.is_file():
            checks.append({"file_id": file_id, "path": definition["path"], "status": "missing"})
            continue
        digest, size = _sha256(path_on_disk), path_on_disk.stat().st_size
        ok = (digest == entry.get("sha256") == definition["expected_sha256"]
              and size == entry.get("byte_count") == definition["expected_byte_count"])
        checks.append({"file_id": file_id, "path": definition["path"], "format": definition["format"],
                       "byte_count": size, "sha256": digest, "status": "valid" if ok else "fingerprint_mismatch"})
    if any(row["status"] != "valid" for row in checks):
        raise IcaseesAssessmentError("One or more ICASEES files are missing or differ from the manifest")
    return manifest, checks


def _normal(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise IcaseesAssessmentError("Boolean encountered where a numeric observation was expected")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise IcaseesAssessmentError(f"Non-numeric workbook observation: {value!r}") from exc
    if not math.isfinite(number):
        raise IcaseesAssessmentError(f"Non-finite workbook observation: {value!r}")
    return number


def _cell_number(sheet, row: int, col: int, stack: set[str] | None = None) -> float | None:
    """Evaluate numeric cells and restricted arithmetic formulas with cell references."""
    cell = sheet.cell(row, col)
    value = cell.value
    if not (isinstance(value, str) and value.startswith("=")):
        return _number(value)
    stack = set() if stack is None else stack
    if cell.coordinate in stack:
        raise IcaseesAssessmentError(f"Circular formula at {sheet.title}!{cell.coordinate}")
    stack.add(cell.coordinate)
    try:
        reference_pattern = re.compile(r"(?<![A-Za-z0-9_])\$?([A-Z]{1,3})\$?(\d+)")
        def replace_reference(match: re.Match[str]) -> str:
            ref_cell = sheet[f"{match.group(1)}{match.group(2)}"]
            ref_value = _cell_number(sheet, ref_cell.row, ref_cell.column, stack)
            if ref_value is None:
                raise IcaseesAssessmentError(
                    f"Formula at {sheet.title}!{cell.coordinate} references empty cell {ref_cell.coordinate}"
                )
            return repr(ref_value)
        expression = reference_pattern.sub(replace_reference, value[1:])
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise IcaseesAssessmentError(
                f"Unsupported workbook formula at {sheet.title}!{cell.coordinate}: {value}"
            ) from exc
        def evaluate(node: ast.AST) -> float:
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return float(node.value)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                operand = evaluate(node.operand)
                return operand if isinstance(node.op, ast.UAdd) else -operand
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                left, right = evaluate(node.left), evaluate(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if right == 0:
                    raise IcaseesAssessmentError(f"Division by zero in formula {sheet.title}!{cell.coordinate}")
                return left / right
            raise IcaseesAssessmentError(
                f"Unsupported workbook formula at {sheet.title}!{cell.coordinate}: {value}"
            )
        result = evaluate(tree)
        if not math.isfinite(result):
            raise IcaseesAssessmentError(f"Non-finite formula result at {sheet.title}!{cell.coordinate}")
        return result
    finally:
        stack.remove(cell.coordinate)


def _find_row(sheet, label_col: int, label: str, start_row: int = 2) -> int:
    target = _normal(label)
    matches = [row for row in range(start_row, sheet.max_row + 1)
               if _normal(sheet.cell(row, label_col).value) == target]
    if len(matches) != 1:
        raise IcaseesAssessmentError(f"Expected exactly one {label!r} row in {sheet.title}; found {len(matches)}")
    return matches[0]


def _year_columns(sheet, header_row: int, start_col: int, end_col: int) -> dict[int, int]:
    return {value: col for col in range(start_col, end_col + 1)
            if isinstance((value := sheet.cell(header_row, col).value), int) and 1900 <= value <= 2100}


def _extract_gdp_rows(workbook) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    series: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}
    for sheet_name in ("Donnee", "Donnée nouvelle"):
        sheet = workbook[sheet_name]
        years = _year_columns(sheet, 1, 1, sheet.max_column)
        gdp_row = _find_row(sheet, 2, GDP_LABEL)
        vab_row = _find_row(sheet, 2, "TOTAL VAB")
        tax_row = _find_row(sheet, 2, "IMPÔTS ET TAXES SUR LES PRODUITS")
        for year, col in sorted(years.items()):
            gdp, vab, taxes = (_cell_number(sheet, row, col) for row in (gdp_row, vab_row, tax_row))
            if None in (gdp, vab, taxes):
                raise IcaseesAssessmentError(f"Missing GDP aggregate in {sheet_name}, {year}")
            series.append({"series_block": "revised", "sheet": sheet_name, "indicator": "IND35",
                           "indicator_name": GDP_LABEL, "year": year, "value": gdp,
                           "unit_label": sheet.cell(gdp_row, 3).value, "scale_label": sheet.cell(gdp_row, 4).value})
            checks[f"{sheet_name}_{year}_gdp_equals_vab_plus_taxes"] = abs(gdp - vab - taxes) <= TOLERANCE
    old = workbook["Donnee_2013-2019"]
    old_years = _year_columns(old, 1, 1, old.max_column)
    old_gdp_row = _find_row(old, 2, GDP_LABEL)
    for year, col in sorted(old_years.items()):
        if 2013 <= year <= 2019:
            series.append({"series_block": "historical", "sheet": old.title, "indicator": "IND35",
                           "indicator_name": GDP_LABEL, "year": year, "value": _cell_number(old, old_gdp_row, col),
                           "unit_label": old.cell(old_gdp_row, 3).value,
                           "scale_label": old.cell(old_gdp_row, old_years[2013] - 1).value})
    combined = workbook["Donnée_SCN2008"]
    right_label_col = max((col for col in range(1, combined.max_column + 1)
                           if _normal(combined.cell(1, col).value) == "nom des indicateurs"), default=None)
    if right_label_col is None:
        raise IcaseesAssessmentError("Donnée_SCN2008 right-hand indicator block was not found")
    # Exclude the repeated right-hand 2019-2021 headers; 2019 occurs twice.
    left_years = _year_columns(combined, 1, 4, right_label_col - 2)
    old_combined_row = _find_row(combined, 2, GDP_LABEL)
    for year, col in sorted(left_years.items()):
        if 2013 <= year <= 2019:
            series.append({"series_block": "historical", "sheet": combined.title, "indicator": "IND35",
                           "indicator_name": GDP_LABEL, "year": year,
                           "value": _cell_number(combined, old_combined_row, col),
                           "unit_label": combined.cell(old_combined_row, 3).value,
                           "scale_label": combined.cell(old_combined_row, left_years[2013] - 1).value})
    right_years = _year_columns(combined, 1, right_label_col + 3, combined.max_column)
    right_gdp_row = _find_row(combined, right_label_col, GDP_LABEL)
    right_vab_row = _find_row(combined, right_label_col, "TOTAL VAB")
    right_tax_row = _find_row(combined, right_label_col, "IMPÔTS ET TAXES SUR LES PRODUITS")
    for year, col in sorted(right_years.items()):
        if year in (2019, 2020, 2021):
            gdp, vab, taxes = (_cell_number(combined, row, col)
                               for row in (right_gdp_row, right_vab_row, right_tax_row))
            series.append({"series_block": "revised", "sheet": combined.title, "indicator": None,
                           "indicator_name": GDP_LABEL, "year": year, "value": gdp,
                           "unit_label": combined.cell(right_gdp_row, right_label_col + 1).value,
                           "scale_label": combined.cell(right_gdp_row, right_label_col + 2).value})
            checks[f"Donnée_SCN2008_{year}_gdp_equals_vab_plus_taxes"] = (
                None not in (gdp, vab, taxes) and abs(gdp - vab - taxes) <= TOLERANCE)
    revised_by_sheet = {
        name: {row["year"]: row["value"] for row in series
               if row["sheet"] == name and row["series_block"] == "revised"}
        for name in ("Donnee", "Donnée nouvelle", "Donnée_SCN2008")
    }
    for year in (2019, 2020, 2021):
        values = [revised_by_sheet[name].get(year) for name in revised_by_sheet]
        checks[f"revised_gdp_presentations_agree_{year}"] = (
            all(value is not None for value in values) and max(values) - min(values) <= TOLERANCE
        )
    for sheet_name in ("Donnee", "Donnée nouvelle"):
        sheet = workbook[sheet_name]
        years = _year_columns(sheet, 1, 1, sheet.max_column)
        primary = _find_row(sheet, 2, "SECTEUR PRIMAIRE")
        secondary = _find_row(sheet, 2, "SECTEUR SECONDAIRE")
        tertiary = _find_row(sheet, 2, "SECTEUR TERTIAIRE")
        total_vab = _find_row(sheet, 2, "TOTAL VAB")
        for year, col in sorted(years.items()):
            parts = [_cell_number(sheet, row, col) for row in (primary, secondary, tertiary)]
            total = _number(sheet.cell(total_vab, col).value)
            checks[f"{sheet_name}_{year}_sector_vab_equals_total_vab"] = (
                all(value is not None for value in parts) and total is not None
                and abs(sum(parts) - total) <= TOLERANCE
            )
    historical_by_sheet = {
        name: {row["year"]: row["value"] for row in series
               if row["sheet"] == name and row["series_block"] == "historical"}
        for name in ("Donnee_2013-2019", "Donnée_SCN2008")
    }
    for year in range(2013, 2020):
        left, combined_value = historical_by_sheet["Donnee_2013-2019"].get(year), historical_by_sheet["Donnée_SCN2008"].get(year)
        checks[f"historical_gdp_presentations_agree_{year}"] = (
            left is not None and combined_value is not None and abs(left - combined_value) <= TOLERANCE
        )
    old_2019 = _cell_number(old, old_gdp_row, old_years[2019])
    new_sheet = workbook["Donnée nouvelle"]
    new_gdp_row = _find_row(new_sheet, 2, GDP_LABEL)
    new_2019_col = next(col for col in range(1, new_sheet.max_column + 1)
                        if new_sheet.cell(1, col).value == 2019)
    new_2019 = _cell_number(new_sheet, new_gdp_row, new_2019_col)
    delta = new_2019 - old_2019
    checks["gdp_2019_overlap"] = {"historical_value": old_2019, "revised_value": new_2019,
        "absolute_difference": delta, "relative_difference_percent": delta / old_2019 * 100 if old_2019 else None}
    return series, checks


def inspect_workbook(path: Path) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=False, data_only=False)
    inventory, formula_cells = [], []
    for sheet in workbook.worksheets:
        inventory.append({"sheet": sheet.title, "rows": sheet.max_row, "columns": sheet.max_column,
                          "merged_ranges": len(sheet.merged_cells.ranges),
                          "freeze_panes": str(sheet.freeze_panes) if sheet.freeze_panes else None})
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formula_cells.append({"sheet": sheet.title, "cell": cell.coordinate, "formula": cell.value})
    series, checks = _extract_gdp_rows(workbook)
    metadata = []
    if "Metadonnées" in workbook.sheetnames:
        for row in workbook["Metadonnées"].iter_rows(min_row=1, max_col=2, values_only=True):
            if any(value is not None for value in row):
                metadata.append({"key": row[0], "value": row[1]})
    dataset_rows = []
    if "Dataset" in workbook.sheetnames:
        for row in workbook["Dataset"].iter_rows(values_only=True):
            if any(value is not None for value in row):
                dataset_rows.append({"values": list(row)})
    workbook.close()
    return {"sheet_inventory": inventory, "formula_cells": formula_cells, "metadata": metadata,
            "dataset_sheet": dataset_rows, "gdp_series": series, "validation_checks": checks}


def inspect_pdfs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return [{"status": "not_inspected", "reason": "Install pypdf with uv add pypdf to enable PDF text extraction."}]
    results = []
    terms = ("PIB", "base 2019", "SCN 2008", "rebasage", "milliards", "millions", "prix courants")
    for item in manifest["files"]:
        if item["format"] != "pdf":
            continue
        reader = PdfReader(str(ROOT / item["path"]))
        evidence = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            found = [term for term in terms if _normal(term) in _normal(text)]
            if found:
                evidence.append({"page": page_number, "terms": found,
                                 "excerpt": re.sub(r"\s+", " ", text).strip()[:1200]})
        results.append({"file_id": item["file_id"], "path": item["path"], "status": "text_extracted",
                        "page_count": len(reader.pages), "metadata": reader.metadata and
                        {str(k): str(v) for k, v in reader.metadata.items()}, "evidence_pages": evidence})
    return results


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_assessment(manifest_path: Path = MANIFEST) -> dict[str, Any]:
    manifest, integrity = verify_manifest(manifest_path)
    source = _source_contract()
    workbook_file = next(item for item in manifest["files"] if item["format"] == "xlsx")
    workbook = inspect_workbook(ROOT / workbook_file["path"])
    pdfs = inspect_pdfs(manifest)
    overlap = workbook["validation_checks"]["gdp_2019_overlap"]
    unit_labels = sorted({str(row.get("unit_label")) for row in workbook["gdp_series"]
                          if row.get("unit_label") is not None})
    boolean_checks = {key: value for key, value in workbook["validation_checks"].items()
                       if isinstance(value, bool)}
    validation_status = "pass" if all(boolean_checks.values()) else "fail"
    return {"source_id": SOURCE_ID, "snapshot_id": manifest["snapshot_id"],
        "validation_status": validation_status, "boolean_validation_checks": boolean_checks,
        "recorded_manifest": str(manifest_path.relative_to(ROOT)), "source_license": source["license_status"],
        "attribution": source["attribution"], "file_integrity": integrity, "workbook": workbook,
        "pdf_inspection": pdfs, "unit_assessment": {"observed_unit_labels": unit_labels, "status": "unresolved",
        "reason": "Workbook data rows label the GDP and value-added observations as millions de F CFA, while the Dataset sheet describes current-price gross value added in billions de FCFA. This is a scale-label conflict affecting GDP components; no conversion is authorized until the official PDF evidence resolves it."},
        "2019_overlap": overlap, "disposition": {"historical_and_revised_series_spliced": False,
        "normalized_observations_created": False, "source_selection_policy_changed": False,
        "canonical_database_written": False, "release_promoted": False}}


def write_assessment(report: dict[str, Any], output_root: Path = OUTPUT_ROOT) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workbook, checks, overlap = report["workbook"], report["workbook"]["validation_checks"], report["2019_overlap"]
    lines = ["# ICASEES Central African Republic national-accounts assessment", "",
        f"- Source snapshot: {report['snapshot_id']}", f"- Manifest: {report['recorded_manifest']}",
        f"- Files fingerprint-verified: {len(report['file_integrity'])}/3",
        f"- Workbook sheets: {len(workbook['sheet_inventory'])}", f"- Formula cells: {len(workbook['formula_cells'])}",
        f"- GDP 2019 historical: {overlap['historical_value']}", f"- GDP 2019 revised: {overlap['revised_value']}",
        f"- 2019 level difference: {overlap['relative_difference_percent']:.3f}%",
        f"- Workbook unit assessment: {report['unit_assessment']['status']}",
        f"- Structural validation: {report['validation_status'].upper()}",
        "- SQLite writes: no", "- Source-selection policy changes: no", "- Release promotion: no", "",
        "## Workbook sheet inventory", "", "| Sheet | Rows | Columns |", "|---|---:|---:|"]
    lines.extend(f"| {r['sheet']} | {r['rows']} | {r['columns']} |" for r in workbook["sheet_inventory"])
    lines.extend(["", "## GDP internal arithmetic", ""])
    for name, value in checks.items():
        if "gdp_equals_vab_plus_taxes" in name:
            lines.append(f"- {name}: {'PASS' if value else 'FAIL'}")
    lines.extend(["", "## Unit and vintage caveats", "", report["unit_assessment"]["reason"],
        "Historical and revised 2019 observations remain separate; they are not concatenated or converted.",
        "", "## PDF inspection", ""])
    for pdf in report["pdf_inspection"]:
        lines.append(f"- {pdf.get('file_id', 'PDF reader')}: {pdf['status']}; {pdf.get('page_count', 'n/a')} pages")
        for evidence in pdf.get("evidence_pages", []):
            lines.append(f"  - Page {evidence['page']}: {', '.join(evidence['terms'])}; {evidence['excerpt'][:350]}")
    lines.extend(["", "## Boundaries", "", "- Read-only assessment; not an import or approval.",
        "- Unit labels require resolution from the official PDF evidence.",
        "- Indicator codes are not used to join historical and revised sector classifications."])
    paths = write_source_report_bundle(output_root, report_id=run_id, report_type="icasees_national_accounts",
        summary_markdown="\n".join(lines),
        records=[{"source_id": SOURCE_ID, "download_id": item["file_id"], "release_id": report["snapshot_id"],
                  "status": item["status"], "sha256": item["sha256"], "detail": item["path"]}
                 for item in report["file_integrity"]],
        provenance={"source_id": SOURCE_ID, "snapshot_id": report["snapshot_id"],
            "manifest": report["recorded_manifest"], "file_integrity": report["file_integrity"],
            "workbook_inventory": workbook["sheet_inventory"], "unit_assessment": report["unit_assessment"],
            "validation_checks": checks, "pdf_inspection": report["pdf_inspection"],
            "side_effects": report["disposition"]})
    directory = Path(paths["directory"])
    _write_csv(directory / "gdp_series.csv", workbook["gdp_series"],
        ["series_block", "sheet", "indicator", "indicator_name", "year", "value", "unit_label", "scale_label"])
    _write_csv(directory / "workbook_sheets.csv", workbook["sheet_inventory"],
        ["sheet", "rows", "columns", "merged_ranges", "freeze_panes"])
    (directory / "assessment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                               encoding="utf-8")
    return directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    manifest_parser = sub.add_parser("manifest", help="record hashes for the three committed ICASEES files")
    manifest_parser.add_argument("--output", type=Path, default=MANIFEST)
    assess_parser = sub.add_parser("assess", help="verify snapshots and assess workbook/PDF contents")
    assess_parser.add_argument("--manifest", type=Path, default=MANIFEST)
    assess_parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    assess_parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            result = write_manifest(args.output)
            print(json.dumps({"manifest": str(args.output), "files": len(result["files"]),
                              "recorded_at": result["recorded_at"], "raw_files_copied": False}, indent=2))
            return 0
        report = build_assessment(args.manifest)
        directory = write_assessment(report, args.output_root)
        if not args.quiet:
            overlap = report["2019_overlap"]
            print("\n".join(["ICASEES national-accounts assessment",
                f"  Fingerprinted files: {len(report['file_integrity'])}/3",
                f"  Workbook sheets: {len(report['workbook']['sheet_inventory'])}",
                f"  GDP 2019 historical/revised: {overlap['historical_value']} / {overlap['revised_value']}",
                f"  2019 level difference: {overlap['relative_difference_percent']:.3f}%",
                f"  Unit interpretation: {report['unit_assessment']['status']}",
                f"  Structural validation: {report['validation_status']}", f"  Report: {directory}",
                "  SQLite writes: none", "  Source policy changes: none"]))
        return 0 if report["validation_status"] == "pass" else 1
    except (IcaseesAssessmentError, SourceError, OSError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
