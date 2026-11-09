"""Audit and optionally register the two ZIMSTAT workbook acquisitions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.audit_acquisition_manifests import audit_manifests
from tools.database.acquisition_registration import register_manifest_acquisitions
from tools.database.connection import REPOSITORY_ROOT
from tools.database.dataset_catalogue import sync_dataset_catalogue
from tools.database.project_connection import DEFAULT_PROJECT_DATABASE_PATH
from tools.database.source_catalogue import sync_source_catalogue

SOURCE_MANIFEST_DIR = Path("data_manifests/sources/zimstat")
EXPECTED_MANIFEST_COUNT = 2


def process_zimbabwe_national_accounts(*, repository_root: str | Path = REPOSITORY_ROOT,
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH, register: bool = False) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    audit = audit_manifests(repository_root=root, manifest_dir=SOURCE_MANIFEST_DIR)
    summary = {"manifest_dir": SOURCE_MANIFEST_DIR.as_posix(), "status": audit["status"],
               "manifest_count": audit["manifest_count"], "artifact_count": audit["artifact_count"],
               "error_count": audit["error_count"]}
    if audit["status"] != "ok":
        return {"status":"blocked_manifest_integrity","audit":summary,
                "project_database_written":False,"game_database_written":False}
    if audit["manifest_count"] != EXPECTED_MANIFEST_COUNT:
        return {"status":"blocked_unexpected_manifest_count","audit":summary,
                "expected_manifest_count":EXPECTED_MANIFEST_COUNT,
                "project_database_written":False,"game_database_written":False}
    sources = sync_source_catalogue(database_path=database_path, config_path=root/"config"/"data_sources.json")
    datasets = sync_dataset_catalogue(database_path=database_path, config_path=root/"config"/"project_datasets.json")
    preflight = register_manifest_acquisitions(database_path=database_path, repository_root=root,
        manifest_dir=SOURCE_MANIFEST_DIR, dry_run=True)
    eligible = len(preflight["registered"])
    if (preflight["audit_status"] != "ok" or preflight["errors"] or preflight["deferred"]
            or eligible != EXPECTED_MANIFEST_COUNT):
        return {"status":"blocked_registration_preflight","audit":summary,
                "catalogue_sync":{"sources":sources,"datasets":datasets},
                "registration_preflight":preflight,"eligible_count":eligible,
                "project_database_written":False,"game_database_written":False}
    registered = []
    if register:
        result = register_manifest_acquisitions(database_path=database_path, repository_root=root,
            manifest_dir=SOURCE_MANIFEST_DIR, dry_run=False)
        if result["errors"] or result["deferred"]:
            raise RuntimeError("Registration returned errors/deferred records; inspect Project DB before retrying.")
        registered = result["registered"]
    return {"status":"registered" if register else "ready_for_registration","audit":summary,
            "catalogue_sync":{"sources":sources,"datasets":datasets},
            "registration_preflight":preflight,"eligible_count":eligible,"registered":registered,
            "project_database_written":bool(register and registered),"game_database_written":False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--database", type=Path, default=DEFAULT_PROJECT_DATABASE_PATH)
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args()
    result = process_zimbabwe_national_accounts(repository_root=args.root, database_path=args.database,
        register=args.register)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready_for_registration","registered"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
