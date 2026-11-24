"""Canonical value/status rules shared by acquisition and selection pipelines.

Missing observations are represented by absent rows. Explicit null values are
reserved for unavailable or not-applicable observations.
"""
from __future__ import annotations

import json
import math
from typing import Any

UNCLASSIFIED = "unclassified"
NULL_VALUE_STATUSES = frozenset({"unavailable", "not_applicable"})
CLASSIFIED_POPULATED_STATUSES = frozenset({"observed", "estimated", "projected"})
POPULATED_SCALAR_STATUSES = CLASSIFIED_POPULATED_STATUSES | {UNCLASSIFIED}
ALLOWED_VALUE_STATUSES = POPULATED_SCALAR_STATUSES | NULL_VALUE_STATUSES
POPULATED_STRUCTURED_STATUSES = CLASSIFIED_POPULATED_STATUSES


def validate_observation_value(value: Any, status: Any, storage: Any) -> bool:
    """Validate a scalar or structured value/status pair without inference.

    ``unclassified`` is valid only for finite populated scalar values. Structured
    payloads require a classified status. Explicit nulls require unavailable or
    not_applicable; missing observations are represented by absent rows.
    """
    if storage not in {"scalar", "structured"} or status not in ALLOWED_VALUE_STATUSES:
        return False
    if value is None:
        return status in NULL_VALUE_STATUSES
    if storage == "scalar":
        if status not in POPULATED_SCALAR_STATUSES:
            return False
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(float(value))
        except (OverflowError, TypeError, ValueError):
            return False
    if status not in POPULATED_STRUCTURED_STATUSES or not isinstance(value, (dict, list)):
        return False
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True
