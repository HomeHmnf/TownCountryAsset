"""Build a source-faithful annual IMF WEO candidate; no database writes or status inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_data/sources/imf_weo/october_2026/dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv"
IDENTITY = ROOT / "config/country_identity_registry.json"
DEFAULT_CROSSWALK = ROOT / "data/manual/source_crosswalks/imf_weo.json"
OUTPUT = ROOT / "reports/sources/imf-weo-historical-candidate"
EXPECTED_SHA256 = "a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d"
EXPECTED_BYTES = 26692032
INDICATORS = {
    "NGDPD": 15, "NGDPDPC": 16, "PPPGDP": 18, "PCPIPCH": 20, "LUR": 21,
}


class CandidateError(RuntimeError):
    """Invalid source or identity evidence."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity_index(path: Path) -> dict[str, set[str]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateError(f"Cannot read identity registry: {exc}") from exc
    result: dict[str, set[str]] = {}
    for record in document.get("records", []):
        game_id = record.get("game_id")
        source = record.get("source") or {}
        iso = record.get("iso") or {}
        codes = {source.get("current_source_id"), iso.get("alpha3")}
        for code in codes:
            if isinstance(code, str) and code and isinstance(game_id, str) and game_id:
                result.setdefault(code, set()).add(game_id)
    return result


