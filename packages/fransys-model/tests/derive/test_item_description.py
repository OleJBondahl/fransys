"""Tests for `item_description` and its neighbouring `lookups` readers.

See SC4, design/derive-queries.md.
"""

import dataclasses

import pytest
from plant import Plant
from query_builders import make_pin, make_terminal

from fransys_model.derive import build_indexes, item_description
from fransys_model.derive.lookups import (
    channel_devices,
    conductors_by_role,
    pin_order,
    position_rank,
)
from fransys_model.kernel import SchemaError, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import PartCategory, PortRole
from fransys_model.vocab.facets.plc import PlcBindingFacet
from fransys_model.vocab.templates import Part

_PART = Part(
    id=make_id(Part, ("relay",)),
    key=("relay",),
    mpn="EXAMPLE-RLY",
    manufacturer="Example Co",
    description="part text",
    category=PartCategory.GENERIC,
    class_code="K",
)


def _plant_with(key: str, *, part: bool, description: str) -> tuple[Plant, Item]:
    """A plant holding `_PART` and one item `key`, with `description` stored on it."""
    plant = Plant()
    plant.add(_PART)
    item = Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=_PART.id if part else None,
        parent=None,
        position=None,
        tag=None,
        description=description,
    )
    plant.add(item)
    return plant, item


def test_an_items_own_text_wins_over_its_parts() -> None:
    """Fails if the reader always returns the part's text."""
    plant, item = _plant_with("k1", part=True, description="own text")
    assert item_description(plant.model(), item.id) == "own text"


def test_an_empty_own_text_falls_to_the_parts() -> None:
    """Fails if the part fallback is dropped."""
    plant, item = _plant_with("k1", part=True, description="")
    assert item_description(plant.model(), item.id) == "part text"


def test_a_part_less_item_with_no_own_text_reads_empty() -> None:
    """Fails if a part-less item raises or reads some other text."""
    plant, item = _plant_with("board", part=False, description="")
    assert item_description(plant.model(), item.id) == ""


def test_a_part_less_item_reads_its_own_text() -> None:
    """Fails if a part-less item's own text is ignored."""
    plant, item = _plant_with("board", part=False, description="own text")
    assert item_description(plant.model(), item.id) == "own text"


def test_an_unknown_item_raises() -> None:
    """A part id is not an item of the model; the raised error names the item and its id."""
    plant, _ = _plant_with("k1", part=True, description="")
    bad_id = make_id(Item, ("nowhere",))
    with pytest.raises(SchemaError) as excinfo:
        item_description(plant.model(), bad_id)
    assert excinfo.value.kind == "item"
    assert excinfo.value.record_id == bad_id


def test_pin_order_sorts_numeric_markings_by_value_before_any_alphabetic_marking() -> None:
    """Fails if a numeric marking is compared as a string, or alphabetic markings sort first."""
    port = make_id(Port, ("p",))
    assert pin_order("10", port) < pin_order("A1", port)
    assert pin_order("2", port) < pin_order("10", port)
    assert pin_order("A1", port) == (1, 0, "A1", port)


def test_position_rank_puts_every_integer_position_before_none() -> None:
    """Fails if an unplaced module does not sort last."""
    _, item = _plant_with("k1", part=False, description="")
    placed = dataclasses.replace(item, position=1)
    unplaced = dataclasses.replace(item, position=None)
    assert position_rank(placed) < position_rank(unplaced)
    assert position_rank(unplaced) == (1, 0)


def test_position_rank_orders_two_integer_positions_by_their_value() -> None:
    """Fails if two integer positions are not ordered by the integer itself."""
    _, item = _plant_with("k1", part=False, description="")
    first = dataclasses.replace(item, position=1)
    second = dataclasses.replace(item, position=2)
    assert position_rank(first) < position_rank(second)


def test_channel_devices_picks_the_smallest_subject_when_two_bindings_share_a_channel() -> None:
    """Two `plc_binding` facets naming one channel from different subjects: the smaller wins."""
    plant = Plant()
    channel = plant.function(plant.item("mod"), "ch1")
    first = plant.function(plant.item("dev-a"), "signal")
    second = plant.function(plant.item("dev-b"), "signal")
    plant.add(
        PlcBindingFacet(
            id=make_id(PlcBindingFacet, ("dev-a", "binding")),
            key=("dev-a", "binding"),
            subject=first,
            channel=channel,
        ),
        PlcBindingFacet(
            id=make_id(PlcBindingFacet, ("dev-b", "binding")),
            key=("dev-b", "binding"),
            subject=second,
            channel=channel,
        ),
    )
    model = plant.model()
    assert channel_devices(model) == {channel: min(first, second)}


def test_conductors_by_role_keeps_a_terminals_internal_and_external_conductors_apart() -> None:
    """Fails if the two roles are merged into one set under either key."""
    plant = Plant()
    plant.item("x1")
    terminal = make_terminal(plant, "x1", "t1", group="L", index=1)
    inside = plant.wire(make_pin(plant, "in", "K1"), terminal.internal, key="in-wire")
    outside = plant.wire(make_pin(plant, "out", "B1"), terminal.external, key="out-wire")
    model = plant.model()
    by_role = conductors_by_role(model, build_indexes(model), terminal.item)
    assert by_role == {PortRole.INTERNAL: {inside}, PortRole.EXTERNAL: {outside}}
