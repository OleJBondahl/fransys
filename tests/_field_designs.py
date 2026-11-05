"""Small circuits and checks that several field cases build or run alike: an I/O unit, a board unit, a feeder, a PLC card, wire crossings."""

import itertools
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id


class Io(NamedTuple):
    X1_L1: Any
    X2_L2: Any


def io(d: fr.Design) -> Io:
    a1 = d.device("A1", "DEMO-IO-2X", interface=True)
    return Io(a1.x1, a1.x2)


class BoardIo(NamedTuple):
    J1: fr.Device


def board(u: fr.Design) -> BoardIo:
    """A PCB with an interface connector wired to a lamp."""
    pcb = u.device("A1", "DEMO-PCB-IO")
    j1 = u.device("J1", "DEMO-CONN-2P", parent=pcb, interface=True)
    h1 = u.device("H1", "DEMO-LAMP-24", parent=pcb)
    u.series(j1["1"], h1["1"], wire=(BK, 0.75))
    u.series(j1["2"], h1["2"], wire=(BK, 0.75))
    return BoardIo(j1)


def bridged_feeder() -> tuple[Any, Any, Any, Any]:
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4)
    ac = d.ac_supply("400V", 230, x0[1], x0[2], x0[3], n=x0[4])
    return d, ac, d.device("Q0", "DEMO-MCB-3P"), d.terminal_strip("X1", "DEMO-TB-2.5")


def plc_di_design() -> tuple[fr.Design, Any, Any]:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"), names=("P24", "P0"))
    return d, dc, d.device("A1", "DEMO-PLC-DI-16")


def wire_crossings(wires: tuple[Any, ...]) -> int:
    """Horizontal-over-vertical crossings, strictly inside both segments, between drawn wires."""
    found = 0
    for one, two in itertools.combinations(wires, 2):
        for (a0, a1), (b0, b1) in itertools.product(itertools.pairwise(one.points), itertools.pairwise(two.points)):
            if (a0[1] == a1[1]) == (b0[1] == b1[1]):
                continue
            (h0, h1), (v0, v1) = ((a0, a1), (b0, b1)) if a0[1] == a1[1] else ((b0, b1), (a0, a1))
            found += min(h0[0], h1[0]) < v0[0] < max(h0[0], h1[0]) and min(v0[1], v1[1]) < h0[1] < max(v0[1], v1[1])
    return int(found)


def harness_item(model: fr.Model, key: str) -> Id[Any]:
    """The harness item whose key is `<key>/<key>`."""
    (found,) = [i for i, item in items(model).items() if "/".join(item.key) == f"{key}/{key}"]
    return found
