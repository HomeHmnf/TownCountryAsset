from __future__ import annotations

import math

import pytest

from tools.database.observation_contract import validate_observation_value


@pytest.mark.parametrize("status", ["observed", "estimated", "projected", "unclassified"])
def test_finite_scalar_accepts_all_populated_scalar_statuses(status):
    assert validate_observation_value(12.5, status, "scalar")


@pytest.mark.parametrize("status", ["unavailable", "not_applicable"])
def test_null_requires_explicit_missing_value_status(status):
    assert validate_observation_value(None, status, "scalar")
    assert validate_observation_value(None, status, "structured")


@pytest.mark.parametrize("status", ["observed", "estimated", "projected"])
def test_structured_payload_requires_classified_status(status):
    assert validate_observation_value({"key": 1}, status, "structured")


def test_unclassified_is_rejected_for_structured_payloads():
    assert not validate_observation_value({"key": 1}, "unclassified", "structured")


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "12", {"x": 1}])
def test_scalar_rejects_non_finite_or_non_numeric_values(value):
    assert not validate_observation_value(value, "unclassified", "scalar")


def test_populated_value_cannot_be_unavailable_and_null_cannot_be_unclassified():
    assert not validate_observation_value(1, "unavailable", "scalar")
    assert not validate_observation_value(None, "unclassified", "scalar")


def test_structured_payload_rejects_non_json_values():
    assert not validate_observation_value({"bad": math.inf}, "observed", "structured")
