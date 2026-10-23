from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from tools.refresh_flag_source import (
    load_config,
    repository_parts,
    sha256_bytes,
    validate_archive,
)


def make_archive(*, license_text: str = "MIT License\nPermission is hereby granted.", svg_name: str = "flag-icons-main/flags/4x3/us.svg") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("flag-icons-main/LICENSE", license_text)
        archive.writestr(svg_name, '<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    return buffer.getvalue()


def test_repository_parts_accepts_github_repo_url() -> None:
    assert repository_parts("https://github.com/lipis/flag-icons") == ("lipis", "flag-icons")
    assert repository_parts("https://github.com/lipis/flag-icons.git/") == ("lipis", "flag-icons")


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/lipis/flag-icons",
        "https://example.com/lipis/flag-icons",
        "https://github.com/lipis",
        "https://github.com/lipis/flag-icons/tree/main",
    ],
)
def test_repository_parts_rejects_non_repository_urls(url: str) -> None:
    with pytest.raises(ValueError):
        repository_parts(url)


def test_validate_archive_reports_svg_and_license_provenance() -> None:
    archive = make_archive()
    result = validate_archive(archive)
    assert result["svg_file_count"] == 1
    assert result["license_archive_path"] == "flag-icons-main/LICENSE"
    assert result["license_sha256"] == sha256_bytes(result["license_text"].encode("utf-8"))


def test_validate_archive_rejects_missing_license() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("repo/flags/4x3/us.svg", "<svg/>")
    with pytest.raises(ValueError, match="license"):
        validate_archive(buffer.getvalue())


def test_validate_archive_rejects_non_mit_license() -> None:
    with pytest.raises(ValueError, match="MIT"):
        validate_archive(make_archive(license_text="All rights reserved."))


def test_validate_archive_rejects_archive_path_traversal() -> None:
    with pytest.raises(ValueError, match="unsafe path"):
        validate_archive(make_archive(svg_name="repo/flags/../../outside.svg"))


def test_validate_archive_rejects_archive_without_flag_svgs() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("repo/LICENSE", "MIT License\nPermission is hereby granted.")
        archive.writestr("repo/README.md", "not flags")
    with pytest.raises(ValueError, match="no SVG"):
        validate_archive(buffer.getvalue())


def test_load_config_defaults_and_environment_precedence(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TCA_FLAG_SOURCE_URL=https://github.com/example/flags\n"
        "TCA_FLAG_SOURCE_REF=release-tag\n",
        encoding="utf-8",
    )
    config = load_config(env_file, {"TCA_FLAG_SOURCE_REF": "pinned-ref"})
    assert config["TCA_FLAG_SOURCE_URL"] == "https://github.com/example/flags"
    assert config["TCA_FLAG_SOURCE_REF"] == "pinned-ref"
    assert config["TCA_FLAG_SOURCE_DIR"] == "raw_data/flags"


def test_load_config_rejects_malformed_line(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("not-an-assignment\n", encoding="utf-8")
    with pytest.raises(ValueError, match="KEY=VALUE"):
        load_config(env_file, {})
