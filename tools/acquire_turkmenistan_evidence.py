"""Acquire primary Turkmenistan national-accounts, exchange-rate and statistical-reform evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.database.connection import REPOSITORY_ROOT

PUBLICATIONS = (
    {
        "source_id": "imf_turkmenistan_research",
        "dataset_id": "gdp_statistical_shortcomings_wp_2023_207",
        "release": "imf-wp-2023-207",
        "publication_date": "2023-09-29",
        "url": "https://www.imf.org/-/media/files/publications/wp/2023/english/wpiea2023207-print-pdf.pdf",
        "url_fallbacks": [
            "https://www.elibrary.imf.org/downloadpdf/journals/001/2023/207/article-A001-en.pdf",
            "https://www.elibrary.imf.org/view/journals/001/2023/207/article-A001-en.xml",
        ],
        "filename": "IMF_WP_2023_207_Turkmenistan_GDP.xml",
        "format": "xml",
        "signature": "xml",
        "raw_path": "raw_data/sources/imf_turkmenistan_research/gdp_statistical_shortcomings_wp_2023_207/IMF_WP_2023_207_Turkmenistan_GDP.xml",
        "manifest_dir": "data_manifests/sources/imf_turkmenistan_research/gdp_statistical_shortcomings_wp_2023_207",
    },
    {
        "source_id": "turkmenistan_state_statistics",
        "dataset_id": "national_accounts_methodology_2025",
        "release": "turkmenstat-national-accounts-methodology-2025-01",
        "publication_date": "2025-01-17",
        "url": "https://www.stat.gov.tm/en/news/204",
        "filename": "TurkmenStat_national_accounts_methodology_2025-01-17.html",
        "format": "html",
        "signature": "html",
        "raw_path": "raw_data/sources/turkmenistan_state_statistics/national_accounts_methodology_2025/TurkmenStat_national_accounts_methodology_2025-01-17.html",
        "manifest_dir": "data_manifests/sources/turkmenistan_state_statistics/national_accounts_methodology_2025",
    },
    {
        "source_id": "turkmenistan_state_statistics",
        "dataset_id": "statistical_system_reform_2026",
        "release": "turkmenstat-statistical-system-reform-2026-06",
        "publication_date": "2026-06-23",
        "url": "https://www.stat.gov.tm/en/news/359",
        "filename": "TurkmenStat_statistical_system_reform_2026-06-23.html",
        "format": "html",
        "signature": "html",
        "raw_path": "raw_data/sources/turkmenistan_state_statistics/statistical_system_reform_2026/TurkmenStat_statistical_system_reform_2026-06-23.html",
        "manifest_dir": "data_manifests/sources/turkmenistan_state_statistics/statistical_system_reform_2026",
    },
    {
        "source_id": "imf_turkmenistan_research",
        "dataset_id": "article_iv_mission_2025",
        "release": "imf-turkmenistan-article-iv-mission-2025-06",
        "publication_date": "2025-06-10",
        "url": "https://www.imf.org/en/news/articles/2025/06/10/pr-25190-turkmenistan-imf-completes-2025-article-iv-mission",
        "filename": "IMF_Turkmenistan_Article_IV_Mission_2025-06-10.html",
        "format": "html",
        "signature": "html",
        "raw_path": "raw_data/sources/imf_turkmenistan_research/article_iv_mission_2025/IMF_Turkmenistan_Article_IV_Mission_2025-06-10.html",
        "manifest_dir": "data_manifests/sources/imf_turkmenistan_research/article_iv_mission_2025",
    },
    {
        "source_id": "imf_turkmenistan_research",
        "dataset_id": "article_iv_mission_2026",
        "release": "imf-turkmenistan-article-iv-mission-2026-06",
        "publication_date": "2026-06-22",
        "url": "https://www.imf.org/en/news/articles/2026/06/22/pr26218-turkmenistan-imf-staff-completes-2026-article-iv-mission",
        "filename": "IMF_Turkmenistan_Article_IV_Mission_2026-06-22.html",
        "format": "html",
        "signature": "html",
        "raw_path": "raw_data/sources/imf_turkmenistan_research/article_iv_mission_2026/IMF_Turkmenistan_Article_IV_Mission_2026-06-22.html",
        "manifest_dir": "data_manifests/sources/imf_turkmenistan_research/article_iv_mission_2026",
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate(path: Path, signature: str) -> None:
    prefix = path.read_bytes()[:8192].lstrip().lower()
    if signature == "pdf" and not prefix.startswith(b"%pdf-"):
        raise ValueError(f"Response is not a PDF: {path}")
    if signature == "html" and not (
        b"<html" in prefix or b"<!doctype html" in prefix
    ):
        raise ValueError(f"Response is not an HTML document: {path}")
    if signature == "xml" and not (
        prefix.startswith(b"<?xml")
        or prefix.startswith(b"<!doctype html")
        or b"<html" in prefix
        or b"<article" in prefix
    ):
        raise ValueError(f"Response is not an XML document: {path}")


def _download(
    urls: tuple[str, ...] | list[str],
    destination: Path,
    signature: str,
    timeout: float,
    retries: int,
) -> tuple[str, str, int]:
    """Try the canonical URL and documented publisher alternatives in order."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for url in urls:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                request = Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; TownCountryAsset/1.0)",
                        "Accept": "application/pdf,text/html,*/*",
                    },
                )
                with urlopen(request, timeout=timeout) as response:
                    body = response.read()
                    final_url = response.geturl()
                    status = response.status
                    content_type = response.headers.get_content_type()
                if status != 200:
                    raise ValueError(f"Unexpected HTTP status {status}: {url}")
                temporary = destination.with_name(destination.name + ".part")
                temporary.write_bytes(body)
                try:
                    _validate(temporary, signature)
                except ValueError:
                    temporary.unlink(missing_ok=True)
                    raise
                temporary.replace(destination)
                return final_url, content_type, len(body)
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                    break
            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc
            except ValueError as exc:
                last_error = exc
                break
            if attempt < retries:
                time.sleep(min(2**attempt, 16))
        failures.append(f"{url}: {last_error}")
    raise RuntimeError(
        "All publisher URL candidates failed: " + " | ".join(failures)
    )



