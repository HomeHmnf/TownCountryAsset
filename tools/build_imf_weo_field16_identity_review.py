"""Build a field-16-only IMF WEO identity proposal package; never approve or write databases."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "reports/sources/imf-weo-historical-candidate/20261127T180903Z"
DEFAULT_REGISTRY = ROOT / "config/country_identity_registry.json"
DEFAULT_OUTPUT = ROOT / "reports/sources/imf-weo-field16-identity-review"
EXPECTED_REGISTRY_RECORDS = 242
EXPECTED_FIELD_ID = 16
EXPECTED_INDICATOR = "NGDPDPC"


class ReviewBuildError(RuntimeError):
    """Invalid or incomplete field-16 identity evidence."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def build_review(candidate_dir: Path, registry_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    candidate_path = candidate_dir / "candidate.json"
    exceptions_path = candidate_dir / "identity_exceptions.csv"
    observations_path = candidate_dir / "observations.csv"
    if not all(path.is_file() for path in (candidate_path, exceptions_path, observations_path, registry_path)):
        raise ReviewBuildError("Candidate metadata, exceptions, observations, and registry are all required")

    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("field_ids") != [EXPECTED_FIELD_ID] or candidate.get("observation_count") != 0:
        raise ReviewBuildError("Input must be the field-16-only zero-observation diagnostic candidate")
    if candidate.get("database_written") is not False or candidate.get("approval_created") is not False:
        raise ReviewBuildError("Candidate metadata does not prove this was a prepare-only build")
    if sha256(observations_path) != candidate.get("observations_sha256"):
        raise ReviewBuildError("Candidate observations checksum mismatch")
    if sha256(exceptions_path) != candidate.get("exceptions_sha256"):
        raise ReviewBuildError("Candidate exception checksum mismatch")

    registry_doc = json.loads(registry_path.read_text(encoding="utf-8"))
    records = registry_doc.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_REGISTRY_RECORDS:
        raise ReviewBuildError(f"Expected exactly {EXPECTED_REGISTRY_RECORDS} identity registry records")
    by_source: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ReviewBuildError("Registry contains a non-object record")
        source = record.get("source")
        source_id = source.get("current_source_id") if isinstance(source, dict) else None
        if isinstance(source_id, str) and source_id:
            by_source.setdefault(source_id, []).append(record)

    source_path = ROOT / str(candidate.get("source_path", ""))
    if not source_path.is_file() or sha256(source_path) != candidate.get("source_sha256"):
        raise ReviewBuildError("Original WEO source CSV is missing or its checksum differs from the candidate")
    source_rows = {}
    with source_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        year_columns = [name for name in reader.fieldnames or [] if name.isdigit() and len(name) == 4]
        for source_row in reader:
            if source_row.get("SERIES_CODE", "").endswith(f".{EXPECTED_INDICATOR}.A"):
                source_rows[source_row["SERIES_CODE"]] = source_row

    raw_exceptions = read_csv(exceptions_path)
    if len(raw_exceptions) != candidate.get("exception_count"):
        raise ReviewBuildError("Candidate exception row count does not match candidate metadata")
    proposal_rows: list[dict[str, Any]] = []
    unresolved_rows: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for exception in raw_exceptions:
        code = exception.get("source_country_code", "")
        series = exception.get("series_code", "")
        if not code or series != f"{code}.{EXPECTED_INDICATOR}.A":
            raise ReviewBuildError(f"Unexpected field-16 exception series: {series!r}")
        if code in seen_sources:
            raise ReviewBuildError(f"Duplicate field-16 source identity: {code}")
        seen_sources.add(code)
        matches = by_source.get(code, [])
        source_row = source_rows.get(series)
        if source_row is None:
            raise ReviewBuildError(f"Exception series is absent from the fingerprinted WEO CSV: {series}")
        populated_years = [year for year in year_columns if (source_row.get(year) or "").strip()]
        base = {
            "source_id": code,
            "source_name": (source_row.get("COUNTRY") or "").strip(),
            "series_code": series,
            "populated_year_count": len(populated_years),
            "first_populated_year": min(populated_years) if populated_years else "",
            "last_populated_year": max(populated_years) if populated_years else "",
            "candidate_line_number": exception.get("line_number", ""),
            "candidate_exception": exception.get("exception", ""),
        }
        if len(matches) != 1:
            unresolved_rows.append({
                **base,
                "reason": "no_exact_current_source_id_match" if not matches else "ambiguous_current_source_id",
                "candidate_game_ids": ";".join(sorted(str(item.get("game_id", "")) for item in matches)),
                "decision": "HOLD",
                "approved_game_id": "-",
                "owner_rationale": "",
            })
            continue
        target = matches[0]
        names = target.get("names") or {}
        proposal_rows.append({
            **base,
            "proposed_game_id": target.get("game_id", ""),
            "registry_name": names.get("en", ""),
            "registry_status": target.get("status", ""),
            "registry_entity_type": target.get("entity_type", ""),
            "proposal_basis": "exact_unique_registry_current_source_id_match_only",
            "decision": "PENDING",
            "approved_game_id": "-",
            "owner_rationale": "",
        })

    if len(proposal_rows) != 195 or len(unresolved_rows) != 2:
        raise ReviewBuildError(
            f"Expected 195 exact-match proposals and 2 unresolved cases; "
            f"found {len(proposal_rows)} and {len(unresolved_rows)}"
        )
    unresolved_codes = {row["source_id"] for row in unresolved_rows}
    if unresolved_codes != {"SSD", "WBG"}:
        raise ReviewBuildError(f"Unexpected unresolved source identities: {sorted(unresolved_codes)}")
    proposal_rows.sort(key=lambda row: row["source_id"])
    for index, row in enumerate(proposal_rows):
        row["batch"] = f"{index // 20 + 1:02d}"

    metadata = {
        "schema_version": 1,
        "field_id": EXPECTED_FIELD_ID,
        "indicator_code": EXPECTED_INDICATOR,
        "source_release": candidate.get("release"),
        "candidate_directory": str(candidate_dir.resolve().relative_to(ROOT.resolve())),
        "candidate_sha256": sha256(candidate_path),
        "candidate_exceptions_sha256": sha256(exceptions_path),
        "candidate_observations_sha256": sha256(observations_path),
        "registry_path": str(registry_path.resolve().relative_to(ROOT.resolve())),
        "registry_sha256": sha256(registry_path),
        "registry_record_count": len(records),
        "proposal_count": len(proposal_rows),
        "unresolved_count": len(unresolved_rows),
        "batch_sizes": [sum(row["batch"] == f"{n:02d}" for row in proposal_rows) for n in range(1, 11)],
        "identity_rule": "exact_unique_current_source_id_match_is_a_proposal_only_not_an_approval",
        "fixed_unresolved": {"SSD": "no exact registry current_source_id", "WBG": "field-15-only crosswalk approval; field 16 requires separate evidence and owner decision"},
        "database_written": False,
        "approval_created": False,
    }
    return proposal_rows, unresolved_rows, metadata


def write_review(proposals: list[dict[str, Any]], unresolved: list[dict[str, Any]],
                 metadata: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=False)
    for filename, rows in (("identity_proposals.csv", proposals), ("unresolved_identities.csv", unresolved)):
        with (target / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
    metadata["review_directory"] = target.relative_to(ROOT).as_posix()
    metadata["identity_proposals_sha256"] = sha256(target / "identity_proposals.csv")
    metadata["unresolved_identities_sha256"] = sha256(target / "unresolved_identities.csv")
    (target / "review_manifest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--identity-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        proposals, unresolved, metadata = build_review(args.candidate_dir, args.identity_registry)
        target = write_review(proposals, unresolved, metadata, args.output_root)
    except (OSError, ValueError, KeyError, ReviewBuildError) as exc:
        parser.error(str(exc))
    print(json.dumps({**metadata, "review_directory": str(target)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
