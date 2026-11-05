from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.sources import pdf_text


def fake_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\nminimal test fixture")


class FakePage:
    def __init__(self, text: str):
        self.text = text

    def extract_text(self):
        return self.text


class FakeReader:
    def __init__(self, _path: str, strict: bool = True):
        assert strict is True
        self.pages = [FakePage("First page text"), FakePage("Second page text")]
        self.metadata = {"/Title": "Fixture"}


def test_extracts_pdf_text_and_records_both_fingerprints(tmp_path, monkeypatch):
    source = tmp_path / "raw_data" / "sources" / "sample" / "report.pdf"
    fake_pdf(source)
    monkeypatch.setattr("pypdf.PdfReader", FakeReader, raising=False)
    result = pdf_text.extract_pdf_text(source, tmp_path / "derived")
    text_path = Path(result["text_path"])
    metadata_path = Path(result["metadata_path"])

    assert result["status"] == "text_extracted"
    assert result["page_count"] == 2
    assert result["pages_with_text"] == 2
    assert result["pages"] == ["First page text", "Second page text"]
    assert text_path.is_file() and metadata_path.is_file()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert metadata["text_sha256"] == hashlib.sha256(text_path.read_bytes()).hexdigest()


def test_reuses_matching_sidecar_without_overwriting(tmp_path, monkeypatch):
    source = tmp_path / "raw_data" / "sample.pdf"
    fake_pdf(source)
    monkeypatch.setattr("pypdf.PdfReader", FakeReader, raising=False)
    output = tmp_path / "derived"
    first = pdf_text.extract_pdf_text(source, output)
    second = pdf_text.extract_pdf_text(source, output)

    assert first["reused"] is False
    assert second["reused"] is True
    assert Path(first["text_path"]).read_bytes() == Path(second["text_path"]).read_bytes()


def test_rejects_stale_sidecar_when_source_fingerprint_changes(tmp_path, monkeypatch):
    source = tmp_path / "raw_data" / "sample.pdf"
    fake_pdf(source)
    monkeypatch.setattr("pypdf.PdfReader", FakeReader, raising=False)
    output = tmp_path / "derived"
    pdf_text.extract_pdf_text(source, output)
    source.write_bytes(b"%PDF-1.7\nchanged source")

    with pytest.raises(pdf_text.PdfTextError, match="does not match its source"):
        pdf_text.extract_pdf_text(source, output)


def test_identifies_pdf_by_signature_not_extension(tmp_path, monkeypatch):
    source = tmp_path / "download.bin"
    fake_pdf(source)
    monkeypatch.setattr("pypdf.PdfReader", FakeReader, raising=False)
    result = pdf_text.extract_pdf_text(source, tmp_path / "derived")
    assert result["status"] == "text_extracted"


def test_ignores_non_pdf_files(tmp_path):
    source = tmp_path / "document.txt"
    source.write_text("plain text", encoding="utf-8")
    assert pdf_text.extract_pdf_text(source)["status"] == "not_pdf"


def test_tree_backfill_processes_all_pdfs_and_reports_failures(tmp_path, monkeypatch):
    raw = tmp_path / "raw_data"
    fake_pdf(raw / "a.pdf")
    fake_pdf(raw / "nested" / "b.pdf")
    (raw / "c.txt").write_text("not a PDF", encoding="utf-8")
    monkeypatch.setattr("pypdf.PdfReader", FakeReader, raising=False)

    report = pdf_text.extract_pdf_tree(raw, tmp_path / "derived")
    assert report["pdf_count"] == 2
    assert report["status_counts"] == {"text_extracted": 2}
