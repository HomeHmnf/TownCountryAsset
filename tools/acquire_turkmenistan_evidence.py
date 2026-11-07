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
        "filename": "IMF_WP_2023_207_Turkmenistan_GDP.pdf",
        "format": "pdf",
        "signature": "pdf",
        "raw_path": "raw_data/sources/imf_turkmenistan_research/gdp_statistical_shortcomings_wp_2023_207/IMF_WP_2023_207_Turkmenistan_GDP.pdf",
        "manifest_dir": "data_manifests/sources/imf_turkmenistan_research/gdp_statistical_shortcomings_wp_2023_207",
    },
    {
        "source_id": "turkmenistan_state_statistics",
        "dataset_id": "national_accounts_methodology_2025",
        "release": "turkmenstat-national-accounts-methodology-2025-01",
        "publication_date": "2025-01-17",
        "url": "https://editor.stat.gov.tm/en/news/204",
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
        "url": "https://editor.stat.gov.tm/en/news/359",
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
