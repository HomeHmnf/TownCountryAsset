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
    assert values["EXISTING"] == "kept"


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