def build_candidate(raw_path: Path = RAW, identity_path: Path = IDENTITY,
                    *, verify_snapshot: bool = True, crosswalk_path: Path | None = None,
                    field_ids: set[int] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not raw_path.is_file():
        raise CandidateError(f"Missing IMF WEO CSV: {raw_path}")
    raw_hash = sha256(raw_path)
    byte_count = raw_path.stat().st_size
    if verify_snapshot and (raw_hash != EXPECTED_SHA256 or byte_count != EXPECTED_BYTES):
        raise CandidateError("IMF WEO bytes differ from the recorded October 2026 snapshot")
    identities = identity_index(identity_path)
    crosswalk_hash = None
    if crosswalk_path is not None:
        try:
            identity_document = json.loads(identity_path.read_text(encoding="utf-8"))
            known_game_ids = {
                record.get("game_id") for record in identity_document.get("records", [])
                if isinstance(record, dict) and isinstance(record.get("game_id"), str)
            }
            crosswalk = load_crosswalk(
                crosswalk_path, expected_dataset="world_economic_outlook",
                known_game_ids=known_game_ids,
            )
        except (OSError, json.JSONDecodeError, CrosswalkError) as exc:
            raise CandidateError(f"Invalid IMF WEO source crosswalk: {exc}") from exc
        if crosswalk.source_key != "imf_weo":
            raise CandidateError("IMF WEO source crosswalk source_key must be 'imf_weo'")
        for mapping in crosswalk.mappings:
            existing = identities.get(mapping.source_id, set())
            if existing and existing != {mapping.game_id}:
                raise CandidateError(
                    f"IMF WEO crosswalk conflicts with identity registry for {mapping.source_id}"
                )
            identities[mapping.source_id] = {mapping.game_id}
        crosswalk_hash = sha256(crosswalk_path)
    if field_ids is not None:
        unsupported_fields = sorted(field_ids - set(INDICATORS.values()))
        if unsupported_fields:
            raise CandidateError(f"Unsupported WP1.5 field IDs: {unsupported_fields}")
    selected_indicators = {
        code: field_id for code, field_id in INDICATORS.items()
        if field_ids is None or field_id in field_ids
    }
    if field_ids is not None and not selected_indicators:
        raise CandidateError(f"No supported IMF WEO indicators selected for fields {sorted(field_ids)}")
    observations: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    seen_series: set[str] = set()
    series_count: Counter[str] = Counter()
    years: set[int] = set()

    try:
        with raw_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"SERIES_CODE", "COUNTRY", "FREQUENCY", "UNIT", "SCALE",
                        "LATEST_ACTUAL_ANNUAL_DATA", "START_END_MONTHS_OF_REPORTING_YEAR"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CandidateError(f"WEO CSV missing columns: {sorted(missing)}")
            year_columns = [name for name in reader.fieldnames or [] if name.isdigit() and len(name) == 4]
            if not year_columns:
                raise CandidateError("WEO CSV has no annual year columns")
            for line_number, row in enumerate(reader, start=2):
                parts = (row.get("SERIES_CODE") or "").split(".")
                if len(parts) != 3 or parts[1] not in selected_indicators:
                    continue
                if parts[2] != "A" or row.get("FREQUENCY", "").strip() != "Annual":
                    exceptions.append({"line_number": line_number, "series_code": row.get("SERIES_CODE", ""),
                                       "exception": "non_annual_frequency_or_series"})
                    continue
                series_code = row["SERIES_CODE"]
                if series_code in seen_series:
                    raise CandidateError(f"Duplicate WEO series code: {series_code}")
                seen_series.add(series_code)
                source_code = parts[0]
                matches = identities.get(source_code, set())
                if len(matches) != 1:
                    exceptions.append({
                        "line_number": line_number, "series_code": series_code,
                        "source_country_code": source_code,
                        "exception": "unmapped_or_ambiguous_identity" if not matches or len(matches) > 1 else "invalid_identity",
                        "candidate_game_ids": ";".join(sorted(matches)),
                    })
                    continue
                game_id = next(iter(matches))
                field_id = selected_indicators[parts[1]]
                series_count[parts[1]] += 1
                for year_text in year_columns:
                    raw_value = (row.get(year_text) or "").strip()
                    if not raw_value:
                        continue
                    try:
                        value = float(raw_value)
                    except ValueError:
                        exceptions.append({"line_number": line_number, "series_code": series_code,
                                           "year": year_text, "exception": "non_numeric_value",
                                           "raw_value": raw_value})
                        continue
                    if not math.isfinite(value):
                        exceptions.append({"line_number": line_number, "series_code": series_code,
                                           "year": year_text, "exception": "non_finite_value",
                                           "raw_value": raw_value})
                        continue
                    year = int(year_text)
                    years.add(year)
                    observations.append({
                        "game_id": game_id,
                        "source_country_code": source_code,
                        "source_country_name": row.get("COUNTRY", "").strip(),
                        "indicator_code": parts[1],
                        "field_id": field_id,
                        "observation_year": year,
                        "value": value,
                        "unit": (row.get("UNIT") or "").strip() or None,
                        "scale": (row.get("SCALE") or "").strip() or None,
                        "value_status": "unclassified",
                        "latest_actual_annual_data": (row.get("LATEST_ACTUAL_ANNUAL_DATA") or "").strip() or None,
                        "reporting_year_months": (row.get("START_END_MONTHS_OF_REPORTING_YEAR") or "").strip() or None,
                        "source_reference": "https://data.imf.org/datasets/WEO",
                        "source_version": "October 2026 / IMF.RES_WEO_9.0.0",
                        "source_sha256": raw_hash,
                        "acquired_on": "2026-11-02",
                        "acquisition_time_precision": "day",
                    })
    except (OSError, csv.Error) as exc:
        raise CandidateError(f"Cannot parse IMF WEO CSV: {exc}") from exc

    keys = [(r["game_id"], r["indicator_code"], r["observation_year"]) for r in observations]
    if len(keys) != len(set(keys)):
        raise CandidateError("Multiple WEO source rows map to the same game/indicator/year")
    def display_path(path: Path) -> str:
        try:
            return path.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            return path.name

    summary = {
        "schema_version": 1,
        "candidate_type": "imf_weo_annual_historical_observations",
        "source_key": "imf_weo",
        "release": "october_2026",
        "source_path": display_path(raw_path),
        "source_sha256": raw_hash,
        "source_byte_count": byte_count,
        "identity_registry_path": display_path(identity_path),
        "crosswalk_path": display_path(crosswalk_path) if crosswalk_path is not None else None,
        "crosswalk_sha256": crosswalk_hash,
        "field_ids": sorted(field_ids) if field_ids is not None else sorted(set(INDICATORS.values())),
        "observation_count": len(observations),
        "distinct_game_ids": len({r["game_id"] for r in observations}),
        "indicator_counts": dict(sorted(Counter(r["indicator_code"] for r in observations).items())),
        "year_range": [min(years), max(years)] if years else None,
        "exception_count": len(exceptions),
        "status_policy": "unclassified_for_all_rows; latest_actual_annual_data_is_retained_as_source_metadata_only",
        "identity_policy": "retain_existing_game_id; ISO verification status is not changed",
        "completeness_policy": "only finite numeric IMF source cells become observations; blank cells are not synthesized",
        "comparison_policy": "WDI values and comparability gates do not determine WEO observation eligibility",
        "database_written": False,
        "approval_created": False,
    }
    return observations, exceptions, summary


def write_candidate(observations: list[dict[str, Any]], exceptions: list[dict[str, Any]],
                    summary: dict[str, Any], output_root: Path) -> Path:
    import datetime
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=False)
    for name, rows in (("observations.csv", observations), ("identity_exceptions.csv", exceptions)):
        fields = list(rows[0]) if rows else []
        with (target / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    summary["candidate_directory"] = target.relative_to(ROOT).as_posix()
    summary["observations_sha256"] = sha256(target / "observations.csv")
    summary["exceptions_sha256"] = sha256(target / "identity_exceptions.csv")
    (target / "candidate.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=RAW)
    parser.add_argument("--identity-registry", type=Path, default=IDENTITY)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--field-id", type=int, action="append", help="Restrict candidate to one or more WP1.5 field IDs")
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    parser.add_argument("--skip-snapshot-check", action="store_true")
    args = parser.parse_args(argv)
    try:
        observations, exceptions, summary = build_candidate(
            args.csv, args.identity_registry, verify_snapshot=not args.skip_snapshot_check,
            crosswalk_path=args.crosswalk,
            field_ids=set(args.field_id) if args.field_id else None,
        )
        target = write_candidate(observations, exceptions, summary, args.output_root)
    except (CandidateError, OSError, csv.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**summary, "candidate_directory": str(target)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
