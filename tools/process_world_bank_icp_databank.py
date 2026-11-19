"""Validate and register World Bank ICP DataBank saved-report acquisitions.

The Project DB receives acquisition/artifact provenance only. This workflow does not
load statistical observations, create approvals, change source selection, or write
the Game DB.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.audit_acquisition_manifests import audit_manifests
from tools.database.acquisition_registration import register_manifest_acquisitions
from tools.database.project_connection import DEFAULT_PROJECT_DATABASE_PATH
from tools.database.source_catalogue import sync_source_catalogue
from tools.database.dataset_catalogue import sync_dataset_catalogue
from tools.database.connection import REPOSITORY_ROOT
from tools.validate_world_bank_icp_databank import (
    ICPDataBankValidationError,
    validate_manifest,
)

MANIFEST_DIR = Path("data_manifests/sources/world_bank_icp/databank_exports")


def process_world_bank_icp_databank(
    *,
    repository_root: str | Path = REPOSITORY_ROOT,
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH,
    register: bool = False,
) -> dict[str, Any]:
    """Audit and semantically validate all ICP DataBank captures before DB registration."""
    root = Path(repository_root).resolve()
    audit = audit_manifests(repository_root=root, manifest_dir=MANIFEST_DIR)
    audit_summary = {
        "status": audit["status"],
        "manifest_count": audit["manifest_count"],
        "artifact_count": audit["artifact_count"],
        "error_count": audit["error_count"],
    }
    base = {
        "manifest_dir": MANIFEST_DIR.as_posix(),
        "audit": audit_summary,
        "project_database_written": False,
        "game_database_written": False,
        "observations_imported": False,
        "approval_created": False,
        "source_selection_changed": False,
        "canonical_data_promoted": False,
    }
    if audit["status"] != "ok":
        return {**base, "status": "blocked_manifest_integrity",
                "semantic_validations": [], "catalogue_sync_performed": False}
    if audit["manifest_count"] < 1:
        return {**base, "status": "blocked_no_acquisitions",
                "semantic_validations": [], "catalogue_sync_performed": False}

    validations = []
    for audited in audit["manifests"]:
        if audited["status"] != "ok":
            return {**base, "status": "blocked_manifest_integrity",
                    "semantic_validations": validations,
                    "catalogue_sync_performed": False}
        try:
            validation = validate_manifest(
                repository_root=root, manifest_path=audited["manifest_path"]
            )
        except (ICPDataBankValidationError, OSError, ValueError, json.JSONDecodeError) as exc:
            validations.append({
                "manifest_path": audited["manifest_path"],
                "status": "failed", "error": str(exc),
            })
            return {**base, "status": "blocked_semantic_validation",
                    "semantic_validations": validations,
                    "catalogue_sync_performed": False}
        validations.append(validation)

    sources = sync_source_catalogue(
        database_path=database_path,
        config_path=root / "config" / "data_sources.json",
    )
    datasets = sync_dataset_catalogue(
        database_path=database_path,
        config_path=root / "config" / "project_datasets.json",
    )
    preflight = register_manifest_acquisitions(
        database_path=database_path, repository_root=root,
        manifest_dir=MANIFEST_DIR, dry_run=True,
    )
    eligible_count = len(preflight["registered"]) + len(preflight["unchanged"])
    catalogue = {"sources": sources, "datasets": datasets}
    if (preflight["audit_status"] != "ok" or preflight["errors"]
            or preflight["deferred"] or eligible_count != audit["manifest_count"]):
        return {
            **base, "status": "blocked_registration_preflight",
            "semantic_validations": validations,
            "catalogue_sync": catalogue, "catalogue_sync_performed": True,
            "registration_preflight": preflight, "eligible_count": eligible_count,
            "project_database_written": True,
        }

    registration = None
    if register:
        registration = register_manifest_acquisitions(
            database_path=database_path, repository_root=root,
            manifest_dir=MANIFEST_DIR, dry_run=False,
        )
        if registration["audit_status"] != "ok" or registration["errors"] or registration["deferred"]:
            return {
                **base, "status": "registration_error",
                "semantic_validations": validations,
                "catalogue_sync": catalogue, "catalogue_sync_performed": True,
                "registration_preflight": preflight,
                "registration": registration, "eligible_count": eligible_count,
                "project_database_written": True,
            }

    return {
        **base,
        "status": "registered" if register else "ready_for_registration",
        "semantic_validations": validations,
        "catalogue_sync": catalogue,
        "catalogue_sync_performed": True,
        "registration_preflight": preflight,
        "registration": registration,
        "eligible_count": eligible_count,
        "project_database_written": True,
        "acquisition_provenance_registered": bool(register),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--database", type=Path, default=DEFAULT_PROJECT_DATABASE_PATH)
    parser.add_argument(
        "--register", action="store_true",
        help="Write validated acquisition/artifact provenance to the Project DB",
    )
    args = parser.parse_args(argv)
    result = process_world_bank_icp_databank(
        repository_root=args.root, database_path=args.database, register=args.register
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready_for_registration", "registered"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
