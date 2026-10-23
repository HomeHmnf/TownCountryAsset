from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pytest

from tools import run_data_pipeline as pipeline


def test_load_dotenv_defaults_and_environment_precedence(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nTCA_REPORT_DIR='custom reports'\nTCA_HTTP_TIMEOUT_SECONDS=12\n",
        encoding="utf-8",
    )
    values = pipeline.load_dotenv(
        env_file, {"TCA_HTTP_TIMEOUT_SECONDS": "9", "EXISTING": "kept"}
    )
    assert values["TCA_REPORT_DIR"] == "custom reports"
    assert values["TCA_HTTP_TIMEOUT_SECONDS"] == "9"
    assert values["TCA_NATURAL_EARTH_URL"] == pipeline.DEFAULTS["TCA_NATURAL_EARTH_URL"]
    assert values["TCA_PERSIAN_LABEL_SOURCE_URL"] == "https://query.wikidata.org/sparql"
    assert values["TCA_RUN_PERSIAN_LOCALIZATION"] == "true"
    assert values["TCA_FLAG_REFRESH_ENABLED"] == "true"
    assert values["TCA_FLAG_MAPPING"] == "config/country_flag_mapping.json"
    assert values["EXISTING"] == "kept"


def test_flag_report_classifies_only_unreviewed_mappings_as_review_gaps(tmp_path):
    report = tmp_path / "flags.md"
    report.write_text(
        "# Flag asset coverage audit\n\n## Issues\n\n"
        "- tc_one: mapping status is 'unreviewed'; expected 'reviewed'\n"
        "- tc_two: missing flag mapping for game_id tc_two\n",
        encoding="utf-8",
    )
    assert pipeline.flag_report_contains_only_review_gaps(report)

    report.write_text(
        "# Flag asset coverage audit\n\n## Issues\n\n"
        "- tc_one: malformed SVG XML\n",
        encoding="utf-8",
    )
    assert not pipeline.flag_report_contains_only_review_gaps(report)


