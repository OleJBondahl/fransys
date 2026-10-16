"""The `supply_system` core kind: `SupplySystem`, `Rail`, `Current`, `Earthing`.

Decision model-0075; `docs/archive/specs/2026-09-25-model-review.md` Q2, Storage.
Invented data only.
"""

from decimal import Decimal
from typing import Any

import pytest

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Origin,
    SchemaError,
    freeze,
    make_id,
)
from fransys_model.vocab import Current, Earthing, Rail, SupplySystem

_ORIGIN = Origin(file="test_supply_system.py", line=1, note="fixture")


def _system(key: str, rails: Any, **fields: Any) -> SupplySystem:
    return SupplySystem(
        id=make_id(SupplySystem, (key,)), key=(key,), name=key, rails=rails, **fields
    )


def _link() -> SupplySystem:
    return _system(
        "DC link",
        frozendict(
            {
                "DC+": Rail(max_v=Decimal("985.5"), phase=None),
                "DC-": Rail(max_v=Decimal(0), phase=None),
            }
        ),
        current=Current.DC,
        earthing=Earthing.IT,
    )


def _freeze(*records: Any) -> Any:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_a_dict_of_rails_is_refused_at_freeze() -> None:
    """A `dict` for `rails` is one `SchemaError` in a `FreezeError`."""
    with pytest.raises(FreezeError) as excinfo:
        _freeze(_system("400V", {"L1": Rail(max_v=Decimal(230), phase=0)}, current=Current.AC))
    (error,) = excinfo.value.errors
    assert type(error) is SchemaError
    assert str(error) == "SupplySystem.rails: expected frozendict, got dict"
