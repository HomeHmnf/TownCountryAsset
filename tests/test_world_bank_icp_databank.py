from __future__ import annotations

import csv
import io
import json
import urllib.parse
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from tools import acquire_world_bank_icp_databank as databank


class FakeResponse:
    def __init__(self, body: bytes, url: str, content_type: str = "application/octet-stream"):
        self.body = body
        self.status = 200
        self.headers = {"Content-Type": content_type}
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, amount: int = -1):
        return self.body if amount < 0 else self.body[:amount]

    def geturl(self):
        return self.url


class FakeOpener:
    def __init__(self):
        self.calls = []
        self.archive = io.BytesIO()
        with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            zipped.writestr("Data_Extract.csv",
                            "Country Name,Country Code,Time,Time Code,GDP\\n"
                            "Zimbabwe,ZWE,2017,YR2017,0.4894120097\\n")
        self.archive_bytes = self.archive.getvalue()

    def open(self, request, timeout=120):
        url = request.full_url
        data = request.data or b""
        self.calls.append((url, data, request.headers))
        if url == databank.DEFAULT_REPORT_URL:
            page = (
                '<input id="hdnCubeID" value="3869">'
                '<input id="hdnAbobeText" value=\'{"Dimensions":'
                '{"Country":["Zimbabwe"],"Classification":["PPP"],'
                '"Series":["GDP"],"Time":["2017"]}}\'>'
            ).encode()
            return FakeResponse(page, url, "text/html")
        if url.endswith(databank.DIMENSION_ENDPOINT):
            selection = urllib.parse.parse_qs(data.decode())
            payload = json.loads(data.decode())
            control = payload["controlid"]
            hierarchy = payload["hierarchy"]
            member = {
                "Country": ("[Country].[List].&[ZWE]", "Zimbabwe"),
                "Classification": ("[Classification].[List].&[PPPGlob]", "PPP"),
                "Series": ("[Series].[List].&[1000000]", "GDP"),
                "Time": ("[Time].[List].&[YR2017]", "2017"),
            }[control]
            body = json.dumps({"d": {"Sel": {
                member[0]: {"displayname": member[1], "custom": False,
                            "customdefinition": None, "AggregationRule": None}
            }, "Members": {}}}).encode()
            return FakeResponse(body, url, "application/json")
        if url.endswith(databank.SELECTION_ENDPOINT):
            fields = urllib.parse.parse_qs(data.decode())
            assert "hdnSelectVars" in fields
            registered = json.loads(fields["hdnSelectVars"][0])
            assert len(registered) == 4
            assert all(row["aggregationruleall"] is None for row in registered)
            return FakeResponse(b"", url, "text/plain")
        if url.endswith(databank.FILEINFO_ENDPOINT):
            fields = urllib.parse.parse_qs(data.decode())
            assert fields["down-radio"] == ["csv"]
            assert fields["ddl-export-range"] == ["full"]
            return FakeResponse(
                b"filename=P_test.zip&filetype=CSV&language=en&displayfile=P_test.zip",
                url, "text/plain",
            )
        if url.startswith(databank.AJAX_BASE + databank.FILEDOWNLOAD_ENDPOINT):
            return FakeResponse(self.archive_bytes, url, "application/zip")
        raise AssertionError(f"Unexpected URL: {url}")


def test_acquires_saved_report_csv_archive_and_extracts_members(tmp_path, monkeypatch):
    fake = FakeOpener()
    monkeypatch.setattr(databank.urllib.request, "build_opener", lambda *args: fake)
    result = databank.acquire_export(
        repository_root=tmp_path,
        retrieved_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
        retries=0,
    )
    manifest_path = tmp_path / result["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result["selected_dimension_counts"] == {
        "Country": 1, "Classification": 1, "Series": 1, "Time": 1,
    }
    assert result["csv_member_count"] == 1
    assert len(manifest["files"]) == 2
    archive = tmp_path / manifest["files"][0]["local_raw_path"]
    extracted = tmp_path / manifest["files"][1]["local_raw_path"]
    assert zipfile.is_zipfile(archive)
    assert extracted.read_text(encoding="utf-8").startswith("Country Name,Country Code")
    assert manifest["fileinfo_descriptor"].startswith("filename=")
    assert any(url.endswith(databank.SELECTION_ENDPOINT) for url, _, _ in fake.calls)


def test_page_metadata_requires_cube_id():
    try:
        databank._page_metadata(b"<html></html>")
    except databank.DataBankExportError as exc:
        assert "hdnCubeID" in str(exc)
    else:
        raise AssertionError("Expected missing cube ID to be rejected")


def test_selected_variables_matches_databank_payload_contract():
    dimension = {"Sel": {
        "[Series].[List].&[1000000]": {
            "displayname": "1000000:GROSS DOMESTIC PRODUCT",
            "custom": False, "customdefinition": None,
        }
    }}
    result = databank._selected_variables([("Series", dimension)])
    member = result[0]["memberdetails"][0]
    assert member == {
        "uniquename": "[Series].[List].&[1000000]",
        "displayname": "1000000:GROSS DOMESTIC PRODUCT",
        "iscustom": False,
        "customdefinition": None,
        "AggregationRule": None,
    }
