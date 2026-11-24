"""Normalize the immutable WDI WP1.5 area/density snapshot for review/import.

This adapter emits candidate observations only. It does not approve, select, or
write data to either project database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from tools.acquire_world_bank_wdi_wp1_5_area import (
    API, CROSSWALK_DATASET, DATASET_KEY, INDICATORS, ROOT, SOURCE_KEY, AreaSnapshotError, load_snapshot,
)
from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")

def normalize_snapshot(
    manifest_path: str | Path,
    crosswalk_path: str | Path,
    observations_path: str | Path,
    import_manifest_path: str | Path,
    *,
    repository_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    loaded = load_snapshot(manifest_path, repository_root=root)
    crosswalk = load_crosswalk(
        Path(crosswalk_path) if Path(crosswalk_path).is_absolute() else root / crosswalk_path,
        expected_dataset=CROSSWALK_DATASET,
    )
    if crosswalk.source_key != SOURCE_KEY:
        raise AreaSnapshotError("Crosswalk source_key does not match the WDI provider")
    mapping = {item.source_id: item.game_id for item in crosswalk.mappings}
    if len(mapping) != 187:
        raise AreaSnapshotError(f"Expected the owner-approved 187-entry WDI crosswalk; found {len(mapping)}")
    if any(not (len(code) == 3 and code.isupper() and code.isalpha()) for code in mapping):
        raise AreaSnapshotError("Crosswalk source IDs must be uppercase three-letter WDI codes")

    rows: list[dict[str, Any]] = []
    per_indicator: dict[str, int] = {}
    for code, spec in INDICATORS.items():
        latest: dict[str, dict[str, Any]] = {}
        for item in loaded["observations"][code]:
            iso3 = item.get("countryiso3code")
            if not isinstance(iso3, str) or len(iso3) != 3:
                continue
            country = loaded["countries"].get(iso3)
            if country is None or (country.get("region") or {}).get("id") == "NA":
                continue
            value = item.get("value")
            if value is None or iso3 not in mapping:
                continue
            try:
                year = int(item.get("date"))
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise AreaSnapshotError(f"Invalid selected value for {code}/{iso3}") from exc
            if year < 1900 or not __import__("math").isfinite(numeric):
                raise AreaSnapshotError(f"Invalid selected value for {code}/{iso3}/{year}")
            previous = latest.get(iso3)
            if previous is None or year > previous["year"]:
                latest[iso3] = {
                    "year": year, "value": numeric,
                    "provider_status": item.get("obs_status"),
                    "country_name": (item.get("country") or {}).get("value"),
                }
        if set(latest) != set(mapping):
            missing = sorted(set(mapping) - set(latest))
            raise AreaSnapshotError(f"{code}: mapped entities lack non-null observations: {missing[:10]}")
        per_indicator[code] = len(latest)
        metadata = loaded["indicator_metadata"][code]
        for iso3, selected in sorted(latest.items()):
            rows.append({
                "game_id": mapping[iso3],
                "source_id": iso3,
                "field_id": spec["field_id"],
                "value": selected["value"],
                "unit": spec["unit"],
                "value_status": "unclassified",
                "observation_period": str(selected["year"]),
                "source_reference": f"{API}/country/{iso3}/indicator/{code}?date={selected['year']}",
                "methodology": (
                    f"World Bank WDI indicator {code}: {spec['meaning']} "
                    f"Originating source organization: {metadata.get('sourceOrganization') or 'not supplied'}. "
                    "Provider obs_status is blank; the populated scalar value remains unclassified."
                ),
                "provenance": {
                    "wdi_iso3": iso3,
                    "country_name": selected["country_name"],
                    "indicator_code": code,
                    "provider_obs_status": selected["provider_status"],
                    "provider_source_organization": metadata.get("sourceOrganization"),
                    "provider_source_note": metadata.get("sourceNote"),
                    "provider_unit_metadata": metadata.get("unit"),
                },
            })
    expected = len(mapping) * len(INDICATORS)
    if len(rows) != expected or len({(r["game_id"], r["field_id"]) for r in rows}) != expected:
        raise AreaSnapshotError(f"Expected {expected} unique observations; generated {len(rows)}")

    acquisition = loaded["manifest"]
    acquisition_path = Path(loaded["manifest_path"])
    artifacts = acquisition["files"]
    if len(artifacts) != 8:
        raise AreaSnapshotError(f"Expected the immutable eight-artifact WDI bundle; found {len(artifacts)}")
    # Use the captured source metadata response as the required primary raw
    # input; the other seven captured responses remain explicit additional inputs.
    primary = next((item for item in artifacts if Path(item["local_raw_path"]).name == "source_metadata.json"), None)
    if primary is None:
        raise AreaSnapshotError("Snapshot is missing source_metadata.json")
    additional = [item for item in artifacts if item is not primary]
    def raw_input(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "local_raw_path": item["local_raw_path"],
            "sha256": item["sha256"],
            "byte_count": item["byte_count"],
        }
    primary_path = root / primary["local_raw_path"]
    primary_bytes = primary_path.read_bytes()
    import_manifest = {
        "manifest_schema_version": 1,
        "work_package": "WP1.5",
        "source_key": SOURCE_KEY,
        "dataset": CROSSWALK_DATASET,
        "release": acquisition["release"],
        "sha256": hashlib.sha256(primary_bytes).hexdigest(),
        "local_raw_path": primary["local_raw_path"],
        "byte_count": len(primary_bytes),
        "source_url": acquisition["source_url"],
        "final_url": acquisition["final_url"],
        "retrieved_at": acquisition["retrieved_at"],
        "attribution": acquisition.get("attribution"),
        "license_status": acquisition.get("license_status"),
        "additional_inputs": [raw_input(item) for item in additional],
        "upstream_manifests": [{
            "path": acquisition_path.relative_to(root).as_posix(),
            "sha256": loaded["manifest_sha256"],
        }],
    }
    normalized = {
        "schema_version": 1,
        "work_package": "WP1.5",
        "source_key": SOURCE_KEY,
        "dataset": CROSSWALK_DATASET,
        "release": acquisition["release"],
        "source_sha256": import_manifest["sha256"],
        "observations": rows,
        "normalization": {
            "policy": "latest_non_null_per_indicator_and_entity",
            "indicator_counts": per_indicator,
            "observation_count": len(rows),
            "value_status_policy": "unclassified_when_provider_obs_status_blank",
            "unmapped_candidate_codes_excluded": 29,
            "null_only_code_excluded": ["XKX"],
            "official_iso_identity_changed": False,
        },
    }
    output = Path(observations_path)
    manifest_output = Path(import_manifest_path)
    if not output.is_absolute():
        output = root / output
    if not manifest_output.is_absolute():
        manifest_output = root / manifest_output
    _write_json(output, normalized)
    _write_json(manifest_output, import_manifest)
    return {
        "assessment": "world_bank_wdi_wp1_5_area_normalization_candidate",
        "dataset": CROSSWALK_DATASET,
        "acquisition_dataset": DATASET_KEY,
        "source_key": SOURCE_KEY,
        "release": acquisition["release"],
        "observations": len(rows),
        "indicator_counts": per_indicator,
        "observations_path": output.relative_to(root).as_posix(),
        "import_manifest_path": manifest_output.relative_to(root).as_posix(),
        "license_status": acquisition.get("license_status"),
        "side_effects": {
            "canonical_database_written": False,
            "project_database_written": False,
            "approval_created": False,
            "source_selection_changed": False,
        },
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--import-manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        result = normalize_snapshot(
            args.manifest, args.crosswalk, args.observations, args.import_manifest,
            repository_root=args.root,
        )
    except (AreaSnapshotError, CrosswalkError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
