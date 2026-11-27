"""Build a read-only, source-reconciled semantic status proposal for WEO field 15."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "raw_data/sources/imf_weo/october_2026/dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv"
DEFAULT_CANDIDATE = ROOT / "reports/sources/imf-weo-field15-reviewed-candidate/656073575edb005a/candidate"
DEFAULT_OUTPUT = ROOT / "reports/sources/imf-weo-field15-semantic-review"
EXPECTED_SOURCE_SHA256 = "a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d"
EXPECTED_OBSERVATIONS = 9361
EXPECTED_SERIES = 197
EXPECTED_AGGREGATE_VALUES = 665
AGGREGATE_CODES = {
    "G903", "G998", "G001", "G110", "G119", "GX123", "G163",
    "G200", "G205", "G400", "G505", "G510", "G603",
}
FISCAL_PATTERN = re.compile(r"FY([0-9]{4})/([0-9]{2})\\Z")


class SemanticReviewError(RuntimeError):
    """Invalid source, candidate, or semantic metadata."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_actual_cutoff(metadata: str) -> tuple[int, str]:
    """Return inclusive observation-year cutoff and rule identifier."""
    value = metadata.strip()
    if value == "0":
        return 0, "zero_means_all_estimated"
    if value.isdigit():
        year = int(value)
        if not 1900 <= year <= 2200:
            raise SemanticReviewError(f"Latest-actual year outside supported range: {value}")
        return year, "integer_latest_actual_year"
    match = FISCAL_PATTERN.fullmatch(value)
    if match:
        start = int(match.group(1))
        end = (start // 100) * 100 + int(match.group(2))
        if end < start:
            end += 100
        if end != start + 1:
            raise SemanticReviewError(f"Invalid fiscal-year span: {value}")
        return end, "fiscal_year_ending_year"
    raise SemanticReviewError(f"Blank or unrecognized latest-actual metadata: {value!r}")


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise SemanticReviewError(f"CSV has no header: {path}")
        return list(reader), list(reader.fieldnames)


def build_review(source_path: Path, candidate_dir: Path, *, verify_snapshot: bool = True
                 ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not source_path.is_file():
        raise SemanticReviewError(f"Missing IMF WEO source CSV: {source_path}")
    source_hash = sha256(source_path)
    if verify_snapshot and source_hash != EXPECTED_SOURCE_SHA256:
        raise SemanticReviewError("IMF WEO source checksum differs from the recorded October 2026 snapshot")

    summary_path = candidate_dir / "candidate.json"
    observations_path = candidate_dir / "observations.csv"
    if not summary_path.is_file() or not observations_path.is_file():
        raise SemanticReviewError("Field-15 candidate package is incomplete")
    candidate_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if candidate_summary.get("candidate_type") != "imf_weo_annual_historical_observations":
        raise SemanticReviewError("Unsupported candidate type")
    if candidate_summary.get("field_ids") != [15]:
        raise SemanticReviewError("Candidate must be restricted to field 15")
    if candidate_summary.get("source_sha256") != source_hash:
        raise SemanticReviewError("Candidate and raw source fingerprints differ")
    if candidate_summary.get("observations_sha256") != sha256(observations_path):
        raise SemanticReviewError("Candidate observations checksum mismatch")
    if candidate_summary.get("observation_count") != EXPECTED_OBSERVATIONS:
        raise SemanticReviewError("Candidate summary does not record 9,361 observations")

    raw_rows, raw_headers = _read_csv(source_path)
    required = {
        "SERIES_CODE", "COUNTRY", "FREQUENCY", "LATEST_ACTUAL_ANNUAL_DATA",
        "START_END_MONTHS_OF_REPORTING_YEAR",
    }
    if not required.issubset(raw_headers):
        raise SemanticReviewError(f"Raw source is missing columns: {sorted(required - set(raw_headers))}")
    year_columns = [name for name in raw_headers if name.isdigit() and len(name) == 4]
    source_series: dict[str, dict[str, Any]] = {}
    aggregate_values = 0
    aggregate_codes_seen: set[str] = set()
    for raw in raw_rows:
        parts = (raw.get("SERIES_CODE") or "").split(".")
        if len(parts) != 3 or parts[1:] != ["NGDPD", "A"]:
            continue
        if parts[0] in AGGREGATE_CODES:
            aggregate_codes_seen.add(parts[0])
            aggregate_values += sum(1 for year in year_columns if (raw.get(year) or "").strip())
            continue
        if raw.get("FREQUENCY", "").strip() != "Annual":
            raise SemanticReviewError(f"Unexpected non-annual NGDPD series: {raw.get('SERIES_CODE')}")
        code = parts[0]
        if code in source_series:
            raise SemanticReviewError(f"Duplicate source series code: {code}")
        source_series[code] = {
            "row": raw,
            "values": {
                int(year): (raw.get(year) or "").strip()
                for year in year_columns if (raw.get(year) or "").strip()
            },
        }

    if aggregate_codes_seen != AGGREGATE_CODES:
        raise SemanticReviewError("Raw aggregate series inventory differs from the 13 approved exclusions")
    if aggregate_values != EXPECTED_AGGREGATE_VALUES:
        raise SemanticReviewError(
            f"Expected {EXPECTED_AGGREGATE_VALUES} populated aggregate cells, got {aggregate_values}"
        )

    candidate_rows, candidate_headers = _read_csv(observations_path)
    required_candidate = {
        "game_id", "source_country_code", "source_country_name", "indicator_code",
        "field_id", "observation_year", "value", "value_status",
        "latest_actual_annual_data", "reporting_year_months", "source_sha256",
    }
    if not required_candidate.issubset(candidate_headers):
        raise SemanticReviewError("Candidate observations CSV has an invalid column contract")

    candidate_by_key: dict[tuple[str, int], dict[str, str]] = {}
    candidate_codes: set[str] = set()
    for row in candidate_rows:
        if row.get("indicator_code") != "NGDPD" or row.get("field_id") != "15":
            raise SemanticReviewError("Candidate contains a non-field-15 observation")
        if row.get("value_status") != "unclassified":
            raise SemanticReviewError("Candidate statuses must remain unclassified")
        if row.get("source_sha256") != source_hash:
            raise SemanticReviewError("Candidate observation source checksum mismatch")
        code = row["source_country_code"]
        year = int(row["observation_year"])
        key = (code, year)
        if key in candidate_by_key:
            raise SemanticReviewError(f"Duplicate candidate source/year key: {key}")
        candidate_by_key[key] = row
        candidate_codes.add(code)

    if len(source_series) != EXPECTED_SERIES or len(candidate_codes) != EXPECTED_SERIES:
        raise SemanticReviewError(
            f"Expected {EXPECTED_SERIES} individual series; raw={len(source_series)}, candidate={len(candidate_codes)}"
        )
    if candidate_codes != set(source_series):
        raise SemanticReviewError("Raw individual source codes and candidate source codes do not match")

    proposals: list[dict[str, Any]] = []
    series_rules: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    unresolved: list[dict[str, str]] = []
    for code, source in sorted(source_series.items()):
        raw = source["row"]
        metadata = (raw.get("LATEST_ACTUAL_ANNUAL_DATA") or "").strip()
        reporting = (raw.get("START_END_MONTHS_OF_REPORTING_YEAR") or "").strip()
        try:
            cutoff, rule = latest_actual_cutoff(metadata)
        except SemanticReviewError as exc:
            unresolved.append({"source_code": code, "metadata": metadata, "reason": str(exc)})
            continue
        series_rules[rule] += 1
        for year, raw_value in sorted(source["values"].items()):
            key = (code, year)
            candidate = candidate_by_key.get(key)
            if candidate is None:
                raise SemanticReviewError(f"Raw populated source cell missing from candidate: {code}/{year}")
            try:
                raw_number = float(raw_value)
                candidate_number = float(candidate["value"])
            except ValueError as exc:
                raise SemanticReviewError(f"Non-numeric source/candidate value: {code}/{year}") from exc
            if not math.isfinite(raw_number) or raw_number != candidate_number:
                raise SemanticReviewError(f"Raw/candidate value mismatch: {code}/{year}")
            if candidate.get("latest_actual_annual_data", "") != metadata:
                raise SemanticReviewError(f"Latest-actual metadata mismatch: {code}/{year}")
            if candidate.get("reporting_year_months", "") != reporting:
                raise SemanticReviewError(f"Reporting-period metadata mismatch: {code}/{year}")
            status = "observed" if year <= cutoff else "estimated"
            statuses[status] += 1
            proposals.append({
                "game_id": candidate["game_id"],
                "source_country_code": code,
                "source_country_name": candidate["source_country_name"],
                "indicator_code": "NGDPD",
                "field_id": 15,
                "observation_year": year,
                "value": candidate["value"],
                "current_value_status": "unclassified",
                "proposed_value_status": status,
                "latest_actual_annual_data": metadata,
                "reporting_year_months": reporting,
                "cutoff_year": cutoff,
                "classification_rule": rule,
                "source_sha256": source_hash,
            })

    if len(candidate_by_key) != len(proposals) and not unresolved:
        raise SemanticReviewError(
            f"Candidate/raw populated-cell count mismatch: candidate={len(candidate_by_key)}, proposed={len(proposals)}"
        )
    if not unresolved and len(proposals) != EXPECTED_OBSERVATIONS:
        raise SemanticReviewError(f"Expected {EXPECTED_OBSERVATIONS} proposals, got {len(proposals)}")

    report = {
        "schema_version": 1,
        "review_type": "imf_weo_field15_semantic_status_proposal",
        "source_release": "October 2026 / IMF.RES_WEO_9.0.0",
        "source_sha256": source_hash,
        "candidate_observations_sha256": sha256(observations_path),
        "candidate_directory": candidate_dir.as_posix(),
        "individual_series": len(source_series),
        "aggregate_series_excluded": len(aggregate_codes_seen),
        "aggregate_populated_values_excluded": aggregate_values,
        "candidate_observations": len(candidate_by_key),
        "proposed_observations": len(proposals),
        "proposed_status_counts": dict(sorted(statuses.items())),
        "metadata_rule_series_counts": dict(sorted(series_rules.items())),
        "unresolved_series": unresolved,
        "unresolved_series_count": len(unresolved),
        "projected_status_count": 0,
        "status_policy": (
            "latest_actual_annual_data_inclusive_cutoff; FYyyyy/yy uses ending year; "
            "zero means all estimated; no projected inference"
        ),
        "database_written": False,
        "approval_created": False,
        "complete": not unresolved and len(proposals) == EXPECTED_OBSERVATIONS,
    }
    return proposals, report


def write_review(proposals: list[dict[str, Any]], report: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=False)
    proposal_path = target / "classification_proposals.csv"
    fields = list(proposals[0]) if proposals else []
    with proposal_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(proposals)
    report["proposal_sha256"] = sha256(proposal_path)
    report["output_directory"] = target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else str(target)
    (target / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "summary.md").write_text(
        "# IMF WEO field 15 semantic status proposal\n\n"
        f"- Complete: **{report['complete']}**\n"
        f"- Individual series: {report['individual_series']}\n"
        f"- Candidate/proposed observations: {report['candidate_observations']} / {report['proposed_observations']}\n"
        f"- Observed proposals: {report['proposed_status_counts'].get('observed', 0)}\n"
        f"- Estimated proposals: {report['proposed_status_counts'].get('estimated', 0)}\n"
        f"- Unresolved series: {report['unresolved_series_count']}\n"
        f"- Projected proposals: {report['projected_status_count']}\n"
        f"- Database written: **false**\n- Approval created: **false**\n",
        encoding="utf-8",
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-snapshot-check", action="store_true")
    args = parser.parse_args(argv)
    try:
        proposals, report = build_review(
            args.source, args.candidate_dir, verify_snapshot=not args.skip_snapshot_check
        )
        target = write_review(proposals, report, args.output_root)
    except (OSError, csv.Error, json.JSONDecodeError, ValueError, SemanticReviewError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**report, "output_directory": str(target)}, indent=2, ensure_ascii=False))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
