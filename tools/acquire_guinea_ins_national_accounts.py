"""Acquire two separately versioned Guinea INS national-accounts PDFs."""
from __future__ import annotations
import argparse, hashlib, json, time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any
from tools.database.connection import REPOSITORY_ROOT

PUBLICATIONS = (
 {"dataset_id":"national_accounts_legacy_2023","release":"2023-yearbook-legacy-sna1993","url":"https://www.stat-guinee.org/images/Documents/Publications/INS/annuelles/annuaire/La_Guinee_en_chiffre_2023.pdf","filename":"La_Guinee_en_chiffre_2023.pdf","raw_path":"raw_data/sources/guinea_ins/national_accounts/legacy_2023/La_Guinee_en_chiffre_2023.pdf","manifest_dir":"data_manifests/sources/guinea_ins/national_accounts_legacy_2023","publication_date":"2023"},
 {"dataset_id":"national_accounts_sna2008_2026","release":"june-2026-sna2008-2018-base-accounts","url":"https://stat-guinee.org/images/Documents/Publications/INS/annuelles/CN/Note_analyse_des_comptes_nationaux_definitifs_et_rapides_2018_2024_VC.pdf","filename":"Note_analyse_comptes_nationaux_2018_2024_June_2026.pdf","raw_path":"raw_data/sources/guinea_ins/national_accounts/sna2008_2026/Note_analyse_comptes_nationaux_2018_2024_June_2026.pdf","manifest_dir":"data_manifests/sources/guinea_ins/national_accounts_sna2008_2026","publication_date":"2026-06"},
)
def _sha256(path: Path) -> str:
 digest=hashlib.sha256()
 with path.open("rb") as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
 return digest.hexdigest()

def _download(url: str, destination: Path, timeout: float, retries: int) -> tuple[str,str,int]:
 destination.parent.mkdir(parents=True,exist_ok=True)
 last_error=None
 for attempt in range(retries+1):
  try:
   request=Request(url,headers={"User-Agent":"TownCountryAsset-source-acquisition/1.0"})
   with urlopen(request,timeout=timeout) as response:
    body=response.read(); final_url=response.geturl(); status=response.status
   if status!=200: raise ValueError(f"Unexpected HTTP status {status}: {url}")
   if not body.startswith(b"%PDF-"): raise ValueError(f"Response is not a PDF: {url}")
   temporary=destination.with_name(destination.name+".part")
   temporary.write_bytes(body); temporary.replace(destination)
   return final_url,"application/pdf",len(body)
  except HTTPError as exc:
   last_error=exc
   if exc.code not in {408,425,429,500,502,503,504}: raise
  except (URLError,TimeoutError,OSError) as exc: last_error=exc
  if attempt<retries: time.sleep(min(2**attempt,16))
 raise RuntimeError(f"Download failed after {retries+1} attempts: {url}: {last_error}")

def acquire_guinea_ins_publications(*,repository_root: str|Path=REPOSITORY_ROOT,use_existing: bool=False,timeout: float=120,retries: int=3)->dict[str,Any]:
 root=Path(repository_root).resolve(); results=[]
 for pub in PUBLICATIONS:
  raw=root/pub["raw_path"]; manifest_dir=root/pub["manifest_dir"]
  if use_existing:
   if not raw.is_file(): raise FileNotFoundError(f"Expected existing PDF: {pub['raw_path']}")
   final_url=pub["url"]; content_type="application/pdf"; byte_count=raw.stat().st_size
   retrieved_at=datetime.fromtimestamp(raw.stat().st_mtime).astimezone().isoformat()
   timestamp_basis="filesystem_mtime_existing_manual_download"
  else:
   final_url,content_type,byte_count=_download(pub["url"],raw,timeout,retries)
   retrieved_at=datetime.now().astimezone().isoformat()
   timestamp_basis="acquisition_tool_download_completion"
  if raw.read_bytes()[:5]!=b"%PDF-": raise ValueError(f"File is not a PDF: {pub['raw_path']}")
  digest=_sha256(raw); timestamp_id=datetime.fromisoformat(retrieved_at).astimezone().strftime("%Y%m%dT%H%M%S%f%z")
  manifest_dir.mkdir(parents=True,exist_ok=True); manifest_path=manifest_dir/f"{timestamp_id}.json"
  if manifest_path.exists(): raise FileExistsError(f"Refusing to overwrite acquisition manifest: {manifest_path}")
  manifest={"manifest_schema_version":1,"source_id":"guinea_ins","download_id":pub["dataset_id"],"release":pub["release"],"release_kind":"edition_or_snapshot","publication_date":pub["publication_date"],"retrieved_at":retrieved_at,"retrieval_timestamp_basis":timestamp_basis,"acquisition_method":"automated_https_download" if not use_existing else "existing_file_integrity_capture","files":[{"file_id":pub["filename"],"filename":pub["filename"],"local_raw_path":pub["raw_path"],"url":pub["url"],"final_url":final_url,"content_type":content_type,"format":"pdf","byte_count":byte_count,"sha256":digest}],"validation":{"pdf_signature_verified":True,"byte_count_verified":True,"sha256_calculated":True,"statistical_content_reviewed":False}}
  manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  results.append({"dataset_id":pub["dataset_id"],"raw_path":pub["raw_path"],"manifest_path":manifest_path.relative_to(root).as_posix(),"retrieved_at":retrieved_at,"timestamp_basis":timestamp_basis,"byte_count":byte_count,"sha256":digest})
 return {"source_id":"guinea_ins","acquisition_count":len(results),"acquisitions":results,"project_database_written":False,"game_database_written":False,"semantic_validation":False,"approval_or_promotion":False}

def main()->int:
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--root",type=Path,default=REPOSITORY_ROOT)
 parser.add_argument("--use-existing",action="store_true",help="Verify already downloaded PDFs; timestamp evidence is filesystem mtime.")
 parser.add_argument("--timeout",type=float,default=120); parser.add_argument("--retries",type=int,default=3)
 args=parser.parse_args()
 print(json.dumps(acquire_guinea_ins_publications(repository_root=args.root,use_existing=args.use_existing,timeout=args.timeout,retries=args.retries),ensure_ascii=False,indent=2))
 return 0
if __name__=="__main__": raise SystemExit(main())
