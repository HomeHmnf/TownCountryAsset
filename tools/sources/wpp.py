"""UN World Population Prospects 2024 adapter for WP1.5 candidate preparation.

This module reads immutable source-manager snapshots. It never writes to SQLite,
promotes a release, or infers identity from country names or ISO codes.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from tools.database.source_crosswalk import CrosswalkError, load_crosswalk
from tools.database.connection import REPOSITORY_ROOT

YEAR = 2026
EXPECTED_COUNTRY_AREA_COUNT = 237
VARIANT = "Medium"
VAR_ID = "2"
TOGO_LOC_ID = "768"
AGE_GROUPS = tuple(
    [f"{start}-{start + 4}" for start in range(0, 100, 5)] + ["100+"]
)
MAIN_DEMOGRAPHIC_RELEASE = "2024-main-demographic"
AGE_RELEASE = "2024-main-age-sex"
TOGO_RELEASE = "2026-01-19-togo-update"
SOURCE_KEY = "un_wpp"
TAIWAN_GAME_ID = "tc_98ab3dee1d554162b6bbd5dac6374fc8"
TAIWAN_LOC_ID = "158"
TAIWAN_LOCATION = "China, Taiwan Province of China"


class WPPAdapterError(RuntimeError):
    """Raised when a WPP snapshot fails the WP1.5 source contract."""


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WPPAdapterError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WPPAdapterError(f"{path} must contain a JSON object")
    return value


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot(path: Path, manifest_path: Path, *, expected_download: str) -> dict[str, Any]:
    manifest = _json(manifest_path)
    if manifest.get("manifest_schema_version") != 1:
        raise WPPAdapterError(f"Unsupported acquisition manifest: {manifest_path}")
    if manifest.get("download_id") != expected_download:
        raise WPPAdapterError(
            f"{manifest_path} is for {manifest.get('download_id')!r}, expected {expected_download!r}"
        )
    recorded_path = Path(str(manifest.get("local_raw_path", "")))
    if not recorded_path.is_absolute():
        recorded_path = (REPOSITORY_ROOT / recorded_path).resolve()
    if recorded_path != path.resolve():
        raise WPPAdapterError(f"Manifest raw path does not identify {path}")
    if not path.is_file():
        raise WPPAdapterError(f"Snapshot does not exist: {path}")
    digest = _sha(path)
    if digest != manifest.get("sha256") or path.stat().st_size != manifest.get("byte_count"):
        raise WPPAdapterError(f"Snapshot checksum/size does not match {manifest_path}")
    if not str(manifest.get("final_url") or manifest.get("source_url") or "").startswith("https://"):
        raise WPPAdapterError(f"Snapshot manifest has no HTTPS source URL: {manifest_path}")
    return manifest


def _csv_rows_gzip(path: Path) -> list[dict[str, str]]:
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise WPPAdapterError(f"CSV has no header: {path}")
            return list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise WPPAdapterError(f"Cannot parse gzip CSV {path}: {exc}") from exc


def _csv_rows_zip(path: Path, member_name: str) -> list[dict[str, str]]:
    try:
        with zipfile.ZipFile(path) as archive:
            matches = [name for name in archive.namelist() if Path(name).name == member_name]
            if len(matches) != 1:
                raise WPPAdapterError(
                    f"Expected exactly one {member_name!r} in Togo ZIP; found {len(matches)}"
                )
            with archive.open(matches[0]) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                reader = csv.DictReader(text)
                if not reader.fieldnames:
                    raise WPPAdapterError(f"CSV has no header in {member_name}")
                return list(reader)
    except (OSError, zipfile.BadZipFile, UnicodeError, csv.Error) as exc:
        if isinstance(exc, WPPAdapterError):
            raise
        raise WPPAdapterError(f"Cannot parse Togo ZIP member {member_name}: {exc}") from exc


def _number(row: dict[str, str], key: str, label: str) -> float:
    raw = row.get(key)
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise WPPAdapterError(f"{label}: {key} is not numeric: {raw!r}") from exc
    if not math.isfinite(value):
        raise WPPAdapterError(f"{label}: {key} is not finite")
    return value


def _validate_demographic_rows(
    rows: list[dict[str, str]], label: str, *, expected_count: int | None = None
) -> dict[str, dict[str, str]]:
    required = {
        "LocID", "ISO3_code", "LocTypeName", "VarID", "Variant", "Time",
        "TPopulation1July", "TPopulationMale1July", "TPopulationFemale1July",
        "PopGrowthRate", "MedianAgePop", "NetMigrations",
    }
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0] if rows else []))
        raise WPPAdapterError(f"{label}: missing required demographic columns: {missing}")
    selected = [
        row for row in rows
        if row.get("LocTypeName") == "Country/Area"
        and row.get("Time") == str(YEAR)
        and row.get("Variant") == VARIANT
        and row.get("VarID") == VAR_ID
    ]
    by_id: dict[str, dict[str, str]] = {}
    for row in selected:
        loc_id = row.get("LocID", "")
        if not loc_id or loc_id in by_id:
            raise WPPAdapterError(f"{label}: missing or duplicate LocID {loc_id!r}")
        if not row.get("ISO3_code"):
            raise WPPAdapterError(f"{label}: {loc_id} has no ISO3_code")
        for column in (
            "TPopulation1July", "TPopulationMale1July",
            "TPopulationFemale1July", "PopGrowthRate", "MedianAgePop", "NetMigrations",
        ):
            _number(row, column, f"{label} LocID={loc_id}")
        by_id[loc_id] = row
    if not by_id:
        raise WPPAdapterError(f"{label}: no {YEAR} Medium Country/Area rows")
    if expected_count is not None and len(by_id) != expected_count:
        raise WPPAdapterError(
            f"{label}: expected {expected_count} country/area rows, found {len(by_id)}"
        )
    return by_id


def _validate_age_rows(
    rows: list[dict[str, str]], label: str, *, expected_count: int | None = None
) -> dict[str, dict[str, dict[str, float]]]:
    required = {
        "LocID", "ISO3_code", "LocTypeName", "VarID", "Variant", "Time",
        "AgeGrp", "PopMale", "PopFemale", "PopTotal",
    }
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0] if rows else []))
        raise WPPAdapterError(f"{label}: missing required age-sex columns: {missing}")
    result: dict[str, dict[str, dict[str, float]]] = {}
    for row in rows:
        if not (
            row.get("LocTypeName") == "Country/Area"
            and row.get("Time") == str(YEAR)
            and row.get("Variant") == VARIANT
            and row.get("VarID") == VAR_ID
        ):
            continue
        loc_id = row.get("LocID", "")
        age = row.get("AgeGrp", "")
        if age not in AGE_GROUPS:
            raise WPPAdapterError(f"{label}: unexpected age band {age!r} for LocID {loc_id}")
        bands = result.setdefault(loc_id, {})
        if age in bands:
            raise WPPAdapterError(f"{label}: duplicate age band {age!r} for LocID {loc_id}")
        male = _number(row, "PopMale", f"{label} LocID={loc_id} age={age}")
        female = _number(row, "PopFemale", f"{label} LocID={loc_id} age={age}")
        total = _number(row, "PopTotal", f"{label} LocID={loc_id} age={age}")
        if min(male, female, total) < 0 or abs(male + female - total) > 0.01:
            raise WPPAdapterError(f"{label}: sex totals do not reconcile for LocID={loc_id} age={age}")
        bands[age] = {"male": male, "female": female, "total": total}
    if not result:
        raise WPPAdapterError(f"{label}: no {YEAR} Medium Country/Area age rows")
    if expected_count is not None and len(result) != expected_count:
        raise WPPAdapterError(
            f"{label}: expected {expected_count} country/area locations, found {len(result)}"
        )
    for loc_id, bands in result.items():
        if tuple(sorted(bands, key=AGE_GROUPS.index)) != AGE_GROUPS:
            raise WPPAdapterError(
                f"{label}: LocID {loc_id} has {len(bands)} age bands; expected all {len(AGE_GROUPS)}"
            )
    return result


def _check_population_consistency(row: dict[str, str], bands: dict[str, dict[str, float]], label: str) -> None:
    age_total = sum(item["total"] for item in bands.values())
    population = _number(row, "TPopulation1July", label)
    male = _number(row, "TPopulationMale1July", label)
    female = _number(row, "TPopulationFemale1July", label)
    if abs(age_total - population) > max(0.05, population * 0.00002):
        raise WPPAdapterError(f"{label}: age-band total does not reconcile to 1 July population")
    if abs(male + female - population) > max(0.05, population * 0.00002):
        raise WPPAdapterError(f"{label}: male/female totals do not reconcile to 1 July population")


def _validate_taiwan_crosswalk(
    mappings: tuple[Any, ...],
    demographic: dict[str, dict[str, str]],
    ages: dict[str, dict[str, dict[str, float]]],
) -> None:
    taiwan_by_game = [item for item in mappings if item.game_id == TAIWAN_GAME_ID]
    taiwan_by_source = [item for item in mappings if item.source_id == TAIWAN_LOC_ID]
    if not taiwan_by_game and not taiwan_by_source:
        return
    if len(taiwan_by_game) != 1 or len(taiwan_by_source) != 1:
        raise WPPAdapterError("Taiwan must have exactly one WPP mapping to LocID 158")
    mapping = taiwan_by_game[0]
    if mapping.source_id != TAIWAN_LOC_ID or mapping.match_method != "reviewed_manual":
        raise WPPAdapterError(
            "Taiwan WPP mapping must use reviewed_manual and source LocID 158"
        )
    row = demographic.get(TAIWAN_LOC_ID)
    if row is None or TAIWAN_LOC_ID not in ages:
        raise WPPAdapterError("Taiwan WPP LocID 158 is absent from the selected snapshots")
    if (
        row.get("Location") != TAIWAN_LOCATION
        or row.get("ISO2_code") != "TW"
        or row.get("ISO3_code") != "TWN"
    ):
        raise WPPAdapterError(
            "WPP LocID 158 does not identify the expected Taiwan location and ISO metadata"
        )


def prepare_un_wpp(
    *,
    demographic_path: Path,
    demographic_manifest_path: Path,
    age_path: Path,
    age_manifest_path: Path,
    togo_zip_path: Path,
    togo_manifest_path: Path,
    crosswalk_path: Path,
    output_dir: Path,
    target_year: int = YEAR,
) -> dict[str, Any]:
    if target_year != YEAR:
        raise WPPAdapterError(f"This validated adapter currently supports target year {YEAR} only")
    main_demographic_manifest = _snapshot(
        demographic_path, demographic_manifest_path, expected_download="demographic_indicators_medium"
    )
    age_manifest = _snapshot(
        age_path, age_manifest_path, expected_download="population_by_age_5_group_sex_medium"
    )
    togo_manifest = _snapshot(
        togo_zip_path, togo_manifest_path, expected_download="interim_update_togo"
    )
    main_demo_rows = _csv_rows_gzip(demographic_path)
    main_age_rows = _csv_rows_gzip(age_path)
    togo_demo_rows = _csv_rows_zip(togo_zip_path, "WPP2024_Demographic_Indicators_Medium_Update.csv")
    togo_age_rows = _csv_rows_zip(togo_zip_path, "WPP2024_PopulationByAge5GroupSex_Medium_Update.csv")

    demo = _validate_demographic_rows(
        main_demo_rows, "main demographic file", expected_count=EXPECTED_COUNTRY_AREA_COUNT
    )
    ages = _validate_age_rows(
        main_age_rows, "main age-sex file", expected_count=EXPECTED_COUNTRY_AREA_COUNT
    )
    togo_demo = _validate_demographic_rows(togo_demo_rows, "Togo demographic supplement")
    togo_ages = _validate_age_rows(togo_age_rows, "Togo age-sex supplement")
    if set(togo_demo) != {TOGO_LOC_ID} or set(togo_ages) != {TOGO_LOC_ID}:
        raise WPPAdapterError("Togo supplement must contain Togo (LocID 768) only for the selected year")
    if togo_demo[TOGO_LOC_ID].get("ISO3_code") != "TGO":
        raise WPPAdapterError("Togo supplement LocID 768 does not carry ISO3_code TGO")
    if TOGO_LOC_ID not in demo or TOGO_LOC_ID not in ages:
        raise WPPAdapterError("Main WPP datasets do not contain Togo LocID 768")
    if set(demo) != set(ages):
        raise WPPAdapterError("Main demographic and age-sex files have different country/area LocID coverage")

    selected_demo = dict(demo)
    selected_ages = dict(ages)
    selected_demo[TOGO_LOC_ID] = togo_demo[TOGO_LOC_ID]
    selected_ages[TOGO_LOC_ID] = togo_ages[TOGO_LOC_ID]
    for loc_id, row in selected_demo.items():
        if loc_id not in selected_ages:
            raise WPPAdapterError(f"LocID {loc_id} has no age-sex records")
        _check_population_consistency(row, selected_ages[loc_id], f"LocID={loc_id}")

    try:
        crosswalk = load_crosswalk(crosswalk_path, expected_dataset=SOURCE_KEY)
    except CrosswalkError as exc:
        raise WPPAdapterError(f"Invalid reviewed WPP crosswalk: {exc}") from exc
    if crosswalk.source_key != SOURCE_KEY:
        raise WPPAdapterError(
            f"Crosswalk source_key must be {SOURCE_KEY!r}, received {crosswalk.source_key!r}"
        )
    mapping = {item.source_id: item.game_id for item in crosswalk.mappings}
    if len(mapping) != len(crosswalk.mappings):
        raise WPPAdapterError("WPP crosswalk contains duplicate source IDs")
    unknown_loc_ids = sorted(set(mapping) - set(selected_demo))
    if unknown_loc_ids:
        raise WPPAdapterError(f"WPP crosswalk contains unknown LocID values: {unknown_loc_ids[:20]}")
    _validate_taiwan_crosswalk(crosswalk.mappings, selected_demo, selected_ages)

    output_dir.mkdir(parents=True, exist_ok=True)
    observations: list[dict[str, Any]] = []
    mapped_loc_ids = set(mapping) & set(selected_demo)
    status = "projected"
    methodology_base = (
        "UN World Population Prospects 2024 Medium variant, target year 2026; "
        "annual population reference date 1 July. Source counts are in thousands "
        "and are converted to people by multiplying by 1,000."
    )
    source_url = str(main_demographic_manifest.get("final_url") or main_demographic_manifest["source_url"])
    retrieved_at = str(main_demographic_manifest["retrieved_at"])
    for loc_id in sorted(mapped_loc_ids, key=lambda value: int(value)):
        game_id = mapping[loc_id]
        row = selected_demo[loc_id]
        age_rows = selected_ages[loc_id]
        is_togo = loc_id == TOGO_LOC_ID
        demo_manifest = togo_manifest if is_togo else main_demographic_manifest
        age_source_manifest = togo_manifest if is_togo else age_manifest
        demographic_release = TOGO_RELEASE if is_togo else MAIN_DEMOGRAPHIC_RELEASE
        age_release = TOGO_RELEASE if is_togo else AGE_RELEASE
        reference = (
            f"UN WPP 2024 {demographic_release}; {demo_manifest.get('final_url') or demo_manifest.get('source_url')}"
        )
        common = {
            "game_id": game_id, "source_id": loc_id, "observation_period": str(YEAR),
            "value_status": status, "source_reference": reference,
        }
        scalar_fields = (
            (1, "TPopulation1July", "people", "Population at 1 July, source thousands × 1,000."),
            (2, "PopGrowthRate", "percent_per_year", "Annual population growth rate, percent per year."),
            (6, "MedianAgePop", "years", "Median age at 1 July, in years."),
            (14, "NetMigrations", "people_or_rate", "Net number of migrants in thousands × 1,000; not the net migration rate."),
        )
        for field_id, column, unit, method in scalar_fields:
            factor = 1000 if field_id in {1, 14} else 1
            observations.append({
                **common, "field_id": field_id,
                "value": _number(row, column, f"LocID={loc_id}") * factor,
                "unit": unit,
                "methodology": f"{methodology_base} {method}",
                "source_reference": reference,
            })
        male = _number(row, "TPopulationMale1July", f"LocID={loc_id}") * 1000
        female = _number(row, "TPopulationFemale1July", f"LocID={loc_id}") * 1000
        observations.append({
            **common, "field_id": 13, "value": {"male": male, "female": female},
            "unit": "people_or_share",
            "methodology": f"{methodology_base} Male and female totals are 1 July population counts.",
            "source_reference": reference,
        })
        age_value = [
            {
                "age_band": band,
                "population_male": age_rows[band]["male"] * 1000,
                "population_female": age_rows[band]["female"] * 1000,
                "population_total": age_rows[band]["total"] * 1000,
            }
            for band in AGE_GROUPS
        ]
        age_reference = (
            f"UN WPP 2024 {age_release}; "
            f"{age_source_manifest.get('final_url') or age_source_manifest.get('source_url')}"
        )
        observations.append({
            **common, "field_id": 12, "value": age_value,
            "unit": "age_band_share_or_count",
            "methodology": (
                f"{methodology_base} Five-year age bands plus 100+; male, female and total counts "
                "are converted from thousands to people. Male plus female reconciles to total."
            ),
            "source_reference": age_reference,
        })

    # Preserve all acquired snapshots as approval-bound inputs in a derived WP1.5 manifest.
    main_raw_sha = str(main_demographic_manifest["sha256"])
    manifest = {
        "manifest_schema_version": 1, "work_package": "WP1.5",
        "source_key": SOURCE_KEY,
        "release": f"{MAIN_DEMOGRAPHIC_RELEASE}+{TOGO_RELEASE}",
        "source_url": str(main_demographic_manifest.get("source_url")),
        "final_url": str(main_demographic_manifest.get("final_url") or main_demographic_manifest.get("source_url")),
        "retrieved_at": retrieved_at,
        "local_raw_path": str(demographic_path.resolve()),
        "byte_count": demographic_path.stat().st_size,
        "sha256": main_raw_sha,
        "attribution": main_demographic_manifest.get("attribution"),
        "license_status": main_demographic_manifest.get("license_status"),
        "terms_url": main_demographic_manifest.get("terms_url"),
        "additional_inputs": [
            {
                "label": "WPP 2024 age-sex main snapshot",
                "local_raw_path": str(age_path.resolve()),
                "byte_count": age_path.stat().st_size,
                "sha256": str(age_manifest["sha256"]),
            },
            {
                "label": "WPP 2026 Togo interim update",
                "local_raw_path": str(togo_zip_path.resolve()),
                "byte_count": togo_zip_path.stat().st_size,
                "sha256": str(togo_manifest["sha256"]),
            },
        ],
        "upstream_manifests": [
            {"path": str(demographic_manifest_path.resolve()), "sha256": _sha(demographic_manifest_path)},
            {"path": str(age_manifest_path.resolve()), "sha256": _sha(age_manifest_path)},
            {"path": str(togo_manifest_path.resolve()), "sha256": _sha(togo_manifest_path)},
        ],
        "adapter": "tools.sources.wpp",
        "target_year": YEAR,
        "variant": VARIANT,
        "population_reference_date": "1 July",
    }
    normalized = {
        "schema_version": 1, "work_package": "WP1.5", "source_key": SOURCE_KEY,
        "release": manifest["release"], "source_sha256": main_raw_sha,
        "observations": observations,
    }
    coverage = {
        "source_key": SOURCE_KEY, "target_year": YEAR, "variant": VARIANT,
        "source_country_area_count": len(selected_demo),
        "crosswalk_mapped_count": len(mapped_loc_ids),
        "crosswalk_unmapped_count": len(set(selected_demo) - set(mapping)),
        "unmapped_source_ids": sorted(set(selected_demo) - set(mapping), key=lambda value: int(value)),
        "crosswalk_ids_not_in_source": unknown_loc_ids,
        "observation_count": len(observations),
        "observations_per_mapped_country": 6,
        "togo_supplement_applied": True,
        "togo_source_id": TOGO_LOC_ID,
        "main_release": MAIN_DEMOGRAPHIC_RELEASE,
        "age_release": AGE_RELEASE,
        "togo_release": TOGO_RELEASE,
        "all_source_rows_validated": True,
        "sqlite_written": False,
        "latest_validated_promoted": False,
    }
    (output_dir / "normalized_observations.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output_dir / "application_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output_dir / "coverage.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return coverage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare a validated UN WPP 2024 WP1.5 candidate; no SQLite writes.")
    parser.add_argument("--demographic", type=Path, required=True)
    parser.add_argument("--demographic-manifest", type=Path, required=True)
    parser.add_argument("--age", type=Path, required=True)
    parser.add_argument("--age-manifest", type=Path, required=True)
    parser.add_argument("--togo-zip", type=Path, required=True)
    parser.add_argument("--togo-manifest", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-year", type=int, default=YEAR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = prepare_un_wpp(
            demographic_path=args.demographic,
            demographic_manifest_path=args.demographic_manifest,
            age_path=args.age,
            age_manifest_path=args.age_manifest,
            togo_zip_path=args.togo_zip,
            togo_manifest_path=args.togo_manifest,
            crosswalk_path=args.crosswalk,
            output_dir=args.output_dir,
            target_year=args.target_year,
        )
    except (WPPAdapterError, OSError, ValueError) as exc:
        print(f"UN WPP preparation failed: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
