#!/usr/bin/env python3
"""Propose ISO 3166-1 candidates from an explicitly supplied reference CSV.

This tool is deliberately read-only with respect to the identity registry. It
matches normalized English names only; it never treats Natural Earth source IDs
or existing ISO fields as proof of an ISO assignment.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {"alpha2", "alpha3", "english_name"}

# Explicit, review-only naming variants. These are maintained mappings, not
# fuzzy matches; every resulting code remains a candidate requiring human review.
# The keys are normalized registry labels and values are exact reference labels.
REVIEWED_NAME_VARIANTS = {
    "aland": ("Åland Islands", "Diacritic and abbreviated display-name variant."),
    "bahamas": ("Bahamas", "Reference uses the formal name without the leading article."),
    "bolivia": ("Bolivia, Plurinational State of", "Reference uses the formal state name."),
    "brunei": ("Brunei Darussalam", "Reference uses the formal country name."),
    "democratic republic of the congo": ("Congo, Democratic Republic of the", "Word-order variant of the formal name."),
    "east timor": ("Timor-Leste", "Common English name variant."),
    "federated states of micronesia": ("Micronesia, Federated States of", "Word-order variant of the formal name."),
    "french southern and antarctic lands": ("French Southern Territories", "Natural Earth display label differs from the ISO reference name; verify entity scope."),
    "falkland islands": ("Falkland Islands (the) [Malvinas]", "Reference includes the formal Malvinas name and article; verify entity scope."),
    "hong kong s a r": ("Hong Kong", "Administrative-region suffix variant."),
    "iran": ("Iran, Islamic Republic of", "Reference uses the formal name."),
    "ivory coast": ("Côte d'Ivoire", "Common English name variant."),
    "laos": ("Lao People's Democratic Republic", "Common English name variant."),
    "macao s a r": ("Macao", "Administrative-region suffix variant."),
    "moldova": ("Moldova, Republic of", "Reference uses the formal name."),
    "north korea": ("Korea, Democratic People's Republic of", "Common English name variant."),
    "palestine": ("Palestine, State of", "Reference uses the formal name."),
    "pitcairn islands": ("Pitcairn", "Plural display-name variant."),
    "republic of the congo": ("Congo", "Common country-name variant; verify entity distinction."),
    "republic of serbia": ("Serbia", "Display-name prefix variant."),
    "russia": ("Russian Federation", "Common English name variant."),
    "saint helena": ("Saint Helena, Ascension and Tristan da Cunha", "Reference uses the extended territory name."),
    "saint martin": ("Saint Martin (French part)", "Reference identifies the French part explicitly; verify geometry/entity scope."),
    "sint maarten": ("Sint Maarten (Dutch part)", "Reference explicitly identifies the Dutch part; verify geometry/entity scope."),
    "south georgia and the islands": ("South Georgia and the South Sandwich Islands", "Display-name variant; verify geometry/entity scope."),
    "south korea": ("Korea, Republic of", "Common English name variant."),
    "syria": ("Syrian Arab Republic", "Common English name variant."),
    "taiwan": ("Taiwan, Province of China", "Reference uses its published formal label; assignment requires policy review."),
    "the bahamas": ("Bahamas", "Reference omits the leading article."),
    "turkey": ("Türkiye", "Current reference spelling differs."),
    "united kingdom": ("United Kingdom of Great Britain and Northern Ireland", "Reference uses the full formal name."),
    "united republic of tanzania": ("Tanzania, United Republic of", "Word-order variant of the formal name."),
    "united states virgin islands": ("Virgin Islands (U.S.)", "Display-name variant; verify entity scope."),
    "vatican": ("Holy See", "ISO reference identifies the Holy See; review entity-vs-display-label semantics."),
    "venezuela": ("Venezuela, Bolivarian Republic of", "Reference uses the formal name."),
    "vietnam": ("Viet Nam", "Current reference spelling differs from the registry display name."),
    "british virgin islands": ("Virgin Islands (British)", "Display-name variant."),
    "kosovo": ("", "No ISO 3166-1 candidate is proposed by this alias map."),
    "somaliland": ("", "No ISO 3166-1 candidate is proposed by this alias map."),
    "northern cyprus": ("", "No ISO 3166-1 candidate is proposed by this alias map."),
}
DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_OUTPUT = Path("reports/iso-assignment-proposals.md")


def normalize_name(value: str) -> str:
    """Normalize presentation differences without guessing synonyms."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def read_reference(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise ValueError(
                "ISO reference CSV is missing required columns: " + ", ".join(missing)
            )
        rows: list[dict[str, str]] = []
        seen2: set[str] = set()
        seen3: set[str] = set()
        for line, raw in enumerate(reader, start=2):
            row = {key: (raw.get(key) or "").strip() for key in REQUIRED_COLUMNS}
            alpha2, alpha3, name = row["alpha2"], row["alpha3"], row["english_name"]
            if not re.fullmatch(r"[A-Z]{2}", alpha2):
                raise ValueError(f"ISO reference line {line}: invalid alpha2 {alpha2!r}")
            if not re.fullmatch(r"[A-Z]{3}", alpha3):
                raise ValueError(f"ISO reference line {line}: invalid alpha3 {alpha3!r}")
            if not name:
                raise ValueError(f"ISO reference line {line}: english_name is empty")
            if alpha2 in seen2 or alpha3 in seen3:
                raise ValueError(f"ISO reference line {line}: duplicate ISO code")
            seen2.add(alpha2)
            seen3.add(alpha3)
            rows.append(row)
    return rows


