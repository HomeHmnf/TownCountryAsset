from __future__ import annotations
import json
from pathlib import Path
import pytest
from tools import acquire_guinea_ins_national_accounts as acquisition

def _pdf(path: Path, payload: bytes=b"%PDF-1.7\\nfixture")->Path:
 path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(payload); return path

def test_existing_files_create_separate_manifests(tmp_path:Path)->None:
 for pub in acquisition.PUBLICATIONS: _pdf(tmp_path/pub["raw_path"])
 result=acquisition.acquire_guinea_ins_publications(repository_root=tmp_path,use_existing=True)
 assert result["acquisition_count"]==2 and not result["project_database_written"] and not result["game_database_written"]
 paths=[tmp_path/item["manifest_path"] for item in result["acquisitions"]]
 assert paths[0]!=paths[1]
 payloads=[json.loads(path.read_text()) for path in paths]
 assert {p["download_id"] for p in payloads}=={"national_accounts_legacy_2023","national_accounts_sna2008_2026"}
 assert all(p["retrieval_timestamp_basis"]=="filesystem_mtime_existing_manual_download" for p in payloads)
 assert all(p["files"][0]["sha256"]==acquisition._sha256(tmp_path/p["files"][0]["local_raw_path"]) for p in payloads)

def test_non_pdf_is_rejected(tmp_path:Path)->None:
 for pub in acquisition.PUBLICATIONS: _pdf(tmp_path/pub["raw_path"],b"not a pdf")
 with pytest.raises(ValueError,match="not a PDF"): acquisition.acquire_guinea_ins_publications(repository_root=tmp_path,use_existing=True)

def test_missing_existing_file_is_rejected(tmp_path:Path)->None:
 with pytest.raises(FileNotFoundError): acquisition.acquire_guinea_ins_publications(repository_root=tmp_path,use_existing=True)

def test_manifest_is_never_overwritten(tmp_path:Path)->None:
 for pub in acquisition.PUBLICATIONS: _pdf(tmp_path/pub["raw_path"])
 first=acquisition.acquire_guinea_ins_publications(repository_root=tmp_path,use_existing=True)
 first_path=tmp_path/first["acquisitions"][0]["manifest_path"]
 first_path.write_text("sentinel")
 with pytest.raises(FileExistsError,match="Refusing to overwrite"): acquisition.acquire_guinea_ins_publications(repository_root=tmp_path,use_existing=True)
