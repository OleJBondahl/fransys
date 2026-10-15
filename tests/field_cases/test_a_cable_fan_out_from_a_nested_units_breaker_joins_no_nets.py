"""Field case: one breaker fanning out to three cables on a page draws no net onto another's ink.

The engineering shape: a container unit nests a cabinet unit that hands up a two-pole breaker,
two relays, a PLC input module and a fused terminal. Three valve functions each hold a four-pin
actuator with two changeover position switches and an eight-core cable. Cores 1 and 2 come from
the breaker's two outputs, the same two nets for all three valves. Cores 3 and 4 come from relay
changeover contacts. Cores 5 and 7 run by series from input channels to the position switches
and cores 6 and 8 from one fused-terminal pin.

The bug (v0.19.1): the build gave a `DRAWING_SHORTS_NETS` finding, 0 in v0.18.7 on the same model.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
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
    for i in (1, 2, 3):
        with u.function(f"V{i}", f"Valve {i}"):
            v = u.device(f"V{i}", "DEMO-ACT-4P-2SW")
            c = u.cable(f"W{i}", "DEMO-CBL-8G0.75", length_m=5)
            c.core(1, cab.F1.pole_1["2"], v.power["1"])
            c.core(2, cab.F1.pole_2["4"], v.power["2"])
            c.core(3, getattr(cab.K1, f"co_{i}")[f"{i}4"], v.drive["3"])
            c.core(4, getattr(cab.K2, f"co_{i}")[f"{i}4"], v.drive["4"])
            c.core(6, cab.X1[1].outer, v.sw_1["6"])
            c.core(8, cab.X1[1].outer, v.sw_2["8"])
            v.sw_1.plc(fr.DI, f"Pos {i}.1")
            v.sw_2.plc(fr.DI, f"Pos {i}.2")
            u.series(v.sw_1, c, cab.A1, wire=WIRE)
            u.series(v.sw_2, c, cab.A1, wire=WIRE)
    return _Open()


@cache
def _findings() -> list[fr.Finding]:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Skid\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.add(_skid, "S1", place=None)
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-skid", cover=cover)
        return list(fr.check(fr.build(d, document)))


@pytest.mark.xfail(strict=True, reason="LEGACY-SHORTS: 0.19.1 draws shorted nets, 0.18.7 drew none")
def test_the_fan_out_draws_no_shorted_nets() -> None:
    assert [f for f in _findings() if f.code == "DRAWING_SHORTS_NETS"] == []
