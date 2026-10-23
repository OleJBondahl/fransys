"""Field case: a star-net terminal on a declared net is drawn at its wires and nowhere else.

The engineering shape: one strip terminal X1:1 feeds the same contact pin of three relays, a
star net of four ports, and the terminal is also named by a declared net (a supply label).

The bug: layout-0216 and model-0220 give each wire a copy of the terminal under its contact, so
the wires end at the copies. layout-0214 kept every copy of a terminal on a declared net, the
home too, so the home stood at its column with no wire and no marker: a loose terminal symbol.

The rule, decision model-0220 with layout-0214 amended: once the copies are made, a home that
no wire reaches is dropped, whatever keep clause fired. Every drawn terminal symbol has a wire.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab.tables import conductors

_RELAYS = 3


class _Io(NamedTuple):
    feed: fr.TerminalStrip


def _supply(u: fr.Design) -> _Io:
    feed = u.terminal_strip("X1", "DEMO-TB-2.5", 2)
    relays = [u.device(f"K{i + 1}", "DEMO-RLY-2CO-24") for i in range(_RELAYS)]
    for relay in relays:
        u.detail.wire(feed[1], relay.co_1["11"], wire=("WH", 0.75))
    u.detail.net("L1", feed[1])
    return _Io(feed)


@cache
def _model() -> Any:
    unit = fr.unit(
        "demo-stranded", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB"
    )(_supply)
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Stranded\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.add(unit, "U1")
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-stranded", cover=cover)
        return fr.build(d, document).model


def test_the_terminal_stands_once_at_each_wire_and_no_home_is_left() -> None:
    model = _model()
    drawings = list(drawn_pages(model).values())
    stood = [one for d in drawings for one in d.symbols if one.key == "terminal"]
    wires = [w for d in drawings for w in d.wires]
    assert len(conductors(model)) == _RELAYS
    assert len(wires) == _RELAYS
    assert len(stood) == _RELAYS


def test_no_marker_stands_for_the_terminal() -> None:
    assert not layout_of(_model(), LinkMarker)
