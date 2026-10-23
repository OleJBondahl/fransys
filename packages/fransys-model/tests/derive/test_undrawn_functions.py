"""`undrawn_functions`: the loose, spare and idle-terminal functions the schematic leaves off."""

import pytest
from plant import Plant

from fransys_model.derive import undrawn_functions
from fransys_model.vocab.enums import FunctionKind
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Function


def _plant() -> Plant:
    """K1.coil wired to X1.t1; K2.coil loose; a lone contact, an unused lamp and a lone terminal."""
    plant = Plant()
    plant.wire(plant.pin("K1", "coil", "A1"), plant.pin("X1", "t1", "1"), key="w1")
    plant.pin("K2", "coil", "A1")
    for item, name, kind in (
        ("K3", "aux", FunctionKind.CONTACT_NO),
        ("P9", "lamp", FunctionKind.GENERIC),
        ("X2", "t2", FunctionKind.TERMINAL),
    ):
        function = plant.function(plant.item(item), name, kind=kind)
        plant.port(function, "1")
    return plant


def test_loose_is_every_function_with_nothing_connected() -> None:
    plant = _plant()
    found = undrawn_functions(plant.model(), hide_unused_pins=False, wired=frozenset())
    assert plant.function_id("K2", "coil") in found.loose
    assert plant.function_id("K1", "coil") not in found.loose


def test_an_unused_contact_is_a_spare_and_another_only_when_hidden() -> None:
    plant = _plant()
    model = plant.model()
    off = undrawn_functions(model, hide_unused_pins=False, wired=frozenset())
    on = undrawn_functions(model, hide_unused_pins=True, wired=frozenset())
    contact, lamp = plant.function_id("K3", "aux"), plant.function_id("P9", "lamp")
    assert contact in off.spare
    assert lamp not in off.spare
    assert lamp in on.spare
    assert plant.function_id("K1", "coil") not in on.spare


def test_a_terminal_none_of_whose_ports_is_wired_is_idle() -> None:
    plant = _plant()
    model = plant.model()
    lone = plant.function_id("X2", "t2")
    port = plant.pin("X2", "t2", "1")
    assert lone in undrawn_functions(model, hide_unused_pins=False, wired=frozenset()).idle
    assert (
        lone not in undrawn_functions(model, hide_unused_pins=False, wired=frozenset({port})).idle
    )
    assert (
        plant.function_id("X1", "t1")
        not in undrawn_functions(model, hide_unused_pins=False, wired=frozenset()).spare
    )


def _holder_with_link(*, unused: bool) -> tuple[Plant, Id[Function], Id[Function]]:
    """A tagged holder with a function, and an untagged `parent=` link with one function."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    link = plant.item("link", part=plant.part("F"), parent=holder)
    held = plant.function(holder, "body")
    own = plant.function(link, "body")
    for function in (held, own):
        plant.port(function, "1")
    if unused:
        plant.unused(own)
    return plant, held, own


@pytest.mark.parametrize("hide", [False, True])
def test_every_function_of_an_accessory_is_undrawn_whatever_the_profile(*, hide: bool) -> None:
    plant, held, own = _holder_with_link(unused=True)
    found = undrawn_functions(plant.model(), hide_unused_pins=hide, wired=frozenset())
    assert own in found.accessory
    assert held not in found.accessory


@pytest.mark.parametrize("hide", [False, True])
def test_an_untagged_parent_device_without_unused_is_not_an_accessory(*, hide: bool) -> None:
    plant, _, _ = _holder_with_link(unused=False)
    found = undrawn_functions(plant.model(), hide_unused_pins=hide, wired=frozenset())
    assert found.accessory == ()
