#!/usr/bin/env python3
"""Fetch configured sources and prepare candidate country assets for the game.

This tool operates only in TownCountryAsset. It never writes to the game repo,
never approves ISO assignments, and never promotes candidate output to approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import shutil
import tempfile
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "TCA_NATURAL_EARTH_URL": "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip",
    "TCA_ISO_REFERENCE_URL": "https://raw.githubusercontent.com/stefangabos/world_countries/master/data/countries/en/world.csv",
    "TCA_PERSIAN_LABEL_SOURCE_URL": "https://query.wikidata.org/sparql",
    "TCA_FLAG_SOURCE_URL": "https://github.com/lipis/flag-icons",
    "TCA_FLAG_SOURCE_REF": "main",
    "TCA_FLAG_SOURCE_DIR": "raw_data/flags",
    "TCA_FLAG_ASSET_OUTPUT_DIR": "generated/town_country_asset_candidate/flags",
    "TCA_FLAG_MAPPING": "config/country_flag_mapping.json",
    "TCA_FLAG_REPORT": "reports/flag-asset-review.md",
    "TCA_FLAG_REFRESH_ENABLED": "true",
    "TCA_FETCHED_DATA_DIR": "raw_data/fetched",
    "TCA_ISO_DATA_DIR": "raw_data/iso",
    "TCA_PERSIAN_DATA_DIR": "raw_data/persian",
    "TCA_PERSIAN_LOCALIZATION_REPORT": "reports/persian-localization-proposals.md",
    "TCA_GAME_DATA_OUTPUT_DIR": "generated/town_country_asset_candidate",
    "TCA_APPROVED_DATA_DIR": "generated/town_country_asset",
    "TCA_REPORT_DIR": "reports/data-refresh",
    "TCA_ISO_PROPOSAL_REPORT": "reports/iso-assignment-proposals.md",
    "TCA_GENERATION_CONFIG": "config/generation.json",
    "TCA_REGIONS_CONFIG": "config/regions.json",
    "TCA_IDENTITY_REGISTRY": "config/country_identity_registry.json",
    "TCA_GENERATE_SVGS": "true",
    "TCA_COMPARE_WITH_APPROVED": "true",
    "TCA_RUN_ISO_REVIEW": "true",
    "TCA_RUN_PERSIAN_LOCALIZATION": "true",
    "TCA_HTTP_TIMEOUT_SECONDS": "60",
}
USER_AGENT = "TownCountryAsset-DataPipeline/1.0"
MANUAL_ISO_REFERENCE_CSV = Path("data/reference/iso/iso-3166-1-2026-10.csv")
MANUAL_ISO_REFERENCE_ODS = Path("data/reference/iso/iso-3166-1-2026-10.ods")
ISO_REFERENCE_FIELDS = ("name_en", "name_fr", "alpha2", "alpha3", "numeric")


def _normalize_iso_header(value: str) -> str | None:
    normalized = "".join(character for character in value.casefold() if character.isalnum())
    aliases = {
        "nameen": "name_en", "englishshortname": "name_en", "englishname": "name_en",
        "namefr": "name_fr", "frenchshortname": "name_fr", "frenchname": "name_fr",
        "alpha2": "alpha2", "alpha2code": "alpha2", "iso31661alpha2": "alpha2",
        "alpha3": "alpha3", "alpha3code": "alpha3", "iso31661alpha3": "alpha3",
        "numeric": "numeric", "numericcode": "numeric", "isonumeric": "numeric",
        "iso31661numeric": "numeric",
    }
    return aliases.get(normalized)


def _validate_iso_rows(rows: list[dict[str, str]], *, allow_missing_numeric: bool = False) -> list[dict[str, str]]:
    if not rows:
        raise ValueError("reference has no data rows")
    seen_alpha2: set[str] = set()
    for number, row in enumerate(rows, start=2):
        for field in ISO_REFERENCE_FIELDS:
            row[field] = row.get(field, "").strip()
        if not row["name_en"] or not row["alpha2"] or not row["alpha3"]:
            raise ValueError(f"row {number} has a missing required field")
        if not row["numeric"] and not allow_missing_numeric:
            raise ValueError(f"row {number} has a missing numeric code")
        row["alpha2"] = row["alpha2"].upper()
        row["alpha3"] = row["alpha3"].upper()
        if len(row["alpha2"]) != 2 or not row["alpha2"].isalpha():
            raise ValueError(f"row {number} has invalid alpha-2 code {row['alpha2']!r}")
        if len(row["alpha3"]) != 3 or not row["alpha3"].isalpha():
            raise ValueError(f"row {number} has invalid alpha-3 code {row['alpha3']!r}")
        numeric = row["numeric"]
        if numeric:
            if not numeric.isdigit() or len(numeric) > 3:
                raise ValueError(f"row {number} has invalid numeric code {numeric!r}")
            row["numeric"] = numeric.zfill(3)
        if row["alpha2"] in seen_alpha2:
            raise ValueError(f"duplicate alpha-2 code {row['alpha2']!r}")
        seen_alpha2.add(row["alpha2"])
    return rows


def read_iso_csv(path: Path) -> list[dict[str, str]]:
    """Read the primary manual ISO reference as delimited text from Calc."""
    import csv

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        if sample.lstrip().startswith("<?xml") or "<Workbook" in sample or "<ss:Worksheet" in sample:
            raise ValueError("file contains spreadsheet XML, not delimited text")
        if not sample.strip():
            raise ValueError("file is empty")
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t")
        except csv.Error as exc:
            raise ValueError("could not detect comma, semicolon, or tab field delimiter") from exc
        if dialect.delimiter not in {",", ";", "\\t"}:
            raise ValueError("unsupported field delimiter")
        stream.seek(0)
        reader = csv.reader(stream, dialect)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("file is empty") from exc
        mapped = [_normalize_iso_header(value) for value in header]
        if set(mapped) != set(ISO_REFERENCE_FIELDS) or len(mapped) != len(ISO_REFERENCE_FIELDS):
            raise ValueError("CSV header must identify name_en, name_fr, alpha2, alpha3, numeric")
        rows: list[dict[str, str]] = []
        for values in reader:
            if not values or all(not value.strip() for value in values):
                continue
            if len(values) != len(mapped):
                raise ValueError(f"row {reader.line_num} has {len(values)} fields; expected {len(mapped)}")
            rows.append({field: value for field, value in zip(mapped, values)})
    return _validate_iso_rows(rows, allow_missing_numeric=True)

def read_iso_ods(path: Path) -> list[dict[str, str]]:
    """Read the first sheet of an ODS workbook using the standard library."""
    import zipfile
    import xml.etree.ElementTree as ET

    namespaces = {
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    }
    try:
        with zipfile.ZipFile(path) as archive:
            xml_content = archive.read("content.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(f"cannot read ODS workbook: {exc}") from exc
    root = ET.fromstring(xml_content)
    sheet = root.find(".//table:table", namespaces)
    if sheet is None:
        raise ValueError("ODS workbook contains no sheet")
    table_rows: list[list[str]] = []
    for row_element in sheet.findall("table:table-row", namespaces):
        cells: list[str] = []
        for cell in list(row_element):
            if cell.tag not in {
                f"{{{namespaces['table']}}}table-cell",
                f"{{{namespaces['table']}}}covered-table-cell",
            }:
                continue
            value = "".join(part.text or "" for part in cell.findall(".//text:p", namespaces)).strip()
            if not value:
                value = cell.get(f"{{{namespaces['office']}}}value", "")
            repeat = int(cell.get(f"{{{namespaces['table']}}}number-columns-repeated", "1"))
            if repeat > 1000:
                raise ValueError("ODS contains an unreasonable repeated-column count")
            cells.extend([value] * repeat)
        repeat_rows = int(row_element.get(f"{{{namespaces['table']}}}number-rows-repeated", "1"))
        if repeat_rows > 1000:
            raise ValueError("ODS contains an unreasonable repeated-row count")
        table_rows.extend([cells] * repeat_rows)
    table_rows = [row for row in table_rows if any(value.strip() for value in row)]
    if not table_rows:
        raise ValueError("ODS sheet is empty")
    mapped = [_normalize_iso_header(value) for value in table_rows[0]]
    if set(mapped) != set(ISO_REFERENCE_FIELDS) or len(mapped) != len(ISO_REFERENCE_FIELDS):
        raise ValueError("ODS header must identify English/French names, alpha-2, alpha-3, and numeric")
    rows: list[dict[str, str]] = []
    for row_number, values in enumerate(table_rows[1:], start=2):
        values = values[:len(mapped)] + [""] * max(0, len(mapped) - len(values))
        rows.append({field: value for field, value in zip(mapped, values)})
    return _validate_iso_rows(rows, allow_missing_numeric=True)


def select_manual_iso_reference(root: Path = ROOT) -> dict[str, Any]:
    """Prefer the CSV export; fall back to the editable ODS workbook if needed."""
    csv_path = root / MANUAL_ISO_REFERENCE_CSV
    ods_path = root / MANUAL_ISO_REFERENCE_ODS
    csv_error: str | None = None
    if csv_path.is_file():
        try:
            rows = read_iso_csv(csv_path)
            incomplete_numeric = [row["name_en"] for row in rows if not row["numeric"]]
            warning_parts = []
            # Calc may export tab-delimited text depending on the selected export options.
            # Accept it for compatibility, while the .csv extension remains the preferred filename.
            with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
                sample = stream.read(8192)
            try:
                delimiter = __import__("csv").Sniffer().sniff(sample, delimiters=",;\\t").delimiter
            except __import__("csv").Error:
                delimiter = ","
            if delimiter == "\\t":
                warning_parts.append(
                    "The primary .csv reference is tab-delimited; it was parsed successfully, "
                    "but export comma-delimited CSV from Calc for format consistency."
                )
            elif delimiter == ";":
                warning_parts.append(
                    "The primary .csv reference uses semicolon delimiters; it was parsed successfully."
                )
            if incomplete_numeric:
                warning_parts.append(
                    "CSV has missing numeric codes for: " + ", ".join(incomplete_numeric[:10]) +
                    (" (and more)" if len(incomplete_numeric) > 10 else "") +
                    ". Do not compare numeric codes for those rows until corrected."
                )
            return {
                "path": csv_path, "format": "csv", "rows": rows,
                "warning": " ".join(warning_parts) or None,
            }
        except (OSError, ValueError, UnicodeError) as exc:
            csv_error = str(exc)
    else:
        csv_error = "CSV file is missing"
    if ods_path.is_file():
        try:
            rows = read_iso_ods(ods_path)
            incomplete_numeric = [row["name_en"] for row in rows if not row["numeric"]]
            warning_parts = [
                f"CSV reference is unusable ({csv_error}); using the ODS workbook as the manual reference instead."
            ]
            if incomplete_numeric:
                warning_parts.append(
                    "ODS has missing numeric codes for: " + ", ".join(incomplete_numeric[:10]) +
                    (" (and more)" if len(incomplete_numeric) > 10 else "") +
                    ". Do not compare numeric codes for those rows until corrected."
                )
            return {
                "path": ods_path,
                "format": "ods",
                "rows": rows,
                "warning": " ".join(warning_parts),
            }
        except (OSError, ValueError, UnicodeError) as exc:
            return {
                "path": None, "format": None, "rows": [],
                "warning": f"Neither manual reference is usable. CSV: {csv_error}. ODS: {exc}.",
            }
    return {
        "path": None, "format": None, "rows": [],
        "warning": f"Neither manual reference is usable. CSV: {csv_error}. ODS workbook is missing.",
    }


def manual_iso_reference_warning(root: Path = ROOT) -> str:
    """Return CLI warning/status text for the monthly manual ISO reference."""
    selected = select_manual_iso_reference(root)
    notes = [
        "Manual ISO reference reminder: review and refresh the saved reference monthly.",
        "This snapshot is a manual comparison aid, not proof of an official ISO-hosted export; it never verifies or approves registry assignments.",
    ]
    if selected["path"] is not None:
        notes.append(
            f"Selected {selected['format'].upper()} reference: {selected['path'].relative_to(root).as_posix()} "
            f"({len(selected['rows'])} validated data rows)."
        )
    if selected["warning"]:
        notes.append("WARNING: " + selected["warning"])
    return " ".join(notes)


def load_dotenv(path: Path, environ: dict[str, str] | None = None) -> dict[str, str]:
    """Load simple KEY=VALUE lines; existing environment values win."""
    result = dict(os.environ if environ is None else environ)
    if not path.exists():
        return result
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            raise ValueError(f"{path}:{number}: invalid environment variable name")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        result.setdefault(key, value)
    for key, default in DEFAULTS.items():
        result.setdefault(key, default)
    return result


def enabled(value: str, key: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{key} must be true/false, yes/no, on/off, or 1/0")


def configured_path(config: dict[str, str], key: str) -> Path:
    path = Path(config[key]).expanduser()
    return path if path.is_absolute() else ROOT / path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_archive(url: str, destination_dir: Path, timeout: float, now: datetime) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Natural Earth source URL must be an absolute HTTPS URL")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"HTTP status {status}")
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc
    if not payload:
        raise RuntimeError(f"Download returned an empty response: {url}")
    # A ZIP signature check catches HTML error pages served with HTTP 200.
    if not payload.startswith(b"PK\x03\x04"):
        raise ValueError("Natural Earth download does not look like a ZIP archive (missing ZIP signature)")
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_path = destination_dir / f"natural-earth-admin0-{stamp}.zip"
    provenance_path = destination_dir / f"natural-earth-admin0-provenance-{stamp}.json"
    if archive_path.exists() or provenance_path.exists():
        raise FileExistsError(f"Refusing to overwrite source snapshot for {stamp}")
    archive_path.write_bytes(payload)
    metadata = {
        "dataset": "Natural Earth Admin 0 Countries",
        "source_url": url,
        "retrieved_at_utc": now.astimezone(timezone.utc).isoformat(),
        "archive_path": str(archive_path.relative_to(ROOT)) if archive_path.is_relative_to(ROOT) else str(archive_path),
        "archive_sha256": sha256_bytes(payload),
        "archive_size_bytes": len(payload),
        "release_version": None,
        "release_version_note": "Not inferred from the download URL; fill only from verifiable upstream release metadata.",
    }
    provenance_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"archive": archive_path, "provenance": provenance_path, **metadata}


def create_staging_dir(output_dir: Path) -> Path:
    """Create an isolated sibling directory for a candidate build."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def publish_candidate(staging_dir: Path, output_dir: Path) -> None:
    """Replace candidate output only after all build stages and audits pass.

    The existing candidate is moved aside first and restored if publishing the
    staging directory fails. The approved snapshot is never touched.
    """
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = output_dir.with_name(f".{output_dir.name}.backup-{uuid.uuid4().hex}")
    had_output = output_dir.exists() or output_dir.is_symlink()
    if had_output:
        output_dir.rename(backup_dir)
    try:
        staging_dir.rename(output_dir)
    except OSError:
        if had_output and backup_dir.exists() and not output_dir.exists():
            backup_dir.rename(output_dir)
        raise
    if had_output:
        _remove_path(backup_dir)


