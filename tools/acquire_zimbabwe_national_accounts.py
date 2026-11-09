"""Acquire the two reviewed ZIMSTAT national-accounts workbooks."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.database.connection import REPOSITORY_ROOT

PUBLICATIONS = (
    {
        "source_id": "zimstat", "dataset_id": "gdp_trends_2009_2018",
        "release": "gdp-trends-2009-2018", "publication_date": "2019",
        "url": "https://www.zimstat.co.zw/wp-content/uploads/Macro/NationalAccounts/Publications/GDP_Trends_2009to2018.xls",
        "filename": "GDP_Trends_2009to2018.xls", "format": "xls", "signature": "xls",
        "raw_path": "raw_data/sources/zimstat/gdp_trends_2009_2018/GDP_Trends_2009to2018.xls",
        "manifest_dir": "data_manifests/sources/zimstat/gdp_trends_2009_2018",
    },
    {
        "source_id": "zimstat", "dataset_id": "gdp_tables_2019_2024",
        "release": "revised-gdp-tables-2019-2024-june-2025", "publication_date": "2025-06-27",
        "url": "https://www.zimstat.co.zw/wp-content/uploads/Macro/NationalAccounts/2025/GDP_Tables_2019_2024_June.xlsx",
        "filename": "GDP_Tables_2019_2024_June.xlsx", "format": "xlsx", "signature": "xlsx",
        "raw_path": "raw_data/sources/zimstat/gdp_tables_2019_2024/GDP_Tables_2019_2024_June.xlsx",
        "manifest_dir": "data_manifests/sources/zimstat/gdp_tables_2019_2024",
    },
)
XLS_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate(path: Path, signature: str) -> None:
    prefix = path.read_bytes()[:8]
    if signature == "xls":
        if prefix != XLS_SIGNATURE:
            raise ValueError(f"Response is not an OLE XLS workbook: {path}")
    elif signature == "xlsx":
        if not prefix.startswith(b"PK\x03\x04"):
            raise ValueError(f"Response is not an OOXML ZIP workbook: {path}")
        try:
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
                if bad_member is not None or "xl/workbook.xml" not in archive.namelist():
                    raise ValueError(f"Invalid XLSX workbook structure: {path}")
        except zipfile.BadZipFile as exc:
            raise ValueError(f"Response is not a valid XLSX ZIP archive: {path}") from exc
    else:
        raise ValueError(f"Unsupported workbook signature: {signature}")


def _completed_acquisition(root: Path, publication: dict[str, Any], raw: Path, manifest_dir: Path) -> dict[str, Any] | None:
    manifests = sorted(manifest_dir.glob("*.json")) if manifest_dir.exists() else []
    if not manifests:
        if raw.exists():
            raise FileExistsError(f"Raw workbook exists without a manifest; refusing to overwrite: {raw}")
        return None
    if not raw.is_file():
        raise FileNotFoundError(f"Existing manifest has no raw workbook: {publication['raw_path']}")
    _validate(raw, publication["signature"])
    digest, byte_count = _sha256(raw), raw.stat().st_size
    verified = []
    for manifest_path in manifests:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = payload.get("files", [])
        if (payload.get("source_id") != publication["source_id"]
            or payload.get("download_id") != publication["dataset_id"]
            or len(files) != 1
            or files[0].get("local_raw_path") != publication["raw_path"]
            or files[0].get("sha256") != digest
            or files[0].get("byte_count") != byte_count):
            raise ValueError(f"Existing manifest does not match current workbook: {manifest_path}")
        verified.append({"manifest_path": manifest_path.relative_to(root).as_posix(),
                         "retrieved_at": payload.get("retrieved_at"),
                         "sha256": digest, "byte_count": byte_count})
    return {"dataset_id": publication["dataset_id"], "raw_path": publication["raw_path"],
            "existing_acquisitions": verified, "status": "already_acquired_verified"}


def _curl_download(url: str, destination: Path, *, timeout: float, retries: int,
                   socks5_proxy: str | None) -> tuple[str, str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    command = ["curl", "-fL", "--silent", "--show-error", "--retry", str(retries),
               "--retry-connrefused", "--connect-timeout", "30", "--max-time", str(int(timeout)),
               "--output", str(temporary), "--write-out", "%{url_effective}\n%{content_type}\n%{http_code}"]
    if socks5_proxy:
        command[1:1] = ["--socks5-hostname", socks5_proxy]
    command.append(url)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(completed.stderr.strip() or f"curl exit status {completed.returncode}")
    parts = completed.stdout.strip().splitlines()
    if len(parts) != 3 or parts[2] != "200":
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Unexpected curl response metadata for {url}: {completed.stdout!r}")
    temporary.replace(destination)
    return parts[0], parts[1] or "application/octet-stream", destination.stat().st_size


def acquire_zimbabwe_national_accounts(*, repository_root: str | Path = REPOSITORY_ROOT,
    timeout: float = 120, retries: int = 3, socks5_proxy: str | None = None) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    acquired, skipped, failures = [], [], []
    for publication in PUBLICATIONS:
        raw, manifest_dir = root / publication["raw_path"], root / publication["manifest_dir"]
        prior = _completed_acquisition(root, publication, raw, manifest_dir)
        if prior is not None:
            skipped.append(prior)
            continue
        try:
            final_url, content_type, byte_count = _curl_download(
                publication["url"], raw, timeout=timeout, retries=retries, socks5_proxy=socks5_proxy)
            _validate(raw, publication["signature"])
        except (RuntimeError, ValueError, OSError) as exc:
            raw.with_name(raw.name + ".part").unlink(missing_ok=True)
            raw.unlink(missing_ok=True)
            failures.append({"dataset_id": publication["dataset_id"], "requested_url": publication["url"],
                             "error": str(exc), "status": "acquisition_failed_no_manifest"})
            continue
        retrieved_at = datetime.now().astimezone().isoformat()
        timestamp_id = datetime.fromisoformat(retrieved_at).astimezone().strftime("%Y%m%dT%H%M%S%f%z")
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f"{timestamp_id}.json"
        if manifest_path.exists():
            raise FileExistsError(f"Refusing to overwrite acquisition manifest: {manifest_path}")
        digest = _sha256(raw)
        manifest = {
            "manifest_schema_version": 1, "source_id": publication["source_id"],
            "download_id": publication["dataset_id"], "release": publication["release"],
            "release_kind": "edition_or_snapshot", "publication_date": publication["publication_date"],
            "retrieved_at": retrieved_at, "retrieval_timestamp_basis": "acquisition_tool_download_completion",
            "acquisition_method": "automated_https_download",
            "files": [{"file_id": publication["filename"], "filename": publication["filename"],
                       "local_raw_path": publication["raw_path"], "url": final_url,
                       "requested_url": publication["url"], "final_url": final_url,
                       "content_type": content_type, "format": publication["format"],
                       "byte_count": byte_count, "sha256": digest}],
            "validation": {"format_signature_verified": True,
                           "workbook_container_integrity_verified": publication["signature"] == "xlsx",
                           "byte_count_verified": True, "sha256_calculated": True,
                           "statistical_content_reviewed": False},
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        acquired.append({"dataset_id": publication["dataset_id"], "raw_path": publication["raw_path"],
                         "manifest_path": manifest_path.relative_to(root).as_posix(),
                         "retrieved_at": retrieved_at, "byte_count": byte_count,
                         "sha256": digest, "final_url": final_url})
    return {"acquisition_count": len(acquired), "acquisitions": acquired,
            "skipped_existing_count": len(skipped), "skipped_existing": skipped,
            "failure_count": len(failures), "failures": failures,
            "project_database_written": False, "game_database_written": False,
            "semantic_validation": False, "approval_or_promotion": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--socks5-proxy", default=None,
                        help="Optional SOCKS5 proxy host:port; DNS is resolved through the proxy.")
    args = parser.parse_args()
    result = acquire_zimbabwe_national_accounts(repository_root=args.root, timeout=args.timeout,
        retries=args.retries, socks5_proxy=args.socks5_proxy)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
