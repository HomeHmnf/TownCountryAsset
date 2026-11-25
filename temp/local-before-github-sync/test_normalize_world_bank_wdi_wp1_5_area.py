from __future__ import annotations

import pytest

from tools.acquire_world_bank_wdi_wp1_5_area import AreaSnapshotError
from tools.normalize_world_bank_wdi_wp1_5_area import _value_status


@pytest.mark.parametrize("provider_status", [None, ""])
def test_blank_wdi_provider_status_is_unclassified(provider_status):
    assert _value_status(provider_status) == "unclassified"


@pytest.mark.parametrize("provider_status", ["E", "P", "A", "unknown"])
def test_nonblank_wdi_provider_status_requires_explicit_mapping(provider_status):
    with pytest.raises(AreaSnapshotError, match="requires an explicit canonical status mapping"):
        _value_status(provider_status)
