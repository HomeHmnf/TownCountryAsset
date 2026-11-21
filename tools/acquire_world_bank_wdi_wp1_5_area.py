"""Acquire and validate the separate WP1.5 WDI area/density snapshot.

This profile is intentionally independent of the IMF/WDI macro-comparison snapshot.
It writes immutable raw responses, a manifest, and read-only candidate reports only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools import acquire_world_bank_wdi_snapshot as common
from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

ROOT = Path(__file__).resolve().parents[1]
SOURCE_KEY = "world_bank_wdi"
DATASET_KEY = "wdi_wp1_5_area"
SOURCE_ID = "2"
API = common.API
PER_PAGE = 20000
RAW_BASE = Path("raw_data/sources/world_bank_wdi") / DATASET_KEY
MANIFEST_BASE = Path("data_manifests/sources/world_bank_wdi") / DATASET_KEY
REPORT_BASE = Path("reports/sources/world-bank-wdi-wp1-5-area")
TERMS_URL = common.TERMS_URL
API_DOCS_URL = common.API_DOCS_URL

INDICATORS = {
    "EN.POP.DNST": {
        "field_id": 3, "key": "population_density", "unit": "people_per_km2",
        "meaning": "Midyear population divided by land area; people per square kilometre of land area.",
        "minimum": 0.0, "strictly_positive": False,
    },
    "AG.SRF.TOTL.K2": {
        "field_id": 33, "key": "total_area", "unit": "km2",
        "meaning": "Surface area including inland water and some coastal waterways.",
        "minimum": 0.0, "strictly_positive": True,
    },
    "AG.LND.TOTL.K2": {
        "field_id": 34, "key": "land_area", "unit": "km2",
        "meaning": "Land area excluding inland water; not interchangeable with surface area.",
        "minimum": 0.0, "strictly_positive": True,
    },
}


class AreaSnapshotError(RuntimeError):
    """Invalid WDI WP1.5 area snapshot or candidate validation failure."""


def _url(path: str, params: dict[str, str]) -> str:
    return f"{API}/{path}?{urllib.parse.urlencode(params)}"


def _save(root: Path, raw_dir: Path, filename: str, url: str, params: dict[str, str],
          request_get: Callable[[str], tuple[bytes, int, dict[str, str], str]],
          page: int | None = None) -> tuple[dict[str, Any], Any]:
    body, status, headers, final_url = request_get(url)
    if status != 200 or not body:
        raise AreaSnapshotError(f"Invalid HTTP response ({status}) or empty body: {url}")
    payload = common._payload(body, filename)
    path = raw_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(body)
    except FileExistsError as exc:
        raise AreaSnapshotError(f"Refusing to overwrite {path}") from exc
    artifact = {
        "filename": filename, "local_raw_path": path.relative_to(root).as_posix(),
        "content_type": next((v for k, v in headers.items() if k.casefold() == "content-type"), "application/json"),
        "format": "json", "byte_count": len(body),
        "sha256": hashlib.sha256(body).hexdigest(), "url": url, "final_url": final_url,
        "http_status": status, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "request_parameters": params, "response_headers": headers,
        "request_headers": {"User-Agent": "TownCountryAsset-WDI-WP1.5-Area/1.0", "Accept": "application/json"},
        "page_number": page,
    }
    return artifact, payload


def capture_snapshot(*, repository_root: str | Path = ROOT, start_year: int = 2015,
                     end_year: int = 2025, retrieved_at: str | None = None,
                     request_get: Callable[[str], tuple[bytes, int, dict[str, str], str]] = common._request) -> dict[str, Any]:
    if start_year < 1900 or end_year < start_year or end_year > 2100:
        raise AreaSnapshotError("Invalid snapshot year range")
    root = Path(repository_root).resolve()
    started = common._aware(retrieved_at)
    snapshot_id = "api_snapshot_" + started.strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = root / RAW_BASE / snapshot_id
    manifest_path = root / MANIFEST_BASE / f"{snapshot_id}.json"
    if raw_dir.exists() or manifest_path.exists():
        raise AreaSnapshotError(f"Snapshot already exists: {snapshot_id}")
    raw_dir.mkdir(parents=True, exist_ok=False)
    artifacts: list[dict[str, Any]] = []

    params = {"format": "json"}
    artifact, source_payload = _save(root, raw_dir, "source_metadata.json",
        _url("sources/2", params), params, request_get)
    if not any(str(row.get("id")) == SOURCE_ID and row.get("name") == "World Development Indicators"
               for row in source_payload[1]):
        raise AreaSnapshotError("API source ID 2 is not World Development Indicators")
    artifacts.append(artifact)

    country_rows: list[dict[str, Any]] = []
    page = 1
    country_pages = None
    while True:
        params = {"format": "json", "per_page": "400", "page": str(page)}
        artifact, payload = _save(root, raw_dir, f"country_metadata_page_{page:03d}.json",
            _url("country", params), params, request_get, page)
        pages = common._pages(payload, page, "country metadata")
        if country_pages is not None and pages != country_pages:
            raise AreaSnapshotError("Country metadata pagination changed during capture")
        country_pages = pages
        artifact.update({"page_count": pages, "row_count": len(payload[1])})
        artifacts.append(artifact)
        country_rows.extend(payload[1])
        if page == pages:
            break
        page += 1
    if not country_rows:
        raise AreaSnapshotError("Country metadata catalogue is empty")

    summaries = {}
    for code in INDICATORS:
        params = {"format": "json"}
        artifact, payload = _save(root, raw_dir, f"indicator_metadata_{code}.json",
            _url(f"indicator/{urllib.parse.quote(code, safe='.')}", params), params, request_get)
        meta = next((row for row in payload[1] if row.get("id") == code), None)
        if meta is None or str((meta.get("source") or {}).get("id")) != SOURCE_ID:
            raise AreaSnapshotError(f"{code} is not confirmed as a WDI indicator")
        artifacts.append(artifact)
        rows = []
        page = 1
        page_count = None
        api_last_updated = None
        while True:
            params = {"format": "json", "date": f"{start_year}:{end_year}",
                      "per_page": str(PER_PAGE), "page": str(page)}
            artifact, response = _save(root, raw_dir, f"observations_{code}_page_{page:03d}.json",
                _url(f"country/all/indicator/{urllib.parse.quote(code, safe='.')}", params),
                params, request_get, page)
            pages = common._pages(response, page, f"{code} observations")
            if page_count is not None and pages != page_count:
                raise AreaSnapshotError(f"{code}: pagination changed during capture")
            page_count = pages
            api_last_updated = response[0].get("lastupdated") or api_last_updated
            if any((row.get("indicator") or {}).get("id") not in (None, code) for row in response[1]):
                raise AreaSnapshotError(f"{code}: unexpected indicator in observation response")
            artifact.update({"page_count": pages, "row_count": len(response[1])})
            artifacts.append(artifact)
            rows.extend(response[1])
            if page == pages:
                break
            page += 1
        summaries[code] = {
            "field_id": INDICATORS[code]["field_id"], "pages": page_count,
            "observation_rows": len(rows), "api_last_updated": api_last_updated,
            "indicator_name": meta.get("name"), "unit_metadata": meta.get("unit"),
            "source_organization": meta.get("sourceOrganization"),
            "source_note": meta.get("sourceNote"),
        }

    completed = datetime.now(timezone.utc)
    manifest = {
        "manifest_schema_version": 1, "source_id": SOURCE_KEY,
        "source_name": "World Bank World Development Indicators",
        "download_id": DATASET_KEY, "dataset_id": DATASET_KEY,
        "release": snapshot_id, "snapshot_id": snapshot_id,
        "release_kind": "rolling_api_snapshot", "release_discovery_mode": "api_capture",
        "source_url": API, "final_url": API, "api_documentation_url": API_DOCS_URL,
        "terms_url": TERMS_URL,
        "attribution": "World Bank Group, World Development Indicators; originating organisations and source notes retained per indicator.",
        "license_status": "unclear_or_unverified_indicator_level_third_party_review_required",
        "retrieved_at": completed.isoformat(), "capture_started_at": started.isoformat(),
        "snapshot_scope": {
            "profile": "wp1_5_area_and_density", "work_package": "WP1.5",
            "field_ids": [3, 33, 34], "world_bank_source_id": SOURCE_ID,
            "start_year": start_year, "end_year": end_year,
            "primary_indicators": list(INDICATORS), "all_indicators": list(INDICATORS),
            "api_version": "v2", "observation_api_per_page": PER_PAGE,
            "country_catalogue_record_count": len(country_rows),
            "country_catalogue_page_count": country_pages,
            "observation_status": "Preserved verbatim; not interpreted as actual, estimate or forecast.",
        },
        "indicator_summaries": summaries, "files": artifacts,
    }
    common._write_json(manifest_path, manifest)
    report = {
        "assessment": "world_bank_wdi_wp1_5_area_immutable_api_snapshot",
        "snapshot_id": snapshot_id, "retrieved_at": completed.isoformat(),
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "artifact_count": len(artifacts), "artifact_bytes": sum(x["byte_count"] for x in artifacts),
        "country_catalogue_record_count": len(country_rows),
        "period": {"start_year": start_year, "end_year": end_year},
        "indicators": summaries,
        "source_last_updated": source_payload[0].get("lastupdated"),
        "side_effects": {"raw_snapshot_acquired": True, "manifest_written": True,
            "project_database_written": False, "game_database_written": False,
            "candidate_report_written": False, "approval_created": False,
            "source_selection_changed": False},
    }
    report_dir = root / REPORT_BASE / snapshot_id
    common._write_json(report_dir / "acquisition.json", report)
    lines = ["# WDI WP1.5 area and density snapshot", "", f"- Snapshot: {snapshot_id}",
        f"- Period: {start_year}–{end_year}", f"- Manifest: {report['manifest_path']}",
        f"- Raw response artifacts: {len(artifacts)} ({report['artifact_bytes']:,} bytes)", "",
        "| Field | Indicator | Meaning | Rows | API last updated |",
        "|---:|---|---|---:|---|"]
    for code, spec in INDICATORS.items():
        item = summaries[code]
        lines.append(f"| {spec['field_id']} | {code} | {spec['meaning']} | {item['observation_rows']} | {item['api_last_updated'] or 'not supplied'} |")
    lines.extend(["", "Raw response bytes, URLs, headers, retrieval times, byte counts and SHA-256 hashes are preserved.",
        "This is a rolling API snapshot, not a provider-declared release vintage.",
        "No identity mapping, semantic approval, source-selection change or database write occurred."])
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "acquisition.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    return report


def _read(root: Path, artifact: dict[str, Any]) -> Any:
    rel = artifact.get("local_raw_path")
    if not isinstance(rel, str):
        raise AreaSnapshotError("Manifest artifact has no raw path")
    path = (root / rel).resolve(strict=True)
    path.relative_to(root)
    raw = path.read_bytes()
    if len(raw) != artifact.get("byte_count") or hashlib.sha256(raw).hexdigest() != artifact.get("sha256"):
        raise AreaSnapshotError(f"Snapshot integrity mismatch: {rel}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AreaSnapshotError(f"Invalid JSON artifact: {rel}") from exc


def load_snapshot(manifest_path: str | Path, *, repository_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    path = Path(manifest_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve(strict=True)
    path.relative_to(root)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != SOURCE_KEY or manifest.get("download_id") != DATASET_KEY:
        raise AreaSnapshotError("Manifest is not the WP1.5 area/density WDI dataset")
    scope = manifest.get("snapshot_scope") or {}
    if scope.get("profile") != "wp1_5_area_and_density" or scope.get("field_ids") != [3, 33, 34]:
        raise AreaSnapshotError("Unexpected WP1.5 WDI snapshot scope")
    artifacts = manifest.get("files")
    if not isinstance(artifacts, list) or not artifacts:
        raise AreaSnapshotError("Manifest contains no artifacts")
    source = None
    countries: dict[str, dict[str, Any]] = {}
    metadata = {}
    pages: dict[str, list[tuple[int, int, list[dict[str, Any]]]]] = {}
    for item in artifacts:
        name = Path(item["local_raw_path"]).name
        payload = _read(root, item)
        if name == "source_metadata.json":
            source = payload
        elif name.startswith("country_metadata_page_"):
            pages_count = int(item.get("page_count") or 0)
            countries.update({str(row.get("id")): row for row in payload[1] if isinstance(row.get("id"), str)})
            # Country pagination completeness checked below from artifact records.
        elif name.startswith("indicator_metadata_"):
            code = name.removeprefix("indicator_metadata_").removesuffix(".json")
            row = next((r for r in payload[1] if r.get("id") == code), None)
            if row is None or str((row.get("source") or {}).get("id")) != SOURCE_ID:
                raise AreaSnapshotError(f"Indicator metadata mismatch: {code}")
            metadata[code] = row
        elif name.startswith("observations_"):
            stem = name.removeprefix("observations_").removesuffix(".json")
            code, page_text = stem.rsplit("_page_", 1)
            pages.setdefault(code, []).append((int(page_text), int(item.get("page_count") or 0), payload[1]))
    if source is None or not any(str(x.get("id")) == SOURCE_ID for x in source[1]):
        raise AreaSnapshotError("Snapshot lacks WDI source metadata")
    if set(metadata) != set(INDICATORS) or set(pages) != set(INDICATORS):
        raise AreaSnapshotError("Snapshot does not contain all three indicator bundles")
    observations = {}
    for code, bundle in pages.items():
        bundle.sort(key=lambda x: x[0])
        expected = bundle[0][1]
        if expected != len(bundle) or [x[0] for x in bundle] != list(range(1, expected + 1)) or any(x[1] != expected for x in bundle):
            raise AreaSnapshotError(f"{code}: incomplete observation pagination")
        observations[code] = [row for _, _, rows in bundle for row in rows]
    return {"manifest": manifest, "manifest_path": path,
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "countries": countries, "indicator_metadata": metadata, "observations": observations}


def validate_candidates(manifest_path: str | Path, crosswalk_path: str | Path,
                        registry_path: str | Path, *, repository_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    loaded = load_snapshot(manifest_path, repository_root=root)
    registry = json.loads((root / registry_path).read_text(encoding="utf-8") if not Path(registry_path).is_absolute() else Path(registry_path).read_text(encoding="utf-8"))
    records = registry.get("records")
    if not isinstance(records, list):
        raise AreaSnapshotError("Identity registry has no records array")
    known_game_ids = [row["game_id"] for row in records if isinstance(row, dict) and isinstance(row.get("game_id"), str)]
    dataset = "world_bank_wdi_wp1_5_area"
    crosswalk = load_crosswalk(crosswalk_path if Path(crosswalk_path).is_absolute() else root / crosswalk_path,
        expected_dataset=dataset, known_game_ids=known_game_ids)
    iso_to_game = {mapping.source_id.upper(): mapping.game_id for mapping in crosswalk.mappings}
    observations = loaded["observations"]
    selected: dict[str, dict[str, dict[str, Any]]] = {}
    coverage: dict[str, Any] = {}
    anomalies: list[dict[str, Any]] = []
    for code, spec in INDICATORS.items():
        seen: set[tuple[str, int]] = set()
        latest: dict[str, dict[str, Any]] = {}
        null_rows = 0
        aggregates = 0
        unknown_iso3 = set()
        invalid = 0
        for row in observations[code]:
            iso3 = row.get("countryiso3code")
            if not isinstance(iso3, str) or len(iso3) != 3:
                aggregates += 1
                continue
            if iso3 not in loaded["countries"]:
                raise AreaSnapshotError(f"{code}/{iso3} absent from captured country catalogue")
            region = (loaded["countries"][iso3].get("region") or {}).get("id")
            if region == "NA":
                aggregates += 1
                continue
            try:
                year = int(row.get("date"))
            except (TypeError, ValueError):
                invalid += 1
                continue
            key = (iso3, year)
            if key in seen:
                raise AreaSnapshotError(f"Duplicate observation key {code}/{iso3}/{year}")
            seen.add(key)
            value = row.get("value")
            if value is None:
                null_rows += 1
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                invalid += 1
                continue
            if not math.isfinite(numeric) or numeric < spec["minimum"] or (spec["strictly_positive"] and numeric <= 0):
                invalid += 1
                anomalies.append({"indicator": code, "iso3": iso3, "year": year, "value": value, "reason": "non_finite_or_out_of_range"})
                continue
            candidate = {"iso3": iso3, "game_id": iso_to_game.get(iso3),
                "year": year, "value": numeric, "obs_status": row.get("obs_status"),
                "country_name": (row.get("country") or {}).get("value")}
            if iso3 not in latest or year > latest[iso3]["year"]:
                latest[iso3] = candidate
        selected[code] = latest
        coverage[code] = {"field_id": spec["field_id"], "candidate_iso3_count": len(latest),
            "mapped_candidate_count": sum(1 for iso3 in latest if iso3 in iso_to_game),
            "unmapped_candidate_count": sum(1 for iso3 in latest if iso3 not in iso_to_game),
            "null_observation_rows": null_rows, "aggregate_rows_excluded": aggregates,
            "invalid_rows": invalid, "latest_year_min": min((x["year"] for x in latest.values()), default=None),
            "latest_year_max": max((x["year"] for x in latest.values()), default=None)}
    area_checks = []
    for iso3 in set(selected["AG.SRF.TOTL.K2"]) & set(selected["AG.LND.TOTL.K2"]):
        surface, land = selected["AG.SRF.TOTL.K2"][iso3], selected["AG.LND.TOTL.K2"][iso3]
        if surface["year"] == land["year"] and surface["value"] < land["value"]:
            area_checks.append({"iso3": iso3, "year": surface["year"],
                "surface_area_km2": surface["value"], "land_area_km2": land["value"],
                "reason": "surface_area_less_than_land_area"})
    rows = []
    for code, spec in INDICATORS.items():
        for iso3, item in sorted(selected[code].items()):
            rows.append({"game_id": item["game_id"] or "", "country_iso3": iso3,
                "country_name": item["country_name"] or "", "field_id": spec["field_id"],
                "field_key": spec["key"], "indicator_code": code, "value": item["value"],
                "unit": spec["unit"], "reference_year": item["year"],
                "obs_status": item["obs_status"] or "", "mapping_status": "mapped" if item["game_id"] else "unmapped"})
    output_dir = root / REPORT_BASE / loaded["manifest"]["snapshot_id"] / "candidate_validation"
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = output_dir / "wdi_wp1_5_area_candidates.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [
            "game_id", "country_iso3", "country_name", "field_id", "field_key",
            "indicator_code", "value", "unit", "reference_year", "obs_status", "mapping_status"])
        writer.writeheader()
        writer.writerows(rows)
    report = {"assessment": "world_bank_wdi_wp1_5_area_candidate_validation",
        "snapshot_id": loaded["manifest"]["snapshot_id"],
        "manifest_sha256": loaded["manifest_sha256"],
        "crosswalk_dataset": crosswalk.dataset, "crosswalk_source_key": crosswalk.source_key,
        "crosswalk_mappings": len(crosswalk.mappings), "known_game_ids": len(known_game_ids),
        "coverage": coverage, "area_consistency_checks": area_checks,
        "anomalies": anomalies, "candidate_rows": len(rows),
        "candidate_csv": csv_path.relative_to(root).as_posix(),
        "limitations": ["Latest non-null observation is selected independently per indicator and country; years need not align.",
            "Observation status is preserved verbatim; blank status is not interpreted as actual.",
            "ISO3-to-game_id mapping is exclusively through the supplied explicit crosswalk.",
            "Metadata source organization and source notes require human review; WDI source ID alone does not prove originating-organization authority.",
            "Surface/land consistency is checked only where their selected reference years match.",
            "No database writes, approval, source-selection or retention changes."],
        "side_effects": {"canonical_database_written": False, "project_database_written": False,
            "approval_created": False, "source_selection_changed": False}}
    common._write_json(output_dir / "assessment.json", report)
    lines = ["# WDI WP1.5 area/density candidate validation", "",
        f"- Snapshot: {report['snapshot_id']}", f"- Manifest SHA-256: {report['manifest_sha256']}",
        f"- Explicit crosswalk mappings: {len(crosswalk.mappings)}", f"- Candidate rows: {len(rows)}", "",
        "| Field | Indicator | Candidate ISO3 | Mapped | Unmapped | Null rows | Invalid | Latest year range |",
        "|---:|---|---:|---:|---:|---:|---:|---|"]
    for code, item in coverage.items():
        yr = f"{item['latest_year_min']}–{item['latest_year_max']}" if item["latest_year_min"] is not None else "none"
        lines.append(f"| {item['field_id']} | {code} | {item['candidate_iso3_count']} | {item['mapped_candidate_count']} | {item['unmapped_candidate_count']} | {item['null_observation_rows']} | {item['invalid_rows']} | {yr} |")
    lines.extend(["", "## Area consistency", ""])
    lines.extend([f"- {x['iso3']} {x['year']}: surface {x['surface_area_km2']} km² < land {x['land_area_km2']} km²" for x in area_checks] or ["- No same-year surface/land inversion detected."])
    lines.extend(["", "## Review boundary", ""] + [f"- {x}" for x in report["limitations"]])
    (output_dir / "assessment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["report_directory"] = output_dir.relative_to(root).as_posix()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--start-year", type=int, default=2015)
    capture.add_argument("--end-year", type=int, default=2025)
    capture.add_argument("--root", type=Path, default=ROOT)
    capture.add_argument("--timeout", type=int, default=120)
    capture.add_argument("--retries", type=int, default=5)
    capture.add_argument("--retry-delay", type=float, default=2.0)
    validate = sub.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--crosswalk", type=Path, required=True)
    validate.add_argument("--registry", type=Path, default=Path("config/country_identity_registry.json"))
    validate.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            report = capture_snapshot(repository_root=args.root, start_year=args.start_year,
                end_year=args.end_year, request_get=lambda url: common._request(
                    url, timeout=args.timeout, retries=args.retries, retry_delay=args.retry_delay))
        else:
            report = validate_candidates(args.manifest, args.crosswalk, args.registry, repository_root=args.root)
    except (AreaSnapshotError, CrosswalkError, common.SnapshotError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
