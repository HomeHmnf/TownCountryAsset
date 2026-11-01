from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.sources.refresh import run_refresh
from tools.sources.registry import load_registry


def _registry(tmp_path: Path) -> dict:
    config = {
        "schema_version": 1,
        "storage": {"raw_root": "raw", "manifest_root": "manifests", "reports_root": "reports"},
        "release_management": {
            "selection_policy": "latest_validated",
            "discovery_modes": {"manual_review": "manual", "rolling_url": "rolling", "website_page": "page"},
            "release_record": {"path_template": "reports/sources/releases/<source-id>.json"},
        },
        "sources": {
            "sample": {
                "name": "Sample",
                "release_discovery": {
                    "mode": "manual_review", "provider_url": "https://example.test/releases",
                    "automation_status": "not_implemented",
                    "latest_available": None, "latest_validated": None, "latest_applied": None,
                },
                "downloads": [{
                    "id": "dataset", "release": "v1", "release_kind": "edition_or_snapshot",
                    "filename": "data.csv", "url": "https://example.test/data.csv", "format": "csv",
                }],
            },
            "manual": {
                "name": "Manual source",
                "release_discovery": {
                    "mode": "manual_review", "provider_url": "https://example.test/manual",
                    "automation_status": "not_implemented",
                    "latest_available": None, "latest_validated": None, "latest_applied": None,
                },
                "downloads": [],
            },
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return load_registry(path)


def _manifest(registry: dict, payload: bytes) -> None:
    root = registry["_root"]
    raw = root / "raw/sample/dataset/v1/data.csv"
    manifest = root / "manifests/sample/dataset/v1.json"
    raw.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    raw.write_bytes(payload)
    manifest.write_text(json.dumps({
        "source_id": "sample", "download_id": "dataset",
        "sha256": hashlib.sha256(payload).hexdigest(), "byte_count": len(payload),
    }), encoding="utf-8")


def test_refresh_skips_valid_snapshots_and_reports_manual_sources(tmp_path):
    registry = _registry(tmp_path)
    _manifest(registry, b"existing")
    report = run_refresh(registry, report_root=tmp_path / "reports")
    item = report["sources"][0]["downloads"][0]
    assert item["status"] == "unchanged"
    assert report["sources"][1]["discovery_status"] == "manual_review_required"
    assert report["database_imported"] is False
    assert Path(report["report_paths"]["json"]).is_file()
    assert Path(report["report_paths"]["markdown"]).is_file()
    assert (Path(report["report_paths"]["bundle"]) / "records.csv").is_file()
    assert (Path(report["report_paths"]["bundle"]) / "provenance.json").is_file()


def test_refresh_dry_run_does_not_acquire_missing_snapshot(tmp_path):
    registry = _registry(tmp_path)
    report = run_refresh(registry, dry_run=True, report_root=tmp_path / "reports")
    assert report["sources"][0]["downloads"][0]["status"] == "would_acquire"
    assert not (tmp_path / "raw/sample/dataset/v1/data.csv").exists()


def test_refresh_does_not_overwrite_invalid_snapshot(tmp_path):
    registry = _registry(tmp_path)
    _manifest(registry, b"original")
    raw = tmp_path / "raw/sample/dataset/v1/data.csv"
    raw.write_bytes(b"tampered")
    report = run_refresh(registry, report_root=tmp_path / "reports")
    assert report["sources"][0]["downloads"][0]["status"] == "validation_error"
    assert raw.read_bytes() == b"tampered"

def test_refresh_acquires_missing_configured_snapshot_without_promoting_release_state(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _registry(tmp_path)
    monkeypatch.setattr(module, "acquire_one", lambda *args, **kwargs: {
        "sha256": "a" * 64, "byte_count": 12,
    })
    report = run_refresh(registry, report_root=tmp_path / "reports")
    item = report["sources"][0]["downloads"][0]
    assert item["status"] == "acquired_pending_source_validation"
    assert registry["sources"]["sample"]["release_discovery"]["latest_validated"] is None
    assert report["database_imported"] is False


def test_refresh_records_failure_and_continues_other_sources(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _registry(tmp_path)

    def fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(module, "acquire_one", fail)
    report = run_refresh(registry, report_root=tmp_path / "reports")
    assert report["sources"][0]["downloads"][0]["status"] == "acquisition_failed"
    assert report["sources"][1]["discovery_status"] == "manual_review_required"

def test_refresh_reports_incomplete_snapshot_without_overwriting(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _registry(tmp_path)
    raw = tmp_path / "raw/sample/dataset/v1/data.csv"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"partial")
    monkeypatch.setattr(
        module, "acquire_one",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not acquire over partial snapshot")),
    )
    report = run_refresh(registry, report_root=tmp_path / "reports")
    item = report["sources"][0]["downloads"][0]
    assert item["status"] == "validation_error"
    assert raw.read_bytes() == b"partial"

def _enable_fingerprint_discovery(registry: dict, mode: str = "rolling_url") -> dict:
    source = registry["sources"]["sample"]
    source["release_discovery"]["mode"] = mode
    source["release_discovery"]["automation_status"] = "implemented"
    source["downloads"][0]["release_kind"] = "rolling" if mode == "rolling_url" else "current_reference"
    return registry


def _candidate(payload: bytes = b"new-provider-content") -> dict:
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "release_id": "content-" + digest,
        "provider_release_label": "content-sha256:" + digest,
        "sha256": digest,
        "byte_count": len(payload),
        "content_type": "text/csv",
        "url": "https://example.test/data.csv",
        "discovered_at": "2026-11-01T00:00:00+00:00",
    }


def test_fingerprint_discovery_records_latest_available_and_acquires_immutable_release(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _enable_fingerprint_discovery(_registry(tmp_path))
    candidate = _candidate()
    monkeypatch.setattr(module, "_discover_fingerprint", lambda *args, **kwargs: candidate)
    monkeypatch.setattr(module, "_inspect_release_snapshot", lambda *args, **kwargs: {
        "status": "missing", "raw_path": "raw/sample/dataset/missing/data.csv",
    })
    monkeypatch.setattr(module, "acquire_one", lambda reg, sid, item, **kwargs: {
        "sha256": candidate["sha256"], "byte_count": candidate["byte_count"],
    })

    report = run_refresh(registry, report_root=tmp_path / "reports" / "refreshes")
    item = report["sources"][0]["downloads"][0]
    assert item["status"] == "acquired_pending_source_validation"
    state_path = tmp_path / "reports/sources/releases/sample.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["latest_available"]["release_id"] == candidate["release_id"]
    assert state["latest_available"]["status"] == "acquired"
    assert state["latest_validated"] is None
    assert state["latest_applied"] is None
    assert report["database_imported"] is False


def test_fingerprint_discovery_skips_existing_identical_snapshot(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _enable_fingerprint_discovery(_registry(tmp_path))
    candidate = _candidate()
    monkeypatch.setattr(module, "_discover_fingerprint", lambda *args, **kwargs: candidate)
    monkeypatch.setattr(module, "_inspect_release_snapshot", lambda *args, **kwargs: {
        "status": "valid", "raw_path": "raw/sample/dataset/existing/data.csv",
    })
    monkeypatch.setattr(
        module, "acquire_one",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("identical release must not be reacquired")),
    )
    report = run_refresh(registry, report_root=tmp_path / "reports" / "refreshes")
    assert report["sources"][0]["downloads"][0]["status"] == "unchanged"
    state = json.loads((tmp_path / "reports/sources/releases/sample.json").read_text(encoding="utf-8"))
    assert len(state["history"]) == 1
    assert state["latest_validated"] is None


def test_fingerprint_discovery_failure_is_reported_without_release_state(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _enable_fingerprint_discovery(_registry(tmp_path))

    def fail(*args, **kwargs):
        raise RuntimeError("endpoint unavailable")

    monkeypatch.setattr(module, "_discover_fingerprint", fail)
    report = run_refresh(registry, report_root=tmp_path / "reports" / "refreshes")
    assert report["sources"][0]["downloads"][0]["status"] == "discovery_or_acquisition_failed"
    assert not (tmp_path / "reports/sources/releases/sample.json").exists()


def test_fingerprint_discovery_dry_run_does_not_contact_provider(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _enable_fingerprint_discovery(_registry(tmp_path))
    monkeypatch.setattr(
        module, "_discover_fingerprint",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dry run must not contact provider")),
    )
    report = run_refresh(
        registry, dry_run=True, report_root=tmp_path / "reports" / "refreshes",
    )
    assert report["sources"][0]["downloads"][0]["status"] == "would_discover"
    assert not (tmp_path / "reports/sources/releases/sample.json").exists()


def test_fingerprint_acquisition_race_is_not_marked_acquired(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _enable_fingerprint_discovery(_registry(tmp_path))
    candidate = _candidate(b"first response")
    monkeypatch.setattr(module, "_discover_fingerprint", lambda *args, **kwargs: candidate)
    monkeypatch.setattr(module, "_inspect_release_snapshot", lambda *args, **kwargs: {
        "status": "missing", "raw_path": "raw/sample/dataset/missing/data.csv",
    })
    monkeypatch.setattr(module, "acquire_one", lambda *args, **kwargs: {
        "sha256": hashlib.sha256(b"different response").hexdigest(), "byte_count": 18,
    })
    report = run_refresh(registry, report_root=tmp_path / "reports" / "refreshes")
    assert report["sources"][0]["downloads"][0]["status"] == "changed_during_acquisition"
    state = json.loads((tmp_path / "reports/sources/releases/sample.json").read_text(encoding="utf-8"))
    assert state["latest_available"]["status"] == "discovered"
    assert state["latest_validated"] is None

def test_github_git_ref_discovery_records_commit_without_acquiring_archive(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _registry(tmp_path)
    source = registry["sources"]["manual"]
    source["release_discovery"]["mode"] = "git_ref"
    source["release_discovery"]["automation_status"] = "implemented"
    source["release_discovery"]["provider_url"] = "https://github.com/lipis/flag-icons"
    discovered = {
        "release_id": "git-" + ("a" * 40),
        "provider_release_label": "git-commit:" + ("a" * 40),
        "provider_published_at": None,
        "provider_commit_timestamp": "2026-10-31T10:00:00Z",
        "fetched_at": "2026-11-01T00:00:00+00:00",
        "sha256": None,
        "byte_count": None,
        "content_type": "application/json",
        "url": "https://github.com/lipis/flag-icons/commit/" + ("a" * 40),
        "discovered_at": "2026-11-01T00:00:00+00:00",
    }
    monkeypatch.setattr(module, "_discover_git_ref", lambda *args, **kwargs: discovered)
    report = run_refresh(
        registry,
        source_ids=["manual"],
        report_root=tmp_path / "reports" / "refreshes",
    )
    result = report["sources"][0]
    assert result["discovery_status"] == "git_ref_discovery"
    assert result["git_ref"]["release_id"] == discovered["release_id"]
    state = json.loads(
        (tmp_path / "reports/sources/releases/manual.json").read_text(encoding="utf-8")
    )
    assert state["latest_available"]["release_id"] == discovered["release_id"]
    assert state["latest_available"]["status"] == "discovered"
    fetched_at = state["latest_available"]["fetched_at"]
    assert fetched_at.endswith("+00:00") or fetched_at.endswith("Z")
    assert state["latest_available"]["provider_commit_timestamp"] == discovered["provider_commit_timestamp"]
    assert state["latest_validated"] is None
    assert state["latest_applied"] is None
    run_refresh(
        registry,
        source_ids=["manual"],
        report_root=tmp_path / "reports" / "refreshes",
    )
    repeated = json.loads(
        (tmp_path / "reports/sources/releases/manual.json").read_text(encoding="utf-8")
    )
    assert repeated["latest_available"]["fetched_at"] == fetched_at


def test_github_git_ref_dry_run_does_not_query_provider(tmp_path, monkeypatch):
    import tools.sources.refresh as module

    registry = _registry(tmp_path)
    source = registry["sources"]["manual"]
    source["release_discovery"]["mode"] = "git_ref"
    source["release_discovery"]["automation_status"] = "implemented"
    source["release_discovery"]["provider_url"] = "https://github.com/lipis/flag-icons"
    monkeypatch.setattr(
        module, "_discover_git_ref",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dry run must not query GitHub")),
    )
    report = run_refresh(
        registry,
        source_ids=["manual"],
        dry_run=True,
        report_root=tmp_path / "reports" / "refreshes",
    )
    assert report["sources"][0]["discovery_status"] == "dry_run_not_checked"
    assert not (tmp_path / "reports/sources/releases/manual.json").exists()

def test_github_git_ref_adapter_parses_immutable_default_branch_commit(monkeypatch):
    import tools.sources.refresh as module

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return "https://api.github.com/repos/lipis/flag-icons/commits?per_page=1"

        def read(self):
            return json.dumps([{
                "sha": "b" * 40,
                "commit": {
                    "committer": {"date": "2026-10-31T10:20:30Z"},
                },
            }]).encode("utf-8")

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse())
    result = module._discover_git_ref(
        {"provider_url": "https://github.com/lipis/flag-icons"},
        timeout=10,
    )
    assert result["release_id"] == "git-" + ("b" * 40)
    assert result["provider_commit_timestamp"] == "2026-10-31T10:20:30Z"
    assert result["fetched_at"].endswith("+00:00")
    assert result["sha256"] is None


def test_github_git_ref_adapter_rejects_non_github_provider_url():
    import pytest
    from tools.sources.refresh import _discover_git_ref
    from tools.sources.registry import SourceError

    with pytest.raises(SourceError, match="GitHub repository URL"):
        _discover_git_ref({"provider_url": "https://example.test/owner/repo"}, timeout=10)

