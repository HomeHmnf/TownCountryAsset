from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import wp1_5_validation as validation


def test_discovers_newest_complete_candidate(monkeypatch, tmp_path):
    root = tmp_path
    generated = root / "generated"
    older = generated / "candidate_old"
    newer = generated / "candidate_new"
    for directory, retrieved in ((older, "2026-10-01T00:00:00Z"), (newer, "2026-11-01T00:00:00Z")):
        directory.mkdir(parents=True)
        (directory / "application_manifest.json").write_text(json.dumps({
            "source_key": "un_wpp", "retrieved_at": retrieved, "release": "r1"
        }))
        (directory / "normalized_observations.json").write_text(json.dumps({
            "schema_version": 1, "source_key": "un_wpp", "release": "r1", "observations": []
        }))
    monkeypatch.setattr(validation, "REPOSITORY_ROOT", root)
    selected, manifest = validation.discover_candidate("un_wpp")
    assert selected == newer
    assert manifest["retrieved_at"] == "2026-11-01T00:00:00Z"


def test_candidate_discovery_rejects_equal_latest_timestamps(monkeypatch, tmp_path):
    root = tmp_path
    for name in ("candidate_a", "candidate_b"):
        directory = root / "generated" / name
        directory.mkdir(parents=True)
        (directory / "application_manifest.json").write_text(json.dumps({
            "source_key": "un_wpp", "retrieved_at": "2026-11-01T00:00:00Z"
        }))
        (directory / "normalized_observations.json").write_text("{}")
    monkeypatch.setattr(validation, "REPOSITORY_ROOT", root)
    with pytest.raises(validation.ValidationError, match="Ambiguous newest"):
        validation.discover_candidate("un_wpp")


def test_candidate_discovery_rejects_incomplete_latest_candidate(monkeypatch, tmp_path):
    root = tmp_path
    directory = root / "generated" / "candidate"
    directory.mkdir(parents=True)
    (directory / "application_manifest.json").write_text(json.dumps({
        "source_key": "un_wpp", "retrieved_at": "2026-11-01T00:00:00Z"
    }))
    monkeypatch.setattr(validation, "REPOSITORY_ROOT", root)
    with pytest.raises(validation.ValidationError, match="incomplete"):
        validation.discover_candidate("un_wpp")
