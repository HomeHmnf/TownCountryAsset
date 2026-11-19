from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from tools.validate_world_bank_icp_databank import (
    ICPDataBankValidationError,
    validate_manifest,
)


FIELDS = [
    "Classification Name", "Classification Code", "Time", "Time Code",
    "Country Name", "Country Code",
    "1000000:GROSS DOMESTIC PRODUCT [1000000]",
    "9020000:ACTUAL INDIVIDUAL CONSUMPTION [9020000]",
]


def _csv_bytes(rows, encoding="utf-8"):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode(encoding)


def _fixture(root: Path):
    rows = []
    for year, time_code in ((2017, "YR2017"), (2018, "YR2018")):
        for name, code in (("Côte d’Ivoire", "CIV"), ("Zimbabwe", "ZWE")):
            rows.append({
                "Classification Name": "Purchasing power parity (PPP) (US$ = 1)",
                "Classification Code": "PPPGlob",
                "Time": str(year), "Time Code": time_code,
                "Country Name": name, "Country Code": code,
                FIELDS[6]: "1.25" if code == "CIV" else "..",
                FIELDS[7]: "1.10",
            })
    data_rows = rows + [
        {field: "" for field in FIELDS},
        {field: "" for field in FIELDS},
        {field: "" for field in FIELDS},
        {**{field: "" for field in FIELDS},
         "Classification Name": "Data from database: ICP 2021"},
        {**{field: "" for field in FIELDS},
         "Classification Name": "Last Updated: 08/04/2024"},
    ]
    metadata_rows = rows + [
        {field: "" for field in FIELDS},
        {field: "" for field in FIELDS},
        {field: "" for field in FIELDS},
        {**{field: "" for field in FIELDS},
         "Classification Name": "Data from database: ICP 2021"},
        {**{field: "" for field in FIELDS},
         "Classification Name": "Last Updated: 08/04/2024"},
        {**{field: "" for field in FIELDS},
         "Classification Name": "Code", "Classification Code": "Indicator Name"},
        {**{field: "" for field in FIELDS},
         "Classification Name": "1000000", "Classification Code": "Gross domestic product"},
        {**{field: "" for field in FIELDS},
         "Classification Name": "9020000", "Classification Code": "Actual individual consumption"},
    ]
    data_bytes = _csv_bytes(data_rows, "utf-8-sig")
    metadata_bytes = _csv_bytes(metadata_rows, "cp1252")

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("123_Data.csv", data_bytes)
        archive.writestr("123_Series - Metadata.csv", metadata_bytes)
    archive_bytes = archive_buffer.getvalue()

    raw = root / "raw_data/sources/world_bank_icp/databank_exports/test_export"
    contents = raw / "contents"
    contents.mkdir(parents=True)
    archive_path = raw / "databank_export.zip"
    data_path = contents / "123_Data.csv"
    metadata_path = contents / "123_Series - Metadata.csv"
    archive_path.write_bytes(archive_bytes)
    data_path.write_bytes(data_bytes)
    metadata_path.write_bytes(metadata_bytes)

    def artifact(role, path, member=None):
        payload = path.read_bytes()
        item = {
            "artifact_role": role,
            "local_raw_path": path.relative_to(root).as_posix(),
            "byte_count": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if member:
            item["archive_member"] = member
        return item

    manifest = {
        "manifest_schema_version": 1,
        "source_id": "world_bank_icp",
        "dataset_id": "world_bank_icp_databank_saved_report",
        "release": "icp_2021_saved_report",
        "export_id": "test_export",
        "export_format": "CSV",
        "missing_value_token": "..",
        "dimensions": [
            {"control_id": "Country", "selected_count": 2, "selected_members": [
                {"unique_name": "[Country].[List].&[CIV]", "display_name": "Côte d’Ivoire"},
                {"unique_name": "[Country].[List].&[ZWE]", "display_name": "Zimbabwe"},
            ]},
            {"control_id": "Classification", "selected_count": 1, "selected_members": [
                {"unique_name": "[Classification].[List].&[PPPGlob]", "display_name": "PPP"},
            ]},
            {"control_id": "Series", "selected_count": 2, "selected_members": [
                {"unique_name": "[Series].[List].&[1000000]", "display_name": "GDP"},
                {"unique_name": "[Series].[List].&[9020000]", "display_name": "AIC"},
            ]},
            {"control_id": "Time", "selected_count": 2, "selected_members": [
                {"unique_name": "[Time].[List].&[YR2017]", "display_name": "2017"},
                {"unique_name": "[Time].[List].&[YR2018]", "display_name": "2018"},
            ]},
        ],
        "files": [
            artifact("original_export_archive", archive_path),
            artifact("extracted_csv_member", data_path, "123_Data.csv"),
            artifact("extracted_csv_member", metadata_path, "123_Series - Metadata.csv"),
        ],
    }
    manifest_path = root / "data_manifests/sources/world_bank_icp/databank_exports/test_export.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, data_path, metadata_path


def test_validates_observation_scope_encoding_missingness_and_csv_parity(tmp_path):
    manifest, _, _ = _fixture(tmp_path)
    result = validate_manifest(repository_root=tmp_path, manifest_path=manifest)

    assert result["status"] == "passed"
    assert result["selected_dimension_counts"] == {
        "Country": 2, "Classification": 1, "Series": 2, "Time": 2,
    }
    assert result["observation_count"] == 4
    assert result["expected_observation_count"] == 4
    assert result["csv_encodings"] == {
        "data": "utf-8-sig", "series_metadata": "cp1252",
    }
    assert result["missing_value_counts_by_indicator"] == {
        "1000000": 2, "9020000": 0,
    }
    assert result["data_csv_non_observation_rows"] == 5
    assert result["series_metadata_non_observation_rows"] == 8
    assert result["series_metadata_dictionary_row_count"] == 2
    assert result["data_metadata_identity_and_value_parity"] is True
    assert Path(tmp_path / result["validation_report_path"]).is_file()


def test_rejects_duplicate_observation_keys(tmp_path):
    manifest, data_path, _ = _fixture(tmp_path)
    _, rows, _ = __import__(
        "tools.validate_world_bank_icp_databank", fromlist=["_read_csv"]
    )._read_csv(data_path)
    rows.append(dict(rows[0]))
    data_path.write_bytes(_csv_bytes(rows, "utf-8-sig"))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = next(x for x in payload["files"] if x["local_raw_path"].endswith("_Data.csv"))
    artifact["byte_count"] = data_path.stat().st_size
    artifact["sha256"] = hashlib.sha256(data_path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ICPDataBankValidationError, match="duplicate observation key"):
        validate_manifest(repository_root=tmp_path, manifest_path=manifest)


def test_rejects_data_metadata_value_mismatch(tmp_path):
    manifest, _, metadata_path = _fixture(tmp_path)
    _, rows, _ = __import__(
        "tools.validate_world_bank_icp_databank", fromlist=["_read_csv"]
    )._read_csv(metadata_path)
    rows[0][FIELDS[6]] = "999"
    metadata_path.write_bytes(_csv_bytes(rows, "cp1252"))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = next(x for x in payload["files"]
                    if x["local_raw_path"].endswith("Series - Metadata.csv"))
    artifact["byte_count"] = metadata_path.stat().st_size
    artifact["sha256"] = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ICPDataBankValidationError, match="differs from ZIP bytes"):
        validate_manifest(repository_root=tmp_path, manifest_path=manifest)
