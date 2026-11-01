from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.resolve_source_selection import main as resolve_main
from tools.sources.reporting import write_refresh_report_bundle, write_selection_report_bundle


def test_refresh_bundle_separates_release_changes_unchanged_and_failures(tmp_path):
    report = {
        "run_id": "20261101T120000000000Z",
        "checked_at": "2026-11-01T12:00:00+00:00",
        "dry_run": False,
        "source_count": 3,
        "counts": {"unchanged": 1, "acquired_pending_source_validation": 1, "validation_error": 1},
        "limitations": ["Provider semantic validation remains separate."],
        "sources": [
            {
                "source_id": "sample",
                "discovery_status": "content_fingerprint_discovery",
                "downloads": [
                    {"download_id": "main", "configured_release": "rolling", "discovered_release": "content-a",
                     "release_kind": "rolling", "status": "acquired_pending_source_validation",
                     "discovered_sha256": "a" * 64, "detail": "Acquired candidate."},
                    {"download_id": "old", "configured_release": "v1", "release_kind": "edition_or_snapshot",
                     "status": "unchanged", "detail": "Already present."},
                ],
            },
            {
                "source_id": "bad",
                "discovery_status": "implemented_adapter_not_applicable",
                "downloads": [
                    {"download_id": "broken", "configured_release": "v1", "status": "validation_error",
                     "detail": "Checksum mismatch."},
                ],
            },
            {
                "source_id": "manual",
                "discovery_status": "manual_review_required",
                "detail": "No adapter.",
                "downloads": [],
            },
        ],
    }
    paths = write_refresh_report_bundle(report, tmp_path / "refreshes")
    assert Path(paths["summary"]).is_file()
    assert Path(paths["records"]).is_file()
    assert Path(paths["release_changes"]).is_file()
    assert Path(paths["failures"]).is_file()
    with Path(paths["release_changes"]).open(encoding="utf-8", newline="") as handle:
        changes = list(csv.DictReader(handle))
    assert len(changes) == 1
    assert changes[0]["release_id"] == "content-a"
    with Path(paths["failures"]).open(encoding="utf-8", newline="") as handle:
        failures = list(csv.DictReader(handle))
    assert len(failures) == 1
    assert failures[0]["status"] == "validation_error"
    provenance = json.loads(Path(paths["provenance"]).read_text(encoding="utf-8"))
    assert provenance["database_imported"] is False


def test_selection_bundle_writes_missing_fallback_conflict_and_override_audits(tmp_path):
    decisions = [
        {
            "storage": "scalar",
            "result": {
                "game_id": "tc_a", "field_key": "population", "field_id": 1,
                "primary_source": "un_wpp", "selection_mode": "priority_source",
                "selected_source": "un_wpp", "release_id": "wpp-2024",
                "selection_status": "observed", "value": 10, "unit": "people",
                "fallback_used": False,
            },
        },
        {
            "storage": "scalar",
            "result": {
                "game_id": "tc_a", "field_key": "labour_force", "field_id": 22,
                "primary_source": "ilostat", "selection_mode": "primary_with_fallback",
                "selected_source": "world_bank_wdi", "release_id": "wdi-2025",
                "selection_status": "estimated", "value": 20, "unit": "people",
                "fallback_used": True, "compatibility_reference": "review:compat-1",
                "reason": "Compatible fallback selected",
                "primary_candidate": {"source_id": "ilostat", "release_id": "ilo-2025"},
            },
        },
        {
            "storage": "scalar",
            "result": {
                "game_id": "tc_a", "field_key": "gdp", "field_id": 15,
                "primary_source": "imf_weo", "selection_mode": "priority_source",
                "selected_source": None, "release_id": None,
                "selection_status": "unavailable", "value": None, "unit": "usd",
                "fallback_used": False, "reason": "No validated observation",
            },
        },
        {
            "storage": "scalar",
            "result": {
                "game_id": "tc_a", "field_key": "capital_city", "field_id": 65,
                "primary_source": "official_national_sources", "selection_mode": "primary_with_fallback",
                "selected_source": "manual_override", "release_id": None,
                "selection_status": "observed", "value": "Example City", "unit": "city_name",
                "fallback_used": False, "override_id": "ovr-1", "override_reason": "Reviewed correction",
                "override_author": "reviewer", "effective_at": "2026-11-01T10:00:00+00:00",
                "prior_provider_candidate": None,
            },
        },
    ]
    paths, summary = write_selection_report_bundle(
        output_root=tmp_path / "selections",
        report_id="run-1",
        decisions=decisions,
        provenance={"policy_version": 1, "game_ids": ["tc_a"]},
    )
    assert summary["decision_count"] == 4
    assert summary["selected_count"] == 3
    assert summary["unavailable_count"] == 1
    assert summary["fallback_count"] == 1
    assert summary["override_count"] == 1
    for key in ("records", "missing", "fallbacks", "conflicts", "overrides", "provenance"):
        assert Path(paths[key]).is_file()
    with Path(paths["conflicts"]).open(encoding="utf-8", newline="") as handle:
        conflicts = list(csv.DictReader(handle))
    assert conflicts[0]["candidate_source"] == "ilostat"


