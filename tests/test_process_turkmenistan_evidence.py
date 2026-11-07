from __future__ import annotations

from pathlib import Path

from tools import process_turkmenistan_evidence as process


def _audit_ok(root: Path, manifest_dir: Path) -> dict:
    is_state = "turkmenistan_state_statistics" in manifest_dir.as_posix()
    return {
        "status": "ok",
        "manifest_count": 2 if is_state else 1,
        "artifact_count": 2 if is_state else 1,
        "error_count": 0,
    }


def test_preflight_syncs_catalogues_and_does_not_register(
    tmp_path: Path, monkeypatch
) -> None:
    calls = []
    monkeypatch.setattr(process, "audit_manifests", _audit_ok)
    monkeypatch.setattr(
        process, "sync_source_catalogue",
        lambda **kwargs: {"sources": 34, "source_urls": 106},
    )
    monkeypatch.setattr(
        process, "sync_dataset_catalogue",
        lambda **kwargs: {"datasets": 13, "streams": 11},
    )

    def register(**kwargs):
        calls.append(kwargs)
        count = 2 if "turkmenistan_state_statistics" in str(kwargs["manifest_dir"]) else 1
        return {
            "audit_status": "ok",
            "registered": [{"status": "would_register_as_acquired"}] * count,
            "unchanged": [],
            "deferred": [],
            "errors": [],
            "dry_run": kwargs["dry_run"],
        }

    monkeypatch.setattr(process, "register_manifest_acquisitions", register)
    result = process.process_turkmenistan_evidence(repository_root=tmp_path)

    assert result["status"] == "ready_for_registration"
    assert result["eligible_count"] == 3
    assert result["project_database_written"] is False
    assert result["game_database_written"] is False
    assert len(calls) == 2
    assert all(call["dry_run"] is True for call in calls)


def test_registration_requires_clean_complete_preflight(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(process, "audit_manifests", _audit_ok)
    monkeypatch.setattr(process, "sync_source_catalogue", lambda **kwargs: {})
    monkeypatch.setattr(process, "sync_dataset_catalogue", lambda **kwargs: {})
    calls = []

    def register(**kwargs):
        calls.append(kwargs)
        return {
            "audit_status": "ok",
            "registered": [{"status": "would_register_as_acquired"}],
            "unchanged": [],
            "deferred": [],
            "errors": [],
            "dry_run": kwargs["dry_run"],
        }

    monkeypatch.setattr(process, "register_manifest_acquisitions", register)
    result = process.process_turkmenistan_evidence(
        repository_root=tmp_path, register=True
    )

    assert result["status"] == "blocked_registration_preflight"
    assert result["project_database_written"] is False
    assert len(calls) == 2
    assert all(call["dry_run"] is True for call in calls)


def test_manifest_integrity_failure_stops_before_catalogue_sync(
    tmp_path: Path, monkeypatch
) -> None:
    calls = []
    monkeypatch.setattr(
        process, "audit_manifests",
        lambda **kwargs: {
            "status": "error", "manifest_count": 1,
            "artifact_count": 0, "error_count": 1,
        },
    )
    monkeypatch.setattr(
        process, "sync_source_catalogue",
        lambda **kwargs: calls.append("source"),
    )
    monkeypatch.setattr(
        process, "sync_dataset_catalogue",
        lambda **kwargs: calls.append("dataset"),
    )

    result = process.process_turkmenistan_evidence(repository_root=tmp_path)

    assert result["status"] == "blocked_manifest_integrity"
    assert calls == []
    assert result["project_database_written"] is False
