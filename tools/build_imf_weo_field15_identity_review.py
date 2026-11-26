#!/usr/bin/env python3
"""Compile the manually reviewed IMF WEO field-15 identity proposals in one pass.

This tool does not infer identities, retrieve or interpret provider evidence, approve
mappings, modify the canonical registry, edit crosswalks, or write either database.
The Batch 10 cumulative register is the human-reviewed proposal input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/sources/imf-weo-field15-identity-review/20261126"
DEFAULTS = {
    "inventory": ROOT / "temp/imf-weo-field15-identity-inventory.csv",
    "baseline": BASE / "field_15_identity_review_register.csv",
    "seed": BASE / "field_15_identity_review_register_batch10.csv",
    "exclusions": ROOT / "reports/sources/imf-weo-historical-candidate/20261125T152006Z/field_15_exclusion_register.csv",
    "registry": ROOT / "config/country_identity_registry.json",
    "crosswalk": ROOT / "data/manual/source_crosswalks/imf_weo.json",
    "output": BASE / "field_15_identity_review_register_final.csv",
}
IMF_REF = "https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf"
M49_REF = "https://unstats.un.org/unsd/methodology/m49/"
REVIEW_FIELDS = (
    "independent_evidence_reference",
    "review_outcome",
    "approved_game_id",
    "owner_decision",
    "review_notes",
    "reviewed_proposed_game_id",
    "proposed_registry_name",
    "un_m49_code",
)
IMMUTABLE_FIELDS = (
    "field_id", "indicator_code", "source_id", "source_name", "series_code",
    "populated_year_count", "first_populated_year", "last_populated_year",
    "triage_name_candidate_game_id", "triage_registry_name",
    "triage_registry_status", "triage_entity_type",
    "triage_iso_assignment_status", "exact_normalized_name_match",
)


class ReviewBuildError(ValueError):
    """Invalid review inputs or proposal governance state."""


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ReviewBuildError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReviewBuildError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compile_review_register(
    inventory_path: Path = DEFAULTS["inventory"],
    baseline_path: Path = DEFAULTS["baseline"],
    seed_path: Path = DEFAULTS["seed"],
    exclusions_path: Path = DEFAULTS["exclusions"],
    registry_path: Path = DEFAULTS["registry"],
    crosswalk_path: Path = DEFAULTS["crosswalk"],
) -> tuple[list[str], list[dict[str, str]], dict[str, Any]]:
    inventory_fields, inventory = _read_csv(inventory_path)
    exclusion_fields, exclusions = _read_csv(exclusions_path)
    baseline_fields, baseline = _read_csv(baseline_path)
    seed_fields, seed = _read_csv(seed_path)
    registry = _read_json(registry_path)
    crosswalk = _read_json(crosswalk_path)

    for label, fields, required in (
        ("inventory", inventory_fields, {"source_id", "source_name", "series_code"}),
        ("exclusions", exclusion_fields, {"source_country_code", "disposition", "populated_year_count", "field_id", "indicator_code"}),
        ("baseline", baseline_fields, set(IMMUTABLE_FIELDS)),
        ("seed", seed_fields, set(IMMUTABLE_FIELDS) | set(REVIEW_FIELDS)),
    ):
        missing = required - set(fields)
        if missing:
            raise ReviewBuildError(f"{label} is missing columns: {sorted(missing)}")

    inventory_by_code = {row["source_id"]: row for row in inventory}
    if len(inventory_by_code) != 210 or len(inventory) != 210:
        raise ReviewBuildError("Expected 210 unique IMF NGDPD source identities in the inventory")

    aggregate_codes = {row["source_country_code"] for row in exclusions}
    if len(exclusions) != 13 or len(aggregate_codes) != 13:
        raise ReviewBuildError("Expected 13 unique aggregate exclusion records")
    if any(row["disposition"] != "excluded" or row["field_id"] != "15" or row["indicator_code"] != "NGDPD" for row in exclusions):
        raise ReviewBuildError("Aggregate exclusion register contains an invalid disposition or scope")
    if sum(int(row["populated_year_count"]) for row in exclusions) != 665:
        raise ReviewBuildError("Aggregate exclusion register no longer accounts for 665 populated values")

    approval = crosswalk.get("review_approval", {})
    mappings = crosswalk.get("mappings", [])
    wbg = [row for row in mappings if row.get("source_id") == "WBG"]
    if approval.get("status") != "approved" or len(wbg) != 1:
        raise ReviewBuildError("Expected the separately owner-approved WBG crosswalk mapping")
    if wbg[0].get("game_id") != "tc_50c420df8b2c4c6eaae47d795f9a1ea2":
        raise ReviewBuildError("WBG crosswalk target differs from the recorded owner approval")
    if "Field 15" not in approval.get("scope", ""):
        raise ReviewBuildError("WBG approval scope is not explicitly field 15")

    expected_codes = set(inventory_by_code) - aggregate_codes - {"WBG"}
    baseline_by_code = {row["source_id"]: row for row in baseline}
    seed_by_code = {row["source_id"]: row for row in seed}
    if len(baseline) != 196 or len(baseline_by_code) != 196 or set(baseline_by_code) != expected_codes:
        raise ReviewBuildError("Baseline must contain exactly the 196 non-aggregate, non-WBG identities")
    if len(seed) != 196 or len(seed_by_code) != 196 or set(seed_by_code) != expected_codes:
        raise ReviewBuildError("Reviewed seed must contain the same 196 source identities as the baseline")

    records = registry.get("records")
    if not isinstance(records, list):
        raise ReviewBuildError("Canonical registry records must be an array")
    registry_by_id = {row.get("game_id"): row for row in records if isinstance(row, dict)}
    if len(registry_by_id) != len(records):
        raise ReviewBuildError("Canonical registry game_id values are missing or duplicated")

    output_fields = list(baseline_fields)
    for field in ("reviewed_proposed_game_id", "proposed_registry_name", "un_m49_code"):
        if field not in output_fields:
            output_fields.append(field)

    output: list[dict[str, str]] = []
    proposed_ids: set[str] = set()
    proposal_count = 0
    hold_codes: list[str] = []

    for source_code in [row["source_id"] for row in baseline]:
        original = baseline_by_code[source_code]
        reviewed = seed_by_code[source_code]
        for field in IMMUTABLE_FIELDS:
            if original.get(field, "") != reviewed.get(field, ""):
                raise ReviewBuildError(f"Seed changed immutable baseline field {field} for {source_code}")
        row = dict(original)
        for field in REVIEW_FIELDS:
            row[field] = reviewed.get(field, "")

        evidence = row["independent_evidence_reference"].split(";")
        if IMF_REF not in evidence or M49_REF not in evidence:
            raise ReviewBuildError(f"{source_code} lacks both official evidence references")

        proposed_id = row["reviewed_proposed_game_id"]
        if row["review_outcome"] == "proposed_manual_review":
            proposal_count += 1
            if not proposed_id or not row["proposed_registry_name"]:
                raise ReviewBuildError(f"{source_code} has an incomplete proposal")
            if proposed_id in proposed_ids:
                raise ReviewBuildError(f"Duplicate proposed game_id: {proposed_id}")
            proposed_ids.add(proposed_id)
            target = registry_by_id.get(proposed_id)
            if target is None:
                raise ReviewBuildError(f"{source_code} targets unknown game_id {proposed_id}")
            canonical_name = target.get("names", {}).get("en")
            if canonical_name != row["proposed_registry_name"]:
                raise ReviewBuildError(f"{source_code} proposed name does not match canonical registry")
            if len(row["un_m49_code"]) != 3 or not row["un_m49_code"].isascii() or not row["un_m49_code"].isdigit():
                raise ReviewBuildError(f"{source_code} has an invalid M49 numeric code")
            if row["owner_decision"] != "pending_explicit_owner_approval" or row["approved_game_id"]:
                raise ReviewBuildError(f"{source_code} is not pending explicit owner approval")
        elif row["review_outcome"] == "hold_for_evidence":
            hold_codes.append(source_code)
            if proposed_id or row["proposed_registry_name"] or row["un_m49_code"] or row["approved_game_id"]:
                raise ReviewBuildError(f"Held identity {source_code} must not have a mapping")
        else:
            raise ReviewBuildError(f"Unsupported review outcome for {source_code}: {row['review_outcome']}")

        output.append(row)

    if proposal_count != 195 or len(proposed_ids) != 195:
        raise ReviewBuildError("Expected 195 unique proposal-only mappings")
    if hold_codes != ["KOS"]:
        raise ReviewBuildError(f"Expected only KOS to remain held; found {hold_codes}")

    summary = {
        "status": "passed",
        "rows": len(output),
        "unique_source_ids": len({row["source_id"] for row in output}),
        "proposal_count": proposal_count,
        "unique_proposed_game_ids": len(proposed_ids),
        "held_source_ids": hold_codes,
        "approved_game_ids": sum(bool(row["approved_game_id"]) for row in output),
        "unproposed_source_ids": [],
        "database_written": False,
        "approval_created": False,
        "registry_modified": False,
        "crosswalk_modified": False,
        "evidence_policy": "official IMF and UN M49 references are carried from the manually reviewed seed; no identity inference or live evidence retrieval is performed",
    }
    return output_fields, output, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inventory", "baseline", "seed", "exclusions", "registry", "crosswalk", "output"):
        parser.add_argument(f"--{name}", type=Path, default=DEFAULTS[name])
    parser.add_argument("--force", action="store_true", help="Allow replacing the output and its verification report")
    args = parser.parse_args(argv)
    report_path = args.output.with_suffix(".verification.json")
    if not args.force and (args.output.exists() or report_path.exists()):
        parser.error("Output already exists; choose another path or pass --force")
    try:
        fields, rows, summary = compile_review_register(
            args.inventory, args.baseline, args.seed, args.exclusions, args.registry, args.crosswalk
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x" if not args.force else "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        summary.update({
            "output_path": str(args.output),
            "output_sha256": _sha256(args.output),
            "input_seed_sha256": _sha256(args.seed),
            "registry_sha256": _sha256(args.registry),
            "crosswalk_sha256": _sha256(args.crosswalk),
        })
        report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, csv.Error, ReviewBuildError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
