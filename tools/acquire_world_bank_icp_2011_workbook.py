"""Acquire the official original ICP 2011 results workbook without transformation.

The workbook is preserved byte-for-byte with a release-scoped manifest. Inspection
is performed separately by tools.assess_world_bank_icp_exports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from io import BytesIO
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "world_bank_icp"
RELEASE = "icp_2011_cycle"
DATASET_ID = "world_bank_icp_2011_original_results"
SOURCE_URL = (
    "https://pubdocs.worldbank.org/en/108821487172249299/"
    "2011-International-Comparison-Program-results.xlsx"
)
CATALOGUE_URL = "https://www.worldbank.org/en/programs/icp/data"
RAW_BASE = Path("raw_data/sources/world_bank_icp") / RELEASE
MANIFEST_BASE = Path("data_manifests/sources/world_bank_icp") / RELEASE
REPORT_BASE = Path("reports/sources/world-bank-icp")


class ICPWorkbookError(RuntimeError):
    """Original ICP workbook acquisition or integrity failure."""


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def request_get(url: str, *, timeout: int = 180, retries: int = 5,
                retry_delay: float = 2.0) -> tuple[bytes, int, dict[str, str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": "TownCountryAsset/1.0"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.status, dict(response.headers.items()), response.geturl()
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt >= retries:
                raise ICPWorkbookError(f"HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt >= retries:
                raise ICPWorkbookError(f"Request failed for {url}: {exc}") from exc
        time.sleep(retry_delay * (2 ** attempt))
    raise ICPWorkbookError(f"Request failed for {url}")


def acquire_workbook(*, repository_root: str | Path = ROOT,
                     retrieved_at: datetime | None = None, timeout: int = 180,
                     retries: int = 5, retry_delay: float = 2.0,
                     get: Callable[..., tuple[bytes, int, dict[str, str], str]] | None = None
                     ) -> dict[str, Any]:
    if timeout < 1 or retries < 0 or retry_delay < 0:
        raise ValueError("Invalid timeout or retry configuration")
    stamp = retrieved_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    root = Path(repository_root).resolve()
    acquisition_id = "icp_2011_workbook_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = root / RAW_BASE / acquisition_id
    manifest_path = root / MANIFEST_BASE / f"{acquisition_id}.json"
    report_dir = root / REPORT_BASE / acquisition_id
    if raw_dir.exists() or manifest_path.exists() or report_dir.exists():
        raise ICPWorkbookError(f"Acquisition already exists: {acquisition_id}")
    fetch = get or (lambda url, **kwargs: request_get(url, **kwargs))
    body, status, headers, final_url = fetch(
        SOURCE_URL, timeout=timeout, retries=retries, retry_delay=retry_delay
    )
    if status != 200 or not body:
        raise ICPWorkbookError(f"Workbook download failed: HTTP {status}, {len(body)} bytes")
    if not body.startswith(b"PK\x03\x04"):
        raise ICPWorkbookError("Provider response does not have an XLSX ZIP signature")
    try:
        with ZipFile(BytesIO(body)) as workbook:
            bad = workbook.testzip()
            if bad is not None:
                raise ICPWorkbookError(f"Workbook ZIP CRC validation failed for {bad}")
            required = {"[Content_Types].xml", "xl/workbook.xml"}
            missing = required - set(workbook.namelist())
            if missing:
                raise ICPWorkbookError("XLSX package missing required parts: " + ", ".join(sorted(missing)))
    except BadZipFile as exc:
        raise ICPWorkbookError("Provider response is not a valid XLSX package") from exc
    raw_dir.mkdir(parents=True, exist_ok=False)
    path = raw_dir / "2011-International-Comparison-Program-results.xlsx"
    with path.open("xb") as stream:
        stream.write(body)
    completed = datetime.now(timezone.utc)
    artifact = {
        "artifact_role": "original_provider_workbook",
        "local_raw_path": path.relative_to(root).as_posix(),
        "source_filename": path.name,
        "url": SOURCE_URL, "final_url": final_url, "http_status": status,
        "content_type": headers.get("Content-Type", ""),
        "byte_count": len(body), "sha256": sha256(body),
        "xlsx_package_validation": "passed",
    }
    manifest = {
        "manifest_schema_version": 1, "source_id": SOURCE_ID,
        "dataset_id": DATASET_ID, "release": RELEASE,
        "release_kind": "original_benchmark_release",
        "release_semantics": "Original ICP 2011 results workbook; distinct from revised 2011 results in the ICP 2017 cycle.",
        "acquisition_id": acquisition_id, "source_url": SOURCE_URL,
        "catalogue_url": CATALOGUE_URL, "retrieved_at": completed.isoformat(),
        "http_status": status, "final_url": final_url,
        "archive_byte_count": len(body), "archive_sha256": sha256(body),
        "xlsx_package_validation": "passed", "files": [artifact],
        "interpretation_status": "Not assessed; source workbook structure and series semantics require inspection.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    report = {
        "assessment": "world_bank_icp_2011_original_workbook_acquisition",
        "acquisition_id": acquisition_id,
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "workbook_bytes": len(body), "workbook_sha256": sha256(body),
        "xlsx_package_validation": "passed", "retrieved_at": completed.isoformat(),
        "side_effects": {
            "raw_workbook_acquired": True, "manifest_written": True,
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
        result = acquire_workbook(repository_root=args.root, timeout=args.timeout,
                                  retries=args.retries, retry_delay=args.retry_delay)
    except (ICPWorkbookError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
