"""Provider-neutral, read-only identity reconciliation across a registry and reference dataset."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any, Mapping, Sequence


def normalize_identity_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def _value(obj: Mapping[str, Any], path: str) -> str:
    current: Any = obj
    for part in path.split("."):
        current = current.get(part) if isinstance(current, Mapping) else None
    return str(current).strip() if current is not None else ""


def _code_status(existing: str, candidate: str) -> str:
    if not existing:
        return "missing_existing"
    if not candidate:
        return "missing_reference"
    return "match" if existing.casefold() == candidate.casefold() else "mismatch"


def reconcile_identities(
    registry: Mapping[str, Any],
    reference_rows: Sequence[Mapping[str, Any]],
    *,
    fields: Mapping[str, str],
    name_variants: Mapping[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Compare all registry records to reference rows using names only.

    `fields` maps game_id, registry_name, source_id, existing_alpha2,
    existing_alpha3, reference_name, reference_id, reference_alpha2 and
    reference_alpha3 to dotted paths. Explicit variants map normalized registry
    names to (exact reference name, rationale). Codes and source IDs are never
    used to establish identity.
    """
    required = {
        "game_id", "registry_name", "source_id", "existing_alpha2",
        "existing_alpha3", "reference_name", "reference_id",
        "reference_alpha2", "reference_alpha3",
    }
    if set(fields) != required:
        raise ValueError(f"fields must define exactly: {', '.join(sorted(required))}")
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("registry.records must be an array")
    variants = name_variants or {}
    ref_index: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(reference_rows):
        name = _value(row, fields["reference_name"])
        if name:
            ref_index[normalize_identity_name(name)].append(i)

    # Precompute name-only candidates and detect multiple registry records
    # claiming the same single reference row. Such matches remain ambiguous.
    candidate_map: dict[int, tuple[list[int], str]] = {}
    reference_claims: dict[int, int] = defaultdict(int)
    for position, record in enumerate(records):
        name = _value(record, fields["registry_name"])
        normalized = normalize_identity_name(name)
        candidates = list(ref_index.get(normalized, [])) if normalized else []
        variant_note = ""
        if not candidates and normalized in variants:
            target_name, variant_note = variants[normalized]
            candidates = list(ref_index.get(normalize_identity_name(target_name), []))
        candidate_map[position] = (candidates, variant_note)
        if len(candidates) == 1:
            reference_claims[candidates[0]] += 1

    registry_ids: set[str] = set()
    output: list[dict[str, str]] = []
    used_reference_indices: set[int] = set()
    unmatched_registry: list[dict[str, str]] = []
    ambiguous_registry: list[dict[str, str]] = []
    match_counts: dict[str, int] = defaultdict(int)

    for position, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"registry record {position} must be an object")
        game_id = _value(record, fields["game_id"])
        if not game_id or game_id in registry_ids:
            raise ValueError(f"registry record {position} has missing or duplicate game_id {game_id!r}")
        registry_ids.add(game_id)
        name = _value(record, fields["registry_name"])
        candidates, variant_note = candidate_map[position]
        is_variant = bool(variant_note)
        match_type = "explicit_variant" if is_variant else "exact_name"
        if len(candidates) == 1 and reference_claims[candidates[0]] > 1:
            match_type = "ambiguous"
            candidates = [candidates[0], candidates[0]]
        matched_index = candidates[0] if len(candidates) == 1 else None
        if len(candidates) > 1:
            match_type = "ambiguous"
        elif matched_index is None:
            match_type = "unmatched"

        ref = reference_rows[matched_index] if matched_index is not None else {}
        if matched_index is not None:
            used_reference_indices.add(matched_index)
        old2 = _value(record, fields["existing_alpha2"]).upper()
        old3 = _value(record, fields["existing_alpha3"]).upper()
        new2 = _value(ref, fields["reference_alpha2"]).upper()
        new3 = _value(ref, fields["reference_alpha3"]).upper()
        a2 = _code_status(old2, new2) if matched_index is not None else "not_compared"
        a3 = _code_status(old3, new3) if matched_index is not None else "not_compared"
        if matched_index is None:
            pair = "ambiguous_match" if candidates else "unmatched_registry"
        elif a2 == "match" and a3 == "match":
            pair = "complete_pair_agreement"
        elif a2 == "match":
            pair = "alpha2_only_agreement"
        elif a3 == "match":
            pair = "alpha3_only_agreement"
        elif a2 == "mismatch" or a3 == "mismatch":
            pair = "genuine_code_mismatch"
        elif a2 == "missing_existing" and a3 == "missing_existing":
            pair = "both_existing_codes_missing"
        elif a2 == "missing_reference" or a3 == "missing_reference":
            pair = "reference_code_missing"
        else:
            pair = "partial_or_missing_codes"

        source_id = _value(record, fields["source_id"])
        source_vs_alpha3 = (
            "same" if source_id and new3 and source_id.casefold() == new3.casefold()
            else "different" if source_id and new3 else "not_comparable"
        )
        row = {
            "game_id": game_id, "registry_name": name, "source_id": source_id,
            "existing_alpha2": old2, "existing_alpha3": old3,
            "match_type": match_type, "variant_note": variant_note,
            "reference_name": _value(ref, fields["reference_name"]),
            "reference_id": _value(ref, fields["reference_id"]),
            "reference_alpha2": new2, "reference_alpha3": new3,
            "alpha2_comparison": a2, "alpha3_comparison": a3,
            "code_pair_classification": pair,
            "source_id_vs_reference_alpha3": source_vs_alpha3,
        }
        output.append(row)
        match_counts[match_type] += 1
        if matched_index is None:
            (ambiguous_registry if candidates else unmatched_registry).append(row)

    unmatched_reference = []
    for i, ref in enumerate(reference_rows):
        if i not in used_reference_indices:
            unmatched_reference.append({
                "reference_name": _value(ref, fields["reference_name"]),
                "reference_id": _value(ref, fields["reference_id"]),
                "reference_alpha2": _value(ref, fields["reference_alpha2"]).upper(),
                "reference_alpha3": _value(ref, fields["reference_alpha3"]).upper(),
                "reason": "not uniquely matched to a registry record",
            })

    classifications: dict[str, int] = defaultdict(int)
    for row in output:
        classifications[row["code_pair_classification"]] += 1
    return {
        "records": output,
        "unmatched_registry": unmatched_registry,
        "ambiguous_registry": ambiguous_registry,
        "unmatched_reference": unmatched_reference,
        "summary": {
            "registry_count": len(records),
            "reference_count": len(reference_rows),
            "matched_count": sum(1 for row in output if row["match_type"] in {"exact_name", "explicit_variant"}),
            "unmatched_registry_count": len(unmatched_registry),
            "ambiguous_registry_count": len(ambiguous_registry),
            "unmatched_reference_count": len(unmatched_reference),
            "match_types": dict(sorted(match_counts.items())),
            "code_pair_classifications": dict(sorted(classifications.items())),
            "alpha2_matches": sum(row["alpha2_comparison"] == "match" for row in output),
            "alpha3_matches": sum(row["alpha3_comparison"] == "match" for row in output),
            "alpha2_mismatches": sum(row["alpha2_comparison"] == "mismatch" for row in output),
            "alpha3_mismatches": sum(row["alpha3_comparison"] == "mismatch" for row in output),
            "source_id_alpha3_same": sum(row["source_id_vs_reference_alpha3"] == "same" for row in output),
            "source_id_alpha3_different": sum(row["source_id_vs_reference_alpha3"] == "different" for row in output),
        },
    }