def test_manual_iso_reference_uses_ods_when_tsv_is_spreadsheet_xml(tmp_path):
    import zipfile

    reference_dir = tmp_path / "data" / "reference" / "iso"
    reference_dir.mkdir(parents=True)
    (reference_dir / "iso-3166-1-2026-10.tsv").write_text(
        '<?xml version="1.0"?><Workbook><Worksheet/></Workbook>',
        encoding="utf-8",
    )
    content_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <office:document-content
      xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
      xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
      xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
      <office:body><office:spreadsheet><table:table>
        <table:table-row>
          <table:table-cell><text:p>English short name</text:p></table:table-cell>
          <table:table-cell><text:p>French short name</text:p></table:table-cell>
          <table:table-cell><text:p>Alpha-2 code</text:p></table:table-cell>
          <table:table-cell><text:p>Alpha-3 code</text:p></table:table-cell>
          <table:table-cell><text:p>Numeric</text:p></table:table-cell>
        </table:table-row>
        <table:table-row>
          <table:table-cell><text:p>Afghanistan</text:p></table:table-cell>
          <table:table-cell><text:p>Afghanistan</text:p></table:table-cell>
          <table:table-cell><text:p>AF</text:p></table:table-cell>
          <table:table-cell><text:p>AFG</text:p></table:table-cell>
          <table:table-cell office:value-type="float" office:value="4"/>
        </table:table-row>
        <table:table-row>
          <table:table-cell><text:p>Zambia</text:p></table:table-cell>
          <table:table-cell><text:p>Zambie</text:p></table:table-cell>
          <table:table-cell><text:p>ZM</text:p></table:table-cell>
          <table:table-cell><text:p>ZMB</text:p></table:table-cell>
          <table:table-cell/>
        </table:table-row>
      </table:table></office:spreadsheet></office:body>
    </office:document-content>"""
    with zipfile.ZipFile(reference_dir / "iso-3166-1-2026-10.ods", "w") as archive:
        archive.writestr("content.xml", content_xml)

    selected = pipeline.select_manual_iso_reference(tmp_path)

    assert selected["format"] == "ods"
    assert len(selected["rows"]) == 2
    assert selected["rows"][0]["numeric"] == "004"
    assert selected["rows"][1]["numeric"] == ""
    assert "using the ODS workbook" in selected["warning"]
    assert "Zambia" in selected["warning"]


def test_manual_iso_reference_reads_valid_tsv_and_preserves_numeric_leading_zero(tmp_path):
    reference_dir = tmp_path / "data" / "reference" / "iso"
    reference_dir.mkdir(parents=True)
    (reference_dir / "iso-3166-1-2026-10.tsv").write_text(
        "name_en\tname_fr\talpha2\talpha3\tnumeric\n"
        "Afghanistan\tAfghanistan\tAF\tAFG\t004\n",
        encoding="utf-8",
    )

    selected = pipeline.select_manual_iso_reference(tmp_path)

    assert selected["format"] == "tsv"
    assert selected["rows"][0]["numeric"] == "004"
    assert selected["warning"] is None


def test_load_dotenv_rejects_malformed_line(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NOT_A_VALID_LINE\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected KEY=VALUE"):
        pipeline.load_dotenv(env_file, {})


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("YES", True), ("1", True), ("off", False), ("0", False), ("No", False)],
)
def test_enabled_parses_boolean_values(value, expected):
    assert pipeline.enabled(value, "FEATURE") is expected


def test_enabled_rejects_unknown_boolean_value():
    with pytest.raises(ValueError, match="FEATURE"):
        pipeline.enabled("sometimes", "FEATURE")


def test_fetch_archive_preserves_bytes_hash_and_provenance(tmp_path, monkeypatch):
    payload = b"PK\x03\x04test-archive"
    class Response(io.BytesIO):
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(pipeline.urllib.request, "urlopen", lambda request, timeout: Response(payload))
    now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    result = pipeline.fetch_archive(
        "https://example.invalid/data.zip", tmp_path, 3, now
    )
    assert result["archive"].read_bytes() == payload
    assert result["archive_sha256"] == pipeline.sha256_bytes(payload)
    metadata = json.loads(result["provenance"].read_text(encoding="utf-8"))
    assert metadata["archive_sha256"] == result["archive_sha256"]
    assert metadata["release_version"] is None


def test_fetch_archive_rejects_non_zip_payload(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(pipeline.urllib.request, "urlopen", lambda request, timeout: Response(b"<html>error</html>"))
    with pytest.raises(ValueError, match="ZIP signature"):
        pipeline.fetch_archive(
            "https://example.invalid/data.zip", tmp_path,
            3, datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc),
        )


def test_write_summary_writes_success_and_failure_reports(tmp_path):
    started = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    stages = [{"stage": "download", "status": "failed", "stderr": "offline", "stdout": ""}]
    markdown_path, json_path = pipeline.write_summary(
        tmp_path, started, stages, None, tmp_path / "candidate", "failed"
    )
    assert markdown_path.exists()
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["stages"][0]["stderr"] == "offline"
    assert "FAILED" in markdown_path.read_text(encoding="utf-8")

def test_publish_candidate_replaces_existing_output_and_removes_backup(tmp_path):
    output_dir = tmp_path / "candidate"
    output_dir.mkdir()
    (output_dir / "old.json").write_text("old", encoding="utf-8")
    staging_dir = pipeline.create_staging_dir(output_dir)
    (staging_dir / "new.json").write_text("new", encoding="utf-8")

    pipeline.publish_candidate(staging_dir, output_dir)

    assert not staging_dir.exists()
    assert not (output_dir / "old.json").exists()
    assert (output_dir / "new.json").read_text(encoding="utf-8") == "new"
    assert not list(tmp_path.glob(".candidate.backup-*"))


def test_publish_candidate_keeps_existing_output_if_staging_rename_fails(tmp_path, monkeypatch):
    output_dir = tmp_path / "candidate"
    output_dir.mkdir()
    (output_dir / "known-good.json").write_text("known-good", encoding="utf-8")
    staging_dir = pipeline.create_staging_dir(output_dir)
    (staging_dir / "new.json").write_text("new", encoding="utf-8")
    real_rename = pipeline.Path.rename

    def fail_staging_rename(path, target):
        if path == staging_dir:
            raise OSError("simulated publish failure")
        return real_rename(path, target)

    monkeypatch.setattr(pipeline.Path, "rename", fail_staging_rename)
    with pytest.raises(OSError, match="simulated publish failure"):
        pipeline.publish_candidate(staging_dir, output_dir)

    assert (output_dir / "known-good.json").read_text(encoding="utf-8") == "known-good"
    assert not (output_dir / "new.json").exists()
    assert staging_dir.exists()
    assert not list(tmp_path.glob(".candidate.backup-*"))

