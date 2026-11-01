"""Build a reviewed UN WPP LocID crosswalk from the M49 review and WPP snapshots.

Only exact or normalized-name M49 reconciliations are included automatically.
Explicit name variants remain for separate review. Taiwan is a documented,
source-specific manual exception and is validated against the WPP 2026 records.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

def normalize_m49(value: str) -> str:
    """Normalize an official numeric M49 identifier without losing validation."""
    value = value.strip()
    if not value.isdigit():
        raise WPPSourceCrosswalkError(
            f"M49 reference_id must be numeric, received {value!r}"
        )
    return str(int(value))



DEFAULT_REVIEW = Path("reports/sources/crosswalk-review/un-wpp-m49-crosswalk-review.csv")
DEFAULT_DEMOGRAPHIC = Path(
    "raw_data/sources/un_wpp/demographic_indicators_medium/2024-main-demographic/"
    "WPP2024_Demographic_Indicators_Medium.csv.gz"
)
DEFAULT_AGE = Path(
    "raw_data/sources/un_wpp/population_by_age_5_group_sex_medium/2024-main-age-sex/"
    "WPP2024_PopulationByAge5GroupSex_Medium.csv.gz"
)
DEFAULT_OUTPUT = Path("data/manual/source_crosswalks/un_wpp.json")
M49_EVIDENCE_URL = "https://unstats.un.org/unsd/methodology/m49/overview"
TAIWAN_EVIDENCE_URL = "https://population.un.org/wpp/"
TAIWAN_GAME_ID = "tc_98ab3dee1d554162b6bbd5dac6374fc8"
TAIWAN_LOC_ID = "158"
TAIWAN_LOCATION = "China, Taiwan Province of China"
TAIWAN_ISO2 = "TW"
TAIWAN_ISO3 = "TWN"
TARGET_YEAR = "2026"
VARIANT = "Medium"
VAR_ID = "2"
REVIEWABLE_NAME_COMPARISONS = {"exact", "normalized_variation"}


class WPPSourceCrosswalkError(ValueError):
    """Raised when a proposed WPP crosswalk cannot be safely reviewed."""


def _location_index(
    path: Path, label: str, *, allow_repeated_loc_ids: bool = False
) -> dict[str, dict[str, str]]:
    required = {
        "LocID", "Location", "ISO2_code", "ISO3_code", "LocTypeName",
        "VarID", "Variant", "Time",
    }
    result: dict[str, dict[str, str]] = {}
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                missing = sorted(required - set(reader.fieldnames or []))
                raise WPPSourceCrosswalkError(f"{label} is missing columns: {missing}")
            for row in reader:
                if not (
                    row.get("LocTypeName") == "Country/Area"
                    and row.get("VarID") == VAR_ID
                    and row.get("Variant") == VARIANT
                    and row.get("Time") == TARGET_YEAR
                ):
                    continue
                source_id = normalize_m49(row.get("LocID", ""))
                identity = {
                    "source_name": row.get("Location", "").strip(),
                    "iso2": row.get("ISO2_code", "").strip(),
                    "iso3": row.get("ISO3_code", "").strip(),
                }
                if not identity["source_name"]:
                    raise WPPSourceCrosswalkError(
                        f"{label} LocID {source_id} has no Location name"
                    )
                existing = result.get(source_id)
                if existing is not None:
                    if existing != identity:
                        raise WPPSourceCrosswalkError(
                            f"{label} LocID {source_id} has conflicting location metadata"
                        )
                    if not allow_repeated_loc_ids:
                        raise WPPSourceCrosswalkError(
                            f"{label} contains duplicate 2026 Medium LocID {source_id}"
                        )
                result[source_id] = identity
    except (OSError, UnicodeError, csv.Error) as exc:
        raise WPPSourceCrosswalkError(f"Cannot read {label} WPP snapshot {path}: {exc}") from exc
    if not result:
        raise WPPSourceCrosswalkError(f"{label} contains no 2026 Medium Country/Area rows")
    return result


def _read_review(path: Path) -> list[dict[str, str]]:
    required = {
        "proposed_source_id", "game_id", "registry_name", "m49_reference_name",
        "m49_reference_id", "identity_match_type", "name_comparison", "review_status",
    }
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                missing = sorted(required - set(reader.fieldnames or []))
                raise WPPSourceCrosswalkError(f"Review CSV is missing columns: {missing}")
            return list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise WPPSourceCrosswalkError(f"Cannot read M49 review CSV {path}: {exc}") from exc


def build_reviewed_crosswalk(
    records: list[dict[str, str]],
    demographic_index: dict[str, dict[str, str]],
    age_index: dict[str, dict[str, str]],
    *,
    expected_country_area_count: int = 237,
) -> tuple[dict[str, Any], dict[str, int]]:
    if len(demographic_index) != expected_country_area_count:
        raise WPPSourceCrosswalkError(
            f"Expected {expected_country_area_count} demographic locations, "
            f"found {len(demographic_index)}"
        )
    if len(age_index) != expected_country_area_count:
        raise WPPSourceCrosswalkError(
            f"Expected {expected_country_area_count} age-sex locations, found {len(age_index)}"
        )
    if set(demographic_index) != set(age_index):
        raise WPPSourceCrosswalkError(
            "Demographic and age-sex snapshots have different 2026 Medium LocID coverage"
        )

    by_game: dict[str, dict[str, str]] = {}
    for row in records:
        game_id = row.get("game_id", "").strip()
        if game_id in by_game:
            raise WPPSourceCrosswalkError(f"Duplicate game_id in M49 review CSV: {game_id}")
        by_game[game_id] = row

    mappings: list[dict[str, str]] = []
    coverage_exceptions: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    used_games: set[str] = set()
    used_sources: set[str] = set()

    for row in records:
        game_id = row.get("game_id", "").strip()
        if game_id == TAIWAN_GAME_ID:
            counts["handled_by_taiwan_exception"] += 1
            continue
        status = row.get("review_status", "")
        match_type = row.get("identity_match_type", "")
        comparison = row.get("name_comparison", "")
        if status != "review_required" or match_type != "exact_name":
            counts["held_for_identity_review"] += 1
            continue
        if comparison not in REVIEWABLE_NAME_COMPARISONS:
            counts["held_for_name_review"] += 1
            continue
        raw_id = row.get("m49_reference_id", "").strip()
        proposed_id = row.get("proposed_source_id", "").strip()
        if not raw_id or normalize_m49(raw_id) != normalize_m49(proposed_id):
            raise WPPSourceCrosswalkError(
                f"{game_id}: proposed source ID does not agree with its M49 reference ID"
            )
        source_id = normalize_m49(raw_id)
        in_demographic = source_id in demographic_index
        in_age = source_id in age_index
        if in_demographic != in_age:
            raise WPPSourceCrosswalkError(
                f"{game_id}: M49 LocID {source_id} has inconsistent coverage "
                "between demographic and age-sex WPP snapshots"
            )
        if not in_demographic:
            coverage_exceptions.append({
                "game_id": game_id,
                "source_id": source_id,
                "m49_reference_name": row.get("m49_reference_name", "").strip(),
                "status": "source_not_covered",
                "reason": (
                    "The official M49 identifier is not present in either 2026 Medium "
                    "Country/Area WPP snapshot; no substitute identifier was inferred."
                ),
            })
            counts["source_not_covered"] += 1
            continue
        if source_id in used_sources or game_id in used_games:
            raise WPPSourceCrosswalkError(
                f"Duplicate source/game mapping while reviewing {game_id} -> {source_id}"
            )
        metadata = demographic_index[source_id]
        if metadata != age_index[source_id]:
            raise WPPSourceCrosswalkError(
                f"LocID {source_id} has inconsistent metadata between WPP snapshots"
            )
        mappings.append({
            "game_id": game_id,
            "source_id": source_id,
            "match_method": "reviewed_manual",
            "evidence_url": M49_EVIDENCE_URL,
            "source_name": metadata["source_name"],
            "review_note": (
                "Owner-approved M49 identifier correspondence; exact or normalized "
                "name reconciliation; LocID verified in both 2026 Medium WPP snapshots."
            ),
        })
        used_games.add(game_id)
        used_sources.add(source_id)
        counts["included_m49_verified"] += 1

    taiwan_rows = [row for row in records if row.get("game_id", "").strip() == TAIWAN_GAME_ID]
    if len(taiwan_rows) != 1:
        raise WPPSourceCrosswalkError(
            f"Expected exactly one Taiwan identity row ({TAIWAN_GAME_ID}); found {len(taiwan_rows)}"
        )
    taiwan_review = taiwan_rows[0]
    if taiwan_review.get("review_status") != "not_eligible":
        raise WPPSourceCrosswalkError("Taiwan exception expected an unmatched/not_eligible M49 row")
    taiwan_metadata = demographic_index.get(TAIWAN_LOC_ID)
    taiwan_age_metadata = age_index.get(TAIWAN_LOC_ID)
    if taiwan_metadata is None or taiwan_age_metadata is None:
        raise WPPSourceCrosswalkError("Taiwan WPP LocID 158 is absent from one or both snapshots")
    if taiwan_metadata != taiwan_age_metadata:
        raise WPPSourceCrosswalkError("Taiwan WPP metadata differs between the two snapshots")
    if (
        taiwan_metadata["source_name"] != TAIWAN_LOCATION
        or taiwan_metadata["iso2"] != TAIWAN_ISO2
        or taiwan_metadata["iso3"] != TAIWAN_ISO3
    ):
        raise WPPSourceCrosswalkError(
            "WPP LocID 158 does not match the expected Taiwan location name and ISO metadata"
        )
    if TAIWAN_LOC_ID in used_sources or TAIWAN_GAME_ID in used_games:
        raise WPPSourceCrosswalkError("Taiwan mapping conflicts with another reviewed mapping")
    mappings.append({
        "game_id": TAIWAN_GAME_ID,
        "source_id": TAIWAN_LOC_ID,
        "match_method": "reviewed_manual",
        "evidence_url": TAIWAN_EVIDENCE_URL,
        "source_name": TAIWAN_LOCATION,
        "review_note": (
            "Explicit owner-approved WPP-only exception: WPP LocID 158, "
            "Location 'China, Taiwan Province of China', ISO2 TW, ISO3 TWN. "
            "This does not assign or alter an ISO/M49 identity in the project registry."
        ),
    })
    counts["included_taiwan_manual_exception"] += 1

    payload = {
        "schema_version": 1,
        "dataset": "un_wpp",
        "source_key": "un_wpp",
        "mapping_policy": {
            "review_basis": "Owner-approved exact/normalized M49 identity matches, verified against both WPP snapshots.",
            "explicit_name_variants": "Held for separate review; not imported into this initial crosswalk.",
            "unmatched_identities": "Held unless separately approved as a source-specific exception.",
            "taiwan_exception": {
                "game_id": TAIWAN_GAME_ID,
                "source_id": TAIWAN_LOC_ID,
                "source_name": TAIWAN_LOCATION,
                "match_method": "reviewed_manual",
                "evidence_url": TAIWAN_EVIDENCE_URL,
                "scope": "WPP source crosswalk only; no ISO/M49 registry assignment.",
            },
        },
        "review_approval": {
            "status": "approved",
            "approved_on": "2026-11-01",
            "approver_role": "project_owner",
            "approval_record": "docs/data-sources/un-wpp-crosswalk-review.md",
            "scope": (
                "UN WPP source crosswalk only; no global identity, ISO/M49 assignment, "
                "or SQLite application approval."
            ),
        },
        "mappings": sorted(mappings, key=lambda item: int(item["source_id"])),
        "coverage_exceptions": sorted(
            coverage_exceptions, key=lambda item: (item["game_id"], int(item["source_id"]))
        ),
    }
    return payload, dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the owner-approved WPP crosswalk after verifying M49 IDs in both WPP snapshots."
    )
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--demographic", type=Path, default=DEFAULT_DEMOGRAPHIC)
    parser.add_argument("--age", type=Path, default=DEFAULT_AGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-country-area-count", type=int, default=237)
    args = parser.parse_args()
    try:
        records = _read_review(args.review_csv)
        demographic_index = _location_index(args.demographic, "demographic")
        age_index = _location_index(args.age, "age-sex", allow_repeated_loc_ids=True)
        payload, counts = build_reviewed_crosswalk(
            records, demographic_index, age_index,
            expected_country_area_count=args.expected_country_area_count,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(f"WPP crosswalk creation failed: {exc}")
        return 1
    print(json.dumps({
        "output": str(args.output),
        "mapping_count": len(payload["mappings"]),
        "review_status_counts": counts,
        "taiwan_included": any(
            item["game_id"] == TAIWAN_GAME_ID and item["source_id"] == TAIWAN_LOC_ID
            for item in payload["mappings"]
        ),
        "sqlite_written": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
