from __future__ import annotations

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import GNYE

from ._bus import build_bus
from ._field import Estop, build_estop, build_field
from ._plc import build_plc, wire_string_io
from ._release import REVISION, VERSION
from ._string import build_string, wire_plc_can
from ._supply import build_supply, earth_pins
lazy from . import typed as typed

NAME = "dev-top"
INTERFACE = "1"
TITLE = "Top"
NUMBER = "TBD-1"
STRINGS = 1


class Interface(NamedTuple):
    string_pos: tuple[Any, ...]
    string_neg: tuple[Any, ...]
    cmu_link: tuple[Any, ...]
    dc_pos: fr.Terminal
    dc_neg: fr.Terminal
    mains: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    estop: Estop
    ethernet: Any
    ov_loop: tuple[fr.Terminal, ...]
    lt01: tuple[fr.Terminal, fr.Terminal]
    tt01: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    tt02: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    ls01: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    ls02: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    pack_supply: tuple[fr.Terminal, fr.Terminal]


@fr.unit(NAME, version=VERSION, revision=REVISION, interface_version=INTERFACE, title=TITLE, number=NUMBER, date="2026-10-06", text="demo", by="XX")
def build(d: fr.Design) -> Interface:
    d.layout.profile(hide_unused_pins=True)
    supply = build_supply(d)
    plc = build_plc(d, supply)
    d.earth(*earth_pins(supply), plc.pe)
    d.series(supply.psu.input["PE"], supply.pe_bar[5], wire=(GNYE, 1.5))
    d.series(plc.pe, supply.pe_bar[6], wire=(GNYE, 0.5))
    d.series(supply.mains[2], supply.pe_bar[7], wire=(GNYE, 1.5))
    dc_pos, dc_neg = build_bus(d)
    strings = tuple(build_string(d, n, supply, dc_pos, dc_neg, last=n == STRINGS) for n in range(1, STRINGS + 1))
    wire_plc_can(d, strings, plc.plc)
    wire_string_io(d, strings, plc)
    field = build_field(d, supply, plc, STRINGS)
    estop = build_estop(d, strings, supply, plc)
    return Interface(
        string_pos=tuple(s.string_pos for s in strings),
        string_neg=tuple(s.string_neg for s in strings),
        cmu_link=tuple(s.cmu_link for s in strings),
        dc_pos=dc_pos,
        dc_neg=dc_neg,
        mains=supply.mains,
        estop=estop,
        ethernet=plc.bh1.side_b,
        ov_loop=field.ov_loop,
        lt01=field.lt01,
        tt01=field.tt01,
        tt02=field.tt02,
        ls01=field.ls01,
        ls02=field.ls02,
        pack_supply=field.pack_supply,
    )
