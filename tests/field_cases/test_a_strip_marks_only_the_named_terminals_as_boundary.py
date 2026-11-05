"""Field case: a cabinet unit's four-way strip where terminals 1 and 2 reach outside and 3 and 4 wire only inside the cabinet.
The bug: `interface=(1, 2)` marked every terminal as boundary, so 3 and 4 printed BOUNDARY_UNCONNECTED.
Fixed by author-0038, a strip's tuple marks its named terminals."""

from typing import Any, NamedTuple

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BK, BU


class _Io(NamedTuple):
    X1: Any


@fr.unit("cab", revision=1, interface_version=1, date="2026-10-14", text="First", by="XX")
def _cab(c: Any) -> _Io:
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=(1, 2))  # 3 and 4 stay inside
    io = c.device("A1", "DEMO-IO-2X")
    c.series(x1[3].inner, io.x1["1"], wire=(BU, 0.75))
    c.series(x1[4].inner, io.x1["2"], wire=(BU, 0.75))
    return _Io(X1=x1)


def _built(*, wire_inside: bool = False) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    u = d.add(_cab, "U1")
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.series(u.X1[1].outer, lamp.lamp["1"], wire=(BK, 1.5))
    d.series(u.X1[2].outer, lamp.lamp["2"], wire=(BK, 1.5))
    if wire_inside:
        h2 = d.device("H2", "DEMO-LAMP-24")
        d.series(u.X1[3].outer, h2.lamp["1"], wire=(BK, 1.5))
        d.series(h2.lamp["2"], d.terminal_strip("X0", "DEMO-TB-2.5", 1).run("0V", 1)[1].inner, wire=(BK, 1.5))
    return fr.build(d)


def test_a_strip_marks_only_the_named_terminals_as_boundary() -> None:
    assert "BOUNDARY_UNCONNECTED" not in {f.code for f in _built().findings}


def test_a_container_wiring_an_inside_terminal_is_bypassed() -> None:
    expect_codes(_built(wire_inside=True), "UNIT_BOUNDARY_BYPASSED")