def acquire_turkmenistan_evidence(
    *,
    repository_root: str | Path = REPOSITORY_ROOT,
    use_existing: bool = False,
    timeout: float = 120,
    retries: int = 3,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    results = []
    for publication in PUBLICATIONS:
        raw = root / publication["raw_path"]
        manifest_dir = root / publication["manifest_dir"]
        if use_existing:
            if not raw.is_file():
                raise FileNotFoundError(
                    f"Expected existing artifact: {publication['raw_path']}"
                )
            _validate(raw, publication["signature"])
            final_url = publication["url"]
            content_type = {
                "pdf": "application/pdf",
                "html": "text/html",
                "xml": "application/xml",
            }[publication["format"]]
            byte_count = raw.stat().st_size
            retrieved_at = datetime.fromtimestamp(
                raw.stat().st_mtime
            ).astimezone().isoformat()
            timestamp_basis = "filesystem_mtime_existing_manual_download"
        else:
            candidate_urls = [
                publication["url"],
                *publication.get("url_fallbacks", []),
            ]
            final_url, content_type, byte_count = _download(
                candidate_urls, raw, publication["signature"], timeout, retries
            )
            _validate(raw, publication["signature"])
            retrieved_at = datetime.now().astimezone().isoformat()
            timestamp_basis = "acquisition_tool_download_completion"

        digest = _sha256(raw)
        timestamp_id = datetime.fromisoformat(retrieved_at).astimezone().strftime(
            "%Y%m%dT%H%M%S%f%z"
        )
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f"{timestamp_id}.json"
        if manifest_path.exists():
            raise FileExistsError(
                f"Refusing to overwrite acquisition manifest: {manifest_path}"
            )
        manifest = {
            "manifest_schema_version": 1,
            "source_id": publication["source_id"],
            "download_id": publication["dataset_id"],
            "release": publication["release"],
            "release_kind": "edition_or_snapshot",
            "publication_date": publication["publication_date"],
            "retrieved_at": retrieved_at,
            "retrieval_timestamp_basis": timestamp_basis,
            "acquisition_method": (
                "automated_https_download"
                if not use_existing
                else "existing_file_integrity_capture"
            ),
            "files": [{
                "file_id": publication["filename"],
                "filename": publication["filename"],
                "local_raw_path": publication["raw_path"],
                "url": final_url,
                "requested_url": publication["url"],
                "final_url": final_url,
                "content_type": content_type,
                "format": publication["format"],
                "byte_count": byte_count,
                "sha256": digest,
            }],
            "validation": {
                "format_signature_verified": True,
                "byte_count_verified": True,
                "sha256_calculated": True,
                "statistical_content_reviewed": False,
            },
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        results.append({
            "source_id": publication["source_id"],
            "dataset_id": publication["dataset_id"],
            "raw_path": publication["raw_path"],
            "manifest_path": manifest_path.relative_to(root).as_posix(),
            "retrieved_at": retrieved_at,
            "timestamp_basis": timestamp_basis,
            "byte_count": byte_count,
            "sha256": digest,
            "final_url": final_url,
        })
    return {
        "acquisition_count": len(results),
        "acquisitions": results,
        "project_database_written": False,
        "game_database_written": False,
        "semantic_validation": False,
        "approval_or_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--use-existing", action="store_true")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(
        acquire_turkmenistan_evidence(
            repository_root=args.root,
            use_existing=args.use_existing,
            timeout=args.timeout,
            retries=args.retries,
        ),
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
