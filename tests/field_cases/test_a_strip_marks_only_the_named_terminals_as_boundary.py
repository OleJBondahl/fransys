"""Field case: a unit's strip marks only the terminals it names as its boundary.

The engineering shape: a cabinet unit holds a four-way terminal strip X1. Terminals 1 and 2
reach the outside; terminals 3 and 4 are wired inside the cabinet to a device and stay there.
The top design wires a lamp to the strip's two outer terminals.

The bug: `interface=(1, 2)` marked every terminal of the strip as boundary. Terminals 3 and 4,
which only the unit wires, then printed BOUNDARY_UNCONNECTED in the container. A container that
wired X1:3 got no UNIT_BOUNDARY_BYPASSED, and `d.add(..., unused=("X1",))` took every terminal,
inside ones included, so the wire to X1:3 contradicted it.
Fixing decision: author-0038 (a strip's tuple marks its named terminals, and `unused=` covers
only the boundary).
"""

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK, BU


class _Io(NamedTuple):
    X1: Any


@fr.unit("cab", revision=1, interface_version=1, date="2026-10-14", text="First", by="XX")
def _cab(c: Any) -> _Io:
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=(1, 2))  # 3 and 4 stay inside
    io = c.device("A1", "DEMO-IO-2X")
    c.detail.wire(x1[3], io.x1["1"], wire=(BU, 0.75))
    c.detail.wire(x1[4], io.x1["2"], wire=(BU, 0.75))
    return _Io(X1=x1)


def _findings(*, wire_inside: bool = False, unused: bool = False) -> list[Any]:
    d = fr.design("demo_parts", place="C1")
    u = d.add(_cab, "U1", unused=("X1",)) if unused else d.add(_cab, "U1")
    lamp = d.device("H1", "DEMO-LAMP-24")
    if not unused:
        d.detail.wire(u.X1[1], lamp.lamp["1"], wire=(BK, 1.5))
        d.detail.wire(u.X1[2], lamp.lamp["2"], wire=(BK, 1.5))
    if wire_inside:
        d.detail.wire(u.X1[3], d.device("H2", "DEMO-LAMP-24").lamp["1"], wire=(BK, 1.5))
    return list(fr.build(d).findings)


def test_a_strip_marks_only_the_named_terminals_as_boundary() -> None:
    assert "BOUNDARY_UNCONNECTED" not in {f.code for f in _findings()}


def test_a_container_wiring_an_inside_terminal_is_bypassed() -> None:
    assert "UNIT_BOUNDARY_BYPASSED" in {f.code for f in _findings(wire_inside=True)}


def test_unused_on_a_strip_covers_only_its_boundary_terminals() -> None:
    codes = {f.code for f in _findings(wire_inside=True, unused=True)}
    assert "UNUSED_CONTRADICTED" not in codes
