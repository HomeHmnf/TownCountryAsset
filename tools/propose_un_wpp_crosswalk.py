"""Build a review-only UN WPP crosswalk proposal from the shared M49 identity report.

WPP LocID is the location-specific UN M49 code. This command transfers only
uniquely reconciled M49 reference IDs to a review CSV; it does not create an
importable crosswalk or approve any identity mapping.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

DEFAULT_INPUT = Path("reports/database/town_country_asset/identity/m49-current/records.csv")
DEFAULT_OUTPUT = Path("reports/sources/crosswalk-review/un-wpp-m49-crosswalk-review.csv")


def normalize_m49(value: str) -> str:
    value = value.strip()
    if not value.isdigit():
        raise ValueError(f"M49 reference_id must be numeric, received {value!r}")
    return str(int(value))


def build_review_rows(records: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    required = {"game_id", "registry_name", "reference_name", "reference_id", "match_type"}
    if records and not required.issubset(records[0]):
        raise ValueError(f"M49 records CSV is missing columns: {sorted(required - set(records[0]))}")
    eligible = []
    for row in records:
        if row.get("match_type") not in {"exact_name", "explicit_variant"}:
            continue
        if not row.get("reference_id", "").strip():
            continue
        eligible.append(row)

    by_m49: dict[str, list[dict[str, str]]] = {}
    by_game: dict[str, list[dict[str, str]]] = {}
    for row in eligible:
        source_id = normalize_m49(row["reference_id"])
        by_m49.setdefault(source_id, []).append(row)
        by_game.setdefault(row["game_id"], []).append(row)

    output = []
    counts: Counter[str] = Counter()
    for row in records:
        match_type = row.get("match_type", "")
        reference_id = row.get("reference_id", "").strip()
        status = "not_eligible"
        source_id = ""
        if match_type in {"exact_name", "explicit_variant"} and reference_id:
            source_id = normalize_m49(reference_id)
            if len(by_m49[source_id]) > 1 or len(by_game[row["game_id"]]) > 1:
                status = "ambiguous_duplicate"
            else:
                status = "review_required"
        counts[status] += 1
        output.append({
            "proposed_source_id": source_id,
            "game_id": row.get("game_id", ""),
            "registry_name": row.get("registry_name", ""),
            "m49_reference_name": row.get("reference_name", ""),
            "m49_reference_id": reference_id,
            "identity_match_type": match_type,
            "name_comparison": row.get("name_comparison", ""),
            "variant_note": row.get("variant_note", ""),
            "alpha2_comparison": row.get("alpha2_comparison", ""),
            "alpha3_comparison": row.get("alpha3_comparison", ""),
            "review_status": status,
            "reviewer_note": "",
        })
    return output, dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a review-only WPP LocID crosswalk CSV from the M49 identity reconciliation report."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            rows, counts = build_review_rows(list(reader))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        columns = [
            "proposed_source_id", "game_id", "registry_name", "m49_reference_name",
            "m49_reference_id", "identity_match_type", "name_comparison", "variant_note",
            "alpha2_comparison", "alpha3_comparison", "review_status", "reviewer_note",
        ]
        with args.output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, csv.Error, ValueError) as exc:
        print(f"WPP crosswalk review preparation failed: {exc}")
        return 1
    print(json.dumps({
        "input": str(args.input), "output": str(args.output),
        "record_count": len(rows), "review_status_counts": counts,
        "importable_crosswalk_created": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
