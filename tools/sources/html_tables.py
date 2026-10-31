"""Provider-neutral extraction and validation of HTML data tables."""
from __future__ import annotations
import re
from html.parser import HTMLParser
from typing import Iterable

def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ").strip()).casefold()

class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.depth = 0
        self.table = None
        self.row = None
        self.cell_kind = ""
        self.parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self.depth += 1
            if self.depth == 1: self.table = []
        elif self.depth == 1 and tag == "tr":
            self.row = []
        elif self.depth == 1 and tag in {"th", "td"} and self.row is not None:
            self.cell_kind, self.parts = tag, []
        elif self.depth == 1 and tag == "br" and self.cell_kind:
            self.parts.append(" ")

    def handle_data(self, data):
        if self.depth == 1 and self.cell_kind: self.parts.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.depth == 1 and tag in {"th", "td"} and self.cell_kind:
            value = re.sub(r"\s+", " ", "".join(self.parts)).strip()
            self.row.append((self.cell_kind, value))
            self.cell_kind, self.parts = "", []
        elif self.depth == 1 and tag == "tr" and self.row is not None:
            if self.row: self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.depth:
            self.depth -= 1
            if self.depth == 0 and self.table is not None:
                self.tables.append(self.table)
                self.table, self.row, self.cell_kind = None, None, ""

def extract_table(html: str, required_headers: Iterable[str], *, header_aliases=None):
    """Select exactly one table by required headings; reject ambiguous or ragged data."""
    required = {normalize_header(value) for value in required_headers}
    if not required: raise ValueError("At least one required table header must be declared")
    aliases = {normalize_header(k): v for k, v in (header_aliases or {}).items()}
    parser = _TableParser()
    parser.feed(html)
    matches = []
    for table in parser.tables:
        # Some publishers mark column labels with <td> rather than semantic
        # <th> elements. Identify the header row by its declared labels, not
        # by the HTML cell tag or its position in the table.
        for index, row in enumerate(table):
            if not row:
                continue
            headers = [aliases.get(normalize_header(value), value.strip()) for _, value in row]
            normalized = [normalize_header(value) for value in headers]
            if not required.issubset(set(normalized)):
                continue
            if len(set(normalized)) != len(normalized):
                raise ValueError("HTML table contains duplicate column headings")
            matches.append((headers, table[index + 1:]))
            break
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one HTML table matching required headers; found {len(matches)}")
    headers, raw_rows = matches[0]
    rows = []
    for number, row in enumerate(raw_rows, start=1):
        if not row or not any(value for _, value in row): continue
        if len(row) != len(headers):
            raise ValueError(f"HTML table row {number} has {len(row)} cells; expected {len(headers)}")
        rows.append(dict(zip(headers, (value for _, value in row), strict=True)))
    if not rows: raise ValueError("Selected HTML table contains no data rows")
    return headers, rows
