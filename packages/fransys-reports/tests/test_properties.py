"""Hypothesis property test for output purity (decision 0020, WORK-ORDER-PROPS.md, property 4).

An output that needs no layout is a pure function of the model: equal digests give byte-equal
output, and the output is the same when the draft's records were added in a different order.
`bom_csv` is that output here. The strategy is the model-package one, narrowed to what a BOM
line needs (an installed, designated `Item` with a shared `Part`, each with a `Function` and a
`Port`): a few items sharing one part, so every permutation gives a non-trivial, non-empty BOM.
"""

import string
from typing import Any

from fransys_reports import bom_csv
from hypothesis import given
from hypothesis import strategies as st

from fransys_model.kernel import Draft, Model, Origin, freeze, make_id
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PartCategory, PortRole
from fransys_model.vocab.templates import Part

_ORIGIN = Origin(file="test_properties.py", line=1, note="hypothesis")
_DESIGNATION = st.text(alphabet=string.ascii_uppercase, min_size=1, max_size=3)


def _freeze(records: tuple[Any, ...]) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


@st.composite
def _bom_records(draw: st.DrawFn) -> tuple[Any, ...]:
    """A few installed, designated items sharing one part, each with a function and a port."""
    n_items = draw(st.integers(min_value=1, max_value=4))
    designations = draw(st.lists(_DESIGNATION, min_size=n_items, max_size=n_items, unique=True))
    part = Part(
        id=make_id(Part, ("part",)),
        key=("part",),
        mpn="MPN-1",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.GENERIC,
        class_code="K",
    )
    records: list[Any] = [part]
    for index in range(n_items):
        item_key = (f"item{index}",)
        item_id = make_id(Item, item_key)
        records.append(
            Item(
                id=item_id,
                key=item_key,
                part=part.id,
                parent=None,
                position=None,
                tag=designations[index],
                description="Invented",
                installed=True,
            )
        )
        function_key = (*item_key, "f")
        function_id = make_id(Function, function_key)
        records.append(
            Function(
                id=function_id,
                key=function_key,
                item=item_id,
                template=None,
                name="f",
                kind=FunctionKind.GENERIC,
            )
        )
        port_key = (*function_key, "1")
        records.append(
            Port(
                id=make_id(Port, port_key),
                key=port_key,
                function=function_id,
                template=None,
                name="1",
                role=PortRole.GENERIC,
            )
        )
    return tuple(records)


@given(records=_bom_records(), data=st.data())
def test_bom_csv_is_pure_and_order_independent(
    records: tuple[Any, ...], data: st.DataObject
) -> None:
    """Same digest gives byte-equal BOM text, whatever order the draft's records were added in."""
    permuted = data.draw(st.permutations(list(records)))
    baseline = _freeze(records)
    shuffled = _freeze(tuple(permuted))
    assert baseline.digest == shuffled.digest
    assert bom_csv(baseline) == bom_csv(shuffled)
