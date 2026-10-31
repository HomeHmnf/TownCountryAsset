"""UNSD M49 HTML adapter for the review-only ISO proposal workflow."""
from __future__ import annotations
import csv
import io
import re
from typing import Any
from tools.sources.html_tables import extract_table

REQUIRED_HEADERS = ("Country or Area", "M49 Code", "ISO-alpha2 Code", "ISO-alpha3 Code")
OPTIONAL_REGION_HEADERS = (
    "Global Code", "Global Name", "Region Code", "Region Name",
    "Sub-region Code", "Sub-region Name", "Intermediate Region Code", "Intermediate Region Name",
)

def parse_m49_html(html: str) -> dict[str, Any]:
    """Retain all M49 rows; expose only fully coded rows as ISO candidates."""
    # The live UN page contains several translated tables; select English
    # explicitly when its stable table ID is present. Small fixtures and other
    # single-table providers may omit IDs, so retain unique-header selection.
    english_table_present = bool(
        re.search(
            r'<table\\b[^>]*\\bid\\s*=\\s*["\\']downloadTableEN["\\']',
            html,
            re.IGNORECASE,
        )
    )
    selected_table_id = ENGLISH_TABLE_ID if english_table_present else None
    headers, rows = extract_table(
        html,
        REQUIRED_HEADERS,
        table_id=selected_table_id,
    )
    seen_m49, seen_alpha2, seen_alpha3 = set(), set(), set()
    iso_rows, excluded = [], []
    for line, row in enumerate(rows, start=1):
        name = row.get("Country or Area", "").strip()
        m49 = row.get("M49 Code", "").strip()
        alpha2 = row.get("ISO-alpha2 Code", "").strip().upper()
        alpha3 = row.get("ISO-alpha3 Code", "").strip().upper()
        if not name: raise ValueError(f"M49 row {line}: country/area name is empty")
        if not re.fullmatch(r"\d{3}", m49): raise ValueError(f"M49 row {line}: invalid M49 code {m49!r}")
        if m49 in seen_m49: raise ValueError(f"M49 row {line}: duplicate M49 code {m49}")
        seen_m49.add(m49)
        if bool(alpha2) != bool(alpha3):
            raise ValueError(f"M49 row {line}: only one ISO alpha code is populated")
        if not alpha2:
            excluded.append({"m49_code": m49, "country_or_area": name,
                             "reason": "UN M49 row has no ISO alpha-2/alpha-3 assignment"})
            continue
        if not re.fullmatch(r"[A-Z]{2}", alpha2): raise ValueError(f"M49 row {line}: invalid ISO alpha-2 code {alpha2!r}")
        if not re.fullmatch(r"[A-Z]{3}", alpha3): raise ValueError(f"M49 row {line}: invalid ISO alpha-3 code {alpha3!r}")
        if alpha2 in seen_alpha2 or alpha3 in seen_alpha3:
            raise ValueError(f"M49 row {line}: duplicate ISO alpha code")
        seen_alpha2.add(alpha2); seen_alpha3.add(alpha3)
        iso_rows.append({
            "alpha2": alpha2, "alpha3": alpha3, "english_name": name, "m49_code": m49,
            **{key: row.get(key, "") for key in OPTIONAL_REGION_HEADERS if key in headers},
        })
    if not iso_rows: raise ValueError("M49 table contains no rows with ISO alpha-2/alpha-3 codes")
    return {"headers": headers, "table_id": "downloadTableEN", "all_rows": rows, "iso_rows": iso_rows,
            "excluded_without_iso": excluded, "row_count": len(rows),
            "iso_candidate_count": len(iso_rows)}

def render_iso_reference_csv(parsed: dict[str, Any]) -> str:
    """Render the strict normalized CSV consumed by the ISO proposal engine."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["alpha2", "alpha3", "english_name"], lineterminator="\n")
    writer.writeheader()
    for row in parsed["iso_rows"]:
        writer.writerow({key: row[key] for key in ("alpha2", "alpha3", "english_name")})
    return output.getvalue()
