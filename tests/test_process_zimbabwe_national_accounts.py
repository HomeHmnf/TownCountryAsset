from __future__ import annotations

from pathlib import Path

from tools import process_zimbabwe_national_accounts as process


def test_clean_two_manifest_preflight_does_not_register(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(process, "audit_manifests", lambda **kwargs: {
        "status":"ok","manifest_count":2,"artifact_count":2,"error_count":0
    })
    monkeypatch.setattr(process, "sync_source_catalogue", lambda **kwargs: {"sources":1})
    monkeypatch.setattr(process, "sync_dataset_catalogue", lambda **kwargs: {"datasets":2})
    calls=[]
    monkeypatch.setattr(process, "register_manifest_acquisitions", lambda **kwargs: (
        calls.append(kwargs) or {"audit_status":"ok","registered":[{},{}],"unchanged":[],
        "deferred":[],"errors":[],"dry_run":kwargs["dry_run"]}
    ))
    result=process.process_zimbabwe_national_accounts(repository_root=tmp_path)
    assert result["status"]=="ready_for_registration"
    assert result["eligible_count"]==2
    assert len(calls)==1 and calls[0]["dry_run"] is True
    assert result["project_database_written"] is False
    assert result["game_database_written"] is False


def test_wrong_manifest_count_blocks_before_catalogue_sync(tmp_path: Path, monkeypatch) -> None:
    calls=[]
    monkeypatch.setattr(process,"audit_manifests",lambda **kwargs:{
        "status":"ok","manifest_count":1,"artifact_count":1,"error_count":0
    })
    monkeypatch.setattr(process,"sync_source_catalogue",lambda **kwargs:calls.append("source"))
    result=process.process_zimbabwe_national_accounts(repository_root=tmp_path)
    assert result["status"]=="blocked_unexpected_manifest_count"
    assert calls==[]
    assert result["project_database_written"] is False


def test_audit_error_blocks_catalogue_sync(tmp_path: Path, monkeypatch) -> None:
    calls=[]
    monkeypatch.setattr(process,"audit_manifests",lambda **kwargs:{
        "status":"error","manifest_count":2,"artifact_count":1,"error_count":1
    })
    monkeypatch.setattr(process,"sync_source_catalogue",lambda **kwargs:calls.append("source"))
    result=process.process_zimbabwe_national_accounts(repository_root=tmp_path)
    assert result["status"]=="blocked_manifest_integrity"
    assert calls==[]
