"""Field case: a two-pole DC switch, each pole through its own fuse to a monitor whose inner measure function joins both nets.
The bug (v0.21.1): the drawing set cannot be laid out, a PLACEMENT_PROBLEM ERROR (TrunkError in route_trunk); v0.20 laid it out.
Fixed by layout-0392 (BUNDLE R283), a bundle has one lane per pole in use, so the set has a page and no ERROR."""

from functools import cache

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK, RD


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Monitor", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    s1 = d.device("S1", "DEMO-SWITCH-DC-2P")
    f2, f5 = d.device("F2", "DEMO-FUSE-DC-160"), d.device("F5", "DEMO-FUSE-DC-160")
    a4 = d.device("A4", "DEMO-MONITOR-JOINS")
    d.series(s1.main.pole(1), f2.element, wire=(RD, 0.5))
    d.series(f2.element[2], a4.LA[1], wire=(RD, 0.5))
    d.series(s1.main.pole(2), f5.element, wire=(BK, 0.5))
    d.series(f5.element[2], a4.LB[1], wire=(BK, 0.5))
    lamps = [d.device(f"P{n}", "DEMO-LAMP-24") for n in range(1, 5)]
    for pin, lamp in zip((a4.LA[2], a4.LB[2], a4.K[3], a4.K[4]), lamps, strict=True):
        d.series(pin, lamp["1"], wire=(BK, 0.5))
    returns = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    for n, lamp in enumerate(lamps, start=1):
        d.series(lamp["2"], returns[n].outer, wire=(BK, 0.5))
    return fr.build(d, unit_document(cab))


def test_the_set_is_laid_out_with_no_error() -> None:
    errors = [f.message for f in _built().findings if f.severity == fr.Severity.ERROR]
    assert errors == []


def test_no_arrow_of_the_set_stands_over_a_foreign_wire() -> None:
    """a fed arrow is never refused (MARKER_UNPLACED 0) and a marker over a foreign wire (looks) only falls."""
    codes = [f.code for f in _built().findings]
    assert codes.count("MARKER_UNPLACED") == 0
    assert codes.count("WIRE_OVER_MARKER") <= 1  # KI-352, R1081, R1101 (looks): the tip's count at salt -, falls only
