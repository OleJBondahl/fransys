"""Field case: a nested unit's breaker pole feeds a row of one-changeover relays; a control relay coil joins an input card on another page.
The bug (v0.22.5): DRAWING_SHORTS_NETS per relay column, WIRE_THROUGH_BODY; fixed by layout-0446 (R1816, R1818); el-0120 (KI-732) drew no loop.
KI-736 (layout-0516, R1861): the second reference-marker leg starts at the trunk end, no dangling end."""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK, BN, BU, RD, WH

_CTRL, _ZERO, _MAINS = (WH, 0.5), (BK, 0.5), (BU, 0.75)
_RELAYS = ("K31", "K32", "K33", "K34", "K35", "K36")


class _Io(NamedTuple):
    pass


def _starters(d: Any) -> tuple[Any, ...]:
    out = {}
    for tag, brk, ctr, ovl, opts in (
        ("G3", "F11", "Q21", "F15", {}),
        ("G4", "F12", "Q22", "F16", {}),
        ("G2", "F13", "Q23", "F17", {"interface": ("coil", "aux_nc")}),
    ):
        with d.function(tag, f"Block {tag}"):
            d.device(brk, "DEMO-MCB-3P")
            out[tag] = (d.device(ctr, "DEMO-CTR-3P-NC", **opts), d.device(ovl, "DEMO-OVERLOAD-3P"))
    return out["G3"], out["G4"], out["G2"]


def _supply(d: Any, feed: Any, zero: Any) -> Any:
    with d.function("G7", "Block G7"):
        f4 = d.device("F31", "DEMO-MCB-2P-C2")
        psu = d.device("G1", "DEMO-PSU-24")
        d.series(f4.main, (psu.input["L"], psu.input["N"]), wire=((BN, 2.5), (BU, 2.5)))
        dc = d.dc_supply("24VDC", plus=psu.output["+"], minus=psu.output["-"], voltage=24, names=("24V", "GND"))
        d.series(dc.plus, feed[4], wire=(RD, 2.5))
        d.series(dc.minus, zero[1], wire=(BK, 2.5))
    return f4


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Cabinet", number="1")
def _cab(d: Any) -> _Io:
    zero = d.terminal_strip("XB", "DEMO-TB-2.5", 19, bridged=True, rail=True)
    feed = d.terminal_strip("XA", "DEMO-TB-FUSE-2.5", 29, bridged=True)
    (q1, _), (q2, f6), (q3, f7) = _starters(d)
    with d.function("G2", "Block G2"):
        sensor = d.device("B1", "DEMO-PROX-PNP")
        d.series(feed[2].outer, sensor.power, wire=_CTRL)
        d.series(sensor.power, zero[2], wire=_ZERO)
    f4 = _supply(d, feed, zero)
    with d.function("G8", "Block G8"):
        f8 = d.device("F32", "DEMO-MCB-2P-C2")
        d.series((f4.main["1"], f4.main["3"]), f8.main, wire=((BN, 0.75), (BU, 0.75)))
    with d.function("G6", "Block G6"):
        rack = d.rack("R1")
    with d.function("G5", "Block G5"):
        card = d.device("A1", "DEMO-PLC-DI-16", parent=rack, position=2)
    with d.function("G8", "Block G8"):
        for tag in _RELAYS:
            d.series(f8.main["4"], d.device(tag, "DEMO-RLY-2CO-24").co_1["11"], wire=_MAINS)
    with d.function("G1", "Block G1"):
        k1, run, stop = d.device("K11", "DEMO-RLY-4CO-24"), d.device("S11", "DEMO-PB-NO"), d.device("S12", "DEMO-PB-NC")
    with d.function("G3", "Block G3"):
        sel1, lamp1 = d.device("S21", "DEMO-PB-NO"), d.device("H21", "DEMO-LAMP-24")
    with d.function("G4", "Block G4"):
        sel2, lamp2 = d.device("S22", "DEMO-PB-NO"), d.device("H22", "DEMO-LAMP-24")
    with d.function("G1", "Block G1"):
        d.series(feed[7].outer, stop.sw, d.parallel(q1.coil, q2.coil, q3.coil), wire=_CTRL)
        d.series(feed[4].outer, run.sw, k1.coil, wire=_CTRL)
        d.series(k1.coil, zero[4], wire=_ZERO)
        d.series(k1.coil["A1"], card.di_7, wire=_CTRL)
        d.series(q1.coil, k1.co_1["12"], sel1.sw, wire=_CTRL)
    with d.function("G3", "Block G3"):
        d.series(sel1.sw, zero[5], wire=_ZERO)
        d.series(feed[8].outer, q1.aux, lamp1.lamp, wire=_CTRL)
        d.series(lamp1.lamp, zero[16], wire=_ZERO)
        d.series(feed[20].outer, q1.aux_nc, card.di_1, wire=_CTRL)
    with d.function("G1", "Block G1"):
        d.series(q2.coil, k1.co_2["22"], sel2.sw, wire=_CTRL)
    with d.function("G4", "Block G4"):
        d.series(sel2.sw, zero[15], wire=_ZERO)
        d.series(feed[18].outer, q2.aux, lamp2.lamp, wire=_CTRL)
        d.series(lamp2.lamp, zero[17], wire=_ZERO)
        d.series(feed[9].outer, q2.aux_nc, card.di_2, wire=_CTRL)
        d.series(feed[12].outer, f6.aux, card.di_5, wire=_CTRL)
    with d.function("G2", "Block G2"):
        d.series(feed[10].outer, q3.aux_nc, card.di_3, wire=_CTRL)
        d.series(feed[13].outer, f7.aux, card.di_6, wire=_CTRL)
    return _Io()


@fr.unit("demo-top", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Top", number="2")
def _top(u: Any) -> _Io:
    u.add(_cab, "N1")
    return _Io()


@cache
def _codes() -> frozenset[str]:
    d = fr.design("demo_parts")
    d.add(_top, "S1")
    return frozenset(f.code for f in fr.build(d, unit_document("demo-top")).findings if f.severity is fr.Severity.ERROR)


def test_the_relay_row_draws_no_shorted_nets_and_no_wire_through_a_body() -> None:
    assert _codes() == frozenset()
