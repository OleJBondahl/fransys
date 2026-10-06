"""Field case: a nested board pin mated onto a rail draws no power symbol in its outline.

The engineering shape: a cabinet unit holding a 24 V and 0 V supply, a lamp wired to a cabinet plug
whose pins sit on the rails, and a nested board unit whose boundary connector is mated to that plug
and wires its pins to a lamp of its own.

The bug: the mate puts the board's connector pins on the cabinet's rails, so V3 gave the black box
on the cabinet's page a bar and a ground inside the board's outline, where its leads end.

The rule (CONVENTIONS-V06 V3, decision layout-0099; black box, owner 2026-09-23): a nested unit's
boundary port is boundary-only on its parent's page and takes no rail symbol there. The plug's
pins, on the cabinet's own set, keep theirs. The board's own pages still draw them.
"""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import system_document
from fransys.colours import BU

from fransys_model.layout import DrawingSet, Page, PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports, unit_releases, units

_PROJECT: dict[str, Any] = {
    "title": "Board on a rail",
    "number": "P-1011",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


class _Board(NamedTuple):
    X1: Any


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


@fr.unit(
    "demo-io-board",
    revision=3,
    interface_version=2,
    date="2026-01-01",
    text="First release",
    by="XX",
)
def _board(d: fr.Design) -> _Board:
    """The nested board: a boundary connector wired to a lamp of its own."""
    with d.function("BRD", "I/O board"):
        x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
        bulb = d.device("H2", "DEMO-LAMP-24")
        d.wire(x1.x1["1"], bulb.lamp["1"], wire=(BU, 0.5))
        d.wire(x1.x1["2"], bulb.lamp["2"], wire=(BU, 0.5))
    return _Board(x1)


@fr.unit(
    "demo-pump-cabinet",
    revision=2,
    interface_version=1,
    date="2026-01-01",
    text="First release",
    by="XX",
)
def _cabinet(d: fr.Design) -> _Open:
    """The cabinet: a plug on the 24 V and 0 V rails, a lamp, and the board mated to the plug."""
    d.location("C1", "Cabinet")
    with d.function("G", "Group"):
        plug = d.device("P1", "DEMO-CONN-2P")
        lamp = d.device("H1", "DEMO-LAMP-24")
        d.dc_supply("S", plus=plug.x1["1"], minus=plug.x1["2"], voltage=24)
        d.wire(plug.x1["1"], lamp.lamp["1"], wire=(BU, 0.5))
        d.wire(plug.x1["2"], lamp.lamp["2"], wire=(BU, 0.5))
    d.mate(plug, d.add(_board, "IO").X1)
    return _Open()


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    d.add(_cabinet, "CAB")
    return fr.build(d, system_document())


def _symbols(model) -> set[tuple[str, str]]:
    """`(unit name, item tag)` of every power symbol: the unit whose page it is drawn on."""
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    found = set()
    for symbol in layout_of(model, PowerSymbol).values():
        owner = sets[pages[symbol.page].drawing_set].unit
        assert owner is not None
        name = unit_releases(model)[units(model)[owner].release].name
        item = functions(model)[ports(model)[symbol.port].function].item
        tag = items(model)[item].tag
        assert tag is not None
        found.add((name, tag))
    return found


def test_a_black_box_pin_on_a_rail_draws_no_symbol_on_its_parents_page() -> None:
    found = _symbols(_build().model)
    assert (
        "demo-pump-cabinet",
        "P1",
    ) in found  # the plug on the cabinet's own set keeps its symbols
    assert ("demo-io-board", "X1") in found  # and the board's own pages still draw theirs
    assert ("demo-pump-cabinet", "X1") not in found
