"""Register the evidenced IMF WEO October 2026 manual acquisition bundle.

This records byte-level provenance only. It does not semantically validate,
approve, retain, or apply the release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from tools import assess_imf_weo
from tools.database.connection import REPOSITORY_ROOT
from tools.database.project_connection import (
    DEFAULT_PROJECT_DATABASE_PATH,
    PROJECT_MIGRATIONS_DIR,
    connect_project_database,
)
from tools.database.schema import apply_migrations, utc_now

SOURCE_KEY = "imf_weo"
DATASET_KEY = "world_economic_outlook"
STREAM_KEY = "manual_vintage_bundle"
EVENT_KEY = "manual:october_2026:2026-11-02"
ACQUISITION_DATE = "2026-11-02"
PROVIDER_PUBLISHED_AT = "2026-10-13"
DATASET_PAGE_URL = "https://data.imf.org/datasets/WEO"
MANUAL_RECORD = Path("docs/data-sources/imf-weo-october-2026-manual-acquisition.md")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_file(root: Path, path: Path) -> tuple[Path, str]:
    resolved = path.resolve(strict=True)
    relative = resolved.relative_to(root).as_posix()
    if not resolved.is_file():
        raise ValueError(f"Expected a regular file: {relative}")
    return resolved, relative


def register_imf_weo_manual_acquisition(
    *,
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH,
    repository_root: str | Path = REPOSITORY_ROOT,
    csv_path: str | Path | None = None,
    appendix_path: str | Path | None = None,
    manual_record_path: str | Path | None = None,
    acquisition_date: str = ACQUISITION_DATE,
    provider_published_at: str = PROVIDER_PUBLISHED_AT,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Register one manual vintage event after exact snapshot verification."""
    root = Path(repository_root).resolve()
    csv_input = Path(csv_path) if csv_path is not None else root / assess_imf_weo.CSV_PATH.relative_to(assess_imf_weo.ROOT)
    appendix_input = Path(appendix_path) if appendix_path is not None else root / assess_imf_weo.PDF_PATH.relative_to(assess_imf_weo.ROOT)
    record_input = Path(manual_record_path) if manual_record_path is not None else root / MANUAL_RECORD
    acquired_date = date.fromisoformat(acquisition_date)
    published_date = date.fromisoformat(provider_published_at)

    csv_file, csv_relative = _relative_file(root, csv_input)
    appendix_file, appendix_relative = _relative_file(root, appendix_input)
    record_file, record_relative = _relative_file(root, record_input)
    record_text = record_file.read_text(encoding="utf-8")
    record_hash = _sha256(record_file)

    artifacts = []
    for label, path, relative, role, media_type in (
        ("csv", csv_file, csv_relative, "dataset", "text/csv"),
        ("appendix", appendix_file, appendix_relative, "supporting_document", "application/pdf"),
    ):
        expected_hash, expected_bytes = assess_imf_weo.EXPECTED[label]
        actual_hash = _sha256(path)
        actual_bytes = path.stat().st_size
        if actual_hash != expected_hash or actual_bytes != expected_bytes:
            raise ValueError(f"{label} does not match the recorded October 2026 manual snapshot")
        if expected_hash not in record_text or path.name not in record_text:
            raise ValueError(f"{label} checksum/filename is not corroborated by {record_relative}")
        artifacts.append({
            "role": role,
            "path": relative,
            "sha256": actual_hash,
            "byte_count": actual_bytes,
            "media_type": media_type,
            "retrieval_url": DATASET_PAGE_URL,
            "metadata": {
                "artifact_label": label,
                "manual_record": record_relative,
                "manual_acquisition_date": acquired_date.isoformat(),
                "manual_acquisition_date_precision": "day",
                "provider_release": "October 2026",
                "provider_dataset_version": "IMF.RES_WEO_9.0.0",
                "recorded_sha256": expected_hash,
                "recorded_byte_count": expected_bytes,
                "retrieval_method": "manual portal export",
                "retrieval_url_role": "dataset_page",
            },
        })

    evidence = {
        "registration_method": "manual_bundle_record_v1",
        "manual_record_path": record_relative,
        "manual_record_sha256": record_hash,
        "formal_manifest_present": False,
        "acquisition_date": acquired_date.isoformat(),
        "acquisition_date_precision": "day",
        "timestamp_limitation": (
            "The manual record gives a download date but no exact acquisition time. "
            "The CSV filename timestamp is an export-generation timestamp, not an "
            "independently verified acquisition timestamp."
        ),
        "provider_release_label": "October 2026",
        "provider_published_at": published_date.isoformat(),
        "provider_dataset_version": "IMF.RES_WEO_9.0.0",
        "artifacts": [
            {key: value for key, value in artifact.items() if key != "metadata"}
            | {"metadata": artifact["metadata"]}
            for artifact in artifacts
        ],
        "source_page": DATASET_PAGE_URL,
    }

    connection = connect_project_database(database_path)
    try:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        matches = connection.execute(
            """SELECT a.stream_id, d.dataset_id
               FROM sources src
               JOIN datasets d ON d.source_key = src.source_key
               JOIN acquisition_streams a ON a.dataset_id = d.dataset_id
               WHERE src.source_key = ? AND d.dataset_key = ?
                 AND a.stream_key = ? AND a.is_active = 1""",
            (SOURCE_KEY, DATASET_KEY, STREAM_KEY),
        ).fetchall()
        if len(matches) != 1:
            return {
                "registered": [], "unchanged": [], "errors": [{
                    "reason": "expected exactly one active IMF WEO manual_vintage_bundle stream",
                    "matches": len(matches),
                }], "dry_run": dry_run,
            }
        stream_id = int(matches[0]["stream_id"])
        existing = connection.execute(
            """SELECT acquisition_id, provider_release_id, acquisition_year,
                      acquired_at, provider_published_at, status, integrity_status,
                      acquisition_event_key, manifest_sha256, evidence_json
               FROM acquisitions WHERE stream_id = ? AND acquisition_event_key = ?""",
            (stream_id, EVENT_KEY),
        ).fetchone()
        expected_artifacts = sorted(
            [(a["role"], a["path"], a["sha256"], a["byte_count"], a["media_type"],
              a["retrieval_url"], json.dumps(a["metadata"], ensure_ascii=False,
              sort_keys=True, separators=(",", ":"))) for a in artifacts],
            key=lambda item: item[1],
        )
        if existing is not None:
            rows = connection.execute(
                """SELECT artifact_role, relative_path, sha256, byte_count,
                          media_type, retrieval_url, metadata_json
                   FROM acquisition_artifacts WHERE acquisition_id = ?
                   ORDER BY relative_path""",
                (int(existing["acquisition_id"]),),
            ).fetchall()
            actual_artifacts = [
                (r["artifact_role"], r["relative_path"], r["sha256"], r["byte_count"],
                 r["media_type"], r["retrieval_url"], r["metadata_json"]) for r in rows
            ]
            expected_event = (
                "october_2026", acquired_date.year, acquired_date.isoformat(),
                published_date.isoformat(), "acquired", "verified", EVENT_KEY, None,
                json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            )
            actual_event = (
                existing["provider_release_id"], existing["acquisition_year"],
                existing["acquired_at"], existing["provider_published_at"],
                existing["status"], existing["integrity_status"],
                existing["acquisition_event_key"], existing["manifest_sha256"],
                existing["evidence_json"],
            )
            if actual_event != expected_event or actual_artifacts != expected_artifacts:
                return {
                    "registered": [], "unchanged": [],
                    "errors": [{"reason": "manual event identity exists with changed evidence",
                                "acquisition_id": int(existing["acquisition_id"])}],
                    "dry_run": dry_run,
                }
            return {
                "registered": [],
                "unchanged": [{"acquisition_id": int(existing["acquisition_id"]),
                               "artifact_count": len(artifacts)}],
                "errors": [], "dry_run": dry_run,
            }

        if dry_run:
            return {
                "registered": [{
                    "source_key": SOURCE_KEY, "dataset_key": DATASET_KEY,
                    "stream_key": STREAM_KEY, "event_key": EVENT_KEY,
                    "acquisition_date": acquired_date.isoformat(),
                    "artifact_count": len(artifacts), "status": "would_register_as_acquired",
                }],
                "unchanged": [], "errors": [], "dry_run": True,
            }

        connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = connection.execute(
                """INSERT INTO acquisitions (
                    stream_id, provider_release_id, acquisition_year, acquired_at,
                    provider_published_at, status, acquisition_note, metadata_json,
                    created_at, updated_at, acquisition_event_key, manifest_sha256,
                    integrity_status, evidence_json
                ) VALUES (?, 'october_2026', ?, ?, ?, 'acquired', ?, ?, ?, ?, ?, NULL, 'verified', ?)""",
                (
                    stream_id, acquired_date.year, acquired_date.isoformat(),
                    published_date.isoformat(),
                    "Manual October 2026 WEO bundle; date precision is one calendar day.",
                    json.dumps({
                        "manual_record_path": record_relative,
                        "manual_record_sha256": record_hash,
                        "acquisition_date_precision": "day",
                        "provider_dataset_version": "IMF.RES_WEO_9.0.0",
                    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    utc_now(), utc_now(), EVENT_KEY,
                    json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            acquisition_id = int(cursor.lastrowid)
            for artifact in artifacts:
                connection.execute(
                    """INSERT INTO acquisition_artifacts (
                        acquisition_id, artifact_role, relative_path, sha256, byte_count,
                        media_type, retrieval_url, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        acquisition_id, artifact["role"], artifact["path"], artifact["sha256"],
                        artifact["byte_count"], artifact["media_type"], artifact["retrieval_url"],
                        json.dumps(artifact["metadata"], ensure_ascii=False,
                                   sort_keys=True, separators=(",", ":")),
                        utc_now(),
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {
            "registered": [{"acquisition_id": acquisition_id, "artifact_count": len(artifacts),
                            "status": "acquired", "integrity_status": "verified"}],
            "unchanged": [], "errors": [], "dry_run": False,
            "game_database_written": False, "release_promoted": False,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_PROJECT_DATABASE_PATH))
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = register_imf_weo_manual_acquisition(
            database_path=args.database, repository_root=args.root, dry_run=args.dry_run,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"errors": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
