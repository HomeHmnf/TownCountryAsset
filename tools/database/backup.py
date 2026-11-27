"""Safe, reusable SQLite online-backup helpers."""
from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


class BackupError(RuntimeError):
    """SQLite backup creation or verification failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_verified_backup(
    source_path: Path,
    backup_dir: Path,
    *,
    prefix: str | None = None,
) -> dict:
    """Create a unique online backup and verify SQLite integrity and FKs.

    Existing files are never overwritten. The returned SHA-256 is calculated
    only after the destination has been closed and independently checked.
    """
    source = source_path.expanduser().resolve()
    directory = backup_dir.expanduser().resolve()
    if not source.is_file():
        raise BackupError(f"SQLite source does not exist: {source}")
    directory.mkdir(parents=True, exist_ok=True)
    if source.parent == directory and source.name == (prefix or source.stem):
        raise BackupError("Backup destination cannot be the source database")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    stem = prefix or source.stem
    destination = directory / f"{stem}_{stamp}.sqlite"

    # Reserve the name atomically so concurrent runs cannot overwrite one another.
    try:
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise BackupError(f"Refusing to overwrite existing backup: {destination}") from exc
    os.close(descriptor)

    source_uri = "file:" + quote(str(source), safe="/:") + "?mode=ro"
    try:
        source_connection = None
        destination_connection = None
        try:
            source_connection = sqlite3.connect(source_uri, uri=True, timeout=30)
            destination_connection = sqlite3.connect(str(destination), timeout=30)
            source_connection.backup(destination_connection)
        finally:
            if destination_connection is not None:
                destination_connection.close()
            if source_connection is not None:
                source_connection.close()

        check_uri = "file:" + quote(str(destination), safe="/:") + "?mode=ro"
        check = sqlite3.connect(check_uri, uri=True, timeout=30)
        try:
            integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_violations = check.execute("PRAGMA foreign_key_check").fetchall()
        finally:
            check.close()
        if integrity != "ok" or foreign_key_violations:
            raise BackupError(
                f"Backup verification failed: integrity={integrity}, "
                f"foreign_key_violations={len(foreign_key_violations)}"
            )
        return {
            "backup": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
            "integrity": integrity,
            "foreign_key_violations": len(foreign_key_violations),
        }
    except Exception:
        # Only remove the file this invocation reserved; never touch another backup.
        destination.unlink(missing_ok=True)
        raise
