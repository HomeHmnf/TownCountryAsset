#!/usr/bin/env python3
"""Generate all IMF WEO field-15 identity-review batches from source evidence.

No manually prepared identity inventory, batch register, or exclusion register is
read. Inputs are the immutable IMF WEO CSV/Appendix, the UN M49 HTML snapshot,
the canonical identity registry, and the separately approved WBG crosswalk.

The tool generates proposal-only review artifacts. It never approves mappings
or writes to the registry, crosswalk, Project DB, or Game DB.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
import sys
import urllib.request
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.propose_iso_assignments import REVIEWED_NAME_VARIANTS, normalize_name
from tools.sources.m49 import parse_m49_html

ROOT = Path(__file__).resolve().parents[1]
RAW_WEO = ROOT / "raw_data/sources/imf_weo/october_2026/dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv"
IMF_PDF = ROOT / "raw_data/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf"
IMF_TEXT = ROOT / "derived_data/pdf_text/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf.txt"
IMF_TEXT_META = ROOT / "derived_data/pdf_text/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf.txt.json"
M49_HTML = ROOT / "raw_data/sources/un_m49/country_area_overview_html/2026-10-current/m49-country-area-overview.html"
M49_MANIFEST = ROOT / "data_manifests/sources/un_m49/country_area_overview_html/2026-10-current.json"
REGISTRY = ROOT / "config/country_identity_registry.json"
CROSSWALK = ROOT / "data/manual/source_crosswalks/imf_weo.json"
OUTPUT_ROOT = ROOT / "reports/sources/imf-weo-field15-identity-review/automatic"

IMF_PDF_URL = "https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf"
M49_URL = "https://unstats.un.org/unsd/methodology/m49/overview"
M49_FAQ_URL = "https://unstats.un.org/unsd/methodology/m49/"

EXPECTED_WEO_SHA256 = "a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d"
EXPECTED_WEO_BYTES = 26692032
EXPECTED_IMF_PDF_SHA256 = "cd4e2829d7e621d43134728bfc128547f776e909e08ef1d38b837e2d39e5ae2a"
EXPECTED_IMF_PDF_BYTES = 985701

YEAR_RE = re.compile(r"^\d{4}$")
GROUP_CODE_RE = re.compile(r"^(?:G\d{3}|GX\d{3})$")
IMF_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{3}$")

# WEO composite labels are checked against the actual October 2026 Appendix
# classification headings before they are dispositioned as aggregates.
AGGREGATE_EVIDENCE = {
    "world": ("World", "Global WEO composite; the Appendix describes WEO composite data."),
    "advanced economies": ("Advanced Economies", "IMF WEO economy-group composite."),
    "g7": ("Major Advanced Economies (G7)", "IMF WEO G7 composite."),
    "euro area ea": ("Euro Area", "IMF WEO euro-area composite."),
    "emerging market and developing economies": ("Emerging and Developing Economies", "IMF WEO economy-group composite."),
    "latin america and the caribbean lac": ("Latin America and the Caribbean", "IMF WEO regional composite."),
    "middle east and central asia": ("Middle East and Central Asia", "IMF WEO regional composite."),
    "emerging and developing asia": ("Emerging and Developing Asia", "IMF WEO regional composite."),
    "asean 5": ("ASEAN-5", "IMF WEO ASEAN-5 composite."),
    "sub saharan africa ssa": ("Sub-Saharan Africa", "IMF WEO regional composite."),
    "emerging and developing europe": ("Emerging and Developing Europe", "IMF WEO regional composite."),
    "european union eu": ("European Union", "IMF WEO European Union composite."),
    "other advanced economies advanced economies excluding g7 and euro area countries": (
        "Other Advanced Economies", "IMF WEO advanced-economy subgroup composite."
    ),
}

REVIEW_FIELDS = [
    "field_id", "indicator_code", "source_id", "source_name", "series_code",
    "populated_year_count", "first_populated_year", "last_populated_year",
    "triage_name_candidate_game_id", "triage_registry_name",
    "triage_registry_status", "triage_entity_type",
    "triage_iso_assignment_status", "exact_normalized_name_match",
    "independent_evidence_reference", "review_outcome", "approved_game_id",
    "owner_decision", "review_notes", "reviewed_proposed_game_id",
    "proposed_registry_name", "un_m49_code",
]


class IdentityReviewError(RuntimeError):
    """Source, evidence, or reconciliation validation failure."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IdentityReviewError(f"Expected JSON object: {path}")
    return value


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise IdentityReviewError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def _pdf_pages(text: str) -> dict[int, str]:
    parts = re.split(r"(?m)^--- PAGE (\d+) ---\s*$", text)
    pages: dict[int, str] = {}
    for index in range(1, len(parts), 2):
        pages[int(parts[index])] = parts[index + 1].strip()
    if len(pages) < 14:
        raise IdentityReviewError("IMF Appendix text sidecar does not contain pages 1–14")
    return pages


