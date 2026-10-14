from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone

import pytest

from tools import refresh_iso_review as refresh_tool


def upstream_csv(rows=None):
    rows = rows or [
        {"id": "4", "alpha2": "af", "alpha3": "afg", "name": "Afghanistan"},
        {"id": "8", "alpha2": "al", "alpha3": "alb", "name": "Albania"},
    ]
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["id", "alpha2", "alpha3", "name"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def test_normalize_source_uppercases_codes_and_preserves_names():
    payload = upstream_csv()
    normalized, count = refresh_tool.normalize_source(payload)
    assert count == 2
    assert normalized.splitlines()[0] == "alpha2,alpha3,english_name"
    assert "AF,AFG,Afghanistan" in normalized
    assert "AL,ALB,Albania" in normalized


def test_normalize_source_rejects_changed_schema_and_duplicates():
    with pytest.raises(ValueError, match="schema changed"):
        refresh_tool.normalize_source(b"code,name\nAA,Alpha\n")
    duplicate = upstream_csv([
        {"id": "1", "alpha2": "aa", "alpha3": "aaa", "name": "Alpha"},
        {"id": "2", "alpha2": "bb", "alpha3": "aaa", "name": "Beta"},
    ])
    with pytest.raises(ValueError, match="duplicate ISO code"):
        refresh_tool.normalize_source(duplicate)


def test_refresh_preserves_raw_snapshot_and_writes_provenance_and_report(tmp_path, monkeypatch):
    rows = [
        {"id": str(i), "alpha2": f"{chr(65 + i // 26)}{chr(65 + i % 26)}",
         "alpha3": f"X{i:02d}", "name": f"Entity {i}"}
        for i in range(210)
    ]
    # Use unique three-letter codes, as the production validator requires.
    rows = [
        {"id": str(i), "alpha2": f"{chr(65 + i // 26)}{chr(65 + i % 26)}",
         "alpha3": f"{chr(65 + i // (26 * 26))}{chr(65 + (i // 26) % 26)}{chr(65 + i % 26)}",
         "name": f"Entity {i}"}
        for i in range(210)
    ]
    payload = upstream_csv(rows)
    monkeypatch.setattr(refresh_tool, "fetch_bytes", lambda url: payload)
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({"records": [{
        "game_id": "tc_one",
        "names": {"en": "Entity 0"},
        "iso": {"assignment_status": "unverified"},
    }]}), encoding="utf-8")
    fixed_now = datetime(2026, 10, 14, 12, 30, tzinfo=timezone.utc)
    result = refresh_tool.refresh(
        registry_path=registry_path,
        output_dir=tmp_path / "raw_data" / "iso",
        report_path=tmp_path / "reports" / "proposals.md",
        now=fixed_now,
    )
    raw_path = tmp_path / result["raw_snapshot"]
    metadata_path = tmp_path / result["provenance"]
    normalized_path = tmp_path / result["normalized_reference"]
    report_path = tmp_path / result["report"]
    assert raw_path.read_bytes() == payload
    assert hashlib.sha256(payload).hexdigest() == result["raw_sha256"]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["raw_sha256"] == result["raw_sha256"]
    assert metadata["retrieved_on_utc"] == "2026-10-14"
    assert len(list((tmp_path / "raw_data" / "iso").glob("iso-3166-1-upstream-*.csv"))) == 1
    assert normalized_path.exists()
    assert "candidate_alpha3" not in report_path.read_text(encoding="utf-8")
    assert result["candidate_count"] == 1


def test_normalize_source_rejects_too_small_reference():
    with pytest.raises(ValueError, match="only 2 rows"):
        refresh_tool.normalize_source(upstream_csv())
