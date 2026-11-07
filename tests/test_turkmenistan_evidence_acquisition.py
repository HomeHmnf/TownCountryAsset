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
        else (
            b'<?xml version="1.0" encoding="UTF-8"?><article>fixture</article>'
            if kind == "xml"
            else (
                b'{"title":"IMF Staff Completes 2025 Article IV Mission to Turkmenistan","publishDate":"2025-06-10","sourceUrl":"https://www.imf.org/en/news/articles/2025/06/10/pr-25190-turkmenistan-imf-completes-2025-article-iv-mission","sections":[]}'
                if kind == "json"
                else b"<!doctype html><html><body>fixture</body></html>"
            )
        )
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


def test_download_tries_fallback_after_forbidden_primary_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from io import BytesIO
    from urllib.error import HTTPError
    from email.message import Message

    calls: list[str] = []

    class Response:
        status = 200
        headers = Message()
        def __enter__(self):
            self.headers["Content-Type"] = "application/pdf"
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b"%PDF-1.7\\nvalid fixture"
        def geturl(self):
            return "https://publisher.example/fallback.pdf"

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 403, "Forbidden", {}, None)
        return Response()

    monkeypatch.setattr(acquisition, "urlopen", fake_urlopen)
    destination = tmp_path / "paper.pdf"
    final_url, content_type, byte_count = acquisition._download(
        ["https://imf.example/blocked.pdf", "https://elibrary.example/paper.pdf"],
        destination,
        "pdf",
        1,
        0,
    )
    assert calls == [
        "https://imf.example/blocked.pdf",
        "https://elibrary.example/paper.pdf",
    ]
    assert final_url == "https://publisher.example/fallback.pdf"
    assert content_type == "application/pdf"
    assert byte_count == destination.stat().st_size



def test_xml_and_pdf_signatures_are_not_interchangeable(tmp_path: Path) -> None:
    path = tmp_path / "wrong.xml"
    path.write_bytes(b"<?xml version='1.0'?><article/>")
    acquisition._validate(path, "xml")
    non_xml = tmp_path / "not-xml.pdf"
    non_xml.write_bytes(b"%PDF-1.7\\nnot XML")
    with pytest.raises(ValueError, match="not an XML"):
        acquisition._validate(non_xml, "xml")


def test_download_mode_resumes_without_overwriting_completed_acquisitions(
    tmp_path: Path,
) -> None:
    for publication in acquisition.PUBLICATIONS:
        _artifact(tmp_path / publication["raw_path"], publication["signature"])
    first = acquisition.acquire_turkmenistan_evidence(
        repository_root=tmp_path, use_existing=True
    )
    original_hashes = {
        publication["dataset_id"]: acquisition._sha256(tmp_path / publication["raw_path"])
        for publication in acquisition.PUBLICATIONS
    }

    resumed = acquisition.acquire_turkmenistan_evidence(repository_root=tmp_path)

    assert resumed["acquisition_count"] == 0
    assert resumed["skipped_existing_count"] == 5
    assert len(resumed["skipped_existing"]) == 5
    assert all(item["status"] == "already_acquired_verified" for item in resumed["skipped_existing"])
    assert original_hashes == {
        publication["dataset_id"]: acquisition._sha256(tmp_path / publication["raw_path"])
        for publication in acquisition.PUBLICATIONS
    }
    assert all((tmp_path / item["manifest_path"]).is_file() for item in first["acquisitions"])


def test_download_mode_refuses_unmanifested_existing_raw_artifact(tmp_path: Path) -> None:
    publication = acquisition.PUBLICATIONS[0]
    _artifact(tmp_path / publication["raw_path"], publication["signature"])
    with pytest.raises(FileExistsError, match="without a manifest"):
        acquisition.acquire_turkmenistan_evidence(repository_root=tmp_path)


def test_imf_mission_statement_uses_official_json_alternate_and_validates_identity(
    tmp_path: Path,
) -> None:
    publication = next(
        item for item in acquisition.PUBLICATIONS
        if item["dataset_id"] == "article_iv_mission_2025"
    )
    assert publication["url"].startswith("https://www.imf.org/")
    assert publication["url_fallbacks"] == [
        "https://www.imf.org/en/news/articles/2025/06/10/pr-25190-turkmenistan-imf-completes-2025-article-iv-mission/index.json"
    ]
    assert publication["signature"] == "json"
    assert publication["format"] == "json"
    assert publication["raw_path"].endswith(".json")

    valid = tmp_path / "valid.json"
    valid.write_text(
        json.dumps({
            "title": publication["expected_json_title"],
            "publishDate": publication["expected_json_publication_date"],
            "sourceUrl": publication["url"],
            "sections": [],
        }),
        encoding="utf-8",
    )
    acquisition._validate(valid, "json")

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"title":"wrong"}', encoding="utf-8")
    with pytest.raises(ValueError, match="expected IMF publication structure"):
        acquisition._validate(invalid, "json")


def test_batch_continues_after_one_publication_transport_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed_id = "article_iv_mission_2025"

    def fake_download(urls, destination, signature, timeout, retries):
        if failed_id in str(destination):
            raise RuntimeError("All publisher URL candidates failed: HTTP 403")
        _artifact(destination, signature)
        return urls[0], "application/json" if signature == "json" else "text/html", destination.stat().st_size

    monkeypatch.setattr(acquisition, "_download", fake_download)
    result = acquisition.acquire_turkmenistan_evidence(repository_root=tmp_path)

    assert result["failure_count"] == 1
    assert result["failures"][0]["dataset_id"] == failed_id
    assert result["failures"][0]["status"] == "acquisition_failed_no_manifest"
    assert result["acquisition_count"] == 4
    assert any(
        item["dataset_id"] == "article_iv_mission_2026"
        for item in result["acquisitions"]
    )
    failed_publication = next(
        item for item in acquisition.PUBLICATIONS
        if item["dataset_id"] == failed_id
    )
    assert not (tmp_path / failed_publication["raw_path"]).exists()
    assert not list((tmp_path / failed_publication["manifest_dir"]).glob("*.json")) if (tmp_path / failed_publication["manifest_dir"]).exists() else True


def test_manual_imf_json_capture_checks_publication_identity(tmp_path: Path) -> None:
    for publication in acquisition.PUBLICATIONS:
        artifact = _artifact(tmp_path / publication["raw_path"], publication["signature"])
        if publication["signature"] == "json":
            artifact.write_text(
                json.dumps({
                    "title": "A different IMF publication",
                    "publishDate": publication["expected_json_publication_date"],
                    "sourceUrl": publication["url"],
                    "sections": [],
                }),
                encoding="utf-8",
            )
    with pytest.raises(ValueError, match="Existing JSON publication identity"):
        acquisition.acquire_turkmenistan_evidence(
            repository_root=tmp_path, use_existing=True
        )
