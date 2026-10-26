from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from tools.generate_country_flags import (
    audit_and_generate,
    load_config,
    load_latest_source,
    load_source_svgs,
    publish_flags,
    sha256_bytes,
    validate_svg,
    write_source_previews,
)


def svg(label: str = "flag") -> bytes:
    return f'<svg xmlns="http://www.w3.org/2000/svg"><title>{label}</title></svg>'.encode()


def registry(*ids: str) -> dict:
    return {"records": [{"game_id": item} for item in ids]}


def mapping(*pairs: tuple[str, str], status: str = "reviewed") -> dict:
    return {"records": [
        {"game_id": game_id, "source_flag_code": code, "status": status}
        for game_id, code in pairs
    ]}


def provenance() -> dict:
    return {
        "source_url": "https://github.com/lipis/flag-icons",
        "configured_ref": "main",
        "resolved_commit": "a" * 40,
        "retrieved_at_utc": "2026-10-22T00:00:00Z",
        "archive_sha256": "b" * 64,
        "license": "MIT",
        "license_sha256": "c" * 64,
        "archive_file": "flag-icons.zip",
    }


def test_audit_generates_deterministic_game_id_filenames() -> None:
    result = audit_and_generate(
        registry("tc_one", "tc_two"),
        mapping(("tc_one", "us"), ("tc_two", "gb")),
        {"us": svg("US"), "gb": svg("GB")},
        provenance(),
    )
    assert result["ok"] is True
    assert result["generated_count"] == 2
    assert set(result["generated"]) == {"tc_one.svg", "tc_two.svg"}
    assert [item["game_id"] for item in result["files"]] == ["tc_one", "tc_two"]
    assert result["files"][0]["sha256"] == sha256_bytes(svg("US"))


def test_audit_fails_for_unreviewed_mapping() -> None:
    result = audit_and_generate(
        registry("tc_one"), mapping(("tc_one", "us"), status="unreviewed"),
        {"us": svg()}, provenance(),
    )
    assert not result["ok"]
    assert result["generated_count"] == 0
    assert "expected 'reviewed'" in result["issues"][0]


def test_audit_reports_missing_mapping_and_unknown_mapping_id() -> None:
    result = audit_and_generate(
        registry("tc_one", "tc_two"),
        mapping(("tc_one", "us"), ("tc_unknown", "gb")),
        {"us": svg(), "gb": svg()},
        provenance(),
    )
    assert not result["ok"]
    assert any("missing flag mapping for game_id tc_two" in issue for issue in result["issues"])
    assert any("unknown game_id tc_unknown" in issue for issue in result["issues"])


def test_audit_rejects_duplicate_mapping_and_duplicate_source_code() -> None:
    duplicate_id = {"records": [
        {"game_id": "tc_one", "source_flag_code": "us", "status": "reviewed"},
        {"game_id": "tc_one", "source_flag_code": "gb", "status": "reviewed"},
    ]}
    result = audit_and_generate(registry("tc_one"), duplicate_id, {"us": svg(), "gb": svg()}, provenance())
    assert not result["ok"]
    assert any("duplicate mapping" in issue for issue in result["issues"])

    result = audit_and_generate(
        registry("tc_one", "tc_two"), mapping(("tc_one", "us"), ("tc_two", "us")),
        {"us": svg()}, provenance(),
    )
    assert not result["ok"]
    assert any("maps to both" in issue for issue in result["issues"])


@pytest.mark.parametrize("code", ["US", "usa", "1a", "../"])
def test_audit_rejects_invalid_source_code(code: str) -> None:
    result = audit_and_generate(registry("tc_one"), mapping(("tc_one", code)), {code: svg()}, provenance())
    assert not result["ok"]
    assert any("lowercase two-letter code" in issue for issue in result["issues"])


