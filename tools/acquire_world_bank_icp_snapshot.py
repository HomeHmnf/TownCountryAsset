"""Acquire the public World Bank ICP 2021 dataset and preserve its resources.

This captures the May 2024 ICP 2021-cycle release, which contains revised 2017
and 2021 benchmark results plus annual PPP series. It does not interpret values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
API = "https://ddh-openapi.worldbank.org"
DATASET_ID = "0066092"
SOURCE_KEY = "world_bank_wdi"
DATASET_KEY = "icp_2021_cycle"
RAW_BASE = Path("raw_data/sources/world_bank_icp/icp_2021_cycle")
MANIFEST_BASE = Path("data_manifests/sources/world_bank_icp/icp_2021_cycle")
REPORT_BASE = Path("reports/sources/world-bank-icp")
DATA_URL = "https://www.worldbank.org/en/programs/icp/data"
CATALOG_URL = "https://datacatalog.worldbank.org/search/dataset/0066092/international-comparison-program-2021"


class ICPSnapshotError(RuntimeError):
    """ICP catalog response or snapshot integrity failure."""


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _request(url: str, *, timeout: int = 120, retries: int = 5,
             retry_delay: float = 2.0) -> tuple[bytes, int, dict[str, str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": "TownCountryAsset/1.0"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                return body, response.status, dict(response.headers.items()), response.geturl()
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt >= retries:
                raise ICPSnapshotError(f"HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt >= retries:
                raise ICPSnapshotError(f"Request failed for {url}: {exc}") from exc
        time.sleep(retry_delay * (2 ** attempt))
    raise ICPSnapshotError(f"Request failed for {url}")


def _json_request(url: str, request_get: Callable[..., tuple[bytes, int, dict[str, str], str]],
                  timeout: int, retries: int, retry_delay: float) -> tuple[dict[str, Any], dict[str, Any]]:
    body, status, headers, final_url = request_get(
        url, timeout=timeout, retries=retries, retry_delay=retry_delay
    )
    if status != 200:
        raise ICPSnapshotError(f"Unexpected HTTP status {status}: {url}")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ICPSnapshotError(f"Expected JSON response from {url}") from exc
    if not isinstance(payload, dict):
        raise ICPSnapshotError(f"Expected JSON object from {url}")
    return payload, {"url": url, "final_url": final_url, "http_status": status,
                     "content_type": headers.get("Content-Type", ""),
                     "byte_count": len(body), "sha256": _hash(body), "body": body}


def _write_exclusive(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(body)
    except FileExistsError as exc:
        raise ICPSnapshotError(f"Refusing to overwrite existing artifact: {path}") from exc


def _safe_name(value: str, fallback: str) -> str:
    name = Path(value.replace("\\", "/")).name
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return cleaned or fallback


def acquire_snapshot(*, repository_root: str | Path = ROOT,
                     retrieved_at: datetime | None = None, timeout: int = 120,
                     retries: int = 5, retry_delay: float = 2.0,
                     request_get: Callable[..., tuple[bytes, int, dict[str, str], str]] | None = None
                     ) -> dict[str, Any]:
    if timeout < 1 or retries < 0 or retry_delay < 0:
        raise ValueError("Invalid timeout or retry configuration")
    root = Path(repository_root).resolve()
    stamp = retrieved_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    snapshot_id = "icp_2021_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = root / RAW_BASE / snapshot_id
    manifest_path = root / MANIFEST_BASE / f"{snapshot_id}.json"
    if raw_dir.exists() or manifest_path.exists():
        raise ICPSnapshotError(f"Snapshot already exists: {snapshot_id}")
    get = request_get or (lambda url, **kw: _request(url, **kw))
    raw_dir.mkdir(parents=True, exist_ok=False)
    artifacts: list[dict[str, Any]] = []

    dataset_url = f"{API}/datasets/{DATASET_ID}"
    dataset, metadata = _json_request(dataset_url, get, timeout, retries, retry_delay)
    if str(dataset.get("dataset_unique_id") or dataset.get("id") or "") != DATASET_ID:
        raise ICPSnapshotError("Catalog response does not identify ICP dataset 0066092")
    metadata_path = raw_dir / "dataset_metadata.json"
    _write_exclusive(metadata_path, metadata.pop("body"))
    artifacts.append({"artifact_role": "dataset_metadata",
                      "local_raw_path": metadata_path.relative_to(root).as_posix(), **metadata})

    rows: list[dict[str, Any]] = []
    skip = 0
    page_number = 1
    expected_count: int | None = None
    while True:
        resources_url = f"{API}/resources?{urllib.parse.urlencode({'dataset_unique_id': DATASET_ID, 'top': 100, 'skip': skip})}"
        resources_payload, resource_meta = _json_request(resources_url, get, timeout, retries, retry_delay)
        page_rows = resources_payload.get("data")
        if not isinstance(page_rows, list):
            raise ICPSnapshotError("Catalog resource listing has no data array")
        count = resources_payload.get("count")
        if isinstance(count, int):
            if expected_count is not None and count != expected_count:
                raise ICPSnapshotError("Resource listing count changed during pagination")
            expected_count = count
        page_path = raw_dir / f"resource_listing_page_{page_number:03d}.json"
        _write_exclusive(page_path, resource_meta.pop("body"))
        artifacts.append({"artifact_role": "resource_listing",
                          "page_number": page_number,
                          "local_raw_path": page_path.relative_to(root).as_posix(), **resource_meta})
        rows.extend(page_rows)
        if not page_rows or len(page_rows) < 100:
            break
        skip += len(page_rows)
        page_number += 1
        if page_number > 100:
            raise ICPSnapshotError("Resource listing exceeds the 10,000-row safety limit")
    if expected_count is not None and len(rows) != expected_count:
        raise ICPSnapshotError(f"Incomplete resource listing: captured {len(rows)} of {expected_count}")
    if not rows:
        raise ICPSnapshotError("ICP dataset exposes no catalogue resources")
    skipped_resources: list[dict[str, Any]] = []
    downloaded_resources = 0
    for index, resource in enumerate(rows, start=1):
        resource_id = str(resource.get("resource_unique_id") or resource.get("id") or "").strip()
        if not resource_id:
            raise ICPSnapshotError(f"Resource row {index} has no resource identifier")
        title = str(resource.get("title") or resource.get("name") or f"resource_{index}")
        resource_format = str(resource.get("format") or "").strip().upper()
        if resource_format in {"API", "DATABANK", "HTML"} or not resource_format:
            skipped_resources.append({"resource_unique_id": resource_id, "title": title,
                                      "format": resource.get("format"),
                                      "reason": "catalogue navigation/API reference, not a downloadable file"})
            continue
        extension = Path(title).suffix.lower()
        filename = _safe_name(title, f"resource_{index:03d}{extension}")
        url = f"{API}/resources/{urllib.parse.quote(resource_id, safe='')}/download"
        body, status, headers, final_url = get(
            url, timeout=timeout, retries=retries, retry_delay=retry_delay
        )
        if status != 200 or not body:
            raise ICPSnapshotError(f"Resource download failed or empty: {resource_id}")
        if body.lstrip().startswith((b"{", b"[")) and "json" in headers.get("Content-Type", "").lower():
            try:
                error_payload = json.loads(body.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                error_payload = None
            if isinstance(error_payload, dict) and error_payload.get("error"):
                raise ICPSnapshotError(f"Catalog rejected resource {resource_id}: {error_payload}")
        target = raw_dir / "resources" / f"{index:03d}_{filename}"
        _write_exclusive(target, body)
        downloaded_resources += 1
        artifacts.append({
            "artifact_role": "data_resource", "resource_unique_id": resource_id,
            "title": title, "format": resource.get("format"),
            "local_raw_path": target.relative_to(root).as_posix(),
            "url": url, "final_url": final_url, "http_status": status,
            "content_type": headers.get("Content-Type", mimetypes.guess_type(filename)[0] or ""),
            "byte_count": len(body), "sha256": _hash(body),
        })

    completed = datetime.now(timezone.utc)
    manifest = {
        "manifest_schema_version": 1, "source_id": SOURCE_KEY,
        "download_id": DATASET_KEY, "dataset_id": DATASET_ID,
        "release": "icp-2021-cycle-may-2024", "release_kind": "edition_or_snapshot",
        "release_date": "2024-05", "snapshot_id": snapshot_id,
        "retrieved_at": completed.isoformat(), "source_url": DATA_URL,
        "catalogue_url": CATALOG_URL, "catalogue_api_base_url": API,
        "capture_scope": {
            "reference_years": [2017, 2021], "revised_2017_included": True,
            "annual_ppp_years": [2017, 2018, 2019, 2020, 2021],
            "provider_claims": "See retained dataset metadata and official ICP release page.",
        },
        "files": artifacts,
        "non_file_resources_skipped": skipped_resources,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    report = {
        "assessment": "world_bank_icp_2021_release_acquisition",
        "snapshot_id": snapshot_id, "manifest_path": manifest_path.relative_to(root).as_posix(),
        "artifact_count": len(artifacts), "artifact_bytes": sum(x["byte_count"] for x in artifacts),
        "resource_count": len(rows), "downloaded_file_resource_count": downloaded_resources,
        "non_file_resource_count": len(skipped_resources), "retrieved_at": completed.isoformat(),
        "side_effects": {"raw_snapshot_acquired": True, "manifest_written": True,
                         "project_database_written": False, "game_database_written": False,
                         "semantic_validation_performed": False, "approval_created": False,
                         "source_selection_changed": False, "retention_applied": False},
    }
    report_dir = root / REPORT_BASE / snapshot_id
    report_dir.mkdir(parents=True, exist_ok=False)
    with (report_dir / "assessment.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        result = acquire_snapshot(repository_root=args.root, timeout=args.timeout,
                                  retries=args.retries, retry_delay=args.retry_delay)
    except (ICPSnapshotError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
