"""Field case: a relay's poles feed a card's pins, and the poles stand in the pins' order (R11).

The engineering shape: a relay with three independent changeover contacts, each common fed from
its own pin of a controller. Each make throw runs to a pin of an output card whose pins are marked
13, 23 and 43. Pole 1 feeds pin 43, pole 2 pin 23, pole 3 pin 13.

The bug: the card printed 13 23 43 in marking order, but the poles kept the relay's own order
(1, 2, 3), so the three wires from the poles to the pins crossed.

The rule (layout-0264): every column wired to a box's pins, above or below, takes the order of
the pins it lands on; a device's poles may reverse their column order to match.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from fransys.colours import BU
from fransys_el import OPTIONS
from route_meter import page_crossings

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items

WIRE = (BU, 0.5)
PINS = ("13", "23", "43")
FEEDS = {1: "43", 2: "23", 3: "13"}  # pole -> the card pin its make throw feeds


@cache
def _built() -> tuple:
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
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model
    results, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    return model, results.layout


def _x_of_poles_and_pins() -> tuple[dict[int, float], dict[str, float]]:
    model, layout = _built()
    tag_of = {i.id: i.tag for i in items(model).values()}
    named = {f.id: (tag_of[f.item], f.name) for f in functions(model).values()}
    poles, pins = {}, {}
    for placed in layout.placed:
        tag, name = named.get(placed.function, ("", ""))
        if tag == "K1":
            (com,) = (g for g in placed.geometry.ports if g.name == "com")
            poles[int(name[-1])] = placed.at.x + com.at.x
        elif tag == "DO1":
            pins = {g.name: placed.at.x + g.at.x for g in placed.geometry.ports}
    return poles, pins


def test_the_card_prints_its_pins_in_marking_order() -> None:
    _, pins = _x_of_poles_and_pins()
    assert sorted(PINS, key=pins.__getitem__) == list(PINS)


def test_the_poles_stand_in_the_order_of_the_pins_they_feed_and_no_wire_crosses() -> None:
    poles, pins = _x_of_poles_and_pins()
    assert sorted(poles, key=lambda pole: pins[FEEDS[pole]]) == sorted(poles, key=poles.__getitem__)
    assert len(_built()[1].routes) == 6, "every wire is drawn"
    assert page_crossings(_built()[1]) == 0