def parse_imf_appendix_codes(
    text: str, source_codes: set[str], *, expected_count: int | None = 197
) -> tuple[set[str], dict[int, str]]:
    """Read the Appendix ISO Code column from Country Data Documentation pages."""
    pages = _pdf_pages(text)
    table_text = "\n".join(pages.get(number, "") for number in range(10, 15))
    observed = {
        match.group(1)
        for match in re.finditer(r"(?m)^\s*([A-Z]{3})\s+\S", table_text)
    }
    codes = observed.intersection(source_codes)
    if re.search(r"(?m)^\s*UVK\s+Kosovo\b", table_text):
        codes.add("UVK")
    if "WBG" not in codes:
        raise IdentityReviewError("IMF Appendix Country Data Documentation is missing WBG")
    if "TWN" not in codes:
        raise IdentityReviewError("IMF Appendix Country Data Documentation is missing TWN")
    if "KOS" in codes or "UVK" not in codes:
        raise IdentityReviewError("Expected the documented KOS/UVK IMF Appendix code discrepancy")
    if expected_count is not None and len(codes) != expected_count:
        raise IdentityReviewError(
            f"Expected {expected_count} Appendix identity codes including UVK; found {len(codes)}"
        )
    return codes, pages


def read_weo_ngdpd_inventory(path: Path, *, expected_count: int = 210) -> list[dict[str, str]]:
    """Derive the full field-15 identity inventory directly from the WEO CSV."""
    _, raw_rows = _read_csv(path)
    if not raw_rows:
        raise IdentityReviewError("IMF WEO CSV contains no data rows")
    required = {"SERIES_CODE", "COUNTRY", "FREQUENCY"}
    if not required.issubset(raw_rows[0]):
        raise IdentityReviewError(f"IMF WEO CSV missing columns: {sorted(required - set(raw_rows[0]))}")
    headers = list(raw_rows[0])
    year_columns = sorted((name for name in headers if YEAR_RE.fullmatch(name)), key=int)
    if not year_columns:
        raise IdentityReviewError("IMF WEO CSV has no four-digit annual columns")

    inventory: list[dict[str, str]] = []
    seen_codes: set[str] = set()
    seen_series: set[str] = set()
    for line_number, row in enumerate(raw_rows, start=2):
        series = (row.get("SERIES_CODE") or "").strip()
        parts = series.split(".")
        if len(parts) != 3 or parts[1] != "NGDPD" or parts[2] != "A":
            continue
        if (row.get("FREQUENCY") or "").strip() != "Annual":
            raise IdentityReviewError(f"NGDPD annual series has unexpected frequency at CSV line {line_number}")
        source_id = parts[0]
        source_name = (row.get("COUNTRY") or "").strip()
        if not source_id or not source_name:
            raise IdentityReviewError(f"Missing source identity at CSV line {line_number}")
        if source_id in seen_codes or series in seen_series:
            raise IdentityReviewError(f"Duplicate IMF WEO source identity or series: {source_id}")
        seen_codes.add(source_id)
        seen_series.add(series)

        populated: list[int] = []
        for year_text in year_columns:
            value_text = (row.get(year_text) or "").strip()
            if not value_text:
                continue
            try:
                value = float(value_text)
            except ValueError as exc:
                raise IdentityReviewError(
                    f"Non-numeric NGDPD value at CSV line {line_number}, year {year_text}: {value_text!r}"
                ) from exc
            if not math.isfinite(value):
                raise IdentityReviewError(
                    f"Non-finite NGDPD value at CSV line {line_number}, year {year_text}"
                )
            populated.append(int(year_text))
        inventory.append({
            "source_id": source_id,
            "source_name": source_name,
            "series_code": series,
            "populated_year_count": str(len(populated)),
            "first_populated_year": str(min(populated)) if populated else "",
            "last_populated_year": str(max(populated)) if populated else "",
            "latest_actual_annual_data": (row.get("LATEST_ACTUAL_ANNUAL_DATA") or "").strip(),
        })

    inventory.sort(key=lambda row: row["source_id"])
    if len(inventory) != expected_count or len({row["source_id"] for row in inventory}) != expected_count:
        raise IdentityReviewError(f"Expected {expected_count} unique NGDPD annual source identities; found {len(inventory)}")
    return inventory


