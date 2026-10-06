"""Hypothesis property tests for the determinism rules (decision 0020, WORK-ORDER-PROPS.md).

Properties, numbered as in the work order:

1. Freeze is order-independent: the same records, added in any permutation, freeze to one
   `Model.digest`.
2. Canonical round trip: `loads(dumps(model))` gives back a model with the same digest.
3. Digest sensitivity: changing one field of one record changes `Model.digest`.

The strategy builds a small valid draft through the public model API only: a handful of
`Item`/`Function`/`Port` records sharing one in-test `Part`, plus a few `Conductor`s and an
optional `Net`. Every item is installed, parted and designated (property 4, in
fransys-reports, reuses installed+designated items for a BOM).
"""

import dataclasses
import string
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from fransys_model.kernel import Draft, Id, Model, Origin, dumps, freeze, loads, make_id
from fransys_model.vocab.connectivity import Conductor, Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    NetClass,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.templates import Part

_ORIGIN = Origin(file="test_properties.py", line=1, note="hypothesis")
_DESIGNATION = st.text(alphabet=string.ascii_uppercase, min_size=1, max_size=3)


def _freeze(records: tuple[Any, ...]) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


@st.composite
def _plant_records(draw: st.DrawFn) -> tuple[Any, ...]:
    """A tiny valid draft: one part, a few items each with a function and a port, some wires."""
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
    ports: list[Id[Port]] = []
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
        port_id = make_id(Port, port_key)
        records.append(
            Port(
                id=port_id,
                key=port_key,
                function=function_id,
                template=None,
                name="1",
                role=PortRole.GENERIC,
            )
        )
        ports.append(port_id)

    if n_items >= 2:
        pair_strategy = st.tuples(
            st.integers(min_value=0, max_value=n_items - 1),
            st.integers(min_value=0, max_value=n_items - 1),
        ).filter(lambda pair: pair[0] != pair[1])
        wire_pairs = draw(st.lists(pair_strategy, max_size=2))
        for wire_index, (a_index, b_index) in enumerate(wire_pairs):
            key = (f"wire{wire_index}",)
            records.append(
                Conductor(
                    id=make_id(Conductor, key),
                    key=key,
                    a=ports[a_index],
                    b=ports[b_index],
                    kind=ConductorKind.WIRE,
                    carrier=None,
                )
            )
        if draw(st.booleans()):
            net_key = ("net",)
            records.append(
                Net(
                    id=make_id(Net, net_key),
                    key=net_key,
                    name=None,
                    net_class=NetClass.GENERIC,
                    ports=tuple(sorted(ports[:2])),
                )
            )

    return tuple(records)


@given(records=_plant_records(), data=st.data())
def test_freeze_is_order_independent(records: tuple[Any, ...], data: st.DataObject) -> None:
    """The same records, added in any permutation, freeze to one `Model.digest`."""
    permuted = data.draw(st.permutations(list(records)))
    assert _freeze(records).digest == _freeze(tuple(permuted)).digest


@given(records=_plant_records())
def test_canonical_round_trip_preserves_digest(records: tuple[Any, ...]) -> None:
    """`loads(dumps(model))` gives back a model with the same digest."""
    model = _freeze(records)
    reloaded = loads(dumps(model))
    assert reloaded.digest == model.digest


@given(records=_plant_records(), data=st.data())
def test_digest_is_sensitive_to_a_field_change(
    records: tuple[Any, ...], data: st.DataObject
) -> None:
    """Changing one field of one `Item` record changes `Model.digest`."""
    item_indices = [index for index, record in enumerate(records) if isinstance(record, Item)]
    index = data.draw(st.sampled_from(item_indices))
    original = records[index]
    new_description = data.draw(
        st.text(min_size=1, max_size=6).filter(lambda text: text != original.description)
    )
    mutated = list(records)
    mutated[index] = dataclasses.replace(original, description=new_description)

    original_model = _freeze(records)
    mutated_model = _freeze(tuple(mutated))
    assert original_model.digest != mutated_model.digest
