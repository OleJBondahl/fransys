from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload

from fransys.colours import BK, RD, WH
lazy import fransys as fr

from . import typed
from ._supply import LEVEL_POLES, POLE_ESTOP, POLE_PACK, POLE_S1_CONTACT_2, Supply
lazy from ._plc import Plc

if TYPE_CHECKING:
    from ._string import String
TERMINAL = typed.PRT15
NTC = typed.PRT08
SIGNAL_GAUGE = 0.25
PACK_SUPPLY_GAUGE = 0.5
WHITE = WH
NTC_PORTS = (("TEMP1A", "TEMP1B"), ("TEMP2A", "TEMP2B"), ("TEMP3A", "TEMP3B"))


class Estop(NamedTuple):
    out: fr.Terminal
    back: fr.Terminal


class Field(NamedTuple):
    ov_loop: tuple[fr.Terminal, ...]
    lt01: tuple[fr.Terminal, fr.Terminal]
    tt01: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    tt02: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    ls01: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    ls02: tuple[fr.Terminal, fr.Terminal, fr.Terminal]
    pack_supply: tuple[fr.Terminal, fr.Terminal]


@overload
def _terminals(run: fr.Run, count: Literal[2]) -> tuple[fr.Terminal, fr.Terminal]: ...


@overload
def _terminals(run: fr.Run, count: Literal[3]) -> tuple[fr.Terminal, fr.Terminal, fr.Terminal]: ...


@overload
def _terminals(run: fr.Run, count: int) -> tuple[fr.Terminal, ...]: ...


def _terminals(run: fr.Run, count: int) -> tuple[fr.Terminal, ...]:
    return tuple(run[i] for i in range(1, count + 1))


def build_field(d: fr.Design, supply: Supply, plc: Plc, strings: int) -> Field:
    with d.function("FIELD", "Field terminals"):
        x5 = d.terminal_strip("X5", TERMINAL, interface=True)
        ov_runs = [x5.run(f"OV{n}", 1) for n in range(1, strings + 1)]
        switches = [x5.run(f"LS0{n}", 3) for n in (1, 2)]
        lt01 = x5.run("LT01", 2)
        rtds = [x5.run(f"TT0{channel}", 3) for channel in (1, 2)]
        pack = x5.run("PACK_SUPPLY", 2)
        for run, count in (*((r, 1) for r in ov_runs), *((r, 3) for r in (*switches, *rtds))):
            _terminals(run, count)
        _terminals(lt01, 2)
        _terminals(pack, 2)
    ov_loop = tuple(run[1] for run in ov_runs)
    for n, terminal in enumerate(ov_loop, start=1):
        d.series(terminal, getattr(plc.dio, f"di_{4 + n}")[str(4 + n)], wire=(WHITE, SIGNAL_GAUGE))
    for n, run in enumerate(switches, start=1):
        d.series(
            (supply.x1[LEVEL_POLES[n - 1]].inner, supply.x2[LEVEL_POLES[n - 1]].inner),
            (run[1], run[3]),
            wire=((RD, SIGNAL_GAUGE), (BK, SIGNAL_GAUGE)),
        )
        d.series(run[2], getattr(plc.di, f"di_{n}")[str(n)], wire=(WHITE, SIGNAL_GAUGE))
    for pin in (1, 2):
        d.series(lt01[pin], plc.ai.ai_current_1[pin], wire=(WHITE, SIGNAL_GAUGE))
    for (channel, first), run in zip(((1, 1), (2, 5)), rtds, strict=True):
        for pin in (1, 2, 3):
            d.series(run[pin], getattr(plc.rtd, f"rtd_{channel}")[str(first + pin - 1)], wire=(WHITE, SIGNAL_GAUGE))
    d.series((supply.x1[POLE_PACK].inner, supply.x2[POLE_PACK].inner), (pack[1], pack[2]), wire=((RD, PACK_SUPPLY_GAUGE), (BK, PACK_SUPPLY_GAUGE)))
    return Field(
        ov_loop,
        _terminals(lt01, 2),
        _terminals(rtds[0], 3),
        _terminals(rtds[1], 3),
        _terminals(switches[0], 3),
        _terminals(switches[1], 3),
        _terminals(pack, 2),
    )


def build_estop(d: fr.Design, strings: tuple[String, ...], supply: Supply, plc: Plc) -> Estop:
    with d.function("ESTOP", "Emergency stop"):
        s1 = d.device("S1", typed.PRT38, place="DOOR")
        d.device(None, typed.PRT37, name="head", parent=s1)
        x3 = d.terminal_strip("X3", TERMINAL, interface=True)
        out = x3.run("ESTOP_OUT", 1)[1]
        back = x3.run("ESTOP_BACK", 1)[1]
    d.series(supply.x1[POLE_ESTOP].inner, s1.nc_1, wire=(RD, 0.5))
    d.series(s1.nc_1, out, wire=(WHITE, 0.5))
    d.series(strings[0].j1_plug[3], back, wire=(WHITE, 0.5))
    d.series(supply.x1[POLE_S1_CONTACT_2].inner, s1.nc_2, wire=(RD, SIGNAL_GAUGE))
    d.series(s1.nc_2, plc.di.di_3["3"], wire=(WHITE, SIGNAL_GAUGE))
    return Estop(out, back)


def build_ntcs(d: fr.Design, bdv: Any) -> None:
    for k, (pin_a, pin_b) in enumerate(NTC_PORTS, start=1):
        ntc = d.device(f"NTC-0{k}", NTC)
        d.series(getattr(bdv, f"temp_{k}")[pin_a], ntc.ntc["1"], wire=(WHITE, SIGNAL_GAUGE))
        d.series(getattr(bdv, f"temp_{k}")[pin_b], ntc.ntc["2"], wire=(WHITE, SIGNAL_GAUGE))
