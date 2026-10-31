"""Validate explicit provider-to-game identity crosswalks for WP1.5 imports.

Crosswalks are curated inputs. This module deliberately performs no fuzzy,
name-based, ISO-inferred, or coordinate-based identity matching.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

GAME_ID = re.compile(r"^tc_[0-9a-f]{32}$")
ALLOWED_MATCH_METHODS = {"authoritative_identifier", "reviewed_manual"}


class CrosswalkError(ValueError):
    """Raised when a source identity crosswalk is unsafe or inconsistent."""


@dataclass(frozen=True)
class CrosswalkMapping:
    game_id: str
    source_id: str
    match_method: str
    evidence_url: str | None = None
    source_name: str | None = None


@dataclass(frozen=True)
class Crosswalk:
    dataset: str
    source_key: str
    mappings: tuple[CrosswalkMapping, ...]

    def coverage(self, expected_game_ids: Iterable[str]) -> dict[str, list[str] | int]:
        expected = set(expected_game_ids)
        mapped = {item.game_id for item in self.mappings}
        return {
            "expected_count": len(expected),
            "mapped_count": len(expected & mapped),
            "missing_game_ids": sorted(expected - mapped),
            "unexpected_game_ids": sorted(mapped - expected),
        }


def load_crosswalk(
    path: str | Path,
    *,
    expected_dataset: str,
    known_game_ids: Iterable[str] | None = None,
) -> Crosswalk:
    """Load and validate a JSON crosswalk; partial source coverage is permitted."""
    try:
        payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CrosswalkError(f"Cannot read crosswalk {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise CrosswalkError("Unsupported crosswalk schema version")
    dataset = payload.get("dataset")
    source_key = payload.get("source_key")
    if dataset != expected_dataset:
        raise CrosswalkError(
            f"Crosswalk dataset mismatch: expected {expected_dataset!r}, received {dataset!r}"
        )
    if not isinstance(source_key, str) or not source_key.strip():
        raise CrosswalkError("Crosswalk source_key must be a non-empty string")
    rows = payload.get("mappings")
    if not isinstance(rows, list) or not rows:
        raise CrosswalkError("Crosswalk mappings must be a non-empty array")

    known = set(known_game_ids) if known_game_ids is not None else None
    game_ids: set[str] = set()
    source_ids: set[str] = set()
    mappings: list[CrosswalkMapping] = []
    for index, row in enumerate(rows):
        label = f"mappings[{index}]"
        if not isinstance(row, dict):
            raise CrosswalkError(f"{label} must be an object")
        game_id, source_id = row.get("game_id"), row.get("source_id")
        method = row.get("match_method")
        if not isinstance(game_id, str) or not GAME_ID.fullmatch(game_id):
            raise CrosswalkError(f"{label}.game_id is not a valid persistent game_id")
        if known is not None and game_id not in known:
            raise CrosswalkError(f"{label}.game_id is absent from the canonical identity registry")
        if not isinstance(source_id, str) or not source_id.strip():
            raise CrosswalkError(f"{label}.source_id must be explicit and non-empty")
        if not isinstance(method, str) or method not in ALLOWED_MATCH_METHODS:
            raise CrosswalkError(
                f"{label}.match_method must be one of {sorted(ALLOWED_MATCH_METHODS)}"
            )
        if game_id in game_ids:
            raise CrosswalkError(f"Duplicate game_id in crosswalk: {game_id}")
        if source_id in source_ids:
            raise CrosswalkError(f"Duplicate source_id in crosswalk: {source_id}")
        evidence = row.get("evidence_url")
        source_name = row.get("source_name")
        if evidence is not None and (
            not isinstance(evidence, str) or not evidence.startswith("https://")
        ):
            raise CrosswalkError(f"{label}.evidence_url must be an HTTPS URL")
        if source_name is not None and (
            not isinstance(source_name, str) or not source_name.strip()
        ):
            raise CrosswalkError(f"{label}.source_name must be a non-empty string when supplied")
        game_ids.add(game_id)
        source_ids.add(source_id)
        mappings.append(CrosswalkMapping(game_id, source_id, method, evidence, source_name))

    return Crosswalk(dataset, source_key, tuple(mappings))
