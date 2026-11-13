"""The witness build of a board nested in a unit (KI-806, RETURNS-023 R-D16), shared by the field cases and `rel_sweep`."""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK


class Open(NamedTuple):
    pass


class Io(NamedTuple):
    X7: fr.Device


def board_fn(u: Any) -> Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    x7 = u.device("X7", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    k1 = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.series(x7[1], k1["1"], wire=(BK, 0.5))
    u.series(x7[2], k1["2"], wire=(BK, 0.5))
    return Io(x7)


board = fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")(board_fn)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def board_cab(u: Any) -> Open:
    nested = u.add(board, "U1")
    j1 = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    for n in (1, 2):
        lamp = u.device(f"H{n}", "DEMO-LAMP-24")
        u.series(j1[n], lamp["1"], wire=(BK, 0.5))
        u.series(j1[n + 2], lamp["2"], wire=(BK, 0.5))
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, nested.X7[1], j1[1])
    cable.core(2, nested.X7[2], j1[2])
    return Open()


def build_board_cab() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(board_cab, "C1", place=None)
    return fr.build(d, unit_document("demo-cab"))
