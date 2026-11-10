"""Acquire the official World Bank ICP 2017 CSV archive.

The archive is a complete provider-published bundle (data, country metadata and
series metadata). This tool preserves the original ZIP and extracted CSV members;
it does not interpret observations or change source selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "world_bank_icp"
DATASET_ID = "0038406"
RELEASE = "icp_2017_cycle"
ARCHIVE_URL = "https://databankfiles.worldbank.org/public/ddpext_download/ICP_2017_csv.zip"
CATALOGUE_URL = "https://datacatalog.worldbank.org/search/dataset/0038406"
RAW_BASE = Path("raw_data/sources/world_bank_icp") / RELEASE
MANIFEST_BASE = Path("data_manifests/sources/world_bank_icp") / RELEASE
REPORT_BASE = Path("reports/sources/world-bank-icp")
EXPECTED_MEMBERS = {
    "ICP_2017_Data.csv": "observations",
    "ICP_2017_Country-Metadata.csv": "country_metadata",
    "ICP_2017_Series-Metadata.csv": "series_metadata",
}


class ICPArchiveError(RuntimeError):
    """Official ICP archive acquisition or integrity failure."""


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _request(url: str, *, timeout: int = 180, retries: int = 5,
             retry_delay: float = 2.0) -> tuple[bytes, int, dict[str, str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": "TownCountryAsset/1.0"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.status, dict(response.headers.items()), response.geturl()
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt >= retries:
                raise ICPArchiveError(f"HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt >= retries:
                raise ICPArchiveError(f"Request failed for {url}: {exc}") from exc
        time.sleep(retry_delay * (2 ** attempt))
    raise ICPArchiveError(f"Request failed for {url}")


def _write_exclusive(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(body)
    except FileExistsError as exc:
        raise ICPArchiveError(f"Refusing to overwrite existing artifact: {path}") from exc


def acquire_archive(*, repository_root: str | Path = ROOT,
                    retrieved_at: datetime | None = None, timeout: int = 180,
                    retries: int = 5, retry_delay: float = 2.0,
                    request_get: Callable[..., tuple[bytes, int, dict[str, str], str]] | None = None
                    ) -> dict[str, Any]:
    if timeout < 1 or retries < 0 or retry_delay < 0:
        raise ValueError("Invalid timeout or retry configuration")
    stamp = retrieved_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    root = Path(repository_root).resolve()
    acquisition_id = "icp_2017_archive_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = root / RAW_BASE / acquisition_id
    manifest_path = root / MANIFEST_BASE / f"{acquisition_id}.json"
    report_dir = root / REPORT_BASE / acquisition_id
    if raw_dir.exists() or manifest_path.exists() or report_dir.exists():
        raise ICPArchiveError(f"Acquisition already exists: {acquisition_id}")

    get = request_get or (lambda url, **kwargs: _request(url, **kwargs))
    archive, status, headers, final_url = get(
        ARCHIVE_URL, timeout=timeout, retries=retries, retry_delay=retry_delay
    )
    if status != 200 or not archive:
        raise ICPArchiveError(f"Archive download failed: HTTP {status}, {len(archive)} bytes")
    if not zipfile.is_zipfile(BytesIO(archive)):
        raise ICPArchiveError("Provider response is not a ZIP archive")

    with zipfile.ZipFile(BytesIO(archive)) as zipped:
        bad_member = zipped.testzip()
        if bad_member is not None:
            raise ICPArchiveError(f"ZIP CRC validation failed for {bad_member}")
        files = [item for item in zipped.infolist() if not item.is_dir()]
        by_basename = {Path(item.filename.replace("\\", "/")).name: item for item in files}
        missing = sorted(set(EXPECTED_MEMBERS) - set(by_basename))
        if missing:
            raise ICPArchiveError("Archive is missing required members: " + ", ".join(missing))
        if len(files) != len(EXPECTED_MEMBERS):
            raise ICPArchiveError(
                f"Unexpected archive member count: expected {len(EXPECTED_MEMBERS)}, found {len(files)}"
            )
        for item in files:
            path = Path(item.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise ICPArchiveError(f"Unsafe ZIP member path: {item.filename}")
            if item.file_size <= 0:
                raise ICPArchiveError(f"Empty required archive member: {item.filename}")

    raw_dir.mkdir(parents=True, exist_ok=False)
    archive_path = raw_dir / "ICP_2017_csv.zip"
    _write_exclusive(archive_path, archive)
    artifacts: list[dict[str, Any]] = [{
        "artifact_role": "original_export_archive",
        "local_raw_path": archive_path.relative_to(root).as_posix(),
        "source_filename": "ICP_2017_csv.zip",
        "url": ARCHIVE_URL, "final_url": final_url, "http_status": status,
        "content_type": headers.get("Content-Type", "application/zip"),
        "byte_count": len(archive), "sha256": _sha256(archive),
    }]
    with zipfile.ZipFile(BytesIO(archive)) as zipped:
        by_basename = {Path(item.filename.replace("\\", "/")).name: item
                       for item in zipped.infolist() if not item.is_dir()}
        for filename, role in EXPECTED_MEMBERS.items():
            body = zipped.read(by_basename[filename])
            target = raw_dir / "contents" / filename
            _write_exclusive(target, body)
            artifacts.append({
                "artifact_role": role, "archive_member": by_basename[filename].filename,
                "derived_from": archive_path.relative_to(root).as_posix(),
                "local_raw_path": target.relative_to(root).as_posix(),
                "byte_count": len(body), "sha256": _sha256(body),
            })

    completed = datetime.now(timezone.utc)
    manifest = {
        "manifest_schema_version": 1,
        "source_id": SOURCE_ID,
        "dataset_id": DATASET_ID,
        "release": RELEASE,
        "release_kind": "edition_or_snapshot",
        "release_semantics": "Official ICP 2017 cycle archive; contains 2011-2017 annual observations and source metadata. Original/revised benchmark and annual-series status require separate interpretation.",
        "provider_dataset_id": DATASET_ID,
        "acquisition_id": acquisition_id,
        "source_url": ARCHIVE_URL,
        "catalogue_url": CATALOGUE_URL,
        "retrieved_at": completed.isoformat(),
        "http_status": status,
        "final_url": final_url,
        "archive_byte_count": len(archive),
        "archive_sha256": _sha256(archive),
        "zip_crc_validation": "passed",
        "required_members": list(EXPECTED_MEMBERS),
        "capture_scope": {
            "observation_year_columns": list(range(2011, 2018)),
            "includes_country_metadata": True,
            "includes_series_metadata": True,
            "interpretation_status": "Not assessed; do not infer benchmark/interpolation status from year columns alone.",
        },
        "files": artifacts,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    report = {
        "assessment": "world_bank_icp_2017_archive_acquisition",
        "acquisition_id": acquisition_id,
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "archive_bytes": len(archive),
        "archive_sha256": _sha256(archive),
        "zip_crc_validation": "passed",
        "member_count": len(EXPECTED_MEMBERS),
        "artifact_count": len(artifacts),
        "retrieved_at": completed.isoformat(),
        "side_effects": {
            "raw_archive_acquired": True, "manifest_written": True,
            "project_database_written": False, "game_database_written": False,
            "semantic_validation_performed": False, "approval_created": False,
            "source_selection_changed": False, "retention_applied": False,
        },
    }
    report_dir.mkdir(parents=True, exist_ok=False)
    with (report_dir / "assessment.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        result = acquire_archive(repository_root=args.root, timeout=args.timeout,
                                 retries=args.retries, retry_delay=args.retry_delay)
    except (ICPArchiveError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