def propose(registry: dict[str, Any], reference: list[dict[str, str]]) -> dict[str, Any]:
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("registry.records must be an array")

    by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in reference:
        by_name[normalize_name(row["english_name"])].append(row)

    proposals: list[dict[str, str]] = []
    no_match = 0
    ambiguous = 0
    already_verified = 0
    exact_match_count = 0
    explicit_variant_count = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        names = record.get("names") if isinstance(record.get("names"), dict) else {}
        iso = record.get("iso") if isinstance(record.get("iso"), dict) else {}
        name = names.get("en")
        if not isinstance(name, str) or not name.strip():
            proposals.append({
                "game_id": str(record.get("game_id") or f"record-{index}"),
                "english_name": "",
                "candidate_alpha2": "",
                "candidate_alpha3": "",
                "reference_name": "",
                "match_type": "unmatched",
                "decision": "review: missing registry English name",
                "note": "No assignment proposed.",
            })
            no_match += 1
            continue

        normalized_name = normalize_name(name)
        matches = by_name.get(normalized_name, [])
        variant = REVIEWED_NAME_VARIANTS.get(normalized_name)
        variant_note = ""
        if not matches and variant and variant[0]:
            variant_name, variant_note = variant
            matches = by_name.get(normalize_name(variant_name), [])
        if len(matches) == 1:
            candidate = matches[0]
            current_status = iso.get("assignment_status")
            if current_status == "verified":
                decision = "review: already marked verified; compare before changing"
            elif variant_note:
                decision = "candidate: explicit name-variant match; human verification required"
            else:
                decision = "candidate: exact normalized English-name match; human verification required"
            note = (
                f"Explicit variant: {variant_note} "
                "This is review evidence, not approval; confirm entity scope and source provenance."
                if variant_note
                else "Name match is evidence for review, not approval. Confirm entity scope and source provenance."
            )
            match_type = "explicit name variant" if variant_note else "exact normalized name"
            proposals.append({
                "game_id": str(record.get("game_id") or ""),
                "english_name": name,
                "candidate_alpha2": candidate["alpha2"],
                "candidate_alpha3": candidate["alpha3"],
                "reference_name": candidate["english_name"],
                "match_type": match_type,
                "decision": decision,
                "note": note,
            })
            if variant_note:
                explicit_variant_count += 1
            else:
                exact_match_count += 1
            if current_status == "verified":
                already_verified += 1
        elif len(matches) > 1:
            ambiguous += 1
            proposals.append({
                "game_id": str(record.get("game_id") or ""),
                "english_name": name,
                "candidate_alpha2": "",
                "candidate_alpha3": "",
                "reference_name": "; ".join(item["english_name"] for item in matches),
                "match_type": "ambiguous",
                "decision": "review: ambiguous reference names",
                "note": "No code proposed because the reference contains multiple normalized-name matches.",
            })
        else:
            no_match += 1
            variant_message = variant[1] if variant and variant[1] else ""
            proposals.append({
                "game_id": str(record.get("game_id") or ""),
                "english_name": name,
                "candidate_alpha2": "",
                "candidate_alpha3": "",
                "reference_name": "",
                "match_type": "unmatched",
                "decision": "review: no exact normalized English-name match",
                "note": (
                    f"{variant_message} No assignment proposed."
                    if variant_message
                    else "Do not infer codes from source IDs, existing ISO fields, aliases, or approximate names."
                ),
            })

    return {
        "record_count": len(records),
        "reference_count": len(reference),
        "candidate_count": sum(bool(row["candidate_alpha2"]) for row in proposals),
        "exact_match_count": exact_match_count,
        "explicit_variant_count": explicit_variant_count,
        "no_match_count": no_match,
        "ambiguous_count": ambiguous,
        "already_verified_count": already_verified,
        "proposals": proposals,
    }


