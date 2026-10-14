"""Field case: a series that passes a unit's strip takes a terminal wired inside, not a spare.

The engineering shape: an io-board unit has a 4-terminal strip X1. Terminals 1 and 2 are the
interface; the board wires them through a lamp (`series(x1, h1.lamp, x1)`, which lands terminal
1 on its outer port and terminal 2 on its inner). Terminals 3 and 4 are declared unused. The
container feeds the strip with `d.series(dc.plus, io.x1)` and `d.series(io.x1, dc.minus)`.

The bug: the container skipped terminal 1, because its outer port already held the board's own
wire, and took terminal 3, a declared spare: `BOUNDARY_UNCONNECTED` on terminal 1 (ERROR) and
`UNUSED_CONTRADICTED` on terminal 3 (WARNING).

Rule (author-0040): a strip passed across a unit boundary takes, in order, a terminal whose inside
is wired and whose outside is free, and never one declared unused.
"""

from functools import cache
from typing import NamedTuple

import fransys as fr
from fransys.colours import BU

CTRL = (BU, 0.75)


class _Io(NamedTuple):
    x1: fr.TerminalStrip


@fr.unit("io-board", revision=1, interface_version=1, date="2026-01-01", text="First", by="XX")
def _io_board(c: fr.Design) -> _Io:
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=(1, 2), unused=(3, 4))
    h1 = c.device("H1", "DEMO-LAMP-24")
    c.series(x1, h1.lamp, x1, wire=CTRL)
    return _Io(x1)


@cache
def _codes() -> tuple[str, ...]:
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
    io = d.add(_io_board, "U2")
    d.series(dc.plus, io.x1, wire=CTRL)
    d.series(io.x1, dc.minus, wire=CTRL)
    return tuple(f.code for f in fr.check(fr.build(d)))


def test_the_boundary_terminals_are_connected_across() -> None:
    """Terminals 1 and 2 are taken, so no boundary function is left unconnected."""
    assert "BOUNDARY_UNCONNECTED" not in _codes()


def test_a_declared_spare_is_not_taken() -> None:
    """Terminals 3 and 4 stay unused, so nothing contradicts a declaration."""
    assert "UNUSED_CONTRADICTED" not in _codes()
