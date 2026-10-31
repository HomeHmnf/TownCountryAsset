from __future__ import annotations
import hashlib,json
from pathlib import Path
import pytest
from tools.sources.registry import load_registry,inspect_snapshots,acquire_one,SourceError

def fixture(tmp_path):
 p=tmp_path/"registry.json"; p.write_text(json.dumps({"schema_version":1,"storage":{"raw_root":"raw","manifest_root":"manifests"},"sources":{"sample":{"name":"Sample","downloads":[{"id":"dataset","release":"v1","filename":"data.csv","url":"https://example.test/data.csv","format":"csv"}]}}}),encoding="utf-8"); return p
class Response:
 headers={"Content-Type":"text/csv"}
 def __init__(self,b): self.b=b
 def __enter__(self): return self
 def __exit__(self,*a): return False
 def geturl(self): return "https://example.test/data.csv"
 def read(self,n=-1): out=self.b[:n] if n>=0 else self.b; self.b=self.b[len(out):]; return out

def test_registry_validates_and_rejects_http(tmp_path):
 p=fixture(tmp_path); assert "sample" in load_registry(p)["sources"]
 d=json.loads(p.read_text()); d["sources"]["sample"]["downloads"][0]["url"]="http://example.test/a"; p.write_text(json.dumps(d))
 with pytest.raises(SourceError,match="HTTPS"): load_registry(p)

def test_acquisition_creates_manifest_and_status_verifies_checksum(tmp_path,monkeypatch):
 import tools.sources.registry as module
 p=fixture(tmp_path); registry=load_registry(p); payload=b"a,b\\n1,2\\n"
 monkeypatch.setattr(module.urllib.request,"urlopen",lambda *a,**k:Response(payload))
 meta=acquire_one(registry,"sample",registry["sources"]["sample"]["downloads"][0])
 assert meta["sha256"]==hashlib.sha256(payload).hexdigest()
 rows=inspect_snapshots(registry); assert rows[0]["status"]=="valid"

def test_existing_snapshot_is_never_overwritten(tmp_path,monkeypatch):
 import tools.sources.registry as module
 p=fixture(tmp_path); registry=load_registry(p); item=registry["sources"]["sample"]["downloads"][0]
 raw=tmp_path/"raw/sample/dataset/v1/data.csv"; raw.parent.mkdir(parents=True); raw.write_bytes(b"original")
 monkeypatch.setattr(module.urllib.request,"urlopen",lambda *a,**k:Response(b"new"))
 with pytest.raises(SourceError,match="already exists"): acquire_one(registry,"sample",item)
 assert raw.read_bytes()==b"original"


def test_project_registry_contains_wp1_5_field_sources_without_contract_duplication():
    registry = json.loads((Path(__file__).resolve().parents[1] / "config/data_sources.json").read_text(encoding="utf-8"))
    contract = json.loads((Path(__file__).resolve().parents[1] / "config/wp1_5_data_sources.json").read_text(encoding="utf-8"))
    assert "sources" not in contract
    assert len(contract["fields"]) == 41
    for field in contract["fields"]:
        assert field["primary_source"] in registry["sources"]
        assert field["id"] in registry["sources"][field["primary_source"]].get("field_ids", [])


def test_expected_checksum_mismatch_removes_download(tmp_path, monkeypatch):
    import tools.sources.registry as module
    path = fixture(tmp_path)
    registry = load_registry(path)
    item = registry["sources"]["sample"]["downloads"][0]
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: Response(b"payload"))
    with pytest.raises(SourceError, match="SHA-256 mismatch"):
        acquire_one(registry, "sample", item, expected_sha256="0" * 64)
    raw = tmp_path / "raw/sample/dataset/v1/data.csv"
    assert not raw.exists()


def test_html_page_contract_is_reusable_and_enforced(tmp_path, monkeypatch):
    import tools.sources.registry as module

    path = fixture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    item = data["sources"]["sample"]["downloads"][0]
    item["filename"] = "overview.html"
    item["format"] = "html"
    item["validation"] = {
        "content_types": ["text/html"],
        "required_text": ["Country or Area", "M49 Code", "ISO-alpha2 Code", "ISO-alpha3 Code"],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    registry = load_registry(path)
    item = registry["sources"]["sample"]["downloads"][0]
    html = (
        "<html><table><th>Country or Area</th><th>M49 Code</th>"
        "<th>ISO-alpha2 Code</th><th>ISO-alpha3 Code</th></table></html>"
    ).encode()

    class HtmlResponse(Response):
        headers = {"Content-Type": "text/html; charset=utf-8"}

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: HtmlResponse(html))
    meta = acquire_one(registry, "sample", item)
    assert meta["format"] == "html"
    assert meta["validation_contract"] == item["validation"]
    assert inspect_snapshots(registry)[0]["status"] == "valid"


def test_html_page_contract_rejects_changed_page_and_removes_snapshot(tmp_path, monkeypatch):
    import tools.sources.registry as module

    path = fixture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    item = data["sources"]["sample"]["downloads"][0]
    item["filename"] = "overview.html"
    item["validation"] = {
        "content_types": ["text/html"],
        "required_text": ["Country or Area", "M49 Code", "ISO-alpha2 Code", "ISO-alpha3 Code"],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    registry = load_registry(path)
    item = registry["sources"]["sample"]["downloads"][0]

    class HtmlResponse(Response):
        headers = {"Content-Type": "text/html; charset=utf-8"}

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: HtmlResponse(b"<html>changed layout</html>"))
    with pytest.raises(SourceError, match="required-text validation"):
        acquire_one(registry, "sample", item)
    raw = tmp_path / "raw/sample/dataset/v1/overview.html"
    assert not raw.exists()
