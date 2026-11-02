"""Acquire an immutable snapshot of Bahrain's annual unemployment API dataset.

This adapter preserves provider JSON as received. It does not normalize values,
write to SQLite, or change source-selection policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ID = "bahrain_open_data"
DOWNLOAD_ID = "unemployment_yearly"
DATASET_ID = "03-unemployment-yearly"
API_BASE = "https://data.gov.bh/api/explore/v2.1/catalog/datasets"
PAGE_SIZE = 100


class BahrainAcquisitionError(RuntimeError):
    """Bahrain API response or snapshot-contract failure."""


def _request_json(url: str, timeout: int = 45) -> tuple[bytes, dict[str, str], str]:
    request = urllib.request.Request(url, headers={
        "User-Agent": "TownCountryAsset-Bahrain-SourceAcquisition/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            if not final_url.startswith("https://"):
                raise BahrainAcquisitionError("API redirect target must remain HTTPS")
            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                raise BahrainAcquisitionError(
                    f"Expected JSON from {url}; received {content_type or 'no content type'}"
                )
            payload = response.read()
            json.loads(payload.decode("utf-8"))
            return payload, {"content_type": content_type}, final_url
    except BahrainAcquisitionError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise BahrainAcquisitionError(f"Cannot retrieve Bahrain API URL {url}: {exc}") from exc


def _json_payload(response: tuple[bytes, dict[str, str], str], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(response[0].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BahrainAcquisitionError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise BahrainAcquisitionError(f"{label} must be a JSON object")
    return payload


def _registry_contract(registry_path: Path) -> dict[str, Any]:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        source = registry["sources"][SOURCE_ID]
        api = source["api"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise BahrainAcquisitionError(
            f"Cannot load the registered Bahrain source contract: {exc}"
        ) from exc
    if api.get("dataset_id") != DATASET_ID or api.get("base_url") != API_BASE:
        raise BahrainAcquisitionError("Bahrain API settings differ from the central source registry")
    return {"source": source, "api": api}


def acquire_snapshot(
    raw_root: Path | None = None,
    manifest_root: Path | None = None,
    registry_path: Path | None = None,
    request_json: Callable[[str, int], tuple[bytes, dict[str, str], str]] = _request_json,
    now: datetime | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    """Fetch metadata and every record page, then write one immutable snapshot."""
    raw_root = raw_root or ROOT / "raw_data" / "sources"
    manifest_root = manifest_root or ROOT / "data_manifests" / "sources"
    registry_path = registry_path or ROOT / "config" / "data_sources.json"
    contract = _registry_contract(registry_path)
    api = contract["api"]
    page_size = int(api.get("page_size", PAGE_SIZE))
    if not 1 <= page_size <= 100:
        raise BahrainAcquisitionError("Configured API page size must be between 1 and 100")

    base = api["base_url"].rstrip("/") + "/" + DATASET_ID
    metadata_response = request_json(base, timeout)
    metadata = _json_payload(metadata_response, "Dataset metadata")
    returned_id = metadata.get("dataset_id") or metadata.get("dataset", {}).get("dataset_id")
    if returned_id is not None and returned_id != DATASET_ID:
        raise BahrainAcquisitionError(f"Unexpected dataset metadata identity: {returned_id}")

    pages: list[tuple[bytes, dict[str, str], str]] = []
    total_count: int | None = None
    offset = 0
    while total_count is None or offset < total_count:
        query = urllib.parse.urlencode({"limit": page_size, "offset": offset})
        response = request_json(f"{base}/records?{query}", timeout)
        payload = _json_payload(response, f"Records page at offset {offset}")
        if not isinstance(payload.get("results"), list) or not isinstance(payload.get("total_count"), int):
            raise BahrainAcquisitionError("Records response lacks integer total_count or results array")
        if total_count is None:
            total_count = payload["total_count"]
            if total_count < 1:
                raise BahrainAcquisitionError("Bahrain annual unemployment dataset returned no records")
        elif payload["total_count"] != total_count:
            raise BahrainAcquisitionError("Dataset total_count changed during paginated acquisition")
        records = payload["results"]
        if not records:
            raise BahrainAcquisitionError(f"Empty records page before reaching total_count={total_count}")
        pages.append(response)
        offset += len(records)
        if len(records) > page_size or offset > total_count:
            raise BahrainAcquisitionError("Records page exceeds the requested pagination bounds")
    if offset != total_count:
        raise BahrainAcquisitionError(f"Retrieved {offset} records but API reports {total_count}")

    retrieved = now or datetime.now(timezone.utc)
    if retrieved.tzinfo is None:
        raise BahrainAcquisitionError("Snapshot timestamp must be timezone-aware")
    stamp = retrieved.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = raw_root / SOURCE_ID / DOWNLOAD_ID / stamp
    manifest_dir = manifest_root / SOURCE_ID / DOWNLOAD_ID
    manifest_path = manifest_dir / f"{stamp}.json"
    if raw_dir.exists() or manifest_path.exists():
        raise BahrainAcquisitionError(f"Refusing to overwrite existing snapshot {stamp}")

    files = []
    payloads = [("dataset_metadata.json", metadata_response), *[
        (f"records_page_{index:04d}.json", response)
        for index, response in enumerate(pages, start=1)
    ]]
    try:
        raw_dir.mkdir(parents=True, exist_ok=False)
        manifest_dir.mkdir(parents=True, exist_ok=True)
        for filename, response in payloads:
            body, headers, final_url = response
            path = raw_dir / filename
            with path.open("xb") as stream:
                stream.write(body)
            files.append({
                "filename": filename,
                "url": base if filename == "dataset_metadata.json" else f"{base}/records",
                "final_url": final_url,
                "content_type": headers.get("content_type"),
                "byte_count": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "local_raw_path": path.relative_to(ROOT).as_posix()
                if path.is_relative_to(ROOT) else str(path),
            })
        meta = metadata.get("metas", {}) if isinstance(metadata.get("metas"), dict) else {}
        manifest = {
            "manifest_schema_version": 1,
            "source_id": SOURCE_ID,
            "source_name": contract["source"]["name"],
            "download_id": DOWNLOAD_ID,
            "release": stamp,
            "release_kind": "rolling",
            "release_discovery_mode": "rolling_url",
            "dataset_id": DATASET_ID,
            "source_url": contract["source"].get("homepage_url"),
            "api_base_url": API_BASE,
            "retrieved_at": retrieved.astimezone(timezone.utc).isoformat(),
            "dataset_metadata_processed": meta.get("metadata_processed"),
            "dataset_data_processed": meta.get("data_processed"),
            "total_record_count": total_count,
            "page_size": page_size,
            "page_count": len(pages),
            "files": files,
            "license_status": contract["source"].get("license_status"),
            "terms_url": contract["source"].get("terms_url"),
            "attribution": contract["source"].get("attribution"),
            "side_effects": {
                "database_written": False,
                "source_selection_policy_changed": False,
                "release_promoted": False,
                "observations_normalized": False,
            },
        }
        with manifest_path.open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except Exception:
        shutil.rmtree(raw_dir, ignore_errors=True)
        manifest_path.unlink(missing_ok=True)
        raise
    return {"manifest_path": str(manifest_path), "raw_directory": str(raw_dir), **manifest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=45, help="HTTP timeout in seconds")
    args = parser.parse_args(argv)
    try:
        result = acquire_snapshot(timeout=args.timeout)
    except (BahrainAcquisitionError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Source: {result['source_id']}/{result['download_id']}")
    print(f"Records: {result['total_record_count']}")
    print(f"Pages: {result['page_count']}")
    print(f"Retrieved: {result['retrieved_at']}")
    print(f"Raw data: {result['raw_directory']}")
    print(f"Manifest: {result['manifest_path']}")
    print("Database writes: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
