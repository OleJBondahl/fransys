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

import fransys as fr
from fransys.colours import BU
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items, ports

COUNT = 8
PINS = tuple(f"CH{j:02d}-" for j in range(1, COUNT + 1))


@cache
def _built() -> tuple:
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
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    return model, results.layout


def _crosses(a, b) -> bool:
    """Whether a horizontal and a vertical segment cross strictly inside both."""
    (a0, a1), (b0, b1) = a, b
    if (a0.y == a1.y) == (b0.y == b1.y):
        return False
    h, v = (a, b) if a0.y == a1.y else (b, a)
    (h0, h1), (v0, v1) = h, v
    return min(h0.x, h1.x) < v0.x < max(h0.x, h1.x) and min(v0.y, v1.y) < h0.y < max(v0.y, v1.y)


def _segments(route) -> list:
    pts = [p.at for p in route.points]
    return list(itertools.pairwise(pts))


def _returns(model, layout) -> list:
    """The routes that end at a coil's A2."""
    by_id = ports(model)
    return [r for r in layout.routes if any(by_id[end].name == "A2" for end in (r.a, r.b))]


def test_returns_to_channels_do_not_cross() -> None:
    model, layout = _built()
    returns = _returns(model, layout)
    assert len(returns) == COUNT
    crossings = sum(
        _crosses(s, t)
        for one, two in itertools.combinations(returns, 2)
        if (one.drawing_set, one.page) == (two.drawing_set, two.page)
        for s in _segments(one)
        for t in _segments(two)
    )
    assert crossings == 0


def test_the_coils_stand_over_the_controller_in_channel_order() -> None:
    """Every coil over the box, in channel order: none hangs below on a pin of no fixed side."""
    model, layout = _built()
    tag_of = {i.id: i.tag for i in items(model).values()}
    coil_of = {f.id: tag_of[f.item] for f in functions(model).values() if f.name == "coil"}
    coils = sorted((p for p in layout.placed if p.function in coil_of), key=lambda p: p.at.x)
    (box,) = (p for p in layout.placed if tag_of.get(functions(model)[p.function].item) == "A1")
    assert [coil_of[p.function] for p in coils] == [f"K{i + 1}" for i in range(COUNT)]
    assert all((p.page, p.at.y < box.at.y) == (box.page, True) for p in coils)
