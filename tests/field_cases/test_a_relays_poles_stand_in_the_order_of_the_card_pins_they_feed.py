"""Field case: a relay's poles feed a card's pins, and the poles stand in the order of the pins they feed (R11).
The bug: the card printed its pins in marking order, but the poles kept the relay's own order, so the three wires crossed.
Fixed by layout-0264, every column wired to a box's pins takes the order of the pins it lands on (a device's poles may reverse)."""

from functools import cache
from typing import TYPE_CHECKING, Any

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from _field_designs import wire_crossings
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Model

WIRE = (BU, 0.5)
PINS = ("13", "23", "43")
FEEDS = {1: "43", 2: "23", 3: "13"}  # pole -> the card pin its make throw feeds


@cache
def _built() -> Model:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("A", "Outputs"):
        card = d.device("DO1", None, pins=PINS, external=True)
    with d.function("S", "Supply"):
        source = d.device("A1", "DEMO-CTRL-8")
    with d.function("R", "Relay"):
        relay = d.device("K1", "DEMO-RLY-4CO-24")
    for pole, pin in FEEDS.items():
        contact = getattr(relay, f"co_{pole}")
        d.series(source.X1[str(pole)], contact[f"{pole}1"], wire=WIRE)
        d.series(contact[f"{pole}4"], card[pin], wire=WIRE)
    return fr.build(d, unit_document(cab)).model


def _x_of_poles_and_pins() -> tuple[dict[Any, Any], dict[Any, Any], dict[Any, Any]]:
    """The x of each K1 pole's symbol, of each DO1 pin (box origin plus offset) and its side."""
    model = _built()
    name_of = {f.id.value: f.name for f in functions(model).values()}
    poles, pins, sides = {}, {}, {}
    for drawn in symbol_subjects(model):
        if drawn.tag == "K1":
            poles[int(name_of[drawn.owner][-1])] = drawn.x
        elif drawn.tag == "DO1":
            pins = {pin: drawn.x + offset for pin, offset in dict(drawn.offsets).items()}
            sides = dict(drawn.sides)
    return poles, pins, sides


def test_the_card_prints_its_pins_in_marking_order() -> None:
    """The box is two-sided (BOX-SIDES): the first pins stand on the north side, then the rest."""
    _, pins, sides = _x_of_poles_and_pins()
    north = sorted((p for p in PINS if sides[p] == "n"), key=pins.__getitem__)
    south = sorted((p for p in PINS if sides[p] == "s"), key=pins.__getitem__)
    assert north + south == list(PINS)


def test_the_poles_stand_in_the_order_of_the_pins_they_feed_and_no_wire_crosses() -> None:
    poles, pins, _ = _x_of_poles_and_pins()
    assert sorted(poles, key=lambda pole: pins[FEEDS[pole]]) == sorted(poles, key=poles.__getitem__)
    drawings = drawn_pages(_built()).values()
    assert sum(len(d.wires) for d in drawings) == 6, "every wire is drawn"
    assert sum(wire_crossings(d.wires) for d in drawings) == 0
