from __future__ import annotations
import pytest
from tools.sources.html_tables import extract_table
from tools.sources.m49 import parse_m49_html, render_iso_reference_csv

def test_generic_html_table_selects_by_headers_and_normalizes_cells():
    html = """<table><tr><th>Other</th></tr><tr><td>x</td></tr></table>
    <table><tr><th>Country or Area</th><th>M49 Code</th><th>ISO-alpha2 Code</th><th>ISO-alpha3 Code</th></tr>
    <tr><td>Example&nbsp;Land</td><td>001</td><td>EX</td><td>EXM</td></tr></table>"""
    headers, rows = extract_table(html, ["Country or Area", "M49 Code"])
    assert headers[0] == "Country or Area"
    assert rows[0]["Country or Area"] == "Example Land"


def test_generic_html_table_detects_header_labels_in_td_cells():
    html = """<table>
    <tr><td>Country or Area</td><td>M49 Code</td><td>ISO-alpha2 Code</td><td>ISO-alpha3 Code</td></tr>
    <tr><td>Example Land</td><td>001</td><td>EX</td><td>EXM</td></tr>
    </table>"""
    headers, rows = extract_table(html, ["Country or Area", "M49 Code", "ISO-alpha2 Code", "ISO-alpha3 Code"])
    assert headers == ["Country or Area", "M49 Code", "ISO-alpha2 Code", "ISO-alpha3 Code"]
    assert rows[0]["M49 Code"] == "001"

def test_generic_html_table_rejects_ambiguous_matching_tables():
    html = "<table><tr><th>Name</th></tr><tr><td>A</td></tr></table>" * 2
    with pytest.raises(ValueError, match="exactly one"): extract_table(html, ["Name"])

def test_generic_html_table_rejects_row_width_mismatch():
    html = "<table><tr><th>Name</th><th>Code</th></tr><tr><td>A</td></tr></table>"
    with pytest.raises(ValueError, match="cells"): extract_table(html, ["Name", "Code"])

def test_m49_adapter_retains_regions_and_excludes_rows_without_iso_codes():
    html = """<table>
    <tr><th>Country or Area</th><th>M49 Code</th><th>ISO-alpha2 Code</th><th>ISO-alpha3 Code</th><th>Region Name</th><th>Sub-region Name</th></tr>
    <tr><td>Example Land</td><td>001</td><td>EX</td><td>EXM</td><td>Region A</td><td>Sub A</td></tr>
    <tr><td>Unassigned Area</td><td>002</td><td></td><td></td><td>Region B</td><td>Sub B</td></tr>
    </table>"""
    parsed = parse_m49_html(html)
    assert parsed["row_count"] == 2 and parsed["iso_candidate_count"] == 1
    assert parsed["excluded_without_iso"][0]["m49_code"] == "002"
    assert parsed["iso_rows"][0]["Region Name"] == "Region A"
    assert "EX,EXM,Example Land" in render_iso_reference_csv(parsed)

def test_m49_adapter_rejects_partial_iso_pair():
    html = """<table><tr><th>Country or Area</th><th>M49 Code</th><th>ISO-alpha2 Code</th><th>ISO-alpha3 Code</th></tr>
    <tr><td>Example</td><td>001</td><td>EX</td><td></td></tr></table>"""
    with pytest.raises(ValueError, match="only one ISO"): parse_m49_html(html)

def test_m49_adapter_rejects_duplicate_iso_codes():
    html = """<table><tr><th>Country or Area</th><th>M49 Code</th><th>ISO-alpha2 Code</th><th>ISO-alpha3 Code</th></tr>
    <tr><td>One</td><td>001</td><td>EX</td><td>EXM</td></tr>
    <tr><td>Two</td><td>002</td><td>EX</td><td>EXM</td></tr></table>"""
    with pytest.raises(ValueError, match="duplicate ISO"): parse_m49_html(html)


def test_generic_html_table_selects_exact_table_id_among_multilingual_matches():
    html = """
    <div id="ENG_Overview"><table id="downloadTableEN">
      <tr><td>Name</td><td>Code</td></tr><tr><td>Algeria</td><td>012</td></tr>
    </table></div>
    <div id="FRA_Overview"><table id="downloadTableFR">
      <tr><td>Name</td><td>Code</td></tr><tr><td>Algérie</td><td>012</td></tr>
    </table></div>
    """
    headers, rows = extract_table(html, ["Name", "Code"], table_id="downloadTableEN")
    assert headers == ["Name", "Code"]
    assert rows == [{"Name": "Algeria", "Code": "012"}]


def test_generic_html_table_rejects_missing_or_duplicate_requested_id():
    with pytest.raises(ValueError, match="with id"):
        extract_table("<table id='other'><tr><td>Name</td></tr><tr><td>A</td></tr></table>",
                      ["Name"], table_id="wanted")
    html = ("<table id='wanted'><tr><td>Name</td></tr><tr><td>A</td></tr></table>"
            "<table id='wanted'><tr><td>Name</td></tr><tr><td>B</td></tr></table>")
    with pytest.raises(ValueError, match="with id"):
        extract_table(html, ["Name"], table_id="wanted")


def test_m49_adapter_selects_english_table_from_multilingual_page():
    def table(table_id, name):
        return (
            f'<table id="{table_id}"><tr><td>Country or Area</td><td>M49 Code</td>'
            '<td>ISO-alpha2 Code</td><td>ISO-alpha3 Code</td></tr>'
            f'<tr><td>{name}</td><td>012</td><td>DZ</td><td>DZA</td></tr></table>'
        )
    html = table("downloadTableEN", "Algeria") + table("downloadTableFR", "Algérie")
    parsed = parse_m49_html(html)
    assert parsed["table_id"] == "downloadTableEN"
    assert parsed["iso_rows"][0]["english_name"] == "Algeria"
