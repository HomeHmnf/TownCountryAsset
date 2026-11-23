from __future__ import annotations

import json
import sqlite3

import pytest

from tools.database import application_approval as approval


def setup_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE application_approvals (
            approval_id TEXT PRIMARY KEY, domain TEXT NOT NULL, artifact_sha256 TEXT NOT NULL,
            artifact_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
            approved_by TEXT, approved_at TEXT, decision_note TEXT, applied_at TEXT, application_id TEXT
        );
        CREATE TABLE database_application_events (
            event_id INTEGER PRIMARY KEY, approval_id TEXT NOT NULL, event_type TEXT NOT NULL,
            event_at TEXT NOT NULL, actor TEXT, details_json TEXT NOT NULL
        );
    """)
    return connection


def test_approval_is_explicit_and_consumed_once(monkeypatch, tmp_path):
    monkeypatch.setattr(approval, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "normalized.json"
    source.write_text('{"value": 10}', encoding="utf-8")
    artifact = approval.build_application_artifact(
        domain="wp1_5_statistics", inputs=[source],
        metadata={"policy_version": 1, "release": "2024-r1"},
    )
    connection = setup_connection()
    approval.propose_application(connection, approval_id="wp1-5-test-0001", artifact=artifact)
    with pytest.raises(approval.ApplicationApprovalError, match="not approved"):
        approval.require_approved_application(
            connection, approval_id="wp1-5-test-0001", artifact=artifact
        )
    approval.decide_application(
        connection, approval_id="wp1-5-test-0001", decision="approved", actor="reviewer"
    )
    approval.require_approved_application(
        connection, approval_id="wp1-5-test-0001", artifact=artifact
    )
    approval.record_application_applied(
        connection, approval_id="wp1-5-test-0001", application_id="apply-0001"
    )
    with pytest.raises(approval.ApplicationApprovalError, match="status=applied"):
        approval.require_approved_application(
            connection, approval_id="wp1-5-test-0001", artifact=artifact
        )
    assert [row[0] for row in connection.execute(
        "SELECT event_type FROM database_application_events ORDER BY event_id"
    ).fetchall()] == ["proposed", "approved", "applied"]


def test_changed_file_invalidates_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(approval, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "normalized.json"
    source.write_text('{"value": 10}', encoding="utf-8")
    artifact = approval.build_application_artifact(domain="country_data", inputs=[source])
    connection = setup_connection()
    approval.propose_application(connection, approval_id="country-data-0001", artifact=artifact)
    approval.decide_application(
        connection, approval_id="country-data-0001", decision="approved", actor="reviewer"
    )
    source.write_text('{"value": 11}', encoding="utf-8")
    with pytest.raises(approval.ApplicationApprovalError, match="inputs changed"):
        approval.require_approved_application(
            connection, approval_id="country-data-0001", artifact=artifact
        )
    assert connection.execute(
        "SELECT status FROM application_approvals WHERE approval_id='country-data-0001'"
    ).fetchone()[0] == "invalidated"


def test_rejected_proposal_cannot_be_applied(monkeypatch, tmp_path):
    monkeypatch.setattr(approval, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    artifact = approval.build_application_artifact(domain="identity", inputs=[source])
    connection = setup_connection()
    approval.propose_application(connection, approval_id="identity-test-0001", artifact=artifact)
    approval.decide_application(
        connection, approval_id="identity-test-0001", decision="rejected",
        actor="reviewer", note="Evidence insufficient",
    )
    with pytest.raises(approval.ApplicationApprovalError, match="status=rejected"):
        approval.require_approved_application(
            connection, approval_id="identity-test-0001", artifact=artifact
        )


def test_artifact_requires_unique_repo_local_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(approval, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    with pytest.raises(approval.ApplicationApprovalError, match="Duplicate"):
        approval.build_application_artifact(domain="test", inputs=[source, source])
    with pytest.raises(approval.ApplicationApprovalError, match="At least one"):
        approval.build_application_artifact(domain="test", inputs=[])


def test_shared_approval_workflow_creates_and_commits_explicit_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(approval, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "reviewed.json"
    source.write_text('{"approved": true}', encoding="utf-8")
    artifact = approval.build_application_artifact(
        domain="future_project_domain", inputs=[source], metadata={"batch": "one"}
    )
    connection = setup_connection()

    row = approval.approve_application(
        connection,
        approval_id="future-domain-0001",
        artifact=artifact,
        actor="project_owner",
        note="Reviewed and approved for application.",
    )

    assert row["status"] == "approved"
    assert not connection.in_transaction
    assert connection.execute(
        "SELECT status, approved_by, decision_note FROM application_approvals WHERE approval_id=?",
        ("future-domain-0001",),
    ).fetchone()[:] == ("approved", "project_owner", "Reviewed and approved for application.")
    assert [row[0] for row in connection.execute(
        "SELECT event_type FROM database_application_events ORDER BY event_id"
    ).fetchall()] == ["proposed", "approved"]


def test_shared_approval_workflow_respects_callers_transaction(monkeypatch, tmp_path):
    monkeypatch.setattr(approval, "REPOSITORY_ROOT", tmp_path)
    source = tmp_path / "reviewed.json"
    source.write_text("{}", encoding="utf-8")
    artifact = approval.build_application_artifact(domain="country_data", inputs=[source])
    connection = setup_connection()
    connection.execute("BEGIN")

    approval.approve_application(
        connection,
        approval_id="country-data-0002",
        artifact=artifact,
        actor="project_owner",
        note="Reviewed.",
    )

    assert connection.in_transaction
    connection.rollback()
    assert connection.execute(
        "SELECT COUNT(*) FROM application_approvals"
    ).fetchone()[0] == 0
