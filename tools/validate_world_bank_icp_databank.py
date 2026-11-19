"""Validate a World Bank ICP DataBank saved-report CSV bundle.

This is source-specific semantic validation. It verifies the two CSV representations
against the selected dimensions and each other, without importing observations or
changing database/application state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_DIR = Path("data_manifests/sources/world_bank_icp/databank_exports")
REPORT_ROOT = Path("reports/sources/world-bank-icp")


class ICPDataBankValidationError(RuntimeError):
    """A saved-report export failed source-specific validation."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decode_csv(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        try:
            return raw.decode("cp1252"), "cp1252"
        except UnicodeDecodeError:
            return raw.decode("latin-1"), "latin-1"


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    text, encoding = _decode_csv(path)
    from io import StringIO
    reader = csv.DictReader(StringIO(text, newline=""), strict=True)
    if not reader.fieldnames:
        raise ICPDataBankValidationError(f"CSV has no header: {path}")
    headers = list(reader.fieldnames)
    if len(headers) != len(set(headers)):
        raise ICPDataBankValidationError(f"CSV has duplicate column names: {path}")
    return headers, list(reader), encoding


def _dimension_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    dimensions = manifest.get("dimensions")
    if not isinstance(dimensions, list):
        raise ICPDataBankValidationError("Manifest dimensions must be a list")
    result = {}
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            raise ICPDataBankValidationError("Manifest contains an invalid dimension record")
        control = dimension.get("control_id")
        if not isinstance(control, str) or not control:
            raise ICPDataBankValidationError("Manifest dimension is missing control_id")
        if control in result:
            raise ICPDataBankValidationError(f"Manifest repeats dimension {control}")
        result[control] = dimension
    required = {"Country", "Classification", "Series", "Time"}
    missing = required - result.keys()
    if missing:
        raise ICPDataBankValidationError(
            "Manifest is missing selected dimensions: " + ", ".join(sorted(missing))
        )
    return result


def _member_codes(dimension: dict[str, Any], name: str) -> set[str]:
    members = dimension.get("selected_members")
    if not isinstance(members, list) or not members:
        raise ICPDataBankValidationError(f"{name} selected_members must be a non-empty list")
    codes = set()
    for member in members:
        unique_name = member.get("unique_name") if isinstance(member, dict) else None
        match = re.search(r"&\[([^\]]+)\]$", str(unique_name or ""))
        if not match:
            raise ICPDataBankValidationError(
                f"Cannot extract a selected member code from {name}: {unique_name!r}"
            )
        codes.add(match.group(1))
    if len(codes) != len(members):
        raise ICPDataBankValidationError(f"{name} selected member codes are not unique")
    declared_count = dimension.get("selected_count")
    if declared_count is not None and declared_count != len(codes):
        raise ICPDataBankValidationError(
            f"{name} selected_count does not match selected_members"
        )
    return codes


def _indicator_code(header: str) -> str:
    match = re.match(r"^(\d+):.+\[(\d+)\]$", header.strip())
    if not match or match.group(1) != match.group(2):
        raise ICPDataBankValidationError(f"Unrecognized ICP indicator column: {header!r}")
    return match.group(1)


def _key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        (row.get("Classification Code") or "").strip(),
        (row.get("Time Code") or "").strip(),
        (row.get("Country Code") or "").strip(),
    )


def _is_blank_row(row: dict[str, str]) -> bool:
    return not any(str(value or "").strip() for value in row.values())


def _is_known_footer(row: dict[str, str]) -> bool:
    if _is_blank_row(row):
        return True
    if any((row.get(field) or "").strip() for field in
           ("Classification Code", "Time Code", "Country Code")):
        return False
    label = (row.get("Classification Name") or "").strip()
    return label.startswith("Data from database:") or label.startswith("Last Updated:")