def _validate_wbg_crosswalk(crosswalk: dict[str, Any], registry_by_id: dict[str, dict[str, Any]]) -> str:
    approval = crosswalk.get("review_approval", {})
    mappings = crosswalk.get("mappings", [])
    if approval.get("status") != "approved" or len(mappings) != 1:
        raise IdentityReviewError("WBG must remain the sole owner-approved IMF WEO crosswalk mapping")
    mapping = mappings[0]
    if mapping.get("source_id") != "WBG":
        raise IdentityReviewError("The sole approved IMF WEO crosswalk entry is not WBG")
    game_id = mapping.get("game_id")
    target = registry_by_id.get(game_id)
    if game_id != "tc_50c420df8b2c4c6eaae47d795f9a1ea2" or target is None:
        raise IdentityReviewError("WBG crosswalk target differs from the recorded owner approval")
    if target.get("names", {}).get("en") != "Palestine":
        raise IdentityReviewError("WBG crosswalk target no longer resolves to the Palestine registry record")
    if "Field 15" not in approval.get("scope", ""):
        raise IdentityReviewError("WBG approval is not explicitly scoped to field 15")
    return game_id


def _registry_m49_name_index(
    registry_records: list[dict[str, Any]],
    m49_rows: list[dict[str, Any]],
) -> tuple[dict[str, tuple[dict[str, Any], str]], dict[str, list[str]]]:
    """Resolve registry records to M49 rows by English names only.

    Existing registry source IDs and ISO fields are deliberately not consulted.
    """
    m49_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in m49_rows:
        name = (row.get("Country or Area") or "").strip()
        if name:
            m49_by_name[normalize_name(name)].append(row)

    claims: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for record in registry_records:
        names = record.get("names") if isinstance(record.get("names"), dict) else {}
        name = names.get("en")
        if not isinstance(name, str) or not name.strip():
            continue
        normalized = normalize_name(name)
        matches = m49_by_name.get(normalized, [])
        note = ""
        variant = REVIEWED_NAME_VARIANTS.get(normalized)
        if not matches and variant and variant[0]:
            note = variant[1]
            matches = m49_by_name.get(normalize_name(variant[0]), [])
        if len(matches) == 1:
            m49_code = matches[0].get("M49 Code", "")
            claims[m49_code].append((record, note))

    resolved: dict[str, tuple[dict[str, Any], str]] = {}
    ambiguous: dict[str, list[str]] = {}
    for m49_code, records in claims.items():
        if len(records) == 1:
            resolved[m49_code] = records[0]
        else:
            ambiguous[m49_code] = [str(item[0].get("game_id", "")) for item in records]
    return resolved, ambiguous


