from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone

import shapefile

from tools import refresh_persian_localization as localization


def make_archive(path):
    base = path.parent / "ne_test"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POINT)
    writer.field("ADM0_A3", "C", size=12)
    writer.field("WIKIDATAID", "C", size=12)
    for index, (source_id, qid) in enumerate([
        ("AAA", "Q30"),
        ("BBB", ""),
        ("CCC", "not-a-qid"),
    ]):
        writer.point(index, index)
        writer.record(source_id, qid)
    writer.close()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for suffix in (".shp", ".shx", ".dbf"):
            archive.write(base.with_suffix(suffix), arcname=f"ne_test{suffix}")
    return path


def sample_registry():
    return {
        "records": [
            {
                "game_id": "tc_stable_1",
                "source": {"current_source_id": "AAA"},
                "names": {"en": "Alpha", "fa": None},
            },
            {
                "game_id": "tc_stable_2",
                "source": {"current_source_id": "BBB"},
                "names": {"en": "Beta", "fa": None},
            },
            {
                "game_id": "tc_stable_3",
                "source": {"current_source_id": "CCC"},
                "names": {"en": "Gamma", "fa": "نام فعلی"},
            },
        ]
    }


def test_source_qid_mapping_uses_explicit_natural_earth_fields(tmp_path):
    archive = make_archive(tmp_path / "source.zip")
    assert localization.source_qids_from_archive(archive) == {
        "AAA": "Q30",
        "BBB": "",
        "CCC": "",
    }


def test_sparql_query_uses_only_valid_qids_and_explicit_prefixes():
    query = localization.build_sparql_query(["Q30", "Q42", "Q30", "bad"])
    assert "PREFIX wd:" in query
    assert "PREFIX rdfs:" in query
    assert "wd:Q30" in query and "wd:Q42" in query
    assert "bad" not in query
    assert 'LANG(?itemLabel) = "fa"' in query


def test_fetch_labels_parses_current_persian_label_response(monkeypatch):
    payload = json.dumps({
        "results": {"bindings": [{
            "item": {"value": "http://www.wikidata.org/entity/Q30"},
            "itemLabel": {"value": "ایالات متحده آمریکا"},
        }]}
    }, ensure_ascii=False).encode("utf-8")

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self):
            return payload

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://example.invalid/sparql"
        assert request.get_method() == "POST"
        assert b"query=" in request.data
        assert timeout == 5
        return Response()

    monkeypatch.setattr(localization.urllib.request, "urlopen", fake_urlopen)
    raw, labels = localization.fetch_labels(
        "https://example.invalid/sparql", ["Q30"], timeout=5
    )
    assert raw == payload
    assert labels == {"Q30": "ایالات متحده آمریکا"}


def test_build_review_never_infers_missing_qid_or_approves_candidate():
    registry = sample_registry()
    before = json.loads(json.dumps(registry))
    review = localization.build_review(
        registry,
        {"AAA": "Q30", "BBB": "", "CCC": "Q42"},
        {"Q30": "نام پیشنهادی", "Q42": "نام دیگر"},
    )
    assert review["unique_game_ids"] == 3
    assert review["candidate_count"] == 2
    assert review["missing_qid_count"] == 1
    assert review["rows"][0]["game_id"] == "tc_stable_1"
    assert review["rows"][0]["candidate_persian_name"] == "نام پیشنهادی"
    assert review["rows"][0]["review_status"] == "unreviewed"
    assert review["rows"][1]["candidate_persian_name"] == ""
    assert registry == before


def test_refresh_preserves_timestamped_snapshot_provenance_and_review_report(tmp_path, monkeypatch):
    archive = make_archive(tmp_path / "source.zip")
    registry_path = tmp_path / "registry.json"
    registry = sample_registry()
    original = json.dumps(registry, ensure_ascii=False, indent=2) + "\n"
    registry_path.write_text(original, encoding="utf-8")
    output_dir = tmp_path / "raw"
    report_path = tmp_path / "reports" / "persian-review.md"
    now = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)
    raw = b'{"results":{"bindings":[]}}'

    def fake_fetch(url, qids, timeout):
        assert url == "https://example.invalid/sparql"
        assert qids == ["Q30"]
        assert timeout == 10
        return raw, {"Q30": "نام پیشنهادی"}

    monkeypatch.setattr(localization, "fetch_labels", fake_fetch)
    result = localization.refresh(
        archive, registry_path, output_dir, report_path,
        "https://example.invalid/sparql", 10, now,
    )
    assert result["record_count"] == 3
    assert result["candidate_count"] == 1
    assert result["missing_qid_count"] == 1
    raw_path = output_dir / "wikidata-persian-labels-20261022T080000Z.json"
    provenance_path = output_dir / "wikidata-persian-provenance-20261022T080000Z.json"
    assert raw_path.read_bytes() == raw
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["source_url"] == "https://example.invalid/sparql"
    assert provenance["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert provenance["retrieved_at_utc"] == now.isoformat()
    assert "نام پیشنهادی" in report_path.read_text(encoding="utf-8")
    assert "no label is approved" in report_path.read_text(encoding="utf-8")
    assert registry_path.read_text(encoding="utf-8") == original