def flag_report_contains_only_review_gaps(report_path: Path) -> bool:
    """Distinguish expected unreviewed mapping gaps from source/asset errors."""
    if not report_path.is_file():
        return False
    report_text = report_path.read_text(encoding="utf-8")
    issues_section = report_text.partition("## Issues")[2].partition("\n## ")[0]
    issue_lines = [line[2:] for line in issues_section.splitlines() if line.startswith("- ")]
    return bool(issue_lines) and all(
        ("expected 'reviewed'" in line or "missing flag mapping for game_id " in line)
        for line in issue_lines
    )


def run_command(label: str, command: list[str], results: list[dict[str, Any]]) -> bool:
    try:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=False
        )
        results.append({
            "stage": label,
            "status": "success" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "command": command,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        })
        return completed.returncode == 0
    except OSError as exc:
        results.append({
            "stage": label, "status": "failed", "return_code": None,
            "command": command, "stdout": "", "stderr": str(exc),
        })
        return False


def write_summary(report_dir: Path, started: datetime, stages: list[dict[str, Any]], fetched: dict[str, Any] | None,
                  output_dir: Path, overall_status: str) -> tuple[Path, Path]:
    finished = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"data-refresh-{stamp}.json"
    md_path = report_dir / f"data-refresh-{stamp}.md"
    summary = {
        "status": overall_status,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "candidate_output_dir": str(output_dir),
        "natural_earth": ({
            "source_url": fetched["source_url"],
            "archive": str(fetched["archive"]),
            "provenance": str(fetched["provenance"]),
            "sha256": fetched["archive_sha256"],
            "size_bytes": fetched["archive_size_bytes"],
        } if fetched else None),
        "stages": stages,
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Data refresh run summary", "",
        f"- **Status:** {overall_status.upper()}",
        f"- Started (UTC): {started.isoformat()}",
        f"- Finished (UTC): {finished.isoformat()}",
        f"- Duration: {summary['duration_seconds']} seconds",
        f"- Candidate output: `{output_dir}`",
        "",
        "## Source fetch",
        "",
    ]
    if fetched:
        lines += [
            f"- Source URL: {fetched['source_url']}",
            f"- Archive: `{fetched['archive']}`",
            f"- SHA-256: `{fetched['archive_sha256']}`",
            f"- Size: {fetched['archive_size_bytes']} bytes",
        ]
    else:
        lines.append("- Natural Earth source fetch did not complete.")
    lines += ["", "## Pipeline stages", ""]
    for stage in stages:
        lines.append(f"### {stage['stage']}: {stage['status'].upper()}")
        if stage.get("stdout"):
            lines += ["", "Output:", "```text", stage["stdout"], "```"]
        if stage.get("stderr"):
            lines += ["", "Errors/details:", "```text", stage["stderr"], "```"]
        lines.append("")
    lines += [
        "## Safety notes", "",
        "- Candidate outputs are not promoted to the approved snapshot.",
        "- This run does not write to TownCountryGame.",
        "- ISO candidates remain review-only; no assignment is automatically verified.",
        "- Persian localization labels remain review-only; no label is automatically approved or written to the identity registry.",
        "- Flag assignments require explicit reviewed mappings; incomplete mappings are reported and never guessed.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def execute(config: dict[str, str]) -> int:
    started = datetime.now(timezone.utc)
    report_dir = configured_path(config, "TCA_REPORT_DIR")
    output_dir = configured_path(config, "TCA_GAME_DATA_OUTPUT_DIR")
    source_dir = configured_path(config, "TCA_FETCHED_DATA_DIR")
    iso_dir = configured_path(config, "TCA_ISO_DATA_DIR")
    stages: list[dict[str, Any]] = []
    manual_iso = select_manual_iso_reference()
    manual_iso_warning = manual_iso_reference_warning()
    if manual_iso["warning"]:
        print(f"WARNING: {manual_iso_warning}", file=sys.stderr)
    else:
        print(manual_iso_warning)
    stages.append({
        "stage": "validate manual ISO reference",
        "status": "warning" if manual_iso["warning"] or not manual_iso["path"] else "success",
        "stdout": (
            f"Selected {manual_iso['format'].upper()} reference with {len(manual_iso['rows'])} validated rows."
            if manual_iso["path"] else "No valid manual ISO reference was selected."
        ),
        "stderr": manual_iso_warning if manual_iso["warning"] or not manual_iso["path"] else "",
    })
    fetched: dict[str, Any] | None = None
    staging_dir: Path | None = None
    failed = False
    timeout = float(config["TCA_HTTP_TIMEOUT_SECONDS"])
    if timeout <= 0:
        raise ValueError("TCA_HTTP_TIMEOUT_SECONDS must be positive")
    for flag in ("TCA_GENERATE_SVGS", "TCA_COMPARE_WITH_APPROVED", "TCA_RUN_ISO_REVIEW", "TCA_RUN_PERSIAN_LOCALIZATION", "TCA_FLAG_REFRESH_ENABLED"):
        enabled(config[flag], flag)
    try:
        fetched = fetch_archive(
            config["TCA_NATURAL_EARTH_URL"], source_dir, timeout, started
        )
        stages.append({
            "stage": "fetch Natural Earth archive", "status": "success",
            "stdout": f"Saved {fetched['archive']}\nSHA-256: {fetched['archive_sha256']}",
            "stderr": "",
        })
    except Exception as exc:
        failed = True
        stages.append({"stage": "fetch Natural Earth archive", "status": "failed",
                       "return_code": None, "stdout": "", "stderr": str(exc)})

    if not failed and enabled(config["TCA_RUN_ISO_REVIEW"], "TCA_RUN_ISO_REVIEW"):
        ok = run_command("refresh ISO review proposals", [
            sys.executable, "tools/refresh_iso_review.py",
            "--output-dir", str(iso_dir),
            "--report", str(configured_path(config, "TCA_ISO_PROPOSAL_REPORT")),
            "--source-url", config["TCA_ISO_REFERENCE_URL"],
        ], stages)
        failed = failed or not ok

    if not failed and fetched and enabled(config["TCA_RUN_PERSIAN_LOCALIZATION"], "TCA_RUN_PERSIAN_LOCALIZATION"):
        ok = run_command("refresh Persian localization proposals from current Wikidata labels", [
            sys.executable, "tools/refresh_persian_localization.py",
            "--source-archive", str(fetched["archive"]),
            "--registry", str(configured_path(config, "TCA_IDENTITY_REGISTRY")),
            "--output-dir", str(configured_path(config, "TCA_PERSIAN_DATA_DIR")),
            "--report", str(configured_path(config, "TCA_PERSIAN_LOCALIZATION_REPORT")),
            "--source-url", config["TCA_PERSIAN_LABEL_SOURCE_URL"],
            "--timeout", str(timeout),
        ], stages)
        failed = failed or not ok

    if not failed and fetched and enabled(config["TCA_FLAG_REFRESH_ENABLED"], "TCA_FLAG_REFRESH_ENABLED"):
        ok = run_command("refresh flag source archive and provenance", [
            sys.executable, "tools/refresh_flag_source.py",
            "--source-url", config["TCA_FLAG_SOURCE_URL"],
            "--source-ref", config["TCA_FLAG_SOURCE_REF"],
            "--output-dir", str(configured_path(config, "TCA_FLAG_SOURCE_DIR")),
            "--timeout", config["TCA_HTTP_TIMEOUT_SECONDS"],
        ], stages)
        failed = failed or not ok

    if not failed and fetched:
        try:
            staging_dir = create_staging_dir(output_dir)
            stages.append({
                "stage": "prepare isolated candidate directory", "status": "success",
                "stdout": str(staging_dir), "stderr": "",
            })
        except OSError as exc:
            failed = True
            stages.append({
                "stage": "prepare isolated candidate directory", "status": "failed",
                "return_code": None, "stdout": "", "stderr": str(exc),
            })

    if not failed and fetched and staging_dir:
        compile_command = [
            sys.executable, "tools/compile_natural_earth.py",
            "--source", str(fetched["archive"]),
            "--output", str(staging_dir),
            "--config", str(configured_path(config, "TCA_GENERATION_CONFIG")),
            "--regions", str(configured_path(config, "TCA_REGIONS_CONFIG")),
            "--identity-registry", str(configured_path(config, "TCA_IDENTITY_REGISTRY")),
        ]
        ok = run_command("compile candidate game data", compile_command, stages)
        failed = failed or not ok

    if not failed and staging_dir is not None:
        flag_report = configured_path(config, "TCA_FLAG_REPORT")
        flag_command = [
            sys.executable, "tools/generate_country_flags.py",
            "--registry", str(configured_path(config, "TCA_IDENTITY_REGISTRY")),
            "--mapping", str(configured_path(config, "TCA_FLAG_MAPPING")),
            "--source-dir", str(configured_path(config, "TCA_FLAG_SOURCE_DIR")),
            "--output-dir", str(staging_dir / "flags"),
            "--report", str(flag_report),
        ]
        ok = run_command("generate and audit country flag assets", flag_command, stages)
        if not ok and flag_report_contains_only_review_gaps(flag_report):
            stages[-1]["status"] = "review_required"
            stages[-1]["stderr"] = (
                "Flag assets were not published because mapping decisions remain unreviewed. "
                f"Review {flag_report}; candidate country data refresh may continue without flags."
            )
        else:
            failed = failed or not ok

    if not failed and enabled(config["TCA_GENERATE_SVGS"], "TCA_GENERATE_SVGS"):
        ok = run_command("generate SVG assets", [
            sys.executable, "tools/generate_country_svgs.py",
            "--data", str(staging_dir),
            "--output", str(staging_dir / "svg"),
        ], stages)
        failed = failed or not ok

    if not failed:
        ok = run_command("audit generated assets", [
            sys.executable, "tools/audit_generated_assets.py",
            "--data", str(staging_dir),
            "--source", str(fetched["archive"]),
        ], stages)
        failed = failed or not ok

    if not failed:
        ok = run_command("audit persistent identity registry", [
            sys.executable, "tools/audit_country_identity_registry.py",
            "--registry", str(configured_path(config, "TCA_IDENTITY_REGISTRY")),
            "--output", str(report_dir / "country-identity-review.md"),
        ], stages)
        failed = failed or not ok

    if not failed and enabled(config["TCA_COMPARE_WITH_APPROVED"], "TCA_COMPARE_WITH_APPROVED"):
        approved = configured_path(config, "TCA_APPROVED_DATA_DIR")
        if approved.is_dir() and (approved / "countries.json").is_file():
            ok = run_command("compare candidate with approved snapshot", [
                sys.executable, "tools/compare_asset_snapshots.py",
                "--old", str(approved), "--new", str(staging_dir),
                "--new-display-path", str(output_dir),
                "--output", str(report_dir / "asset-comparison.md"),
            ], stages)
            failed = failed or not ok
        else:
            stages.append({
                "stage": "compare candidate with approved snapshot",
                "status": "skipped",
                "stdout": f"No approved snapshot found at {approved}; no comparison performed.",
                "stderr": "",
            })

    if not failed and staging_dir is not None:
        try:
            publish_candidate(staging_dir, output_dir)
            staging_dir = None
            stages.append({
                "stage": "publish validated candidate", "status": "success",
                "stdout": f"Published validated candidate to {output_dir}", "stderr": "",
            })
        except OSError as exc:
            failed = True
            stages.append({
                "stage": "publish validated candidate", "status": "failed",
                "return_code": None, "stdout": "", "stderr": str(exc),
            })

    if staging_dir is not None:
        _remove_path(staging_dir)

    status = "failed" if failed else "success"
    try:
        md_path, json_path = write_summary(report_dir, started, stages, fetched, output_dir, status)
        print(f"Data refresh {status.upper()}.")
        print(f"Summary: {md_path}")
        print(f"Machine-readable report: {json_path}")
        for stage in stages:
            print(f"- {stage['stage']}: {stage['status']}")
    except OSError as exc:
        print(f"Could not write run summary: {exc}", file=sys.stderr)
        return 1
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env",
                        help="local KEY=VALUE configuration file (default: repository .env)")
    parser.add_argument("--help-config", action="store_true",
                        help="show configuration keys and their defaults")
    args = parser.parse_args()
    if args.help_config:
        for key, value in DEFAULTS.items():
            print(f"{key}={value}")
        return 0
    try:
        config = load_dotenv(args.env_file.expanduser())
        return execute(config)
    except (OSError, ValueError) as exc:
        started = datetime.now(timezone.utc)
        try:
            report_dir = ROOT / "reports" / "data-refresh"
            md_path, json_path = write_summary(
                report_dir, started,
                [{"stage": "load configuration", "status": "failed", "return_code": None,
                  "stdout": "", "stderr": str(exc)}],
                None, ROOT / "generated" / "town_country_asset_candidate", "failed",
            )
            print(f"Configuration failed: {exc}", file=sys.stderr)
            print(f"Failure report: {md_path}", file=sys.stderr)
            print(f"Machine-readable report: {json_path}", file=sys.stderr)
        except OSError as report_error:
            print(f"Configuration error: {exc}; also failed to write report: {report_error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())