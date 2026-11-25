from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from fransys.colours import BK, RD, WH
lazy import fransys as fr

from . import typed
from ._supply import POLE_FIELD, POLE_PLC, Supply

if TYPE_CHECKING:
    from ._string import String
ETHERNET_GAUGE = 0.2
BULKHEAD = typed.PRT07
IO_GAUGE = 0.5


class Plc(NamedTuple):
    plc: Any
    dio: Any
    di: Any
    ai: Any
    rtd: Any
    bh1: Any
    pe: fr.Pin


def build_plc(d: fr.Design, supply: Supply) -> Plc:
    with d.function("PLC", "PLC"):
        plc = d.device("PLC1", typed.PRT34)
        dio = d.device("KE1", typed.PRT30, parent=plc)
        di = d.device("KE2", typed.PRT29, parent=plc)
        ai = d.device("KE3", typed.PRT31, parent=plc)
        rtd = d.device("BT1", typed.PRT32, parent=plc)
        d.device(None, typed.PRT33, name="plc_end", parent=plc)
    d.series(
        (supply.x1[POLE_PLC].inner, supply.x2[POLE_PLC].inner), (plc.supply_system["S24V"], plc.supply_system["SGND"]), wire=((RD, 0.5), (BK, 0.5))
    )
    d.series(
        (supply.x1[POLE_FIELD].inner, supply.x2[POLE_FIELD].inner),
        (plc.supply_field["F24V1"], plc.supply_field["FGND1"]),
        wire=((RD, 0.5), (BK, 0.5)),
    )
    with d.function("NET", "Network"):
        bh1 = d.device("BH1", BULKHEAD, interface=("side_b",))
    d.series(plc.X1["X1"], bh1.side_a["side_a_1"], wire=(WH, ETHERNET_GAUGE))
    return Plc(plc, dio, di, ai, rtd, bh1, plc.supply_field["PE1"])


def wire_string_io(d: fr.Design, strings: tuple[String, ...], plc: Plc) -> None:
    for n, string in enumerate(strings, start=1):
        d.series(string.j2_plug[1], getattr(plc.dio, f"di_{n}")[str(n)], wire=(WH, IO_GAUGE))
        d.series(string.j2_plug[2], getattr(plc.dio, f"do_{n}")[str(8 + n)], wire=(WH, IO_GAUGE))