def _observation_rows(
    rows: list[dict[str, str]], label: str, *, allow_series_dictionary: bool = False
) -> tuple[dict[tuple[str, str, str], dict[str, str]], int]:
    keyed: dict[tuple[str, str, str], dict[str, str]] = {}
    non_observation_count = 0
    for row_number, row in enumerate(rows, start=2):
        key = _key(row)
        if not all(key):
            non_observation_count += 1
            first = (row.get("Classification Name") or "").strip()
            second = (row.get("Classification Code") or "").strip()
            dictionary_row = allow_series_dictionary and (
                (first == "Code" and bool(second))
                or (first.isdigit() and bool(second))
            )
            if not _is_known_footer(row) and not dictionary_row:
                raise ICPDataBankValidationError(
                    f"{label} contains an unrecognized non-observation row at CSV row {row_number}: "
                    f"{row!r}"
                )
            continue
        if key in keyed:
            raise ICPDataBankValidationError(f"{label} has duplicate observation key {key!r}")
        keyed[key] = row
    return keyed, non_observation_count


def _verify_manifest_artifact(root: Path, artifact: dict[str, Any]) -> Path:
    relative = artifact.get("local_raw_path")
    if not isinstance(relative, str) or not relative:
        raise ICPDataBankValidationError("Manifest artifact is missing local_raw_path")
    path = (root / relative).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file():
        raise ICPDataBankValidationError(f"Manifest artifact is not a file: {relative}")
    if path.stat().st_size != artifact.get("byte_count"):
        raise ICPDataBankValidationError(f"Artifact byte count mismatch: {relative}")
    if _sha256(path).lower() != str(artifact.get("sha256", "")).lower():
        raise ICPDataBankValidationError(f"Artifact SHA-256 mismatch: {relative}")
    return path


