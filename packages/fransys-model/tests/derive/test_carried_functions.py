"""`carried_functions`, `accessory_functions`: the functions the schematic leaves off, by reason."""

import pytest
from plant import Plant

from fransys_model.derive import (
    Carried,
    CarriedReason,
    ConductorEnd,
    FunctionSymbol,
    accessory_functions,
    carried_functions,
)
from fransys_model.kernel import SchemaError
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import conductors


def _plant() -> Plant:
    """K1.coil wired to X1.t1; K2.coil loose; a lone contact, an unused lamp and a lone terminal."""
    plant = Plant()
    plant.item("K1", designation="K1")
    plant.item("X1", designation="X1")
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


def _held(model, reason, *, hide=False, wired=frozenset()):
    """The functions carried for `reason`."""
    rows = carried_functions(model, hide_unused_pins=hide, wired=wired)
    return {r.symbol.function for r in rows if r.reason is reason and r.symbol is not None}


def test_loose_is_every_function_with_nothing_connected() -> None:
    plant = _plant()
    unwired = _held(plant.model(), CarriedReason.UNWIRED)
    assert plant.function_id("K2", "coil") in unwired
    assert plant.function_id("K1", "coil") not in unwired


def test_an_unused_contact_is_a_spare_and_another_only_when_hidden() -> None:
    plant = _plant()
    model = plant.model()
    off = _held(model, CarriedReason.SPARE)
    on = _held(model, CarriedReason.SPARE, hide=True)
    contact, lamp = plant.function_id("K3", "aux"), plant.function_id("P9", "lamp")
    assert contact in off
    assert lamp not in off
    assert lamp in on
    assert plant.function_id("K1", "coil") not in on


def test_a_terminal_none_of_whose_ports_is_wired_is_idle() -> None:
    plant = _plant()
    port = plant.pin("X2", "t2", "1")
    plant.wire(port, plant.pin("K2", "coil", "A1"), key="w2")
    model = plant.model()
    lone = plant.function_id("X2", "t2")
    assert lone in _held(model, CarriedReason.UNWIRED)
    assert lone not in _held(model, CarriedReason.UNWIRED, wired=frozenset({port}))


def _holder_with_link(*, unused: bool) -> tuple[Plant, object, object]:
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


def test_every_function_of_an_accessory_is_undrawn_whatever_the_profile() -> None:
    plant, held, own = _holder_with_link(unused=True)
    found = set(accessory_functions(plant.model()))
    assert own in found
    assert held not in found


def test_an_untagged_parent_device_without_unused_is_not_an_accessory() -> None:
    plant, _, _ = _holder_with_link(unused=False)
    found = set(accessory_functions(plant.model()))
    assert not found


def test_a_carried_names_exactly_one_row() -> None:
    plant = _plant()
    function = FunctionSymbol(function=plant.function_id("K2", "coil"))
    assert Carried(reason=CarriedReason.SPARE, symbol=function).symbol == function
    with pytest.raises(SchemaError, match="one conductor end or one function symbol"):
        Carried(reason=CarriedReason.SPARE)
    pin = plant.pin("K1", "coil", "A1")
    (conductor,) = conductors(plant.model())
    end = ConductorEnd(conductor=conductor, port=pin, far=plant.pin("X1", "t1", "1"))
    with pytest.raises(SchemaError, match="one conductor end or one function symbol"):
        Carried(reason=CarriedReason.SPARE, symbol=function, end=end)
