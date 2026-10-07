"""Field case: two instances of a board unit, each declaring its through-net "BUS", are chained.

The shape: a board unit declares `d.net("BUS", J1[1], J2[1])`. A container adds two instances,
mates a plug to the first board's J2 and another plug to the second board's J1, and wires the two
plugs together, so the one bus runs through both boards.

The bug (v0.11.1): `NET_SHORTED` fired, "one physical net joins the declared nets BUS, BUS",
because it errored whenever a physical net held more than one declared net, whatever their names.
Fixing decision: model-0156 (declared nets of one name join with no finding; `NET_SHORTED` needs
different names, or an unnamed declared net with another).
"""

from typing import NamedTuple

import fransys as fr
from fransys.colours import BK

_CONN = "DEMO-CONN-2P"


class _Io(NamedTuple):
    J1: fr.Fn
    J2: fr.Fn


@fr.unit("demo-bus-board", revision=1, interface_version=1, date="2026-10-06", text="1", by="AB")
def _board(u: fr.Design) -> _Io:
    j1 = u.device("J1", _CONN, interface=True)
    j2 = u.device("J2", _CONN, interface=True)
    u.net("BUS", j1["1"], j2["1"])
    return _Io(j1.x1, j2.x1)


def _chain() -> fr.Design:
    d = fr.design("demo_parts")
    b1, b2 = d.add(_board, "B1"), d.add(_board, "B2")
    p1, p2 = d.device("P1", _CONN), d.device("P2", _CONN)
    d.mate(p1, b1.J2)
    d.mate(p2, b2.J1)
    d.wire(p1["1"], p2["1"], wire=(BK, 1.5))
    return d


def _shorted(d: fr.Design) -> list[str]:
    return [f.message for f in fr.build(d).findings if f.code == "NET_SHORTED"]


def test_a_chain_of_boards_joins_their_one_named_net() -> None:
    assert _shorted(_chain()) == []


def test_the_bus_wired_to_a_differently_named_net_is_still_shorted() -> None:
    d = fr.design("demo_parts")
    b1 = d.add(_board, "B1")
    other = d.device("X1", _CONN)
    d.net("OTHER", other["1"])
    plug = d.device("P1", _CONN)
    d.mate(plug, b1.J2)
    d.wire(plug["1"], other["1"], wire=(BK, 1.5))
    assert len(_shorted(d)) == 1
