from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from tools import acquire_zimbabwe_national_accounts as acquisition


def _workbook(path: Path, signature: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if signature == "xls":
        path.write_bytes(acquisition.XLS_SIGNATURE + b"fixture")
    else:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/workbook.xml", "<workbook/>")
            archive.writestr("[Content_Types].xml", "<Types/>")
    return path


def test_publications_are_separate_official_datasets() -> None:
    assert [p["dataset_id"] for p in acquisition.PUBLICATIONS] == [
        "gdp_trends_2009_2018", "gdp_tables_2019_2024"
    ]
    assert acquisition.PUBLICATIONS[0]["url"].endswith("GDP_Trends_2009to2018.xls")
    assert acquisition.PUBLICATIONS[1]["url"].endswith("GDP_Tables_2019_2024_June.xlsx")


def test_existing_workbooks_create_two_manifests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(url, destination, *, timeout, retries, socks5_proxy):
        publication = next(p for p in acquisition.PUBLICATIONS if p["url"] == url)
        _workbook(destination, publication["signature"])
        content_type = "application/vnd.ms-excel" if publication["signature"] == "xls" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return url, content_type, destination.stat().st_size

    monkeypatch.setattr(acquisition, "_curl_download", fake_download)
    result = acquisition.acquire_zimbabwe_national_accounts(repository_root=tmp_path)
    assert result["acquisition_count"] == 2
    assert result["failure_count"] == 0
    assert result["project_database_written"] is False
    assert result["game_database_written"] is False
    payloads = [json.loads((tmp_path/item["manifest_path"]).read_text()) for item in result["acquisitions"]]
    assert {p["download_id"] for p in payloads} == {"gdp_trends_2009_2018", "gdp_tables_2019_2024"}
    assert all(p["validation"]["statistical_content_reviewed"] is False for p in payloads)


def test_xls_and_xlsx_signatures_are_distinct(tmp_path: Path) -> None:
    xls = tmp_path/"bad.xls"
    xls.write_bytes(b"PK\x03\x04not an OLE file")
    with pytest.raises(ValueError, match="OLE XLS"):
        acquisition._validate(xls, "xls")
    xlsx = tmp_path/"bad.xlsx"
    xlsx.write_bytes(acquisition.XLS_SIGNATURE+b"not a ZIP")
    with pytest.raises(ValueError, match="OOXML ZIP"):
        acquisition._validate(xlsx, "xlsx")


def test_invalid_xlsx_container_is_rejected(tmp_path: Path) -> None:
    path = tmp_path/"invalid.xlsx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("not-a-workbook.xml", "<x/>")
    with pytest.raises(ValueError, match="Invalid XLSX workbook"):
        acquisition._validate(path, "xlsx")


def test_resume_skips_verified_workbooks_without_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(url, destination, *, timeout, retries, socks5_proxy):
        publication = next(p for p in acquisition.PUBLICATIONS if p["url"] == url)
        _workbook(destination, publication["signature"])
        return url, "application/octet-stream", destination.stat().st_size

    monkeypatch.setattr(acquisition, "_curl_download", fake_download)
    first = acquisition.acquire_zimbabwe_national_accounts(repository_root=tmp_path)
    hashes = {p["dataset_id"]: acquisition._sha256(tmp_path/p["raw_path"]) for p in acquisition.PUBLICATIONS}
    second = acquisition.acquire_zimbabwe_national_accounts(repository_root=tmp_path)
    assert first["acquisition_count"] == 2
    assert second["acquisition_count"] == 0
    assert second["skipped_existing_count"] == 2
    assert hashes == {p["dataset_id"]: acquisition._sha256(tmp_path/p["raw_path"]) for p in acquisition.PUBLICATIONS}


def test_raw_workbook_without_manifest_is_never_overwritten(tmp_path: Path) -> None:
    publication = acquisition.PUBLICATIONS[0]
    _workbook(tmp_path/publication["raw_path"], publication["signature"])
    with pytest.raises(FileExistsError, match="without a manifest"):
        acquisition.acquire_zimbabwe_national_accounts(repository_root=tmp_path)


def test_socks5_proxy_is_forwarded_to_curl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        output = Path(command[command.index("--output")+1])
        _workbook(output, "xls")
        class Result:
            returncode = 0
            stdout = "https://final.example/file.xls\napplication/vnd.ms-excel\n200"
            stderr = ""
        return Result()
    monkeypatch.setattr(acquisition.subprocess, "run", fake_run)
    destination = tmp_path/"capture.xls"
    acquisition._curl_download("https://source.example/file.xls", destination, timeout=30,
        retries=0, socks5_proxy="127.0.0.1:10808")
    assert calls[0][1:3] == ["--socks5-hostname", "127.0.0.1:10808"]
    assert destination.is_file()
