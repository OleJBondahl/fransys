"""Each derive id alias names the Id of its record class (model-0305)."""

from typing import get_args, get_origin

import pytest

from fransys_model import derive
from fransys_model.kernel import Id
from fransys_model.vocab import (
    AspectNode,
    Conductor,
    Document,
    Function,
    Item,
    Net,
    Port,
    Unit,
    UnitRelease,
)

CASES = [
    ("UnitId", Unit),
    ("ItemId", Item),
    ("FunctionId", Function),
    ("PortId", Port),
    ("DocumentId", Document),
    ("NetId", Net),
    ("ConductorId", Conductor),
    ("AspectNodeId", AspectNode),
    ("UnitReleaseId", UnitRelease),
]


@pytest.mark.parametrize(("name", "record"), CASES)
def test_alias_is_id_of_its_record(name: str, record: type) -> None:
    alias = getattr(derive, name)
    assert get_origin(alias.__value__) is Id
    assert get_args(alias.__value__) == (record,)
    assert name in derive.__all__
