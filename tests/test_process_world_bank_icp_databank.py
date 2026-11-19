from __future__ import annotations

from pathlib import Path

from tools import process_world_bank_icp_databank as process


def _audit(**kwargs):
    return {
        "status": "ok", "manifest_count": 1, "artifact_count": 3,
        "error_count": 0,
        "manifests": [{"manifest_path": "data_manifests/sources/world_bank_icp/databank_exports/test.json",
                       "status": "ok"}],
    }


def _validation(**kwargs):
    return {"status": "passed", "validation_report_path": "reports/test/validation.json"}


def test_semantic_failure_blocks_catalogue_sync_and_registration(tmp_path: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(process, "audit_manifests", _audit)
    monkeypatch.setattr(process, "validate_manifest", lambda **kwargs: (
        (_ for _ in ()).throw(process.ICPDataBankValidationError("bad rows"))
    ))
    monkeypatch.setattr(process, "sync_source_catalogue", lambda **kwargs: calls.append("source"))
    monkeypatch.setattr(process, "sync_dataset_catalogue", lambda **kwargs: calls.append("dataset"))
    monkeypatch.setattr(process, "register_manifest_acquisitions", lambda **kwargs: calls.append("register"))

    result = process.process_world_bank_icp_databank(repository_root=tmp_path)

    assert result["status"] == "blocked_semantic_validation"
    assert calls == []
    assert result["project_database_written"] is False
    assert result["game_database_written"] is False


def test_successful_preflight_does_not_register_by_default(tmp_path: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(process, "audit_manifests", _audit)
    monkeypatch.setattr(process, "validate_manifest", _validation)
    monkeypatch.setattr(process, "sync_source_catalogue", lambda **kwargs: {"sources": 1})
    monkeypatch.setattr(process, "sync_dataset_catalogue", lambda **kwargs: {"datasets": 1, "streams": 1})

    def registration(**kwargs):
        calls.append(kwargs)
        return {
            "audit_status": "ok", "registered": [{"status": "would_register"}],
            "unchanged": [], "deferred": [], "errors": [], "dry_run": kwargs["dry_run"],
        }

    monkeypatch.setattr(process, "register_manifest_acquisitions", registration)
    result = process.process_world_bank_icp_databank(repository_root=tmp_path)

    assert result["status"] == "ready_for_registration"
    assert result["eligible_count"] == 1
    assert len(calls) == 1 and calls[0]["dry_run"] is True
    assert result["project_database_written"] is True
    assert result["acquisition_provenance_registered"] is False
    assert result["game_database_written"] is False


def test_register_flag_writes_only_project_acquisition_provenance(tmp_path: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(process, "audit_manifests", _audit)
    monkeypatch.setattr(process, "validate_manifest", _validation)
    monkeypatch.setattr(process, "sync_source_catalogue", lambda **kwargs: {"sources": 1})
    monkeypatch.setattr(process, "sync_dataset_catalogue", lambda **kwargs: {"datasets": 1, "streams": 1})

    def registration(**kwargs):
        calls.append(kwargs["dry_run"])
        return {
            "audit_status": "ok", "registered": [{"acquisition_id": 7}],
            "unchanged": [], "deferred": [], "errors": [], "dry_run": kwargs["dry_run"],
        }

    monkeypatch.setattr(process, "register_manifest_acquisitions", registration)
    result = process.process_world_bank_icp_databank(repository_root=tmp_path, register=True)

    assert result["status"] == "registered"
    assert calls == [True, False]
    assert result["acquisition_provenance_registered"] is True
    assert result["observations_imported"] is False
    assert result["approval_created"] is False
    assert result["game_database_written"] is False


def test_registration_preflight_deferred_blocks_actual_registration(tmp_path: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(process, "audit_manifests", _audit)
    monkeypatch.setattr(process, "validate_manifest", _validation)
    monkeypatch.setattr(process, "sync_source_catalogue", lambda **kwargs: {"sources": 1})
    monkeypatch.setattr(process, "sync_dataset_catalogue", lambda **kwargs: {"datasets": 1, "streams": 1})

    def registration(**kwargs):
        calls.append(kwargs["dry_run"])
        return {
            "audit_status": "ok", "registered": [], "unchanged": [],
            "deferred": [{"reason": "no exact stream"}], "errors": [],
            "dry_run": kwargs["dry_run"],
        }

    monkeypatch.setattr(process, "register_manifest_acquisitions", registration)
    result = process.process_world_bank_icp_databank(repository_root=tmp_path, register=True)

    assert result["status"] == "blocked_registration_preflight"
    assert calls == [True]
    assert result["game_database_written"] is False
