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
