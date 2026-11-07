from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import acquire_turkmenistan_evidence as acquisition


def _artifact(path: Path, kind: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        b"%PDF-1.7\\nfixture"
        if kind == "pdf"
        else b"<!doctype html><html><body>fixture</body></html>"
    )
    path.write_bytes(payload)
    return path


def test_existing_evidence_creates_five_distinct_manifests(tmp_path: Path) -> None:
    for publication in acquisition.PUBLICATIONS:
        _artifact(tmp_path / publication["raw_path"], publication["signature"])

    result = acquisition.acquire_turkmenistan_evidence(
        repository_root=tmp_path, use_existing=True
    )

    assert result["acquisition_count"] == 5
    assert not result["project_database_written"]
    assert not result["game_database_written"]
    assert not result["semantic_validation"]
    manifests = [tmp_path / item["manifest_path"] for item in result["acquisitions"]]
    assert len(set(manifests)) == 5
    payloads = [json.loads(path.read_text()) for path in manifests]
    assert {item["download_id"] for item in payloads} == {
        publication["dataset_id"] for publication in acquisition.PUBLICATIONS
    }
    assert all(
        item["retrieval_timestamp_basis"] == "filesystem_mtime_existing_manual_download"
        for item in payloads
    )
    for publication, payload in zip(acquisition.PUBLICATIONS, payloads, strict=True):
        artifact = tmp_path / publication["raw_path"]
        assert payload["files"][0]["sha256"] == acquisition._sha256(artifact)
        assert payload["files"][0]["byte_count"] == artifact.stat().st_size


def test_pdf_and_html_signatures_are_not_interchangeable(tmp_path: Path) -> None:
    path = tmp_path / "wrong.html"
    path.write_bytes(b"<!doctype html><html></html>")
    with pytest.raises(ValueError, match="not a PDF"):
        acquisition._validate(path, "pdf")


def test_missing_existing_artifact_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        acquisition.acquire_turkmenistan_evidence(
            repository_root=tmp_path, use_existing=True
        )


def test_existing_manifest_is_never_overwritten(tmp_path: Path) -> None:
    for publication in acquisition.PUBLICATIONS:
        _artifact(tmp_path / publication["raw_path"], publication["signature"])
    first = acquisition.acquire_turkmenistan_evidence(
        repository_root=tmp_path, use_existing=True
    )
    manifest = tmp_path / first["acquisitions"][0]["manifest_path"]
    manifest.write_text("sentinel", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        acquisition.acquire_turkmenistan_evidence(
            repository_root=tmp_path, use_existing=True
        )
