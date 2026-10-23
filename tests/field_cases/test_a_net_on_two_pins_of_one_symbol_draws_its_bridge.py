"""Field case: a net whose two pins sit on one symbol draws its wire.

The engineering shape: a relay bank of one coil fed from a terminal strip, with a link wired between
the two terminals of a second relay's coil (a shorted coil). The link's net has two pins, both on
that one symbol.

The bug: the placement dropped a net with fewer than two distinct symbols, so the link had no wire
on the page.

The rule (R371): a net of two or more pins is drawn, whether its pins sit on one symbol or on
several.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU


@cache
def _built(*, linked: bool) -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Supply"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    with d.function("B", "Relay bank"):
        fed = d.device("K1", "DEMO-RLY-2CO-24")
        d.detail.wire(live[1], fed.coil["A1"], wire=(BU, 0.5))
        d.detail.wire(live[2], fed.coil["A2"], wire=(BU, 0.5))
        shorted = d.device("K2", "DEMO-RLY-2CO-24")
        if linked:
            d.detail.wire(shorted.coil["A1"], shorted.coil["A2"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _wire_count(*, linked: bool) -> int:
    return sum(len(drawing.wires) for drawing in drawn_pages(_built(linked=linked)).values())


def test_a_one_symbol_two_pin_net_draws_a_wire() -> None:
    """Wiring the two terminals of a coil together adds exactly one wire to the page."""
    assert _wire_count(linked=True) == _wire_count(linked=False) + 1
