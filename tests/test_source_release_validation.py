from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import validate_source_release as release


def test_proposal_digest_is_stable_across_decision(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "PROPOSALS", tmp_path)
    proposal = {
        "schema_version": 1,
        "approval_id": "wpp-release-test",
        "source_id": "un_wpp",
        "release_id": "release-1",
        "approval": {"status": "pending", "approved_at": None, "actor": None, "note": None},
    }
    proposal["proposal_sha256"] = release._proposal_digest(proposal)
    digest = proposal["proposal_sha256"]
    (tmp_path / "wpp-release-test.json").write_text(json.dumps(proposal), encoding="utf-8")

    result = release.decide_release("wpp-release-test", "reviewer", "Evidence reviewed", True)

    stored = json.loads((tmp_path / "wpp-release-test.json").read_text(encoding="utf-8"))
    assert result["status"] == "approved"
    assert stored["proposal_sha256"] == digest
    assert release._proposal_digest(stored) == digest


def test_decision_rejects_already_decided_proposal(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "PROPOSALS", tmp_path)
    proposal = {
        "schema_version": 1,
        "approval_id": "wpp-release-test",
        "approval": {"status": "rejected", "approved_at": None, "actor": "reviewer", "note": "No"},
    }
    proposal["proposal_sha256"] = release._proposal_digest(proposal)
    (tmp_path / "wpp-release-test.json").write_text(json.dumps(proposal), encoding="utf-8")

    with pytest.raises(release.ReleaseValidationError, match="pending"):
        release.decide_release("wpp-release-test", "reviewer", "Retry", True)


def test_promotion_requires_explicit_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "PROPOSALS", tmp_path)
    proposal = {
        "schema_version": 1,
        "approval_id": "wpp-release-test",
        "approval": {"status": "pending", "approved_at": None, "actor": None, "note": None},
    }
    proposal["proposal_sha256"] = release._proposal_digest(proposal)
    (tmp_path / "wpp-release-test.json").write_text(json.dumps(proposal), encoding="utf-8")

    with pytest.raises(release.ReleaseValidationError, match="explicitly approved"):
        release.promote_release("wpp-release-test")


def test_promotion_rejects_changed_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(release, "PROPOSALS", tmp_path / "proposals")
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"result":"PASS"}', encoding="utf-8")
    proposal = {
        "schema_version": 1,
        "approval_id": "wpp-release-test",
        "source_id": "un_wpp",
        "release_id": "release-1",
        "validation_report": "evidence.json",
        "evidence": [{
            "label": "report",
            "path": "evidence.json",
            "sha256": "0" * 64,
            "byte_count": evidence.stat().st_size,
        }],
        "approval": {"status": "approved", "approved_at": "2026-11-02T00:00:00+00:00",
                     "actor": "reviewer", "note": "Approved"},
    }
    proposal["proposal_sha256"] = release._proposal_digest(proposal)
    proposal_path = release.PROPOSALS / "wpp-release-test.json"
    proposal_path.parent.mkdir(parents=True)
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")

    with pytest.raises(release.ReleaseValidationError, match="evidence changed"):
        release.promote_release("wpp-release-test")
