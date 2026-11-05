"""Register integrity-verified manifest captures in the Project DB.

Registration records provenance only. It does not perform semantic validation,
approval, Game DB application, or retention promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.audit_acquisition_manifests import audit_manifests
from tools.database.connection import REPOSITORY_ROOT
from tools.database.project_connection import (
    DEFAULT_PROJECT_DATABASE_PATH,
    PROJECT_MIGRATIONS_DIR,
    connect_project_database,
)
from tools.database.schema import apply_migrations, utc_now

DEFAULT_MANIFEST_DIR = Path("data_manifests/sources")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_role(artifact: dict[str, Any]) -> str:
    name = str(artifact.get("filename") or artifact.get("file_id") or artifact.get("local_raw_path") or "").lower()
    if "metadata" in name:
        return "metadata"
    if "records_page" in name or "page_" in name:
        return "api_page"
    return "dataset"


def _aware_timestamp(value: Any, manifest_path: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{manifest_path}: retrieved_at/recorded_at is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{manifest_path}: acquisition timestamp must include a timezone")
    return parsed


def register_manifest_acquisitions(
    *,
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH,
    repository_root: str | Path = REPOSITORY_ROOT,
    manifest_dir: str | Path = DEFAULT_MANIFEST_DIR,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Register only manifests with an exact registered dataset and one stream."""
    root = Path(repository_root).resolve()
    audit = audit_manifests(repository_root=root, manifest_dir=manifest_dir)
    result: dict[str, Any] = {
        "audit_status": audit["status"],
        "manifest_count": audit["manifest_count"],
        "registered": [],
        "unchanged": [],
        "deferred": [],
        "errors": [],
        "dry_run": dry_run,
    }
    if audit["status"] != "ok":
        result["errors"].append("Manifest integrity audit failed; no registration attempted.")
        return result

    connection = connect_project_database(database_path)
    try:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        for audited in audit["manifests"]:
            manifest_path = str(audited["manifest_path"])
            path = root / manifest_path
            payload = json.loads(path.read_text(encoding="utf-8"))
            source_key = payload.get("source_id")
            dataset_key = payload.get("dataset_id") or payload.get("download_id")
            if not isinstance(source_key, str) or not isinstance(dataset_key, str):
                result["deferred"].append({"manifest": manifest_path, "reason": "missing source/dataset identity"})
                continue

            rows = connection.execute(
                """SELECT s.stream_id, d.dataset_id
                   FROM sources src
                   JOIN datasets d ON d.source_key = src.source_key
                   JOIN acquisition_streams s ON s.dataset_id = d.dataset_id
                   WHERE src.source_key = ? AND d.dataset_key = ? AND s.is_active = 1
                   ORDER BY s.stream_id""",
                (source_key, dataset_key),
            ).fetchall()
            if len(rows) != 1:
                result["deferred"].append({
                    "manifest": manifest_path,
                    "reason": "no exact registered dataset/stream" if not rows else "multiple active streams require explicit mapping",
                    "source_key": source_key,
                    "dataset_key": dataset_key,
                })
                continue

            acquired_at = _aware_timestamp(payload.get("retrieved_at") or payload.get("recorded_at"), manifest_path)
            acquisition_year = acquired_at.year
            event_key = manifest_path
            manifest_hash = _sha256(path)
            raw_artifacts = payload.get("files")
            if not isinstance(raw_artifacts, list) or not raw_artifacts:
                raw_artifacts = [payload]
            artifact_rows: list[dict[str, Any]] = []
            for original in raw_artifacts:
                relative = original.get("local_raw_path") or original.get("repository_path") or original.get("path")
                if not isinstance(relative, str) or not relative:
                    raise ValueError(f"{manifest_path}: artifact path missing")
                artifact_path = (root / relative).resolve(strict=True)
                artifact_path.relative_to(root)
                if not artifact_path.is_file():
                    raise ValueError(f"{manifest_path}: artifact is not a regular file: {relative}")
                actual_hash = _sha256(artifact_path)
                actual_bytes = artifact_path.stat().st_size
                declared_hash = original.get("sha256") or original.get("expected_sha256")
                declared_bytes = original.get("byte_count")
                if declared_bytes is None:
                    declared_bytes = original.get("expected_byte_count")
                if actual_hash.lower() != str(declared_hash).lower() or actual_bytes != declared_bytes:
                    raise ValueError(f"{manifest_path}: artifact changed after integrity audit: {relative}")
                artifact_rows.append({
                    "role": _artifact_role(original),
                    "path": relative,
                    "sha256": actual_hash,
                    "byte_count": actual_bytes,
                    "media_type": original.get("content_type") or original.get("format"),
                    "retrieval_url": original.get("final_url") or original.get("url"),
                    "metadata": original,
                })

            event_evidence = {
                "manifest_path": manifest_path,
                "manifest_schema_version": payload.get("manifest_schema_version"),
                "manifest_payload": payload,
                "registration_method": "manifest_adapter_v1",
            }
            existing = connection.execute(
                """SELECT acquisition_id, manifest_sha256, evidence_json
                   FROM acquisitions WHERE stream_id = ? AND acquisition_event_key = ?""",
                (int(rows[0]["stream_id"]), event_key),
            ).fetchone()
            if existing is not None:
                prior_artifacts = connection.execute(
                    """SELECT artifact_role, relative_path, sha256, byte_count, media_type, retrieval_url, metadata_json
                       FROM acquisition_artifacts WHERE acquisition_id = ?
                       ORDER BY relative_path""",
                    (int(existing["acquisition_id"]),),
                ).fetchall()
                expected_artifacts = sorted(
                    [(a["role"], a["path"], a["sha256"], a["byte_count"], a["media_type"], a["retrieval_url"], _json(a["metadata"])) for a in artifact_rows],
                    key=lambda item: item[1],
                )
                actual_artifacts = [
                    (r["artifact_role"], r["relative_path"], r["sha256"], r["byte_count"], r["media_type"], r["retrieval_url"], r["metadata_json"])
                    for r in prior_artifacts
                ]
                if existing["manifest_sha256"] != manifest_hash or actual_artifacts != expected_artifacts:
                    result["errors"].append({"manifest": manifest_path, "reason": "event identity exists with changed evidence"})
                    continue
                result["unchanged"].append({"manifest": manifest_path, "acquisition_id": int(existing["acquisition_id"])})
                continue

            if dry_run:
                result["registered"].append({
                    "manifest": manifest_path,
                    "source_key": source_key,
                    "dataset_key": dataset_key,
                    "artifact_count": len(artifact_rows),
                    "status": "would_register_as_acquired",
                })
                continue

            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.execute(
                    """INSERT INTO acquisitions (
                        stream_id, provider_release_id, acquisition_year, acquired_at,
                        status, acquisition_note, metadata_json, created_at, updated_at,
                        acquisition_event_key, manifest_sha256, integrity_status, evidence_json
                    ) VALUES (?, ?, ?, ?, 'acquired', ?, ?, ?, ?, ?, ?, 'verified', ?)""",
                    (
                        int(rows[0]["stream_id"]),
                        payload.get("release") or payload.get("snapshot_id"),
                        acquisition_year,
                        acquired_at.isoformat(),
                        "Manifest and all referenced artifacts passed byte-integrity verification.",
                        _json({"manifest_path": manifest_path, "manifest_schema_version": payload.get("manifest_schema_version")}),
                        utc_now(), utc_now(), event_key, manifest_hash, _json(event_evidence),
                    ),
                )
                acquisition_id = int(cursor.lastrowid)
                for artifact in artifact_rows:
                    connection.execute(
                        """INSERT INTO acquisition_artifacts (
                            acquisition_id, artifact_role, relative_path, sha256, byte_count,
                            media_type, retrieval_url, metadata_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            acquisition_id, artifact["role"], artifact["path"], artifact["sha256"],
                            artifact["byte_count"], artifact["media_type"], artifact["retrieval_url"],
                            _json(artifact["metadata"]), utc_now(),
                        ),
                    )
                connection.commit()
                result["registered"].append({
                    "manifest": manifest_path,
                    "acquisition_id": acquisition_id,
                    "artifact_count": len(artifact_rows),
                    "status": "acquired",
                })
            except Exception:
                connection.rollback()
                raise
        return result
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_PROJECT_DATABASE_PATH))
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = register_manifest_acquisitions(
        database_path=args.database,
        repository_root=args.root,
        manifest_dir=args.manifest_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