def test_audit_rejects_missing_and_malformed_source_svgs() -> None:
    result = audit_and_generate(registry("tc_one"), mapping(("tc_one", "us")), {}, provenance())
    assert not result["ok"]
    assert any("source SVG" in issue and "missing" in issue for issue in result["issues"])

    result = audit_and_generate(registry("tc_one"), mapping(("tc_one", "us")), {"us": b"<svg>"}, provenance())
    assert not result["ok"]
    assert any("malformed SVG XML" in issue for issue in result["issues"])


def test_validate_svg_rejects_empty_and_non_svg_xml() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_svg(b"  ", "test")
    with pytest.raises(ValueError, match="root is not svg"):
        validate_svg(b"<html/>", "test")


def test_load_source_svgs_reads_only_4x3_files_and_rejects_bad_paths(tmp_path: Path) -> None:
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("repo-abc/flags/4x3/us.svg", svg("US"))
        archive.writestr("repo-abc/flags/1x1/us.svg", svg("US square"))
        archive.writestr("repo-abc/flags/4x3/gb.svg", svg("GB"))
    assert load_source_svgs(archive_path) == {"us": svg("US"), "gb": svg("GB")}

    bad_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(bad_path, "w") as archive:
        archive.writestr("../flags/4x3/us.svg", svg())
    with pytest.raises(ValueError, match="unsafe path"):
        load_source_svgs(bad_path)


def test_load_latest_source_checks_archive_hash(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    archive.write_bytes(b"not the archive hash")
    (tmp_path / "provenance.json").write_text(json.dumps({
        **provenance(), "archive_sha256": "0" * 64
    }), encoding="utf-8")
    (tmp_path / "latest.json").write_text(json.dumps({
        "archive_file": archive.name,
        "provenance_file": "provenance.json",
        "resolved_commit": "a" * 40,
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        load_latest_source(tmp_path)


def test_publish_flags_writes_manifest_and_flag_files(tmp_path: Path) -> None:
    result = audit_and_generate(
        registry("tc_one"), mapping(("tc_one", "us")), {"us": svg()}, provenance()
    )
    output = tmp_path / "flags"
    publish_flags(output, result, {"us": svg("US"), "gb": svg("GB")})
    assert (output / "tc_one.svg").read_bytes() == svg()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["resolved_commit"] == "a" * 40
    assert manifest["flags"][0]["sha256"] == sha256_bytes(svg("US"))
    assert manifest["profiles"] == ["low", "medium", "high"]
    for profile in ("low", "medium", "high"):
        assert (output / profile / "tc_one.svg").is_file()
        assert (output / "source" / profile / "us.svg").is_file()
        root = ET.fromstring((output / profile / "tc_one.svg").read_bytes())
        assert root.attrib["width"] == "512"
        assert root.attrib["height"] == "384"
    preview_manifest = json.loads((output / "source" / "manifest.json").read_text(encoding="utf-8"))
    assert preview_manifest["purpose"].startswith("Unassigned source previews")
    assert preview_manifest["source_codes"] == ["gb", "us"]


def test_load_config_uses_process_environment_precedence(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TCA_FLAG_MAPPING=from-file.json\n", encoding="utf-8")
    config = load_config(env_file, {"TCA_FLAG_MAPPING": "from-env.json"})
    assert config["TCA_FLAG_MAPPING"] == "from-env.json"
    assert config["TCA_FLAG_SOURCE_DIR"] == "raw_data/flags"



def test_unreviewed_mappings_can_publish_unassigned_profile_previews(tmp_path: Path) -> None:
    output = tmp_path / "flags"
    write_source_previews(output, {"us": svg("US"), "gb": svg("GB")})
    manifest = json.loads((output / "source" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["width"] == 512
    assert manifest["height"] == 384
    assert manifest["profiles"] == ["low", "medium", "high"]
    for profile in ("low", "medium", "high"):
        assert set(path.name for path in (output / "source" / profile).glob("*.svg")) == {"us.svg", "gb.svg"}
        root = ET.fromstring((output / "source" / profile / "us.svg").read_bytes())
        assert root.attrib["width"] == "512"
        assert root.attrib["height"] == "384"
