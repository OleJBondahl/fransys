"""`layout.external_outline`: a positive-sized rectangle on a page, one of the derived kinds.

Can-fail: drop the `width` check in `ExternalOutline.__post_init__` (the width test), the height
check (the height test), or the kind from `DERIVED_KINDS` (the derived test).
"""

from typing import Any

import pytest

from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.layout import DERIVED_KINDS, ExternalOutline


def _outline(**changes: Any) -> ExternalOutline:
    key = ("layout", "schematic", "external_outline", "x90")
    fields: dict[str, Any] = {
        "id": make_id(ExternalOutline, key),
        "key": key,
        "item": Id(kind="item", value="x90"),
        "page": Id(kind="page", value="p1"),
        "x": 4,
        "y": 8,
        "width": 12,
        "height": 20,
        "produced_by": "test",
    }
    return ExternalOutline(**{**fields, **changes})


def test_an_external_outline_is_a_derived_layout_kind() -> None:
    assert ExternalOutline in DERIVED_KINDS


def test_an_outline_of_positive_size_is_accepted() -> None:
    assert _outline().width == 12


@pytest.mark.parametrize("field", ["width", "height"])
def test_a_zero_size_is_refused(field: str) -> None:
    with pytest.raises(SchemaError, match="must be positive"):
        _outline(**{field: 0})