def test_resolution_cli_writes_read_only_project_wide_audit(tmp_path):
    root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "normalized.json"
    input_path.write_text(json.dumps({
        "schema_version": 1,
        "game_ids": ["tc_demo"],
        "release_states": {"un_wpp": "wpp-2024"},
        "observations": [{
            "game_id": "tc_demo", "field_key": "population", "source_id": "un_wpp",
            "release_id": "wpp-2024", "value": 1234, "unit": "people",
            "status": "observed", "observation_period": "2024",
            "source_reference": "table:demo", "methodology": "normalized",
            "retrieved_at": "2026-11-01T08:00:00+00:00",
        }],
    }), encoding="utf-8")
    output_dir = tmp_path / "reports"
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text("[]", encoding="utf-8")
    result = resolve_main([
        "--input", str(input_path),
        "--policy", str(root / "config/source_selection.json"),
        "--registry", str(root / "config/data_sources.json"),
        "--overrides", str(overrides_path),
        "--output-dir", str(output_dir),
    ])
    assert result == 0
    bundles = list(output_dir.iterdir())
    assert len(bundles) == 1
    assert (bundles[0] / "summary.md").is_file()
    assert (bundles[0] / "records.csv").is_file()
    assert (bundles[0] / "missing.csv").is_file()
    provenance = json.loads((bundles[0] / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["database_imported"] is False
    assert provenance["policy_version"] == 1
    assert provenance["summary"]["field_count"] == 41
    assert "religions" in provenance["summary"]["coverage_by_field"]
    with (bundles[0] / "records.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    population = next(row for row in rows if row["field_key"] == "population")
    assert population["value"] == "1234"
    assert population["selected_source"] == "un_wpp"

def test_resolution_cli_reads_latest_validated_ledgers_when_release_states_omitted(tmp_path):
    root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "empty-observations.json"
    input_path.write_text(json.dumps({
        "schema_version": 1,
        "game_ids": ["tc_demo"],
        "observations": [],
    }), encoding="utf-8")
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text("[]", encoding="utf-8")
    result = resolve_main([
        "--input", str(input_path),
        "--policy", str(root / "config/source_selection.json"),
        "--registry", str(root / "config/data_sources.json"),
        "--overrides", str(overrides_path),
        "--output-dir", str(tmp_path / "reports"),
    ])
    assert result == 0
    bundle = next((tmp_path / "reports").iterdir())
    provenance = json.loads((bundle / "provenance.json").read_text(encoding="utf-8"))
    assert isinstance(provenance["latest_validated_releases"], dict)
    assert provenance["database_imported"] is False

def test_source_report_bundle_refuses_to_overwrite_existing_run(tmp_path):
    report = {
        "run_id": "fixed-run",
        "checked_at": "2026-11-01T12:00:00+00:00",
        "dry_run": True,
        "counts": {},
        "limitations": [],
        "sources": [],
    }
    paths = write_refresh_report_bundle(report, tmp_path / "refreshes")
    summary = Path(paths["summary"])
    original = summary.read_text(encoding="utf-8")
    import pytest
    with pytest.raises(FileExistsError, match="refusing to overwrite immutable bundle"):
        write_refresh_report_bundle(report, tmp_path / "refreshes")
    assert summary.read_text(encoding="utf-8") == original


def test_resolution_cli_emits_expected_missing_structured_catalogue_items(tmp_path):
    root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "structured.json"
    input_path.write_text(json.dumps({
        "schema_version": 1,
        "game_ids": ["tc_demo"],
        "observations": [],
        "expected_records": {
            "religions": [{"record_key": "christianity"}]
        },
    }), encoding="utf-8")
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text("[]", encoding="utf-8")
    output_dir = tmp_path / "reports"
    result = resolve_main([
        "--input", str(input_path),
        "--policy", str(root / "config/source_selection.json"),
        "--registry", str(root / "config/data_sources.json"),
        "--overrides", str(overrides_path),
        "--output-dir", str(output_dir),
    ])
    assert result == 0
    bundle = next(output_dir.iterdir())
    with (bundle / "records.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    religion = next(
        row for row in rows
        if row["field_key"] == "religions" and row["record_key"] == "christianity"
    )
    assert religion["storage"] == "structured"
    assert religion["selection_status"] == "unavailable"
    assert religion["value"] == ""
    with (bundle / "missing.csv").open(encoding="utf-8", newline="") as handle:
        missing = list(csv.DictReader(handle))
    assert any(row["field_key"] == "religions" and row["record_key"] == "christianity" for row in missing)

