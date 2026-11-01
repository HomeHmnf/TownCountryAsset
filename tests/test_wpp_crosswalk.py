from __future__ import annotations

import pytest

from tools.build_un_wpp_crosswalk import WPPSourceCrosswalkError, normalize_m49


def test_m49_reference_id_is_normalized_without_leading_zeroes():
    assert normalize_m49("004") == "4"
    assert normalize_m49(" 158 ") == "158"


@pytest.mark.parametrize("value", ["", "TGO", "15A", "-4", "  "])
def test_m49_reference_id_must_be_numeric(value: str):
    with pytest.raises(WPPSourceCrosswalkError, match="must be numeric"):
        normalize_m49(value)