def validate_manifest(
    *, repository_root: str | Path = ROOT,
    manifest_path: str | Path,
    validated_at: datetime | None = None,
) -> dict[str, Any]:
    """Verify artifact integrity, observation structure and CSV-to-CSV parity."""
    root = Path(repository_root).resolve()
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = root / manifest_file
    manifest_file = manifest_file.resolve(strict=True)
    manifest_file.relative_to(root)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ICPDataBankValidationError("Manifest root must be a JSON object")
    if manifest.get("source_id") != "world_bank_icp":
        raise ICPDataBankValidationError("Manifest source_id is not world_bank_icp")
    if manifest.get("export_format") != "CSV":
        raise ICPDataBankValidationError("Only CSV saved-report exports are supported")
    artifacts = manifest.get("files")
    if not isinstance(artifacts, list) or not artifacts:
        raise ICPDataBankValidationError("Manifest files must be a non-empty list")

    verified: list[tuple[dict[str, Any], Path]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ICPDataBankValidationError("Manifest contains an invalid artifact")
        verified.append((artifact, _verify_manifest_artifact(root, artifact)))

    archive_matches = [(a, p) for a, p in verified
                       if a.get("artifact_role") == "original_export_archive"]
    if len(archive_matches) != 1:
        raise ICPDataBankValidationError(
            f"Expected one original_export_archive, found {len(archive_matches)}"
        )
    archive_path = archive_matches[0][1]
    try:
        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise ICPDataBankValidationError(f"ZIP CRC failure: {bad_member}")
            archive_csv = {Path(name).name: archive.read(name)
                           for name in archive.namelist()
                           if not name.endswith("/") and name.lower().endswith(".csv")}
    except zipfile.BadZipFile as exc:
        raise ICPDataBankValidationError("Original export archive is not a valid ZIP") from exc
    if len(archive_csv) != 2:
        raise ICPDataBankValidationError(
            f"Expected exactly two CSV members in the export ZIP, found {len(archive_csv)}"
        )

    csv_artifacts = [(a, p) for a, p in verified
                     if a.get("artifact_role") == "extracted_csv_member"]
    data_matches = [(a, p) for a, p in csv_artifacts
                    if Path(str(a.get("archive_member", a.get("local_raw_path", ""))).replace("\\", "/")).name.endswith("_Data.csv")]
    metadata_matches = [(a, p) for a, p in csv_artifacts
                        if "series" in Path(str(a.get("archive_member", a.get("local_raw_path", "")))).stem.lower()
                        and "metadata" in Path(str(a.get("archive_member", a.get("local_raw_path", "")))).stem.lower()]
    if len(data_matches) != 1 or len(metadata_matches) != 1 or len(csv_artifacts) != 2:
        raise ICPDataBankValidationError(
            "Expected exactly one *_Data.csv and one Series Metadata CSV extracted member"
        )
    data_artifact, data_path = data_matches[0]
    metadata_artifact, metadata_path = metadata_matches[0]
    for artifact, path in ((data_artifact, data_path), (metadata_artifact, metadata_path)):
        archive_member = Path(str(artifact.get("archive_member", "")).replace("\\", "/")).name
        if archive_member not in archive_csv:
            raise ICPDataBankValidationError(f"Extracted member is absent from ZIP: {archive_member}")
        if archive_csv[archive_member] != path.read_bytes():
            raise ICPDataBankValidationError(f"Extracted member differs from ZIP bytes: {archive_member}")

    data_headers, data_rows, data_encoding = _read_csv(data_path)
    metadata_headers, metadata_rows, metadata_encoding = _read_csv(metadata_path)
    if data_headers != metadata_headers:
        raise ICPDataBankValidationError("Data and Series Metadata CSV headers differ")
    required_identity = {
        "Classification Name", "Classification Code", "Time", "Time Code",
        "Country Name", "Country Code",
    }
    if not required_identity.issubset(data_headers):
        raise ICPDataBankValidationError("CSV is missing required ICP dimension columns")

    dimensions = _dimension_map(manifest)
    selected = {name: _member_codes(dimensions[name], name)
                for name in ("Country", "Classification", "Series", "Time")}
    indicator_headers = [header for header in data_headers if "[" in header and header.endswith("]")]
    indicator_codes = [_indicator_code(header) for header in indicator_headers]
    if len(indicator_codes) != len(set(indicator_codes)):
        raise ICPDataBankValidationError("CSV repeats an indicator code")
    if set(indicator_codes) != selected["Series"]:
        raise ICPDataBankValidationError(
            "CSV indicator columns do not exactly match selected Series members"
        )

    data_keyed, data_extras = _observation_rows(data_rows, "Data CSV")
    metadata_keyed, metadata_extras = _observation_rows(
        metadata_rows, "Series Metadata CSV", allow_series_dictionary=True
    )
    if not data_keyed:
        raise ICPDataBankValidationError("Data CSV contains no observations")
    if data_keyed.keys() != metadata_keyed.keys():
        raise ICPDataBankValidationError(
            f"Data/metadata observation keys differ: "
            f"{len(data_keyed.keys() - metadata_keyed.keys())} metadata-only and "
            f"{len(metadata_keyed.keys() - data_keyed.keys())} data-only"
        )

    expected_count = (len(selected["Country"]) * len(selected["Classification"])
                      * len(selected["Time"]))
    if len(data_keyed) != expected_count:
        raise ICPDataBankValidationError(
            f"Expected {expected_count} observations from selected dimensions; "
            f"found {len(data_keyed)}"
        )
    actual_country = {key[2] for key in data_keyed}
    actual_classification = {key[0] for key in data_keyed}
    actual_time = {key[1] for key in data_keyed}
    for name, actual in (
        ("Country", actual_country), ("Classification", actual_classification),
        ("Time", actual_time),
    ):
        if actual != selected[name]:
            raise ICPDataBankValidationError(
                f"Observed {name} members do not match manifest selection "
                f"(missing={sorted(selected[name] - actual)}, "
                f"unexpected={sorted(actual - selected[name])})"
            )

    missing_counts = {code: 0 for code in indicator_codes}
    identity_fields = sorted(required_identity)
    for key, row in data_keyed.items():
        metadata_row = metadata_keyed[key]
        for field in ("Classification Name", "Time", "Country Name"):
            if not (row.get(field) or "").strip():
                raise ICPDataBankValidationError(
                    f"Observation {key!r} has an empty dimension label in {field!r}"
                )
        time_match = re.fullmatch(r"YR(\\d{4})", key[1])
        if not time_match or (row.get("Time") or "").strip() != time_match.group(1):
            raise ICPDataBankValidationError(
                f"Time label/code mismatch for observation {key!r}"
            )
        for field in identity_fields:
            if (row.get(field) or "") != (metadata_row.get(field) or ""):
                raise ICPDataBankValidationError(
                    f"Data/metadata identity mismatch for {key!r}, field {field!r}"
                )
        for header, code in zip(indicator_headers, indicator_codes):
            value = (row.get(header) or "").strip()
            if value == manifest.get("missing_value_token", ".."):
                missing_counts[code] += 1
            else:
                try:
                    number = float(value)
                except ValueError as exc:
                    raise ICPDataBankValidationError(
                        f"Non-numeric value {value!r} for {code} at {key!r}"
                    ) from exc
                if not math.isfinite(number):
                    raise ICPDataBankValidationError(
                        f"Non-finite value for {code} at {key!r}"
                    )
            if (row.get(header) or "") != (metadata_row.get(header) or ""):
                raise ICPDataBankValidationError(
                    f"Data/metadata value mismatch for {key!r}, indicator {code}"
                )

    metadata_codes = set()
    metadata_dictionary_rows = 0
    for row in metadata_rows:
        if all(_key(row)):
            continue
        code = (row.get("Classification Name") or "").strip()
        if code.isdigit():
            metadata_codes.add(code)
            metadata_dictionary_rows += 1
    if metadata_codes != selected["Series"]:
        raise ICPDataBankValidationError(
            "Series Metadata CSV trailing code dictionary does not match selected Series "
            f"(missing={sorted(selected['Series'] - metadata_codes)}, "
            f"unexpected={sorted(metadata_codes - selected['Series'])})"
        )

    stamp = validated_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("validated_at must be timezone-aware")
    export_id = str(manifest.get("export_id") or manifest_file.stem)
    validation_id = "databank_validation_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report_dir = root / REPORT_ROOT / validation_id
    report_dir.mkdir(parents=True, exist_ok=False)
    result = {
        "assessment": "world_bank_icp_databank_saved_report_semantic_validation",
        "validation_id": validation_id,
        "export_id": export_id,
        "manifest_path": manifest_file.relative_to(root).as_posix(),
        "status": "passed",
        "data_csv": data_artifact["local_raw_path"],
        "series_metadata_csv": metadata_artifact["local_raw_path"],
        "csv_encodings": {"data": data_encoding, "series_metadata": metadata_encoding},
        "selected_dimension_counts": {name: len(codes) for name, codes in selected.items()},
        "observation_count": len(data_keyed),
        "expected_observation_count": expected_count,
        "duplicate_observation_keys": 0,
        "data_csv_non_observation_rows": data_extras,
        "series_metadata_non_observation_rows": metadata_extras,
        "series_metadata_dictionary_row_count": metadata_dictionary_rows,
        "indicator_codes": indicator_codes,
        "missing_value_token": manifest.get("missing_value_token", ".."),
        "missing_value_counts_by_indicator": missing_counts,
        "data_metadata_key_parity": True,
        "data_metadata_identity_and_value_parity": True,
        "archive_and_extracted_artifact_integrity": True,
        "validation_report_path": (report_dir / "validation.json").relative_to(root).as_posix(),
        "side_effects": {
            "raw_data_written": False, "project_database_written": False,
            "game_database_written": False, "approval_created": False,
            "source_selection_changed": False, "canonical_data_promoted": False,
        },
    }
    with (report_dir / "validation.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_manifest(repository_root=args.root, manifest_path=args.manifest)
    except (ICPDataBankValidationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
