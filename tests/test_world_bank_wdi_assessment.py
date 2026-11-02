from __future__ import annotations

from urllib.parse import urlparse, parse_qs

import pytest

from tools import assess_world_bank_wdi as wdi


def _metadata(code):
    return [{
        "id": code,
        "name": f"Indicator {code}",
        "unit": "Unit",
        "sourceNote": "Series note",
        "sourceOrganization": "Originating organization",
        "source": {"id": "2", "value": "World Development Indicators"},
        "topics": [{"value": "Economy"}],
    }]


def test_metadata_preserves_source_note_and_originating_organization():
    result = wdi.fetch_indicator_metadata("NY.GDP.MKTP.CD", lambda url: [None, _metadata("NY.GDP.MKTP.CD")])
    assert result["indicator_code"] == "NY.GDP.MKTP.CD"
    assert result["source_note"] == "Series note"
    assert result["source_organization"] == "Originating organization"
    assert result["source_name"] == "World Development Indicators"


def test_observations_follow_pagination_and_exclude_aggregates():
    calls = []

    def fake(url):
        parsed = urlparse(url)
        if parsed.path.endswith("/country"):
            query = parse_qs(parsed.query)
            calls.append(("countries", int(query["page"][0])))
            return [{"pages": 1}, [
                {"id": "USA", "region": {"id": "NAC", "value": "North America"}},
                {"id": "WLD", "region": {"id": "NA", "value": "Aggregates"}},
                {"id": "AFE", "region": {"id": "NA", "value": "Aggregates"}},
            ]]
        query = parse_qs(parsed.query)
        page = int(query["page"][0])
        calls.append(("observations", page))
        row = {
            "country": {"id": "US", "value": "United States"},
            "countryiso3code": "USA",
            "date": "2024",
            "value": "100.5",
        }
        return [{"pages": 2}, [row]] if page == 1 else [{
            "pages": 2
        }, [
            {"country": {"id": "1W", "value": "World"}, "countryiso3code": "WLD", "date": "2024", "value": "200"},
            {"country": {"id": "ZH", "value": "Africa Eastern and Southern"}, "countryiso3code": "AFE", "date": "2024", "value": "300"},
            {"country": {"id": "US", "value": "United States"}, "countryiso3code": "USA", "date": "2025", "value": None},
        ]]

    records = wdi.fetch_indicator_observations("NY.GDP.MKTP.CD", 2020, 2025, fake)
    regions = wdi.fetch_country_regions(fake)
    summary = wdi.summarize_observations("NY.GDP.MKTP.CD", records, regions)
    assert ("observations", 1) in calls
    assert ("observations", 2) in calls
    assert summary["country_count"] == 1
    assert summary["aggregate_rows_excluded"] == 2
    assert summary["countries"][0]["observation_years"] == [2024]


def test_rejects_invalid_period():
    with pytest.raises(wdi.AssessmentError, match="year range"):
        wdi.build_assessment(2026, 2025, lambda _: None)


def test_assessment_marks_imf_comparison_unassessed_and_has_no_side_effects():
    def fake(url):
        parsed = urlparse(url)
        if parsed.path.endswith("/country"):
            return [{"pages": 1}, [
                {"id": "USA", "region": {"id": "NAC", "value": "North America"}},
            ]]
        if "/indicator/" in parsed.path and "/country/" not in parsed.path:
            code = parsed.path.rsplit("/", 1)[-1]
            return [None, _metadata(code)]
        return [{"pages": 1}, [{
            "country": {"id": "US", "value": "United States"},
            "countryiso3code": "USA",
            "date": "2025", "value": "1.0",
        }]]

    report = wdi.build_assessment(2025, 2025, fake)
    assert report["indicator_count"] == 8
    assert all(item["coverage"]["country_count"] == 1 for item in report["indicators"])
    assert all(item["coverage"]["countries"][0]["iso3"] == "USA" for item in report["indicators"])
    assert report["imf_weo_comparison"]["status"] == "not_assessed"
    assert report["side_effects"]["immutable_snapshots_acquired"] is False
    assert report["side_effects"]["canonical_database_written"] is False


def test_write_reports_creates_json_markdown_and_country_csv(tmp_path):
    report = {
        "checked_at": "2026-11-02T00:00:00+00:00",
        "period": {"start_year": 2020, "end_year": 2025},
        "indicator_count": 1,
        "imf_weo_comparison": {"status": "not_assessed"},
        "indicators": [{
            "field_id": 15, "key": "gdp",
            "metadata": {
                "indicator_code": "NY.GDP.MKTP.CD", "name": "GDP",
                "unit": "current US$", "source_organization": "National sources",
                "source_note": "Note", "metadata_url": "https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD?format=json",
            },
            "coverage": {"country_count": 1, "countries": [{
                "iso3": "USA", "country_name": "United States",
                "non_null_observation_count": 2, "first_observation_year": 2024,
                "latest_observation_year": 2025, "observation_years": [2024, 2025],
            }]},
        }],
    }
    target = wdi.write_reports(report, tmp_path)
    assert (target / "assessment.json").is_file()
    assert (target / "assessment.md").is_file()
    csv_text = (target / "country_coverage.csv").read_text()
    assert "USA" in csv_text
    assert "NY.GDP.MKTP.CD" in csv_text
