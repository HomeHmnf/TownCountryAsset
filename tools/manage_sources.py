"""Unified project-wide source management CLI."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from tools.sources.registry import REGISTRY, SourceError, load_registry, inspect_snapshots, acquire_one, check_online

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--registry",type=Path,default=REGISTRY); p.add_argument("--timeout",type=int,default=60)
 sub=p.add_subparsers(dest="command",required=True); sub.add_parser("list"); show=sub.add_parser("show"); show.add_argument("source_id")
 check=sub.add_parser("check"); check.add_argument("--online",action="store_true")
 acq=sub.add_parser("acquire"); group=acq.add_mutually_exclusive_group(required=True); group.add_argument("--all",action="store_true"); group.add_argument("--source")
 sub.add_parser("status"); sub.add_parser("licenses")
 args=p.parse_args(argv)
 try:
  registry=load_registry(args.registry); sources=registry["sources"]
  if args.command=="list":
   for sid,s in sources.items(): print(f"{sid}\\t{s['name']}\\t{s.get('acquisition_mode','manual')}\\t{len(s.get('downloads',[]))} download(s)")
  elif args.command=="show":
   if args.source_id not in sources: raise SourceError(f"Unknown source: {args.source_id}")
   print(json.dumps({"source_id":args.source_id,**sources[args.source_id]},indent=2,ensure_ascii=False))
  elif args.command in {"status","check"}:
   rows=inspect_snapshots(registry)
   if args.command=="check" and args.online: 
    online=check_online(registry,min(args.timeout,60)); print(json.dumps({"snapshots":rows,"online":online},indent=2)); return 1 if any(x["status"]!="valid" for x in rows) or any(x["status"]!="reachable" for x in online) else 0
   print(json.dumps(rows,indent=2)); return 1 if args.command=="check" and any(x["status"]!="valid" for x in rows) else 0
  elif args.command=="licenses":
   for sid,s in sources.items(): print(f"{sid}\\t{s.get('license_status','unclear_or_unverified')}\\t{s.get('terms_url') or 'terms URL not recorded'}")
  elif args.command=="acquire":
   selected=[(sid,s) for sid,s in sources.items() if args.all or sid==args.source]
   if args.source and args.source not in sources: raise SourceError(f"Unknown source: {args.source}")
   outcomes=[]
   for sid,s in selected:
    for item in s.get("downloads",[]):
     try: outcomes.append({"source_id":sid,"download_id":item["id"],"status":"acquired","manifest":acquire_one(registry,sid,item,args.timeout)})
     except Exception as exc: outcomes.append({"source_id":sid,"download_id":item["id"],"status":"failed","error":str(exc)})
   print(json.dumps(outcomes,indent=2,ensure_ascii=False)); return 1 if any(x["status"]=="failed" for x in outcomes) else 0
  return 0
 except SourceError as exc: print(f"ERROR: {exc}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
