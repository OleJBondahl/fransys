"""KEEP-OUT, first half: every symbol's keep-out is its body united with its bound leads."""

import pytest
from symdef import Box, Line, Point, body_box, keepout_box
from symdef.boxes import slot_box

from electrical_symbols import LIBRARY

KEYS = sorted(LIBRARY.symbols)


def _leads(symbol) -> list[Box]:
    """One box per lead: a `Line` whose `port` is set."""
    return [
        Box(
            Point(min(e.start.x, e.end.x), min(e.start.y, e.end.y)),
            Point(max(e.start.x, e.end.x), max(e.start.y, e.end.y)),
        )
        for e in symbol.elements
        if isinstance(e, Line) and e.port is not None
    ]


def _expected(symbol) -> Box:
    """The declared keep-out, else the body united with the leads."""
    if symbol.keepout is not None:
        return keepout_box(symbol)
    return Box.union(body_box(symbol, LIBRARY.font), *_leads(symbol))


@pytest.mark.parametrize("key", KEYS)
def test_keep_out_is_body_plus_leads(key):
    symbol = LIBRARY.get(key)
    assert keepout_box(symbol, LIBRARY.font) == _expected(symbol)


def test_a_slot_beyond_the_leads_does_not_enlarge_the_keep_out():
    """The coil's tag slot stands 6 M beside its body; the keep-out stays body plus leads (D101)."""
    coil = LIBRARY.get("coil")
    tag = next(s for s in coil.slots if s.id == "tag")
    reach = slot_box(tag)
    keep = keepout_box(coil, LIBRARY.font)
    assert reach.min.x < keep.min.x
    assert keep == _expected(coil)