def _triage_candidate(source_name: str, registry_records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Exact normalized-name triage only; never used to select a proposal."""
    key = normalize_name(source_name)
    matches = [
        record for record in registry_records
        if normalize_name(str((record.get("names") or {}).get("en", ""))) == key
    ]
    return matches[0] if len(matches) == 1 else None


def _verify_source_snapshots(
    weo_path: Path,
    pdf_path: Path,
    text_path: Path,
    text_meta_path: Path,
    m49_html_path: Path,
    m49_manifest_path: Path,
) -> dict[str, dict[str, Any]]:
    weo_hash, weo_size = sha256_file(weo_path), weo_path.stat().st_size
    if weo_hash != EXPECTED_WEO_SHA256 or weo_size != EXPECTED_WEO_BYTES:
        raise IdentityReviewError("IMF WEO CSV differs from the recorded October 2026 source snapshot")

    pdf_hash, pdf_size = sha256_file(pdf_path), pdf_path.stat().st_size
    if pdf_hash != EXPECTED_IMF_PDF_SHA256 or pdf_size != EXPECTED_IMF_PDF_BYTES:
        raise IdentityReviewError("IMF October 2026 Appendix differs from the recorded source snapshot")
    text_meta = _read_json(text_meta_path)
    text_hash = sha256_file(text_path)
    if text_meta.get("source_sha256") != pdf_hash or text_meta.get("text_sha256") != text_hash:
        raise IdentityReviewError("IMF Appendix extracted-text sidecar does not match the immutable PDF")

    m49_manifest = _read_json(m49_manifest_path)
    m49_hash, m49_size = sha256_file(m49_html_path), m49_html_path.stat().st_size
    if m49_manifest.get("source_id") != "un_m49" or m49_manifest.get("download_id") != "country_area_overview_html":
        raise IdentityReviewError("UN M49 manifest source/download identity mismatch")
    if m49_manifest.get("sha256") != m49_hash or m49_manifest.get("byte_count") != m49_size:
        raise IdentityReviewError("UN M49 HTML snapshot differs from its acquisition manifest")

    return {
        "imf_weo_csv": {"path": str(weo_path), "sha256": weo_hash, "byte_count": weo_size},
        "imf_appendix_pdf": {"path": str(pdf_path), "sha256": pdf_hash, "byte_count": pdf_size},
        "imf_appendix_text": {"path": str(text_path), "sha256": text_hash},
        "un_m49_html": {
            "path": str(m49_html_path), "sha256": m49_hash, "byte_count": m49_size,
            "manifest": str(m49_manifest_path), "release": m49_manifest.get("release"),
        },
    }



def _validate_m49_faq_html(faq_html: str) -> None:
    normalized = normalize_name(html.unescape(re.sub(r"<[^>]+>", " ", faq_html)))
    for code in ("158", "412"):
        phrase = f"numerical code {code} can be used to represent this area"
        if phrase not in normalized:
            raise IdentityReviewError(f"UN M49 FAQ no longer documents statistical-use code {code}")


def _fetch_m49_faq(url: str = M49_FAQ_URL, timeout: int = 30) -> tuple[str, dict[str, Any]]:
    request = urllib.request.Request(url, headers={
        "User-Agent": "TownCountryAsset-IdentityReview/1.0",
        "Accept": "text/html",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        parsed_url = urlparse(final_url)
        content_type = response.headers.get("Content-Type", "")
        if parsed_url.scheme != "https" or parsed_url.hostname != "unstats.un.org":
            raise IdentityReviewError("UN M49 FAQ redirect left the official HTTPS host")
        if content_type.split(";", 1)[0].strip().lower() != "text/html":
            raise IdentityReviewError(f"Unexpected UN M49 FAQ content type: {content_type!r}")
        payload = response.read()
    if not payload:
        raise IdentityReviewError("UN M49 FAQ response is empty")
    try:
        faq_html = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IdentityReviewError("UN M49 FAQ response is not valid UTF-8") from exc
    _validate_m49_faq_html(faq_html)
    metadata = {
        "source_url": url,
        "final_url": final_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_type": content_type,
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "validation": "official_UN_M49_FAQ_contains_statistical_use_codes_158_and_412",
    }
    return faq_html, metadata

def build_review(
    *,
    weo_path: Path = RAW_WEO,
    pdf_path: Path = IMF_PDF,
    text_path: Path = IMF_TEXT,
    text_meta_path: Path = IMF_TEXT_META,
    m49_html_path: Path = M49_HTML,
    m49_manifest_path: Path = M49_MANIFEST,
    registry_path: Path = REGISTRY,
    crosswalk_path: Path = CROSSWALK,
    verify_snapshots: bool = True,
) -> dict[str, Any]:
    """Build the complete review directly from original source snapshots."""
    required_paths = (
        weo_path, pdf_path, text_path, text_meta_path, m49_html_path,
        m49_manifest_path, registry_path, crosswalk_path,
    )
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise IdentityReviewError("Missing required source inputs: " + "; ".join(missing))

    fingerprints = (
        _verify_source_snapshots(
            weo_path, pdf_path, text_path, text_meta_path, m49_html_path, m49_manifest_path
        ) if verify_snapshots else {}
    )

    inventory = read_weo_ngdpd_inventory(weo_path)
    source_codes = {row["source_id"] for row in inventory}

    appendix_text = text_path.read_text(encoding="utf-8")
    appendix_codes, pages = parse_imf_appendix_codes(appendix_text, source_codes)
    group_section = normalize_name("\n".join(pages[number] for number in range(4, 9)))
    m49_html = m49_html_path.read_text(encoding="utf-8-sig")
    m49_faq_html, m49_faq_provenance = _fetch_m49_faq()

    try:
        parsed_m49 = parse_m49_html(m49_html)
    except (ValueError, UnicodeError) as exc:
        raise IdentityReviewError(f"Cannot parse official UN M49 HTML snapshot: {exc}") from exc
    m49_rows = parsed_m49["all_rows"]
    if parsed_m49["row_count"] != 248:
        raise IdentityReviewError(f"Expected 248 rows in the October 2026 M49 snapshot; found {parsed_m49['row_count']}")
    m49_by_alpha3 = {
        (row.get("ISO-alpha3 Code") or "").strip().upper(): row
        for row in m49_rows if (row.get("ISO-alpha3 Code") or "").strip()
    }
    if len(m49_by_alpha3) != parsed_m49["iso_candidate_count"]:
        raise IdentityReviewError("UN M49 contains duplicate or missing ISO-alpha3 reference keys")

    if verify_snapshots:
        fingerprints["canonical_identity_registry"] = {
            "path": str(registry_path), "sha256": sha256_file(registry_path)
        }
        fingerprints["imf_weo_crosswalk"] = {
            "path": str(crosswalk_path), "sha256": sha256_file(crosswalk_path)
        }

    registry = _read_json(registry_path)
    registry_records = registry.get("records")
    if not isinstance(registry_records, list):
        raise IdentityReviewError("Canonical registry records must be an array")
    registry_by_id = {row.get("game_id"): row for row in registry_records}
    if len(registry_by_id) != len(registry_records):
        raise IdentityReviewError("Canonical registry contains duplicate or missing persistent game IDs")
    approved_wbg_id = _validate_wbg_crosswalk(_read_json(crosswalk_path), registry_by_id)

    registry_by_m49, ambiguous_m49 = _registry_m49_name_index(registry_records, m49_rows)
    registry_by_exact_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in registry_records:
        name = str((record.get("names") or {}).get("en", "")).strip()
        if name:
            registry_by_exact_name[normalize_name(name)].append(record)

    aggregates: list[dict[str, str]] = []
    country_rows: list[dict[str, str]] = []
    exceptions: list[dict[str, str]] = []
    for item in inventory:
        source_id = item["source_id"]
        source_name = item["source_name"]
        group_key = normalize_name(source_name)
        if GROUP_CODE_RE.fullmatch(source_id):
            group_evidence = AGGREGATE_EVIDENCE.get(group_key)
            if not group_evidence:
                raise IdentityReviewError(
                    f"Unrecognized IMF WEO group code/name; refusing automatic exclusion: {source_id} {source_name}"
                )
            heading, rationale = group_evidence
            if group_key != "world" and normalize_name(heading) not in group_section:
                raise IdentityReviewError(
                    f"Aggregate label {source_name!r} is not supported by the IMF Appendix heading {heading!r}"
                )
            if group_key == "world" and "composite data" not in normalize_name(appendix_text):
                raise IdentityReviewError("IMF Appendix does not document composite data for the World aggregate")
            aggregates.append({
                "source_country_code": source_id,
                "series_code": item["series_code"],
                "source_country_name": source_name,
                "indicator_code": "NGDPD",
                "field_id": "15",
                "disposition": "excluded",
                "rationale": rationale + " Source code is outside the Appendix individual-economy ISO Code table.",
                "populated_year_count": item["populated_year_count"],
                "first_populated_year": item["first_populated_year"],
                "last_populated_year": item["last_populated_year"],
                "latest_actual_annual_data": item["latest_actual_annual_data"],
                "release": "october_2026",
                "source_sha256": EXPECTED_WEO_SHA256,
            })
            continue

        if source_id == "WBG":
            if source_id not in appendix_codes:
                raise IdentityReviewError("WBG is missing from the IMF Appendix individual-economy table")
            country_rows.append({**item, "classification": "approved_existing_crosswalk", "game_id": approved_wbg_id})
            continue

        if source_id == "KOS":
            if source_id in appendix_codes or not re.search(r"(?m)^\s*UVK\s+Kosovo\b", "\n".join(pages.values())):
                raise IdentityReviewError("Expected KOS source code versus UVK Appendix code discrepancy")
            if "kosovo" not in normalize_name(source_name):
                raise IdentityReviewError("KOS source row no longer identifies Kosovo")
            exceptions.append({
                "source_country_code": source_id,
                "source_country_name": source_name,
                "series_code": item["series_code"],
                "exception": "imf_appendix_code_discrepancy",
                "candidate_game_ids": "",
                "disposition": "hold_for_evidence",
                "rationale": (
                    "WEO source inventory uses KOS, while the October 2026 IMF Appendix Country Data "
                    "Documentation identifies Kosovo as UVK. UN M49 FAQ permits statistical-use code 412, "
                    "but the source-code discrepancy remains unresolved. Preserve the existing hold; no "
                    "game_id or M49 code is proposed."
                ),
                "evidence_reference": IMF_PDF_URL + ";" + M49_FAQ_URL,
            })
            country_rows.append({**item, "classification": "hold_for_evidence"})
            continue

        if source_id not in appendix_codes:
            raise IdentityReviewError(
                f"Unclassified source identity {source_id} is neither an IMF Appendix economy nor a recognized group"
            )

        triage = _triage_candidate(source_name, registry_records)
        triage_fields = {
            "triage_name_candidate_game_id": str(triage.get("game_id", "")) if triage else "",
            "triage_registry_name": str((triage.get("names") or {}).get("en", "")) if triage else "",
            "triage_registry_status": str(triage.get("status", "")) if triage else "",
            "triage_entity_type": str(triage.get("entity_type", "")) if triage else "",
            "triage_iso_assignment_status": str((triage.get("iso") or {}).get("assignment_status", "")) if triage else "",
            "exact_normalized_name_match": "true" if triage else "false",
        }

        if source_id == "TWN":
            if "taiwan" not in normalize_name(source_name):
                raise IdentityReviewError("TWN source row no longer identifies Taiwan")
            if any(normalize_name(row.get("Country or Area", "")) == "taiwan" for row in m49_rows):
                raise IdentityReviewError("Taiwan unexpectedly appears as a separate row in the M49 country/area table")
            taiwan_matches = registry_by_exact_name.get("taiwan", [])
            if len(taiwan_matches) != 1:
                raise IdentityReviewError("Expected one canonical registry record named Taiwan")
            target = taiwan_matches[0]
            m49_code = "158"
            match_note = (
                "UN M49 FAQ permits numerical code 158 for Taiwan Province of China strictly for statistical "
                "purposes; it is not a separate row in the standard country/area table. No sovereignty "
                "determination is made."
            )
            evidence = IMF_PDF_URL + ";" + M49_FAQ_URL
        else:
            m49_row = m49_by_alpha3.get(source_id)
            if m49_row is None:
                raise IdentityReviewError(f"IMF code {source_id} has no matching UN M49 ISO-alpha3 row")
            m49_code = str(m49_row.get("M49 Code", "")).strip()
            if not re.fullmatch(r"\d{3}", m49_code):
                raise IdentityReviewError(f"Invalid M49 numeric code for {source_id}: {m49_code!r}")
            if m49_code in ambiguous_m49:
                raise IdentityReviewError(
                    f"Ambiguous registry name claims for M49 {m49_code}: {ambiguous_m49[m49_code]}"
                )
            resolved = registry_by_m49.get(m49_code)
            if resolved is None:
                raise IdentityReviewError(
                    f"No unique registry target for M49 {m49_code} ({m49_row.get('Country or Area')})"
                )
            target, variant_note = resolved
            match_note = (
                f"M49 name reconciliation used explicit reviewed registry-name variant: {variant_note}"
                if variant_note else
                "M49 English country/area name matches the canonical registry English name after normalization."
            )
            evidence = IMF_PDF_URL + ";" + M49_URL

        game_id = str(target.get("game_id", ""))
        registry_name = str((target.get("names") or {}).get("en", ""))
        if not game_id or registry_by_id.get(game_id) is not target:
            raise IdentityReviewError(f"Invalid persistent registry target for {source_id}")
        country_rows.append({
            **item, "classification": "proposal", "game_id": game_id,
            "registry_name": registry_name, "m49_code": m49_code,
        })
        country_rows[-1]["_triage"] = triage_fields
        country_rows[-1]["_evidence"] = evidence
        country_rows[-1]["_match_note"] = match_note

    if len(aggregates) != 13 or sum(int(row["populated_year_count"]) for row in aggregates) != 665:
        raise IdentityReviewError(
            f"Expected 13 IMF aggregate series and 665 populated values; found {len(aggregates)} "
            f"series and {sum(int(row['populated_year_count']) for row in aggregates)} values"
        )
    if len(country_rows) != 197 or sum(row["classification"] == "proposal" for row in country_rows) != 195:
        raise IdentityReviewError("Expected 195 proposal identities plus the separately approved WBG identity")
    if len(exceptions) != 1 or exceptions[0]["source_country_code"] != "KOS":
        raise IdentityReviewError("Expected KOS to be the only held identity exception")

    review_rows: list[dict[str, str]] = []
    for item in country_rows:
        if item["classification"] == "approved_existing_crosswalk":
            continue
        triage = item.pop("_triage", {})
        evidence = item.pop("_evidence", "")
        match_note = item.pop("_match_note", "")
        source_id = item["source_id"]
        is_hold = source_id == "KOS"
        review_rows.append({
            "field_id": "15",
            "indicator_code": "NGDPD",
            "source_id": source_id,
            "source_name": item["source_name"],
            "series_code": item["series_code"],
            "populated_year_count": item["populated_year_count"],
            "first_populated_year": item["first_populated_year"],
            "last_populated_year": item["last_populated_year"],
            "triage_name_candidate_game_id": triage.get("triage_name_candidate_game_id", ""),
            "triage_registry_name": triage.get("triage_registry_name", ""),
            "triage_registry_status": triage.get("triage_registry_status", ""),
            "triage_entity_type": triage.get("triage_entity_type", ""),
            "triage_iso_assignment_status": triage.get("triage_iso_assignment_status", ""),
            "exact_normalized_name_match": triage.get("exact_normalized_name_match", "false"),
            "independent_evidence_reference": evidence if not is_hold else IMF_PDF_URL + ";" + M49_FAQ_URL,
            "review_outcome": "hold_for_evidence" if is_hold else "proposed_manual_review",
            "approved_game_id": "",
            "owner_decision": "" if is_hold else "pending_explicit_owner_approval",
            "review_notes": exceptions[0]["rationale"] if is_hold else (
                "Automatically generated proposal; not owner-approved. "
                "Identity chain: IMF WEO source code -> October 2026 IMF Appendix ISO Code -> "
                "UN M49 ISO-alpha3/M49 row -> canonical registry target by M49 English name. "
                "Registry source.current_source_id and registry ISO fields were not used to establish identity. "
                + match_note
            ),
            "reviewed_proposed_game_id": "" if is_hold else item["game_id"],
            "proposed_registry_name": "" if is_hold else item["registry_name"],
            "un_m49_code": "" if is_hold else item["m49_code"],
        })

    review_rows.sort(key=lambda row: row["source_id"])
    if len(review_rows) != 196:
        raise IdentityReviewError(f"Expected 196 review identities excluding aggregates and WBG; found {len(review_rows)}")
    proposal_ids = [row["reviewed_proposed_game_id"] for row in review_rows if row["reviewed_proposed_game_id"]]
    if len(proposal_ids) != 195 or len(set(proposal_ids)) != 195:
        raise IdentityReviewError("Expected 195 unique persistent game_id proposals")
    if any(row["owner_decision"] != "pending_explicit_owner_approval" for row in review_rows if row["reviewed_proposed_game_id"]):
        raise IdentityReviewError("Every generated mapping must remain pending explicit owner approval")

    inventory_output = []
    aggregate_by_code = {row["source_country_code"]: row for row in aggregates}
    review_by_code = {row["source_id"]: row for row in review_rows}
    for item in inventory:
        source_id = item["source_id"]
        if source_id in aggregate_by_code:
            classification = "excluded_aggregate"
        elif source_id == "WBG":
            classification = "approved_existing_crosswalk"
        elif source_id == "KOS":
            classification = "hold_for_evidence"
        else:
            classification = "proposal"
        inventory_output.append({
            **{key: item[key] for key in (
                "source_id", "source_name", "series_code", "populated_year_count",
                "first_populated_year", "last_populated_year",
            )},
            "classification": classification,
            "proposed_game_id": review_by_code.get(source_id, {}).get("reviewed_proposed_game_id", approved_wbg_id if source_id == "WBG" else ""),
        })

    return {
        "inventory": inventory_output,
        "aggregates": aggregates,
        "exceptions": exceptions,
        "review_rows": review_rows,
        "fingerprints": fingerprints,
        "m49_faq_html": m49_faq_html,
        "m49_faq_provenance": m49_faq_provenance,
        "summary": {
            "source": "IMF WEO October 2026 NGDPD",
            "field_id": 15,
            "indicator_code": "NGDPD",
            "source_identity_count": len(inventory),
            "aggregate_exclusion_count": len(aggregates),
            "individual_economy_count": len(country_rows),
            "existing_approved_crosswalk_count": 1,
            "proposal_count": len(proposal_ids),
            "unique_proposed_game_ids": len(set(proposal_ids)),
            "held_identity_count": len(exceptions),
            "held_source_ids": ["KOS"],
            "owner_approved_proposal_count": 0,
            "batch_size": 20,
            "batch_count": math.ceil(len(review_rows) / 20),
            "batch_sizes": [min(20, len(review_rows) - index * 20) for index in range(math.ceil(len(review_rows) / 20))],
            "database_written": False,
            "approval_created": False,
            "registry_modified": False,
            "crosswalk_modified": False,
            "manual_batch_registers_read": False,
            "manual_inventory_or_exclusion_registers_read": False,
        },
    }


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(result: dict[str, Any], output_root: Path = OUTPUT_ROOT, now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / timestamp
    suffix = 1
    while target.exists():
        target = output_root / f"{timestamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=False)

    _write_csv(target / "field_15_identity_inventory.csv", [
        "source_id", "source_name", "series_code", "populated_year_count",
        "first_populated_year", "last_populated_year", "classification", "proposed_game_id",
    ], result["inventory"])
    _write_csv(target / "field_15_exclusion_register.csv", list(result["aggregates"][0]), result["aggregates"])
    _write_csv(target / "identity_exceptions.csv", list(result["exceptions"][0]), result["exceptions"])

    rows = result["review_rows"]
    for batch_number in range(1, result["summary"]["batch_count"] + 1):
        reviewed_count = min(batch_number * 20, len(rows))
        cumulative: list[dict[str, str]] = []
        for index, reviewed in enumerate(rows):
            if index < reviewed_count:
                cumulative.append(dict(reviewed))
            else:
                pending = dict(reviewed)
                for key in (
                    "independent_evidence_reference", "approved_game_id", "owner_decision",
                    "review_notes", "reviewed_proposed_game_id", "proposed_registry_name", "un_m49_code",
                ):
                    pending[key] = ""
                pending["review_outcome"] = "pending_review"
                cumulative.append(pending)
        filename = f"field_15_identity_review_register_batch{batch_number:02d}.csv"
        _write_csv(target / filename, REVIEW_FIELDS, cumulative)

    _write_csv(target / "field_15_identity_review_register_final.csv", REVIEW_FIELDS, rows)
    (target / "m49_faq_snapshot.html").write_text(result["m49_faq_html"], encoding="utf-8")
    (target / "m49_faq_provenance.json").write_text(
        json.dumps(result["m49_faq_provenance"], ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    summary = dict(result["summary"])
    summary["m49_faq_provenance"] = result["m49_faq_provenance"]
    summary["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    summary["output_directory"] = str(target)
    summary["input_fingerprints"] = result["fingerprints"]
    summary["batch_files"] = [
        f"field_15_identity_review_register_batch{number:02d}.csv"
        for number in range(1, summary["batch_count"] + 1)
    ]
    (target / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# IMF WEO field 15 identity review — automatic generation",
        "",
        f"- Generated (UTC): {summary['generated_at_utc']}",
        "- Inputs: immutable IMF WEO CSV and Appendix, UN M49 HTML snapshot, canonical registry, approved WBG crosswalk.",
        "- No manually prepared identity inventory, batch register, or aggregate exclusion register was read.",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| Source identities | {summary['source_identity_count']} |",
        f"| Aggregate exclusions | {summary['aggregate_exclusion_count']} |",
        f"| Individual economies | {summary['individual_economy_count']} |",
        f"| Existing WBG approved crosswalk | {summary['existing_approved_crosswalk_count']} |",
        f"| Proposal-only mappings | {summary['proposal_count']} |",
        f"| Held identities | {summary['held_identity_count']} |",
        f"| Owner-approved new mappings | {summary['owner_approved_proposal_count']} |",
        f"| Automatic batches | {summary['batch_count']} |",
        "",
        "## Governance",
        "",
        "- All 195 generated mappings remain pending explicit project-owner approval.",
        "- KOS remains held because WEO uses KOS while the October 2026 IMF Appendix identifies Kosovo as UVK. The M49 FAQ's statistical-use code 412 is recorded as evidence but does not resolve the IMF code discrepancy.",
        "- TWN uses M49 FAQ numerical code 158 strictly for statistical purposes; no sovereignty determination is made.",
        "- WBG remains the separately owner-approved field-15-only mapping.",
        "- Registry source IDs and registry ISO fields are not used to establish identity; registry targets are resolved by official M49 English names and explicit reviewed name variants.",
        "",
        "## Side effects",
        "",
        "- Database writes: none.",
        "- Owner approvals created: none.",
        "- Canonical registry modified: no.",
        "- IMF WEO crosswalk modified: no.",
        "- Source snapshots modified: no.",
        "",
        "## Generated artifacts",
        "",
        "- `field_15_identity_inventory.csv`: regenerated from the raw IMF WEO CSV.",
        "- `field_15_exclusion_register.csv`: regenerated from IMF group-code and Appendix classification evidence.",
        "- `identity_exceptions.csv`: unresolved identity exceptions.",
        "- `field_15_identity_review_register_batch01.csv` through `batch10.csv`: all cumulative batches generated in one run.",
        "- `field_15_identity_review_register_final.csv`: final 196-row register.",
        "- `summary.json`: counts and source fingerprints.",
    ]
    (target / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weo-csv", type=Path, default=RAW_WEO)
    parser.add_argument("--imf-pdf", type=Path, default=IMF_PDF)
    parser.add_argument("--imf-text", type=Path, default=IMF_TEXT)
    parser.add_argument("--imf-text-metadata", type=Path, default=IMF_TEXT_META)
    parser.add_argument("--m49-html", type=Path, default=M49_HTML)
    parser.add_argument("--m49-manifest", type=Path, default=M49_MANIFEST)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--crosswalk", type=Path, default=CROSSWALK)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        result = build_review(
            weo_path=args.weo_csv, pdf_path=args.imf_pdf, text_path=args.imf_text,
            text_meta_path=args.imf_text_metadata, m49_html_path=args.m49_html,
            m49_manifest_path=args.m49_manifest, registry_path=args.registry,
            crosswalk_path=args.crosswalk,
        )
        target = write_outputs(result, args.output_root)
    except (OSError, csv.Error, json.JSONDecodeError, IdentityReviewError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**result["summary"], "output_directory": str(target)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
