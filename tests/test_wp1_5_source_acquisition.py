from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import pytest
from tools.database.source_acquisition import SourceAcquisitionError, acquire_source_snapshot

class FakeResponse:
    def __init__(self, payload):
        self.stream = io.BytesIO(payload)
        self.headers = {"Content-Type": "text/csv"}
    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def read(self, size=-1): return self.stream.read(size)
    def geturl(self): return "https://data.example.test/release.csv"

def config_file(tmp_path: Path):
    path = tmp_path / "source-contract.json"
    path.write_text(json.dumps({"work_package":"WP1.5","sources":{"fixture":{"name":"Fixture"}}}), encoding="utf-8")
    return path

def test_download_creates_raw_snapshot_and_manifest(tmp_path, monkeypatch):
    data = b"country,value\nAAA,3\n"
    monkeypatch.setattr("tools.database.source_acquisition.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(data))
    result = acquire_source_snapshot(source_key="fixture", release="2026-10", url="https://data.example.test/release.csv",
        filename="data.csv", config_path=config_file(tmp_path), raw_root=tmp_path/"raw", manifest_root=tmp_path/"manifests")
    raw = tmp_path/"raw/fixture/2026-10/data.csv"
    manifest = tmp_path/"manifests/fixture/2026-10.json"
    assert raw.read_bytes() == data
    assert manifest.exists()
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["byte_count"] == len(data)
    assert json.loads(manifest.read_text(encoding="utf-8"))["filename"] == "data.csv"

def test_existing_snapshot_is_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.database.source_acquisition.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(b"replacement"))
    raw_root = tmp_path/"raw"
    target = raw_root/"fixture/2026-10/data.csv"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"original")
    with pytest.raises(SourceAcquisitionError, match="already exists"):
        acquire_source_snapshot(source_key="fixture", release="2026-10", url="https://data.example.test/data.csv",
            filename="data.csv", config_path=config_file(tmp_path), raw_root=raw_root, manifest_root=tmp_path/"manifests")
    assert target.read_bytes() == b"original"

@pytest.mark.parametrize("url", ["http://example.test/data.csv", "file:///tmp/data.csv", "https:///missing-host"])
def test_only_https_urls_are_accepted(tmp_path, url):
    with pytest.raises(SourceAcquisitionError, match="HTTPS"):
        acquire_source_snapshot(source_key="fixture", release="2026-10", url=url, filename="data.csv",
            config_path=config_file(tmp_path), raw_root=tmp_path/"raw", manifest_root=tmp_path/"manifests")

def test_unknown_source_and_path_traversal_are_rejected(tmp_path):
    common = dict(release="2026-10", url="https://data.example.test/data.csv", filename="data.csv",
        config_path=config_file(tmp_path), raw_root=tmp_path/"raw", manifest_root=tmp_path/"manifests")
    with pytest.raises(SourceAcquisitionError, match="Unknown source"):
        acquire_source_snapshot(source_key="missing", **common)
    with pytest.raises(SourceAcquisitionError, match="simple filename"):
        acquire_source_snapshot(source_key="fixture", release="../escape", **{k:v for k,v in common.items() if k!="release"})

def test_checksum_mismatch_removes_untrusted_file(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.database.source_acquisition.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(b"payload"))
    raw_root = tmp_path/"raw"
    with pytest.raises(SourceAcquisitionError, match="SHA-256 mismatch"):
        acquire_source_snapshot(source_key="fixture", release="2026-10", url="https://data.example.test/data.csv",
            filename="data.csv", expected_sha256="0"*64, config_path=config_file(tmp_path),
            raw_root=raw_root, manifest_root=tmp_path/"manifests")
    assert not (raw_root/"fixture/2026-10/data.csv").exists()
