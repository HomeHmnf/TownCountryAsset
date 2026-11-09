"""Acquire a saved World Bank DataBank report through its authenticated export flow.

The browser-equivalent sequence is deliberate: create a cookie-backed report session,
load each selected dimension, register the exact selected-variable payload, request a
CSV export (lowercase down-radio=csv), and download the returned ZIP. The original ZIP
and extracted CSV members are retained with a timestamped manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from http.cookiejar import CookieJar
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_URL = "https://databank.worldbank.org/id/1da9d9a2?Report_Name=ICP-Annual-PPPs"
RAW_BASE = Path("raw_data/sources/world_bank_icp/databank_exports")
MANIFEST_BASE = Path("data_manifests/sources/world_bank_icp/databank_exports")
REPORT_BASE = Path("reports/sources/world-bank-icp")
DIMENSIONS = (
    ("Country", "[Country].[List]"),
    ("Classification", "[Classification].[List]"),
    ("Series", "[Series].[List]"),
    ("Time", "[Time].[List]"),
)
AJAX_BASE = "https://databank.worldbank.org"
DIMENSION_ENDPOINT = "/AjaxServices/AjaxReportMethods.asmx/GetDimensionJSON"
SELECTION_ENDPOINT = "/AjaxDownload/SelectVariableHandler.ashx"
FILEINFO_ENDPOINT = "/AjaxDownload/FileInfoHandler.ashx"
FILEDOWNLOAD_ENDPOINT = "/AjaxDownload/FileDownloadHandler.ashx"


class DataBankExportError(RuntimeError):
    """DataBank session, selection or export failure."""


class _HiddenInputs(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        key = values.get("id") or values.get("name")
        if key:
            self.values[key] = values.get("value", "")


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _safe_name(value: str, fallback: str) -> str:
    name = Path(value.replace("\\", "/")).name
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return cleaned or fallback


def _request(opener: urllib.request.OpenerDirector, url: str, *,
             data: bytes | None = None, headers: dict[str, str] | None = None,
             timeout: int = 120, retries: int = 5,
             retry_delay: float = 2.0) -> tuple[bytes, int, dict[str, str], str]:
    request_headers = {"User-Agent": "TownCountryAsset/1.0"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=data, headers=request_headers)
    for attempt in range(retries + 1):
        try:
            with opener.open(request, timeout=timeout) as response:
                return response.read(), response.status, dict(response.headers.items()), response.geturl()
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt >= retries:
                raise DataBankExportError(f"HTTP {exc.code} for {url}: {exc.read(500)!r}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt >= retries:
                raise DataBankExportError(f"Request failed for {url}: {exc}") from exc
        time.sleep(retry_delay * (2 ** attempt))
    raise DataBankExportError(f"Request failed for {url}")


def _post_json(opener: urllib.request.OpenerDirector, url: str,
               payload: dict[str, Any], *, timeout: int, retries: int,
               retry_delay: float) -> Any:
    body, status, _, _ = _request(
        opener, url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Accept": "application/json, text/javascript, */*; q=0.01"},
        timeout=timeout, retries=retries, retry_delay=retry_delay,
    )
    if status != 200:
        raise DataBankExportError(f"Unexpected HTTP status {status}: {url}")
    try:
        value: Any = json.loads(body.decode("utf-8"))
        if isinstance(value, dict) and "d" in value:
            value = value["d"]
        if isinstance(value, str):
            value = json.loads(value)
        return value
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DataBankExportError(f"Invalid JSON response from {url}: {body[:300]!r}") from exc


def _dimension_response(opener: urllib.request.OpenerDirector, cube_id: str,
                        control_id: str, hierarchy: str, *, expected_count: int | None,
                        timeout: int, retries: int, retry_delay: float) -> dict[str, Any]:
    url = AJAX_BASE + DIMENSION_ENDPOINT
    last_error = "dimension selection was empty or incomplete"
    for attempt in range(retries + 1):
        try:
            value = _post_json(
                opener, url,
                {"cubeid": cube_id, "controlid": control_id, "hierarchy": hierarchy},
                timeout=timeout, retries=0, retry_delay=retry_delay,
            )
            if not isinstance(value, dict):
                raise DataBankExportError("dimension response is not an object")
            selected = value.get("Sel")
            members = value.get("Members")
            if not isinstance(selected, dict) or not isinstance(members, (dict, list)):
                raise DataBankExportError("dimension response lacks Sel or Members")
            if not selected:
                raise DataBankExportError("dimension selection is empty")
            if expected_count is not None and len(selected) != expected_count:
                raise DataBankExportError(
                    f"dimension selection has {len(selected)} of {expected_count} expected members"
                )
            return value
        except DataBankExportError as exc:
            last_error = str(exc)
            if attempt >= retries:
                break
            time.sleep(retry_delay * (2 ** attempt))
    raise DataBankExportError(f"{control_id}: {last_error}")


def _page_metadata(page: bytes) -> tuple[str, dict[str, int]]:
    parser = _HiddenInputs()
    parser.feed(page.decode("utf-8", "replace"))
    cube_id = parser.values.get("hdnCubeID", "").strip()
    if not cube_id:
        raise DataBankExportError("Saved report page does not expose hdnCubeID")
    expected: dict[str, int] = {}
    adobe = parser.values.get("hdnAbobeText", "")
    if not adobe:
        raise DataBankExportError("Saved report page does not expose hdnAbobeText dimension metadata")
    try:
        payload = json.loads(html.unescape(adobe))
        dimensions = payload.get("Dimensions", {})
        if isinstance(dimensions, dict):
            expected = {str(name): len(values) for name, values in dimensions.items()
                        if isinstance(values, list)}
    except (json.JSONDecodeError, AttributeError, TypeError) as exc:
        raise DataBankExportError("Saved report hdnAbobeText is not valid dimension JSON") from exc
    missing = [name for name, _ in DIMENSIONS if expected.get(name, 0) < 1]
    if missing:
        raise DataBankExportError(
            "Saved report dimension metadata is incomplete: " + ", ".join(missing)
        )
    return cube_id, expected


def _selected_variables(dimensions: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    result = []
    for control_id, dimension in dimensions:
        selected = dimension["Sel"]
        members = []
        for unique_name, member in selected.items():
            if not isinstance(member, dict):
                raise DataBankExportError(f"Invalid selected member in {control_id}: {unique_name}")
            custom = bool(member.get("custom", False))
            members.append({
                "uniquename": unique_name,
                "displayname": member.get("displayname", ""),
                "iscustom": custom,
                "customdefinition": member.get("customdefinition") if custom else None,
                "AggregationRule": None,
            })
        result.append({"controlid": control_id, "memberdetails": members,
                       "aggregationruleall": None})
    return result


def _post_form(opener: urllib.request.OpenerDirector, url: str,
               values: dict[str, str], *, timeout: int, retries: int,
               retry_delay: float) -> tuple[bytes, int, dict[str, str], str]:
    data = urllib.parse.urlencode(values).encode("utf-8")
    return _request(
        opener, url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                 "X-Requested-With": "XMLHttpRequest"},
        timeout=timeout, retries=retries, retry_delay=retry_delay,
    )


def acquire_export(*, repository_root: str | Path = ROOT,
                   report_url: str = DEFAULT_REPORT_URL,
                   retrieved_at: datetime | None = None, timeout: int = 120,
                   retries: int = 5, retry_delay: float = 2.0) -> dict[str, Any]:
    if timeout < 1 or retries < 0 or retry_delay < 0:
        raise ValueError("Invalid timeout or retry configuration")
    stamp = retrieved_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    root = Path(repository_root).resolve()
    export_id = "databank_" + stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = root / RAW_BASE / export_id
    manifest_path = root / MANIFEST_BASE / f"{export_id}.json"
    if raw_dir.exists() or manifest_path.exists():
        raise DataBankExportError(f"Export already exists: {export_id}")

    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    page, status, page_headers, final_page_url = _request(
        opener, report_url, timeout=timeout, retries=retries, retry_delay=retry_delay,
    )
    if status != 200:
        raise DataBankExportError(f"Saved report returned HTTP {status}")
    cube_id, expected_counts = _page_metadata(page)

    dimensions: list[tuple[str, dict[str, Any]]] = []
    selection_summary: list[dict[str, Any]] = []
    for control_id, hierarchy in DIMENSIONS:
        dimension = _dimension_response(
            opener, cube_id, control_id, hierarchy,
            expected_count=expected_counts.get(control_id),
            timeout=timeout, retries=retries, retry_delay=retry_delay,
        )
        dimensions.append((control_id, dimension))
        selection_summary.append({
            "control_id": control_id, "hierarchy": hierarchy,
            "selected_count": len(dimension["Sel"]),
            "selected_members": [
                {"unique_name": key, "display_name": value.get("displayname", "")}
                for key, value in dimension["Sel"].items() if isinstance(value, dict)
            ],
        })

    selected_payload = json.dumps(_selected_variables(dimensions), ensure_ascii=False,
                                  separators=(",", ":"))
    _, registration_status, _, _ = _post_form(
        opener, AJAX_BASE + SELECTION_ENDPOINT,
        {"hdnSelectVars": selected_payload},
        timeout=timeout, retries=retries, retry_delay=retry_delay,
    )
    if registration_status != 200:
        raise DataBankExportError("DataBank rejected selected-variable registration")

    fileinfo_values = {
        "reqtype": "data",
        "data-option-radio": "data-download",
        "down-radio": "csv",
        "ddl-text-delimiter": "None",
        "ddl-export-range": "full",
        "ddl-data-format": "Table",
        "ddl-variable-format": "Both",
        "ddl-na-preference": "..",
        "hdnEditMode": "",
        "ddl-export-notes": "N",
        "dataset-name": "",
        "chk-scale-precision": "N",
    }
    fileinfo_body, fileinfo_status, _, _ = _post_form(
        opener, AJAX_BASE + FILEINFO_ENDPOINT, fileinfo_values,
        timeout=timeout, retries=retries, retry_delay=retry_delay,
    )
    descriptor = fileinfo_body.decode("utf-8", "replace").strip()
    if fileinfo_status != 200 or not descriptor.startswith("filename="):
        raise DataBankExportError(f"DataBank did not create an export: {descriptor[:500]!r}")
    descriptor_values = urllib.parse.parse_qs(descriptor, keep_blank_values=True)
    filename = descriptor_values.get("filename", [""])[0]
    filetype = descriptor_values.get("filetype", [""])[0]
    if not filename or filetype.upper() != "CSV":
        raise DataBankExportError(f"Unexpected DataBank export descriptor: {descriptor!r}")

    archive_url = AJAX_BASE + FILEDOWNLOAD_ENDPOINT + "?" + descriptor
    archive, download_status, download_headers, final_download_url = _request(
        opener, archive_url, timeout=timeout, retries=retries, retry_delay=retry_delay,
    )
    if download_status != 200 or not zipfile.is_zipfile(BytesIO(archive)):
        raise DataBankExportError("DataBank download did not return a valid ZIP archive")
    with zipfile.ZipFile(BytesIO(archive)) as zipped:
        bad_member = zipped.testzip()
        if bad_member is not None:
            raise DataBankExportError(f"ZIP CRC validation failed for {bad_member}")
        csv_members = [item for item in zipped.infolist()
                       if not item.is_dir() and item.filename.lower().endswith(".csv")]
        if not csv_members:
            raise DataBankExportError("DataBank ZIP contains no CSV members")
        for item in csv_members:
            target_name = Path(item.filename.replace("\\", "/"))
            if target_name.is_absolute() or ".." in target_name.parts:
                raise DataBankExportError(f"Unsafe ZIP member path: {item.filename}")
    raw_dir.mkdir(parents=True, exist_ok=False)
    archive_path = raw_dir / "databank_export.zip"
    archive_path.write_bytes(archive)
    artifacts: list[dict[str, Any]] = [{
        "artifact_role": "original_export_archive",
        "local_raw_path": archive_path.relative_to(root).as_posix(),
        "source_filename": filename,
        "url": archive_url, "final_url": final_download_url,
        "http_status": download_status,
        "content_type": download_headers.get("Content-Type", ""),
        "byte_count": len(archive), "sha256": _sha256(archive),
    }]
    with zipfile.ZipFile(BytesIO(archive)) as zipped:
        for item in csv_members:
            member_name = _safe_name(item.filename, "export.csv")
            member_path = raw_dir / "contents" / member_name
            member_path.parent.mkdir(parents=True, exist_ok=True)
            member_bytes = zipped.read(item)
            with member_path.open("xb") as stream:
                stream.write(member_bytes)
            artifacts.append({
                "artifact_role": "extracted_csv_member",
                "archive_member": item.filename,
                "derived_from": archive_path.relative_to(root).as_posix(),
                "local_raw_path": member_path.relative_to(root).as_posix(),
                "byte_count": len(member_bytes), "sha256": _sha256(member_bytes),
            })

    completed = datetime.now(timezone.utc)
    manifest = {
        "manifest_schema_version": 1,
        "source_id": "world_bank_wdi",
        "dataset_id": "world_bank_icp_databank_saved_report",
        "release": "saved_report_export",
        "export_id": export_id,
        "report_url": report_url,
        "final_report_url": final_page_url,
        "report_page": {
            "url": report_url, "final_url": final_page_url,
            "http_status": status, "content_type": page_headers.get("Content-Type", ""),
            "byte_count": len(page), "sha256": _sha256(page),
        },
        "cube_id": cube_id,
        "dimension_endpoint": AJAX_BASE + DIMENSION_ENDPOINT,
        "selection_endpoint": AJAX_BASE + SELECTION_ENDPOINT,
        "fileinfo_endpoint": AJAX_BASE + FILEINFO_ENDPOINT,
        "filedownload_endpoint": AJAX_BASE + FILEDOWNLOAD_ENDPOINT,
        "retrieved_at": completed.isoformat(),
        "export_format": "CSV",
        "export_range": "full",
        "data_format": "Table",
        "variable_format": "Both",
        "missing_value_token": "..",
        "dimensions": selection_summary,
        "selected_variable_registration_http_status": registration_status,
        "fileinfo_descriptor": descriptor,
        "files": artifacts,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    report = {
        "assessment": "world_bank_icp_databank_saved_report_acquisition",
        "export_id": export_id,
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "selected_dimension_counts": {x["control_id"]: x["selected_count"]
                                      for x in selection_summary},
        "archive_bytes": len(archive),
        "csv_member_count": len(csv_members),
        "artifact_count": len(artifacts),
        "retrieved_at": completed.isoformat(),
        "side_effects": {
            "raw_export_acquired": True, "manifest_written": True,
            "project_database_written": False, "game_database_written": False,
            "semantic_validation_performed": False, "approval_created": False,
            "source_selection_changed": False, "retention_applied": False,
        },
    }
    report_dir = root / REPORT_BASE / export_id
    report_dir.mkdir(parents=True, exist_ok=False)
    with (report_dir / "assessment.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report-url", default=DEFAULT_REPORT_URL)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        result = acquire_export(
            repository_root=args.root, report_url=args.report_url,
            timeout=args.timeout, retries=args.retries, retry_delay=args.retry_delay,
        )
    except (DataBankExportError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
