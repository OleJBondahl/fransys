"""authoring.md blocks rewritten from `d.wire` to core calls keep their wire rows (C4)."""

from typing import Any

import fransys as fr
from fransys.colours import BU, WH


def _cols(d) -> frozenset[tuple[str, str, str, str]]:
    """The wires of a design as (from, to, colour, size): what a rewrite must keep."""
    rows = fr.derive.wire_rows(fr.build(d).model)
    return frozenset((r.from_, r.to, r.colour, str(r.cross_section_mm2)) for r in rows)


def _strip_sides(d) -> dict[str, str]:
    """The side of each X1 terminal that a conductor lands on: 'internal' or 'external'."""
    tables = fr.build(d).model.tables
    ports: dict[Any, Any] = {p.id: p for p in tables["port"].values()}
    conductors: list[Any] = list(tables["conductor"].values())
    sides = {}
    for c in conductors:
        for p in (ports[c.a], ports[c.b]):
            if p.key[0] == "X1":
                sides[p.key[2]] = p.name
    return sides


def _strips(*, series: bool, colour=BU):
    """authoring.md's Strips and terminals block: a strip of three, a lamp, two wires."""
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    h1 = d.device("H1", "DEMO-LAMP-24")
    with d.function("FEED", "Lamp feed"):
        if series:
            d.series(x1, h1.lamp, x1, wire=(colour, 0.75))
        else:
            d.detail.wire(x1[1], h1[1], wire=(BU, 0.75))
            d.detail.wire(x1[2].outer, h1[2], wire=(BU, 0.75))
    return d


def test_the_strips_block_series_keeps_the_hand_wired_wires():
    assert _cols(_strips(series=True)) == _cols(_strips(series=False))


def test_the_strips_block_series_differs_when_a_colour_changes():
    """Can fail: a planted one-colour change in the series form is seen by the comparison."""
    assert _cols(_strips(series=True, colour=WH)) != _cols(_strips(series=False))


def test_the_strips_block_series_picks_the_sides_itself():
    """The one hop that differs: the hand-wired form fixes terminal 2 on the field side (`.outer`).

    The series chooses each side, so the rows match and the sides do not. detail.md keeps
    the fixed-side case.
    """
    assert _strip_sides(_strips(series=False)) == {"1": "internal", "2": "external"}
    assert _strip_sides(_strips(series=True)) == {"1": "internal", "2": "internal"}
