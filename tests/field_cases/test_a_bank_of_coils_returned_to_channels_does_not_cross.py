"""Field case: a bank of relay coils returned to PLC channels draws no crossing return wires.

The engineering shape: eight relays in one group. Each coil's A1 is fed from a terminal of a
feed strip and its A2 is wired to its own output channel of a controller (an external pin
device), channel i for relay i. The bank is the usual legacy cabinet bank.

The bug: only a coil whose channel sits at A1 stood under its channel. With the channel at A2 the
coils kept the order of their feeds, and the A2 returns fanned in as nested staircases that crossed
(14 crossings among the eight returns).

The rule (decision layout-0208, extending layout-0099): a coil that a PLC channel pin switches
stands under that channel, in channel pin order, on whichever coil terminal the channel wires.
"""

import itertools
import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
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
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    with d.function("B", "Relay bank"):
        for i in range(COUNT):
            relay = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            d.detail.wire(live[1 + i % 4], relay.coil["A1"], wire=(BU, 0.5))
            d.detail.wire(plc[PINS[i]], relay.coil["A2"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _crosses(a, b) -> bool:
    """Whether a horizontal and a vertical segment cross strictly inside both."""
    (a0, a1), (b0, b1) = a, b
    if (a0[1] == a1[1]) == (b0[1] == b1[1]):
        return False
    h, v = (a, b) if a0[1] == a1[1] else (b, a)
    (h0, h1), (v0, v1) = h, v
    return min(h0[0], h1[0]) < v0[0] < max(h0[0], h1[0]) and min(v0[1], v1[1]) < h0[1] < max(
        v0[1], v1[1]
    )


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
    coils = sorted(
        (ps for ps in symbols if ps[1].key == "operating-device"), key=lambda ps: ps[1].x
    )
    ((box_page, box),) = ((page, s) for page, s in symbols if s.key == GENERIC_BOX_KEY)
    assert all(page == box_page and s.y < box.y for page, s in coils)
    coil_tags = [s.tag for s in symbol_subjects(model) if s.key == "operating-device"]
    assert coil_tags == [f"K{i + 1}" for i in range(COUNT)]
