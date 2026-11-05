"""Field case: eight relay coils in one bank, each A1 fed from a feed strip and each A2 wired to its own PLC output channel.
The bug: with the channel at A2 the coils kept their feed order, so the A2 returns crossed as nested staircases (14 crossings).
Fixed by layout-0208 (extends layout-0099), a coil that a PLC channel pin switches stands under that channel, in channel pin order."""

import itertools
from functools import cache
from typing import Any

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_layout.geometry import GENERIC_BOX_KEY

COUNT = 8
PINS = tuple(f"CH{j:02d}-" for j in range(1, COUNT + 1))


@cache
def _built() -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("PLC", "Controller"):
        plc = d.device("A1", None, pins=PINS, external=True)
    with d.function("G1", "Supply"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 4)
    with d.function("B", "Relay bank"):
        for i in range(COUNT):
            relay = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            d.series(live[1 + i % 4].inner, relay.coil["A1"], wire=(BU, 0.5))
            d.series(plc[PINS[i]], relay.coil["A2"], wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc).model


def _crosses(a: tuple[tuple[float, float], tuple[float, float]], b: tuple[tuple[float, float], tuple[float, float]]) -> bool:
    """Whether a horizontal and a vertical segment cross strictly inside both."""
    (a0, a1), (b0, b1) = a, b
    if (a0[1] == a1[1]) == (b0[1] == b1[1]):
        return False
    h, v = (a, b) if a0[1] == a1[1] else (b, a)
    (h0, h1), (v0, v1) = h, v
    return min(h0[0], h1[0]) < v0[0] < max(h0[0], h1[0]) and min(v0[1], v1[1]) < h0[1] < max(v0[1], v1[1])


def test_returns_to_channels_do_not_cross() -> None:
    """No two wires of the page cross: the feeds and the A2 returns share one page."""
    wires = [drawing.wires for drawing in drawn_pages(_built()).values()]
    assert any(wires)
    crossings = sum(
        _crosses(s, t)
        for page in wires
        for one, two in itertools.combinations(page, 2)
        for s in itertools.pairwise(one.points)
        for t in itertools.pairwise(two.points)
    )
    assert crossings == 0


def test_the_coils_stand_over_the_controller_in_channel_order() -> None:
    """Every coil over the box, in channel order: none hangs below on a pin of no fixed side."""
    model = _built()
    symbols = [(page, s) for page, drawing in drawn_pages(model).items() for s in drawing.symbols]
    coils = sorted((ps for ps in symbols if ps[1].key == "operating-device"), key=lambda ps: ps[1].x)
    ((box_page, box),) = ((page, s) for page, s in symbols if s.key == GENERIC_BOX_KEY)
    assert all(page == box_page and s.y < box.y for page, s in coils)
    coil_tags = [s.tag for s in symbol_subjects(model) if s.key == "operating-device"]
    assert coil_tags == [f"K{i + 1}" for i in range(COUNT)]
