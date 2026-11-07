"""Audit, synchronize and optionally register Turkmenistan evidence captures.

The default mode is a read-only registration preflight after idempotent catalogue
synchronization. Pass --register only after reviewing the preflight output to write
the three verified acquisition events to the Project DB.
"""
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

SOURCE_MANIFEST_DIRS = (
    Path("data_manifests/sources/turkmenistan_state_statistics"),
    Path("data_manifests/sources/imf_turkmenistan_research"),
)
EXPECTED_MANIFEST_COUNT = 3


def process_turkmenistan_evidence(
    *,
    repository_root: str | Path = REPOSITORY_ROOT,
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH,
    register: bool = False,
) -> dict[str, Any]:
    """Audit captures, sync catalogues, preflight registration, optionally write."""
    root = Path(repository_root).resolve()
    audits: list[dict[str, Any]] = []
    for manifest_dir in SOURCE_MANIFEST_DIRS:
        result = audit_manifests(
            repository_root=root,
            manifest_dir=manifest_dir,
        )
        audits.append({
            "manifest_dir": manifest_dir.as_posix(),
            "status": result["status"],
            "manifest_count": result["manifest_count"],
            "artifact_count": result["artifact_count"],
            "error_count": result["error_count"],
        })
        if result["status"] != "ok":
            return {
                "status": "blocked_manifest_integrity",
                "audits": audits,
                "catalogue_sync": None,
                "registration_preflight": [],
                "registered": [],
                "project_database_written": False,
                "game_database_written": False,
            }

    manifest_count = sum(item["manifest_count"] for item in audits)
    if manifest_count != EXPECTED_MANIFEST_COUNT:
        return {
            "status": "blocked_unexpected_manifest_count",
            "audits": audits,
            "expected_manifest_count": EXPECTED_MANIFEST_COUNT,
            "project_database_written": False,
            "game_database_written": False,
        }

    source_counts = sync_source_catalogue(
        database_path=database_path,
        config_path=root / "config" / "data_sources.json",
    )
    dataset_counts = sync_dataset_catalogue(
        database_path=database_path,
        config_path=root / "config" / "project_datasets.json",
    )
    preflight: list[dict[str, Any]] = []
    for manifest_dir in SOURCE_MANIFEST_DIRS:
        result = register_manifest_acquisitions(
            database_path=database_path,
            repository_root=root,
            manifest_dir=manifest_dir,
            dry_run=True,
        )
        preflight.append(result)

    eligible_count = sum(len(item["registered"]) for item in preflight)
    error_count = sum(len(item["errors"]) for item in preflight)
    deferred_count = sum(len(item["deferred"]) for item in preflight)
    if (
        error_count
        or deferred_count
        or eligible_count != EXPECTED_MANIFEST_COUNT
        or any(item["audit_status"] != "ok" for item in preflight)
    ):
        return {
            "status": "blocked_registration_preflight",
            "audits": audits,
            "catalogue_sync": {
                "sources": source_counts,
                "datasets": dataset_counts,
            },
            "registration_preflight": preflight,
            "eligible_count": eligible_count,
            "error_count": error_count,
            "deferred_count": deferred_count,
            "registered": [],
            "project_database_written": False,
            "game_database_written": False,
        }

    registered: list[dict[str, Any]] = []
    if register:
        for manifest_dir in SOURCE_MANIFEST_DIRS:
            result = register_manifest_acquisitions(
                database_path=database_path,
                repository_root=root,
                manifest_dir=manifest_dir,
                dry_run=False,
            )
            if result["errors"] or result["deferred"]:
                raise RuntimeError(
                    "Registration changed state but returned errors/deferred items; "
                    "inspect Project DB and reconcile before retrying."
                )
            registered.extend(result["registered"])

    return {
        "status": "registered" if register else "ready_for_registration",
        "audits": audits,
        "catalogue_sync": {
            "sources": source_counts,
            "datasets": dataset_counts,
        },
        "registration_preflight": preflight,
        "eligible_count": eligible_count,
        "registered": registered,
        "project_database_written": bool(register and registered),
        "game_database_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--database", type=Path, default=DEFAULT_PROJECT_DATABASE_PATH)
    parser.add_argument(
        "--register",
        action="store_true",
        help="Write the preflight-verified acquisition events to the Project DB.",
    )
    args = parser.parse_args()
    result = process_turkmenistan_evidence(
        repository_root=args.root,
        database_path=args.database,
        register=args.register,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready_for_registration", "registered"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
