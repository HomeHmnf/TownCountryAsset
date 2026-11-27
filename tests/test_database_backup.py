from __future__ import annotations

import sqlite3

import pytest

from tools.database.backup import BackupError, create_verified_backup


def make_db(path):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
    connection.execute("INSERT INTO sample VALUES ('stable')")
    connection.commit()
    connection.close()


def test_create_verified_backup_returns_hash_and_integrity(tmp_path):
    source = tmp_path / "source.sqlite"
    make_db(source)
    result = create_verified_backup(source, tmp_path / "backups")
    backup = tmp_path / "backups" / result["backup"].split("/")[-1]
    assert backup.is_file()
    assert result["bytes"] == backup.stat().st_size
    assert len(result["sha256"]) == 64
    assert result["integrity"] == "ok"
    assert result["foreign_key_violations"] == 0
    connection = sqlite3.connect(backup)
    try:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "stable"
    finally:
        connection.close()


def test_backup_never_overwrites_existing_timestamped_destination(tmp_path, monkeypatch):
    source = tmp_path / "source.sqlite"
    make_db(source)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("tools.database.backup.datetime", FixedDateTime)
    expected = backup_dir / "source_20261127T120000.000000Z.sqlite"
    expected.write_bytes(b"keep")
    with pytest.raises(BackupError, match="Refusing to overwrite"):
        create_verified_backup(source, backup_dir)
    assert expected.read_bytes() == b"keep"


def test_missing_source_is_rejected(tmp_path):
    with pytest.raises(BackupError, match="does not exist"):
        create_verified_backup(tmp_path / "missing.sqlite", tmp_path / "backups")


class FixedDateTime:
    @staticmethod
    def now(tz):
        from datetime import datetime, timezone
        return datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)