def render_report(
    result: dict[str, Any],
    reference_source: str,
    source_url: str = "not supplied",
    retrieved_on: str = "not supplied",
) -> str:
    lines = [
        "# ISO 3166-1 assignment proposals",
        "",
        f"- Registry records reviewed: {result['record_count']}",
        f"- Reference rows: {result['reference_count']}",
        f"- Total ISO candidates proposed: {result['candidate_count']}",
        f"- Exact normalized-name matches: {result['exact_match_count']}",
        f"- Explicit reviewed name-variant matches: {result['explicit_variant_count']}",
        f"- No-match or missing-name records: {result['no_match_count']}",
        f"- Ambiguous reference matches: {result['ambiguous_count']}",
        f"- Records already marked verified: {result['already_verified_count']}",
        f"- Reference file: `{reference_source}`",
        f"- Reference source URL: {source_url}",
        f"- Retrieved on: {retrieved_on}",
        "",
        "## Candidate review",
        "",
        "| game_id | Registry English name | Candidate alpha-2 | Candidate alpha-3 | Reference English name | Match type | Decision |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in result["proposals"]:
        values = [
            row["game_id"], row["english_name"], row["candidate_alpha2"],
            row["candidate_alpha3"], row["reference_name"], row.get("match_type", ""), row["decision"],
        ]
        lines.append("| " + " | ".join(_md(value) for value in values) + " |")
    lines.extend([
        "",
        "## Safeguards",
        "",
        "- This report is a proposal only. It does not modify the registry or approve an ISO assignment.",
        "- Matching uses normalized English names only; source IDs and existing ISO fields are never used to infer codes.",
        "- A name match is not sufficient by itself: verify the entity is in ISO 3166-1 scope and confirm the reference source and retrieval date.",
        "- Dependencies may have ISO codes; disputed or other features may not. Do not invent codes for unmatched entities.",
        "- Resolve spelling and naming variants through separately documented, human-reviewed evidence rather than fuzzy matching.",
        "- Record the reference source and retrieval date in the review evidence before changing assignment_status to verified.",
        "",
    ])
    return "\n".join(lines)


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--reference", type=Path, required=True,
                        help="CSV exported from an authoritative ISO 3166-1 reference, with alpha2,alpha3,english_name columns")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-url", required=True,
                        help="URL identifying the authoritative reference source")
    parser.add_argument("--retrieved-on", required=True,
                        help="Date the reference was retrieved, in YYYY-MM-DD format")
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    reference = read_reference(args.reference)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.retrieved_on):
        parser.error("--retrieved-on must use YYYY-MM-DD format")
    result = propose(registry, reference)
    report = render_report(result, str(args.reference), args.source_url, args.retrieved_on)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(
        f"ISO proposal report: {args.output} "
        f"({result['candidate_count']} candidates, {result['no_match_count']} no-match/missing, "
        f"{result['ambiguous_count']} ambiguous)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
