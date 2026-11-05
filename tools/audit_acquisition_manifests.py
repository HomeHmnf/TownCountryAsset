"""Read-only adapter and integrity audit for historical source manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from tools.database.connection import REPOSITORY_ROOT

DEFAULT_MANIFEST_DIR = Path("data_manifests/sources")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def _normalise_artifacts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Adapt list-based and legacy single-artifact manifest layouts."""
    files = manifest.get("files")
    if files is not None:
        if not isinstance(files, list):
            raise ValueError("'files' must be a list when present")
        if files:
            if not all(isinstance(item, dict) for item in files):
                raise ValueError("every entry in 'files' must be an object")
            return [dict(item) for item in files]

    # UN M49 and some legacy snapshots describe one artifact at the top level.
    if _first(manifest, "local_raw_path", "repository_path", "path"):
        return [manifest]
    raise ValueError("manifest contains no artifact entries")


def _artifact_path(artifact: dict[str, Any]) -> Any:
    return _first(artifact, "local_raw_path", "repository_path", "path")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _audit_artifact(
    artifact: dict[str, Any],
    *,
    root: Path,
    manifest_path: str,
    index: int,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    relative = _artifact_path(artifact)
    if not isinstance(relative, str) or not relative.strip():
        return {
            "index": index,
            "path": relative,
            "status": "error",
            "issues": [{"code": "missing_path", "message": "Artifact has no repository-relative path"}],
        }

    posix_path = PurePosixPath(relative)
    windows_path = PureWindowsPath(relative)
    if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive or ".." in posix_path.parts:
        return {
            "index": index,
            "path": relative,
            "status": "error",
            "issues": [{"code": "unsafe_path", "message": "Artifact path must stay inside the repository"}],
        }

    candidate = root.joinpath(*posix_path.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except FileNotFoundError:
        issues.append({"code": "missing_file", "message": "Referenced artifact does not exist"})
        resolved = None
    except (OSError, ValueError):
        issues.append({"code": "path_outside_repository", "message": "Resolved artifact is outside the repository"})
        resolved = None

    declared_hash = _first(artifact, "sha256", "expected_sha256")
    expected_hash = artifact.get("expected_sha256")
    declared_bytes = _first(artifact, "byte_count", "expected_byte_count")
    expected_bytes = artifact.get("expected_byte_count")

    if expected_hash and artifact.get("sha256") and expected_hash.lower() != artifact["sha256"].lower():
        issues.append({"code": "conflicting_declared_hashes", "message": "sha256 and expected_sha256 disagree"})
    if expected_bytes is not None and artifact.get("byte_count") is not None:
        if expected_bytes != artifact["byte_count"]:
            issues.append({"code": "conflicting_declared_byte_counts", "message": "byte_count and expected_byte_count disagree"})

    if not isinstance(declared_hash, str) or not _SHA256.fullmatch(declared_hash):
        issues.append({"code": "invalid_sha256", "message": "A 64-character hexadecimal SHA-256 is required"})
    if not isinstance(declared_bytes, int) or isinstance(declared_bytes, bool) or declared_bytes < 0:
        issues.append({"code": "invalid_byte_count", "message": "A non-negative integer byte count is required"})

    actual_bytes = None
    actual_hash = None
    if resolved is not None:
        if not resolved.is_file():
            issues.append({"code": "not_a_file", "message": "Artifact path does not resolve to a regular file"})
        else:
            actual_bytes = resolved.stat().st_size
            actual_hash = _hash_file(resolved)
            if isinstance(declared_bytes, int) and not isinstance(declared_bytes, bool) and actual_bytes != declared_bytes:
                issues.append({"code": "byte_count_mismatch", "message": f"Expected {declared_bytes} bytes; found {actual_bytes}"})
            if isinstance(declared_hash, str) and _SHA256.fullmatch(declared_hash):
                if actual_hash.lower() != declared_hash.lower():
                    issues.append({"code": "sha256_mismatch", "message": "Artifact SHA-256 does not match the manifest"})

    return {
        "index": index,
        "path": relative,
        "role_hint": _first(artifact, "file_id", "filename"),
        "media_type": _first(artifact, "content_type", "format"),
        "declared_byte_count": declared_bytes,
        "actual_byte_count": actual_bytes,
        "declared_sha256": declared_hash,
        "actual_sha256": actual_hash,
        "status": "error" if issues else "ok",
        "issues": issues,
    }


def audit_manifests(
    *,
    repository_root: str | Path = REPOSITORY_ROOT,
    manifest_dir: str | Path = DEFAULT_MANIFEST_DIR,
) -> dict[str, Any]:
    """Read manifests and verify referenced files without modifying repository state."""
    root = Path(repository_root).resolve()
    directory = Path(manifest_dir)
    if not directory.is_absolute():
        directory = root / directory
    try:
        directory = directory.resolve(strict=True)
        directory.relative_to(root)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"Manifest directory is missing or outside repository: {manifest_dir}") from exc
    if not directory.is_dir():
        raise ValueError(f"Manifest path is not a directory: {directory}")

    manifests: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*.json")):
        relative_manifest = path.relative_to(root).as_posix()
        manifest_issues: list[dict[str, str]] = []
        try:
            resolved_manifest = path.resolve(strict=True)
            resolved_manifest.relative_to(root)
            payload = json.loads(resolved_manifest.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("manifest root must be a JSON object")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            manifests.append({
                "manifest_path": relative_manifest,
                "source_id": None,
                "dataset_key": None,
                "release": None,
                "status": "error",
                "artifacts": [],
                "issues": [{"code": "manifest_read_error", "message": str(exc)}],
            })
            continue

        source_id = payload.get("source_id")
        dataset_key = _first(payload, "download_id", "dataset_id")
        release = _first(payload, "release", "snapshot_id")
        for field, value in (("source_id", source_id), ("dataset/download identity", dataset_key), ("release/snapshot identity", release)):
            if not isinstance(value, str) or not value.strip():
                manifest_issues.append({"code": "missing_identity", "message": f"Manifest is missing {field}"})

        try:
            artifacts = _normalise_artifacts(payload)
        except ValueError as exc:
            artifacts = []
            manifest_issues.append({"code": "artifact_layout_error", "message": str(exc)})

        audited = [
            _audit_artifact(item, root=root, manifest_path=relative_manifest, index=index)
            for index, item in enumerate(artifacts, start=1)
        ]
        seen_paths: set[str] = set()
        for artifact in audited:
            artifact_path = artifact.get("path")
            if isinstance(artifact_path, str):
                if artifact_path in seen_paths:
                    manifest_issues.append({"code": "duplicate_artifact_path", "message": f"Artifact path is repeated: {artifact_path}"})
                seen_paths.add(artifact_path)

        status = "error" if manifest_issues or any(item["status"] == "error" for item in audited) else "ok"
        manifests.append({
            "manifest_path": relative_manifest,
            "source_id": source_id,
            "dataset_key": dataset_key,
            "release": release,
            "release_kind": payload.get("release_kind"),
            "retrieved_at": _first(payload, "retrieved_at", "recorded_at"),
            "artifact_count": len(audited),
            "status": status,
            "artifacts": audited,
            "issues": manifest_issues,
        })

    artifact_count = sum(item["artifact_count"] for item in manifests)
    error_count = sum(
        len(item["issues"]) + sum(len(artifact["issues"]) for artifact in item["artifacts"])
        for item in manifests
    )
    return {
        "audit_version": 1,
        "repository_root": str(root),
        "manifest_directory": directory.relative_to(root).as_posix(),
        "manifest_count": len(manifests),
        "artifact_count": artifact_count,
        "valid_manifest_count": sum(item["status"] == "ok" for item in manifests),
        "error_count": error_count,
        "status": "ok" if error_count == 0 else "error",
        "read_only": True,
        "database_written": False,
        "retention_applied": False,
        "manifests": manifests,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    result = audit_manifests(repository_root=args.root, manifest_dir=args.manifest_dir)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Manifest directory: {result['manifest_directory']}")
        print(f"Manifests: {result['manifest_count']} ({result['valid_manifest_count']} valid)")
        print(f"Referenced artifacts: {result['artifact_count']}")
        print(f"Integrity issues: {result['error_count']}")
        for manifest in result["manifests"]:
            print(f"{manifest['status'].upper():5} {manifest['manifest_path']}")
            for issue in manifest["issues"]:
                print(f"  ERROR {issue['code']}: {issue['message']}")
            for artifact in manifest["artifacts"]:
                print(f"  {artifact['status'].upper():5} {artifact['path']}")
                for issue in artifact["issues"]:
                    print(f"    ERROR {issue['code']}: {issue['message']}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
