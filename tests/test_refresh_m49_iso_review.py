from __future__ import annotations
import json
from datetime import datetime, timezone
from tools import refresh_m49_iso_review as tool

def test_refresh_m49_creates_review_only_proposals_and_provenance(tmp_path, monkeypatch):
    html = b"""<table><tr><th>Country or Area</th><th>M49 Code</th><th>ISO-alpha2 Code</th><th>ISO-alpha3 Code</th><th>Region Name</th></tr>
    <tr><td>Example Land</td><td>001</td><td>EX</td><td>EXM</td><td>Region A</td></tr>
    <tr><td>Unassigned Area</td><td>002</td><td></td><td></td><td>Region B</td></tr></table>"""
    monkeypatch.setattr(tool, "fetch_bytes", lambda url: html)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"records":[{"game_id":"tc_example","names":{"en":"Example Land"},"iso":{"assignment_status":"unverified"}}]}))
    now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    result = tool.refresh(registry, tmp_path/"raw", tmp_path/"report.md", now=now)
    metadata = json.loads((tmp_path/result["provenance"]).read_text())
    assert metadata["source_id"] == "un_m49"
    assert metadata["m49_row_count"] == 2
    assert metadata["iso_candidate_count"] == 1
    assert len(metadata["rows_without_iso_codes"]) == 1
    assert result["candidate_count"] == 1
    assert "does not modify" not in (tmp_path/result["report"]).read_text().lower()
