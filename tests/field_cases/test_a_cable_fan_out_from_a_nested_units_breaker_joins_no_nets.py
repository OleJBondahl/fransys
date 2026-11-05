"""Field case: a nested unit's breaker fans out to three eight-core cables whose cores share two nets on one page.
The bug (v0.19.1): the build gave a DRAWING_SHORTS_NETS finding, 0 in v0.18.7 on the same model.
Open: no deciding record is named; the test is a plain regression check."""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK

WIRE = (BK, 0.75)


class _Open(NamedTuple):
    pass


class _Io(NamedTuple):
    F1: fr.Device
    K1: fr.Device
    K2: fr.Device
    A1: fr.Device
    X1: fr.TerminalStrip


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Io:
    f1 = u.device("F1", "DEMO-MCB-2P", interface=("pole_1", "pole_2"))
    k1 = u.device("K1", "DEMO-RLY-4CO-24", interface=("co_1", "co_2", "co_3"))
    k2 = u.device("K2", "DEMO-RLY-4CO-24", interface=("co_1", "co_2", "co_3"))
    a1 = u.device("A1", "DEMO-PLC-DI-16", interface=tuple(f"di_{n}" for n in range(1, 7)))
    x1 = u.terminal_strip("X1", "DEMO-TB-FUSE-2.5", 1, interface=(1,))
    return _Io(f1, k1, k2, a1, x1)


@fr.unit("demo-skid", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _skid(u: Any) -> _Open:
    cab = u.add(_cab, "N")
    x9 = u.terminal_strip("X9", "DEMO-TB-FUSE-2.5", 2)
    w0 = u.cable("W0", "DEMO-CBL-4G1.5", length_m=5)
    w0.core(1, x9[1], cab.F1.pole_1["1"])
    w0.core(2, x9[2], cab.F1.pole_2["3"])
    feed = cab.X1[1].outer
    for i in (1, 2, 3):
        with u.function(f"V{i}", f"Valve {i}"):
            v = u.device(f"V{i}", "DEMO-ACT-4P-2SW")
            c = u.cable(f"W{i}", "DEMO-CBL-8G0.75", length_m=5)
            c.core(1, cab.F1.pole_1["2"], v.power["1"])
            c.core(2, cab.F1.pole_2["4"], v.power["2"])
            c.core(3, getattr(cab.K1, f"co_{i}")[f"{i}4"], v.drive["3"])
            c.core(4, getattr(cab.K2, f"co_{i}")[f"{i}4"], v.drive["4"])
            c.core(6, feed, v.sw_1["6"])
            c.core(8, v.sw_1["6"], v.sw_2["8"])
            feed = v.sw_2["8"]
            v.sw_1.plc(fr.DI, f"Pos {i}.1")
            v.sw_2.plc(fr.DI, f"Pos {i}.2")
            u.series(v.sw_1, c, cab.A1, wire=WIRE)
            u.series(v.sw_2, c, cab.A1, wire=WIRE)
    return _Open()


@cache
def _findings() -> list[fr.Finding]:
    d = fr.design("demo_parts")
    d.add(_skid, "S1", place=None)
    document = unit_document("demo-skid")
    return list(fr.check(fr.build(d, document)))


def test_the_fan_out_draws_every_connection_and_no_shorted_nets() -> None:
    assert [f for f in _findings() if f.code in {"DRAWING_SHORTS_NETS", "CONNECTION_NOT_DRAWN"}] == []
