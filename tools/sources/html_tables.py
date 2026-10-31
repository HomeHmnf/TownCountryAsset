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
        self.table_ids = []
        self.depth = 0
        self.table = None
        self.row = None
        self.cell_kind = ""
        self.parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self.depth += 1
            if self.depth == 1:
                self.table = []
                self.table_id = dict(attrs).get("id")
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
                self.table_ids.append(self.table_id)
                self.table, self.table_id, self.row, self.cell_kind = None, None, None, ""

def extract_table(html: str, required_headers: Iterable[str], *, header_aliases=None, table_id=None):
    """Select by optional exact HTML table id and required headings.

    Without table_id, exactly one table must match the headings. With table_id,
    exactly one table must have that id and satisfy the same validation.
    """
    required = {normalize_header(value) for value in required_headers}
    if not required: raise ValueError("At least one required table header must be declared")
    if table_id is not None and not table_id.strip():
        raise ValueError("table_id must be a non-empty string when supplied")
    aliases = {normalize_header(k): v for k, v in (header_aliases or {}).items()}
    parser = _TableParser()
    parser.feed(html)
    if table_id is None:
        candidates = parser.tables
    else:
        candidates = [
            table for candidate_id, table in zip(parser.table_ids, parser.tables, strict=True)
            if candidate_id == table_id
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"Expected exactly one HTML table with id {table_id!r}; found {len(candidates)}"
            )
    matches = []
    for table in candidates:
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
        if table_id is not None:
            raise ValueError(f"HTML table {table_id!r} does not contain exactly one valid header row")
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
