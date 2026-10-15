"""examples.md's sixteen sensors keep their wires on core calls (API-DETAIL, C4)."""

import fransys as fr
from fransys.colours import BU, WH


def _cols(d) -> frozenset[tuple[str, str, str, str]]:
    """The wires of a design as (from, to, colour, size): what a rewrite must keep."""
    rows = fr.derive.wire_rows(fr.build(d).model)
    return frozenset((r.from_, r.to, r.colour, str(r.cross_section_mm2)) for r in rows)


def _sensors(*, series: bool, colour=BU):
    """examples.md's sixteen sensors: B16 added first, so the strip's next free terminal is B1's."""
    d = fr.design("demo_parts")
    with d.function("SENS", "Sensors"):
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
        for n in range(16, 0, -1):
            b = d.device(f"B{n}", "DEMO-SWITCH-2P")
            if series:
                d.series(b.sw, x1, wire=(colour, 0.75))
            else:
                d.detail.wire(b.sw.B, x1[17 - n], wire=(colour, 0.75))
    return d


def test_the_sensors_as_a_series_keep_the_hand_wired_wires():
    assert _cols(_sensors(series=True)) == _cols(_sensors(series=False))


def test_the_sensors_as_a_series_differ_when_a_colour_changes():
    """Can fail: a planted one-colour change in the series form is seen by the comparison."""
    assert _cols(_sensors(series=True, colour=WH)) != _cols(_sensors(series=False))
