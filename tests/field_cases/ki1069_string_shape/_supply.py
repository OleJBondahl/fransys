from __future__ import annotations

from typing import Any, NamedTuple

from fransys.colours import BK, BN, BU, RD
lazy import fransys as fr

from . import typed

POLE_ESTOP = 10
POLE_S1_CONTACT_2 = 11
POLES = 12
POLE_PACK = 7
POLE_PSU = 3
POLE_PLC = 4
POLE_FIELD = 5
LEVEL_POLES = (6, 12)
PE_BAR_POSITIONS = 7


class Supply(NamedTuple):
    x1: fr.Run
    x2: fr.Run
    mains: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    pe_bar: fr.Run
    psu: Any


def build_supply(d: fr.Design) -> Supply:
    with d.function("SUP", "24 V supply"):
        x4 = d.terminal_strip("X4", typed.PRT15, interface=True, pe=typed.PRT16)
        mains = (x4.run("L", 1)[1], x4.run("N", 1)[1], x4.run("PE", 1)[1])
        psu = d.device("PSU1", typed.PRT17)
        f1 = d.device("F1", typed.PRT01)
        x1 = d.terminal_strip("X1", typed.PRT15).run("24V", POLES, bridged=True)
        x2 = d.terminal_strip("X2", typed.PRT15).run("GND", POLES, bridged=True)
    pe_bar = d.terminal_strip("PE_BAR", typed.PRT16, pe=typed.PRT16).run("PE", PE_BAR_POSITIONS, bridged=True)
    d.series((mains[0], mains[1]), f1.main, (psu.input["L"], psu.input["N"]), wire=((BN, 1.5), (BU, 1.5)))
    d.series(psu.output["24V1"], x1[POLE_PSU], wire=(RD, 1.5))
    d.series(psu.output["GND1"], x2[POLE_PSU], wire=(BK, 1.5))
    plus, minus = (psu.output["24V1"], psu.output["GND1"])
    d.dc_supply("24V", psu.output, plus=plus, minus=minus, names=("24V", "GND"))
    return Supply(x1, x2, mains, pe_bar, psu)


def earth_pins(supply: Supply) -> list[fr.Pin | fr.Terminal]:
    return [supply.psu.input["PE"], supply.mains[2], supply.pe_bar[1]]
