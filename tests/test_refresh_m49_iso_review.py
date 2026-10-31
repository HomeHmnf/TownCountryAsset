from __future__ import annotations
import json
from datetime import datetime, timezone
from tools import refresh_m49_iso_review as tool

def test_refresh_m49_creates_review_only_proposals_and_provenance(tmp_path, monkeypatch):
    html = b"""<table><tr><th>Country or Area</th><th>M49 Code</th><th>ISO-alpha2 Code</th><th>ISO-alpha3 Code</th><th>Region Name</th></tr>
    <tr><td>Example Land</td><td>001</td><td>EX</td><td>EXM</td><td>Region A</td></tr>
    <tr><td>Unassigned Area</td><td>002</td><td></td><td></td><td>Region B</td></tr></table>"""
    registry = {
        "_root": tmp_path,
        "storage": {"raw_root": "raw", "manifest_root": "manifests"},
        "sources": {"un_m49": {"name": "UN M49", "downloads": [{
            "id": "country_area_overview_html", "release": "test-release",
            "filename": "m49.html", "url": "https://example.test/m49",
        }]}},
    }
    state = {"status": "missing"}
    monkeypatch.setattr(tool, "load_registry", lambda path: registry)
    def inspect(_registry):
        return [{"source_id": "un_m49", "download_id": "country_area_overview_html",
                 "status": state["status"], "detail": "test"}]
    monkeypatch.setattr(tool, "inspect_snapshots", inspect)
    def acquire(_registry, sid, item):
        raw = tmp_path / "raw" / sid / item["id"] / item["release"] / item["filename"]
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(html)
        manifest = tmp_path / "manifests" / sid / item["id"] / f"{item['release']}.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("{}", encoding="utf-8")
        state["status"] = "valid"
    monkeypatch.setattr(tool, "acquire_one", acquire)
    identity_registry = tmp_path / "identity.json"
    identity_registry.write_text(json.dumps({"records":[{
        "game_id":"tc_example", "names":{"en":"Example Land"},
        "iso":{"assignment_status":"unverified"}
    }]}), encoding="utf-8")
    now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    result = tool.refresh(identity_registry, tmp_path/"out", tmp_path/"report.md", now=now)
    metadata = json.loads((tmp_path/result["provenance"]).read_text())
    assert metadata["source_id"] == "un_m49"
    assert metadata["m49_row_count"] == 2
    assert metadata["iso_candidate_count"] == 1
    assert len(metadata["rows_without_iso_codes"]) == 1
    assert result["candidate_count"] == 1
    report = (tmp_path/result["report"]).read_text()
    assert "not the ISO 3166 assignment authority" in report
    assert "human review" in report
