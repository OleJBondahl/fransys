"""Field case: a relay bank with a link wired between the two terminals of one relay coil, so the link's net has two pins on one symbol.
The bug: the placement dropped a net with fewer than two distinct symbols, so the link had no wire on the page.
Fixed by R371, a net of two or more pins is drawn, whether its pins sit on one symbol or on several."""

from functools import cache
from typing import Any

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU


@cache
def _built(*, linked: bool) -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Supply"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    with d.function("B", "Relay bank"):
        fed = d.device("K1", "DEMO-RLY-2CO-24")
        d.series(live[1].inner, fed.coil["A1"], wire=(BU, 0.5))
        d.series(live[2].inner, fed.coil["A2"], wire=(BU, 0.5))
        shorted = d.device("K2", "DEMO-RLY-2CO-24")
        if linked:
            d.series(shorted.coil["A1"], shorted.coil["A2"], wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc).model


def _wire_count(*, linked: bool) -> int:
    return sum(len(drawing.wires) for drawing in drawn_pages(_built(linked=linked)).values())


def test_a_one_symbol_two_pin_net_draws_a_wire() -> None:
    """Wiring the two terminals of a coil together adds exactly one wire to the page."""
    assert _wire_count(linked=True) == _wire_count(linked=False) + 1
