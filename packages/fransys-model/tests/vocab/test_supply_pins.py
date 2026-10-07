"""RATINGS-3 Q3: `supply_pins`, the ports a supply name's source declarations put it on.

Invented plant: a DC supply `a` and an AC supply `b`, each declared with its pins. Only the
pins of a source declaration count; a net, a wire or a port no declaration lists adds nothing.
"""

import pytest
from plant import Plant
from rating_plant import rail, supply

from fransys_model.kernel import FreezeError, make_id
from fransys_model.vocab.core import Port, Unit
from fransys_model.vocab.enums import Current
from fransys_model.vocab.supply_sources import supply_pins
from fransys_model.vocab.supply_system import SupplySystem


def test_each_supply_name_gets_the_pins_its_declarations_list() -> None:
    plant = Plant()
    plus, minus, x = plant.pin("G1", "f", "1"), plant.pin("G1", "f", "2"), plant.pin("G2", "f", "1")
    wired, loose = plant.pin("K1", "f", "1"), plant.pin("K2", "f", "1")
    supply(plant, "a", {"L+": rail("24"), "M": rail("0")}, current=Current.DC, pins=(plus, minus))
    supply(plant, "b", {"X": rail("230", 0)}, pins=(x,))
    plant.net("n-other", (loose,), potential="Q")
    plant.wire(plus, wired, key="w1")

    assert supply_pins(plant.model()) == {"a": frozenset({plus, minus}), "b": frozenset({x})}


def test_a_nested_declaration_adds_no_pins_to_its_container() -> None:
    plant = Plant()
    outer, inner = plant.pin("G1", "f", "1"), plant.pin("G2", "f", "1")
    cabinet = plant.unit("cabinet")
    panel = plant.unit("panel", parent=cabinet)
    supply(plant, "s1", {"X": rail("1", 0)}, name="s", unit=cabinet, pins=(outer,))
    supply(plant, "s2", {"X": rail("1", 0)}, name="s", unit=panel, pins=(inner,))

    assert supply_pins(plant.model()) == {"s": frozenset({outer})}


def test_a_declaration_without_pins_gives_an_empty_set() -> None:
    plant = Plant()
    supply(plant, "bare", {"X": rail("1", 0)})

    assert supply_pins(plant.model()) == {"bare": frozenset()}


@pytest.mark.parametrize("field", ["pins", "unit"])
def test_a_pin_or_unit_the_model_does_not_hold_is_refused_at_freeze(field: str) -> None:
    ghost = make_id(Port, ("nowhere", "f", "1")) if field == "pins" else make_id(Unit, ("nowhere",))
    plant = Plant()
    plant.add(
        SupplySystem(
            id=make_id(SupplySystem, ("s",)),
            key=("s",),
            name="s",
            current=Current.DC,
            rails=frozendict({"X": rail("1")}),
            pins=(ghost,) if field == "pins" else (),  # ty: ignore[invalid-argument-type] -- ghost is a port here
            unit=ghost if field == "unit" else None,  # ty: ignore[invalid-argument-type] -- ghost is a unit here
        )
    )
    with pytest.raises(FreezeError):
        plant.model()
