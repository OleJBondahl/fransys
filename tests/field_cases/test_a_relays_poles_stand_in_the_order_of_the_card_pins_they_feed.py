"""Field case: a relay's poles feed a card's pins, and the poles stand in the pins' order (R11).

The engineering shape: a relay with three independent changeover contacts, each common fed from
its own pin of a controller. Each make throw runs to a pin of an output card whose pins are marked
13, 23 and 43. Pole 1 feeds pin 43, pole 2 pin 23, pole 3 pin 13.

The bug: the card printed 13 23 43 in marking order, but the poles kept the relay's own order
(1, 2, 3), so the three wires from the poles to the pins crossed.

The rule (layout-0264): every column wired to a box's pins, above or below, takes the order of
the pins it lands on; a device's poles may reverse their column order to match.
"""

import itertools
import tempfile
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Model

WIRE = (BU, 0.5)
PINS = ("13", "23", "43")
FEEDS = {1: "43", 2: "23", 3: "13"}  # pole -> the card pin its make throw feeds


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


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
        d.detail.wire(source.X1[str(pole)], contact[f"{pole}1"], wire=WIRE)
        d.detail.wire(contact[f"{pole}4"], card[pin], wire=WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model


def _crossings(wires: tuple) -> int:
    """Horizontal-over-vertical crossings, strictly inside both segments, between drawn wires."""
    found = 0
    for one, two in itertools.combinations(wires, 2):
        for (a0, a1), (b0, b1) in itertools.product(
            itertools.pairwise(one.points), itertools.pairwise(two.points)
        ):
            if (a0[1] == a1[1]) == (b0[1] == b1[1]):
                continue
            (h0, h1), (v0, v1) = ((a0, a1), (b0, b1)) if a0[1] == a1[1] else ((b0, b1), (a0, a1))
            found += min(h0[0], h1[0]) < v0[0] < max(h0[0], h1[0]) and min(v0[1], v1[1]) < h0[
                1
            ] < max(v0[1], v1[1])
    return found


def _x_of_poles_and_pins() -> tuple[dict[int, int], dict[str, int], dict[str, str]]:
    """The x of each K1 pole's symbol, of each DO1 pin (box origin plus offset) and its side."""
    model = _built()
    name_of = {f"function:{f.id.value}": f.name for f in functions(model).values()}
    poles, pins, sides = {}, {}, {}
    for drawn in _gap(model, "symbol subject").values():
        tag, _, ref = (drawn.owner or "").partition(" ")  # the owner text: "<tag> <handle>"
        if tag == "K1":
            poles[int(name_of[ref][-1])] = drawn.x
        elif tag == "DO1":
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
    assert sum(_crossings(d.wires) for d in drawings) == 0
