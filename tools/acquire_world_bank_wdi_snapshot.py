"""Acquire an immutable, byte-preserving World Bank WDI API snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.worldbank.org/v2"
SOURCE_KEY = "world_bank_wdi"
DATASET_KEY = "wdi_selected_macro_indicators"
SOURCE_ID = "2"
START_YEAR, END_YEAR, PER_PAGE = 2015, 2025, 20000
PRIMARY_INDICATORS = (
    "NY.GDP.MKTP.CD", "NY.GDP.PCAP.CD", "NY.GDP.MKTP.PP.CD",
    "FP.CPI.TOTL.ZG", "SL.UEM.TOTL.ZS",
)
DIAGNOSTIC_INDICATORS = ("SL.UEM.TOTL.NE.ZS",)
# Supporting series allow arithmetic decomposition of GDP, PPP, population and CPI.
# They remain diagnostic inputs and do not change the five primary comparison fields.
SUPPORTING_INDICATORS = (
    "NY.GDP.MKTP.CN", "PA.NUS.FCRF", "PA.NUS.ATLS",
    "PA.NUS.PPP", "SP.POP.TOTL", "FP.CPI.TOTL",
)
INDICATORS = PRIMARY_INDICATORS + DIAGNOSTIC_INDICATORS
CAPTURE_INDICATORS = INDICATORS + SUPPORTING_INDICATORS
RAW_BASE = Path("raw_data/sources/world_bank_wdi/wdi_selected_macro_indicators")
MANIFEST_BASE = Path("data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators")
REPORT_BASE = Path("reports/sources/world-bank-wdi-snapshot")
TERMS_URL = "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets"
API_DOCS_URL = "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392"


class SnapshotError(RuntimeError):
    """WDI API response or snapshot-integrity failure."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: str | datetime | None) -> datetime:
    result = _now() if value is None else (
        value if isinstance(value, datetime)
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if result.tzinfo is None or result.utcoffset() is None:
        raise SnapshotError("Timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _request(
    url: str, timeout: int = 120, retries: int = 5, retry_delay: float = 2.0,
) -> tuple[bytes, int, dict[str, str], str]:
    """Fetch one API response with bounded retries for transient transport/server failures."""
    if timeout < 1 or retries < 0 or retry_delay < 0:
        raise SnapshotError("Invalid HTTP retry configuration")
    request = urllib.request.Request(url, headers={
        "User-Agent": "TownCountryAsset-WDI-Snapshot/1.0",
        "Accept": "application/json",
    })
    last_error: Exception | None = None
    attempts_made = 0
    for attempt in range(retries + 1):
        attempts_made = attempt + 1
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = int(response.status)
                if status == 200 and body:
                    return body, status, dict(response.headers.items()), response.geturl()
                last_error = SnapshotError(f"Invalid HTTP response ({status}) or empty body")
                if status not in (408, 425, 429) and status < 500:
                    break
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (408, 425, 429) and exc.code < 500:
                break
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(retry_delay * (2 ** attempt))
    raise SnapshotError(
        f"Cannot retrieve {url} after {attempts_made} attempt(s): {last_error}"
    ) from last_error


def _url(path: str, params: dict[str, str]) -> str:
    return f"{API}/{path}?{urllib.parse.urlencode(params)}"


def _payload(body: bytes, label: str) -> list[Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"{label}: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, list) or len(value) < 2 or not isinstance(value[0], dict) or not isinstance(value[1], list):
        raise SnapshotError(f"{label}: unexpected API response envelope")
    return value


def _save_response(
    root: Path, raw_dir: Path, filename: str, url: str,
    params: dict[str, str], request_get: Callable[[str], tuple[bytes, int, dict[str, str], str]],
    page: int | None = None,
) -> tuple[dict[str, Any], bytes]:
    body, status, headers, final_url = request_get(url)
    if status != 200 or not body:
        raise SnapshotError(f"Invalid HTTP response ({status}) or empty body: {url}")
    destination = raw_dir / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as stream:
            stream.write(body)
    except FileExistsError as exc:
        raise SnapshotError(f"Refusing to overwrite {destination}") from exc
    content_type = next((v for k, v in headers.items() if k.casefold() == "content-type"), "application/json")
    return ({
        "filename": filename,
        "local_raw_path": destination.relative_to(root).as_posix(),
        "content_type": content_type,
        "format": "json",
        "byte_count": len(body),
        "sha256": _hash_bytes(body),
        "url": url,
        "final_url": final_url,
        "http_status": status,
        "retrieved_at": _now().isoformat(),
        "request_parameters": params,
        "response_headers": headers,
        "request_headers": {"User-Agent": "TownCountryAsset-WDI-Snapshot/1.0", "Accept": "application/json"},
        "page_number": page,
    }, body)


def _pages(payload: list[Any], expected_page: int, label: str) -> int:
    try:
        actual_page = int(payload[0].get("page", expected_page))
        pages = int(payload[0].get("pages", 1))
    except (TypeError, ValueError) as exc:
        raise SnapshotError(f"{label}: invalid pagination metadata") from exc
    if actual_page != expected_page or not 1 <= pages <= 1000 or actual_page > pages:
        raise SnapshotError(f"{label}: inconsistent pagination metadata")
    return pages


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise SnapshotError(f"Refusing to overwrite {path}") from exc


def capture_snapshot(
    *, repository_root: str | Path = ROOT, start_year: int = START_YEAR,
    end_year: int = END_YEAR, retrieved_at: str | datetime | None = None,
    request_get: Callable[[str], tuple[bytes, int, dict[str, str], str]] = _request,
) -> dict[str, Any]:
    if start_year < 1900 or end_year < start_year or end_year > 2100:
        raise SnapshotError("Invalid snapshot year range")
    root = Path(repository_root).resolve()
    started = _aware(retrieved_at)
    snapshot_id = "api_snapshot_" + started.strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = root / RAW_BASE / snapshot_id
    manifest_path = root / MANIFEST_BASE / f"{snapshot_id}.json"
    if raw_dir.exists() or manifest_path.exists():
        raise SnapshotError(f"Snapshot already exists: {snapshot_id}")
    raw_dir.mkdir(parents=True, exist_ok=False)
    artifacts: list[dict[str, Any]] = []

    params = {"format": "json"}
    artifact, body = _save_response(
        root, raw_dir, "source_metadata.json", _url("sources/2", params),
        params, request_get,
    )
    artifacts.append(artifact)
    source_payload = _payload(body, "WDI source metadata")
    if not any(str(row.get("id")) == SOURCE_ID and row.get("name") == "World Development Indicators"
               for row in source_payload[1]):
        raise SnapshotError("API source ID 2 is not World Development Indicators")

    country_rows: list[dict[str, Any]] = []
    country_page_count = None
    page = 1
    while True:
        params = {"format": "json", "per_page": "400", "page": str(page)}
        artifact, body = _save_response(
            root, raw_dir, f"country_metadata_page_{page:03d}.json",
            _url("country", params), params, request_get, page,
        )
        payload = _payload(body, f"country metadata page {page}")
        pages = _pages(payload, page, "country metadata")
        if country_page_count is not None and pages != country_page_count:
            raise SnapshotError("Country metadata pagination changed during capture")
        country_page_count = pages
        artifact["page_count"] = pages
        artifact["row_count"] = len(payload[1])
        artifacts.append(artifact)
        country_rows.extend(payload[1])
        if page == pages:
            break
        page += 1
    if not country_rows:
        raise SnapshotError("Country metadata catalogue is empty")

    indicator_summaries: dict[str, Any] = {}
    for code in CAPTURE_INDICATORS:
        params = {"format": "json"}
        artifact, body = _save_response(
            root, raw_dir, f"indicator_metadata_{code}.json",
            _url(f"indicator/{urllib.parse.quote(code, safe='.')}", params),
            params, request_get,
        )
        payload = _payload(body, f"{code} metadata")
        indicator = next((row for row in payload[1] if row.get("id") == code), None)
        if indicator is None or str((indicator.get("source") or {}).get("id")) != SOURCE_ID:
            raise SnapshotError(f"{code} is not confirmed as a WDI indicator")
        artifacts.append(artifact)

        rows: list[dict[str, Any]] = []
        page = 1
        page_count = None
        api_last_updated = None
        while True:
            params = {
                "format": "json", "date": f"{start_year}:{end_year}",
                "per_page": str(PER_PAGE), "page": str(page),
            }
            artifact, body = _save_response(
                root, raw_dir, f"observations_{code}_page_{page:03d}.json",
                _url(f"country/all/indicator/{urllib.parse.quote(code, safe='.')}", params),
                params, request_get, page,
            )
            payload = _payload(body, f"{code} observations page {page}")
            pages = _pages(payload, page, f"{code} observations")
            if page_count is not None and pages != page_count:
                raise SnapshotError(f"{code}: pagination changed during capture")
            page_count = pages
            api_last_updated = payload[0].get("lastupdated") or api_last_updated
            for row in payload[1]:
                returned = (row.get("indicator") or {}).get("id")
                if returned is not None and returned != code:
                    raise SnapshotError(f"{code}: unexpected indicator {returned}")
            artifact["page_count"] = pages
            artifact["row_count"] = len(payload[1])
            artifacts.append(artifact)
            rows.extend(payload[1])
            if page == pages:
                break
            page += 1
        indicator_summaries[code] = {
            "pages": page_count, "observation_rows": len(rows),
            "api_last_updated": api_last_updated,
            "indicator_name": indicator.get("name"),
            "source_organization": indicator.get("sourceOrganization"),
        }

    completed = _aware(None)
    manifest = {
        "manifest_schema_version": 1,
        "source_id": SOURCE_KEY,
        "source_name": "World Bank World Development Indicators",
        "download_id": DATASET_KEY,
        "dataset_id": DATASET_KEY,
        "release": snapshot_id,
        "snapshot_id": snapshot_id,
        "release_kind": "rolling_api_snapshot",
        "release_discovery_mode": "api_capture",
        "source_url": API,
        "final_url": API,
        "api_documentation_url": API_DOCS_URL,
        "terms_url": TERMS_URL,
        "attribution": "World Bank Group, World Development Indicators; indicator-level originating organisations and source notes are retained in the captured metadata.",
        "license_status": "CC BY 4.0 default for World Bank-produced datasets; indicator-specific third-party exceptions require review.",
        "retrieved_at": completed.isoformat(),
        "capture_started_at": started.isoformat(),
        "snapshot_scope": {
            "world_bank_source_id": SOURCE_ID, "start_year": start_year, "end_year": end_year,
            "primary_indicators": list(PRIMARY_INDICATORS),
            "diagnostic_indicators": list(DIAGNOSTIC_INDICATORS),
            "all_indicators": list(CAPTURE_INDICATORS),
            "supporting_indicators": list(SUPPORTING_INDICATORS), "api_version": "v2",
            "observation_api_per_page": PER_PAGE,
            "country_catalogue_record_count": len(country_rows),
            "country_catalogue_page_count": country_page_count,
            "observation_status": "Preserved verbatim in raw API rows; not interpreted by this capture.",
        },
        "indicator_summaries": indicator_summaries,
        "files": artifacts,
    }
    _write_json(manifest_path, manifest)

    report_dir = root / REPORT_BASE / snapshot_id
    report = {
        "assessment": "world_bank_wdi_immutable_api_snapshot_acquisition",
        "snapshot_id": snapshot_id, "retrieved_at": completed.isoformat(),
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "artifact_count": len(artifacts),
        "artifact_bytes": sum(item["byte_count"] for item in artifacts),
        "country_catalogue_record_count": len(country_rows),
        "period": {"start_year": start_year, "end_year": end_year},
        "indicators": indicator_summaries,
        "source_last_updated": source_payload[0].get("lastupdated"),
        "licensing": {
            "default": "CC BY 4.0 for World Bank-produced datasets",
            "exception": "Third-party indicator exceptions require indicator-level review before redistribution.",
            "terms_url": TERMS_URL,
        },
        "side_effects": {
            "raw_snapshot_acquired": True, "manifest_written": True,
            "project_database_written": False, "game_database_written": False,
            "semantic_validation_performed": False, "approval_created": False,
            "source_selection_changed": False, "retention_applied": False,
        },
    }
    markdown = [
        "# World Bank WDI immutable API snapshot", "",
        f"- Snapshot: {snapshot_id}", f"- Retrieved: {completed.isoformat()}",
        f"- Period: {start_year}–{end_year}", "- Source: World Development Indicators (API source ID 2)",
        f"- Response artifacts: {len(artifacts)} ({report['artifact_bytes']:,} bytes)",
        f"- Manifest: {report['manifest_path']}", "",
        "| Indicator | Role | Pages | Response rows | API last updated |",
        "|---|---|---:|---:|---|",
    ]
    for code, item in indicator_summaries.items():
        role = ("primary" if code in PRIMARY_INDICATORS else
                "diagnostic" if code in DIAGNOSTIC_INDICATORS else "supporting_decomposition")
        markdown.append(f"| {code} | {role} | {item['pages']} | {item['observation_rows']} | {item['api_last_updated'] or 'not supplied'} |")
    markdown.extend([
        "", "## Integrity and limitations", "",
        "- Raw response bytes are preserved with request URL, headers, retrieval time, byte count and SHA-256.",
        "- Pagination is followed to completion; malformed or changing pagination aborts the capture.",
        "- Country and indicator metadata are retained alongside observation responses.",
        "- Observation status is preserved verbatim and not interpreted.",
        "- This is a rolling API capture, not a provider-declared WDI release vintage.",
        "- World Bank dataset terms default to CC BY 4.0 for World Bank-produced datasets; third-party exceptions require review.",
        "- Acquisition registration records provenance only; it is not semantic validation or approval.",
        "", "## Side effects", "",
        "- Raw snapshot, manifest and report written.",
        "- No SQLite database, policy, approval or retention changes.",
    ])
    _write_json(report_dir / "assessment.json", report)
    try:
        with (report_dir / "assessment.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(markdown) + "\n")
    except FileExistsError as exc:
        raise SnapshotError(f"Refusing to overwrite report directory {report_dir}") from exc
    return report


def _read_artifact(root: Path, artifact: dict[str, Any]) -> Any:
    relative, expected_hash, expected_bytes = (
        artifact.get("local_raw_path"), artifact.get("sha256"), artifact.get("byte_count")
    )
    if not isinstance(relative, str) or not isinstance(expected_hash, str) or not isinstance(expected_bytes, int):
        raise SnapshotError("Invalid artifact record in WDI manifest")
    path = (root / relative).resolve(strict=True)
    path.relative_to(root)
    if path.stat().st_size != expected_bytes or _hash_file(path) != expected_hash:
        raise SnapshotError(f"Snapshot integrity mismatch: {relative}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Invalid snapshot JSON {relative}: {exc}") from exc


def load_snapshot(manifest_path: str | Path, *, repository_root: str | Path = ROOT) -> dict[str, Any]:
    """Load a snapshot only after verifying all raw response fingerprints."""
    root = Path(repository_root).resolve()
    path = Path(manifest_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve(strict=True)
    path.relative_to(root)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Cannot parse WDI snapshot manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise SnapshotError("WDI snapshot manifest root must be an object")
    if manifest.get("source_id") != SOURCE_KEY or manifest.get("download_id") != DATASET_KEY:
        raise SnapshotError("Manifest is not the selected WDI snapshot dataset")
    scope = manifest.get("snapshot_scope") or {}
    start_year, end_year = scope.get("start_year"), scope.get("end_year")
    if not isinstance(start_year, int) or not isinstance(end_year, int) or end_year < start_year:
        raise SnapshotError("Invalid snapshot year range in manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise SnapshotError("Manifest contains no raw response artifacts")

    source_metadata = None
    country_pages: list[tuple[int, int, list[dict[str, Any]]]] = []
    indicator_metadata: dict[str, dict[str, Any]] = {}
    indicator_metadata_api_metadata: dict[str, dict[str, Any]] = {}
    observation_pages: dict[str, list[tuple[int, int, list[dict[str, Any]]]]] = {}
    for artifact in files:
        name = Path(str(artifact.get("local_raw_path", ""))).name
        payload = _read_artifact(root, artifact)
        if name == "source_metadata.json":
            source_metadata = payload
        elif name.startswith("country_metadata_page_"):
            if not isinstance(payload, list) or len(payload) < 2:
                raise SnapshotError(f"Invalid country page {name}")
            country_pages.append((int(artifact.get("page_number") or 0), int(artifact.get("page_count") or 0), payload[1]))
        elif name.startswith("indicator_metadata_"):
            code = name.removeprefix("indicator_metadata_").removesuffix(".json")
            if not isinstance(payload, list) or len(payload) < 2:
                raise SnapshotError(f"Invalid indicator metadata {name}")
            row = next((x for x in payload[1] if x.get("id") == code), None)
            if row is None or str((row.get("source") or {}).get("id")) != SOURCE_ID:
                raise SnapshotError(f"Indicator metadata mismatch: {code}")
            indicator_metadata[code] = row
            indicator_metadata_api_metadata[code] = payload[0]
        elif name.startswith("observations_"):
            stem = name.removeprefix("observations_").removesuffix(".json")
            code, page_text = stem.rsplit("_page_", 1)
            if not isinstance(payload, list) or len(payload) < 2:
                raise SnapshotError(f"Invalid observation page {name}")
            observation_pages.setdefault(code, []).append((
                int(page_text), int(artifact.get("page_count") or 0), payload[1]
            ))
    if source_metadata is None or not country_pages:
        raise SnapshotError("Snapshot lacks source or country metadata")
    if not any(str(x.get("id")) == SOURCE_ID for x in source_metadata[1]):
        raise SnapshotError("Snapshot source metadata is not WDI source 2")

    country_pages.sort(key=lambda x: x[0])
    expected_country_pages = country_pages[0][1]
    if expected_country_pages != len(country_pages) or [x[0] for x in country_pages] != list(range(1, expected_country_pages + 1)):
        raise SnapshotError("Country metadata pagination is incomplete")
    country_regions: dict[str, dict[str, str]] = {}
    for _, _, rows in country_pages:
        for row in rows:
            iso3 = row.get("id")
            if isinstance(iso3, str) and len(iso3) == 3:
                region = row.get("region") or {}
                country_regions[iso3] = {
                    "region_id": str(region.get("id") or "").strip().upper(),
                    "region_value": str(region.get("value") or "").strip(),
                    "special_notes": str(row.get("specialNotes") or "").strip(),
                    "income_level": str((row.get("incomeLevel") or {}).get("value") or "").strip(),
                    "lending_type": str((row.get("lendingType") or {}).get("value") or "").strip(),
                    "capital_city": str(row.get("capitalCity") or "").strip(),
                }
    observations: dict[str, list[dict[str, Any]]] = {}
    available_codes = set(indicator_metadata) & set(observation_pages)
    for code in INDICATORS:
        if code not in available_codes:
            raise SnapshotError(f"Snapshot is missing required indicator {code}")
    for code in SUPPORTING_INDICATORS:
        if (code in indicator_metadata) != (code in observation_pages):
            raise SnapshotError(f"{code}: incomplete optional supporting indicator bundle")
    for code in sorted(available_codes):
        pages = sorted(observation_pages[code], key=lambda x: x[0])
        expected = pages[0][1]
        if expected != len(pages) or [x[0] for x in pages] != list(range(1, expected + 1)) or any(x[1] != expected for x in pages):
            raise SnapshotError(f"{code}: observation pagination is incomplete")
        observations[code] = [row for _, _, rows in pages for row in rows]
    return {
        "manifest": manifest, "manifest_path": path,
        "manifest_sha256": _hash_file(path), "manifest_byte_count": path.stat().st_size,
        "start_year": start_year, "end_year": end_year,
        "source_metadata": source_metadata, "country_regions": country_regions,
        "indicator_metadata": indicator_metadata,
        "indicator_metadata_api_metadata": indicator_metadata_api_metadata,
        "observations": observations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=START_YEAR)
    parser.add_argument("--end-year", type=int, default=END_YEAR)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    args = parser.parse_args(argv)
    if args.timeout < 1 or args.retries < 0 or args.retry_delay < 0:
        parser.error("--timeout must be positive; --retries and --retry-delay must be non-negative")
    try:
        report = capture_snapshot(
            repository_root=args.root, start_year=args.start_year, end_year=args.end_year,
            request_get=lambda url: _request(
                url, timeout=args.timeout, retries=args.retries, retry_delay=args.retry_delay,
            ),
        )
    except (SnapshotError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
