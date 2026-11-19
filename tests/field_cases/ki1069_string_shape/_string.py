from __future__ import annotations

from typing import Any, Literal, NamedTuple

from fransys.colours import BK, GNYE, RD, WH
lazy import fransys as fr

from . import pcb as board_unit
from . import pre as pre_unit
from . import typed
from ._field import build_ntcs
lazy from ._supply import Supply

CONTACTOR = typed.PRT04
FUSE = typed.PRT11
SENSOR = typed.PRT05
BDV = typed.PRT39
HVCONN_POS = typed.PRT09
HVCONN_NEG = typed.PRT10
HOUSING = {
    "pwr_estop": typed.PRT19,
    "plc_io": typed.PRT18,
    "can_in": typed.PRT19,
    "can_out": typed.PRT19,
    "current_sensor": typed.PRT19,
    "hvil": typed.PRT18,
    "contactors": typed.PRT21,
    "bdv_can": typed.PRT20,
    "bdv": typed.PRT22,
}
PCH_COIL_HOUSING = typed.PRT18
BOARD_POLES = (1, 8, 2, 9)
POWER_GAUGE = 0.5
SIGNAL_GAUGE = 0.25
CHASSIS_GAUGE = 0.35
WHITE = WH
CONTACTOR_PINS = (("coil", "X1"), ("coil", "X2"), ("aux", "T1"), ("aux", "T2"))
SENSOR_PINS: tuple[Literal["6", "7", "8", "9"], ...] = ("6", "7", "8", "9")
BDV_CAN_PINS = (("can2", "CAN2L"), ("can1", "CAN1L"), ("can2", "CAN2H"), ("can1", "CAN1GND"), ("can1", "CAN1H"))
BDV_J8_PINS = (
    ("relay_1", "OUT1-"),
    ("relay_2", "OUT2-"),
    ("relay_3", "OUT3-"),
    ("relay_1", "OUT1+"),
    ("relay_2", "OUT2+"),
    ("relay_3", "OUT3+"),
    ("supply_control", "SGND"),
    ("supply_pro", "F24V"),
    ("supply_control", "S24V"),
    ("dci_1", "IN1A"),
    ("dci_2", "IN2A"),
    ("dci_1", "IN1B"),
    ("dci_2", "IN2B"),
)
PLC_CAN_PINS: tuple[Literal["X4_2", "X4_3", "X4_7"], ...] = ("X4_2", "X4_3", "X4_7")


class String(NamedTuple):
    string_pos: Any
    string_neg: Any
    cmu_link: Any
    bdv: Any
    j1_plug: Any
    j2_plug: Any
    can_in: Any
    can_out: Any | None


def _plug(d: fr.Design, child: fr.Device | fr.Fn, part: Any, name: str) -> Any:
    plug = d.device(None, part, name=name)
    d.mate(plug, child)
    return plug


def build_string(d: fr.Design, n: int, supply: Supply, dc_pos: fr.Terminal, dc_neg: fr.Terminal, *, last: bool) -> String:  # noqa: PLR0913 invented shape copied as is
    with d.function(f"S{n}", f"String {n}"):
        return _string(d, n, supply, dc_pos, dc_neg, last=last)


def _string(d: fr.Design, n: int, supply: Supply, dc_pos: fr.Terminal, dc_neg: fr.Terminal, *, last: bool) -> String:  # noqa: PLR0913 invented shape copied as is
    pcb = d.add(board_unit.build, f"JDB{n}")
    if last:
        d.unused(pcb.can_out)
    pch = d.add(pre_unit.build, f"PCH{n}")
    q_pos = d.device(f"Q{2 * n - 1}", CONTACTOR)
    q_neg = d.device(f"Q{2 * n}", CONTACTOR)
    sensor = d.device(f"CS{n}", SENSOR)
    bdv = d.device(f"BDV{n}", BDV, interface=("J5",))
    string_pos = d.device(None, HVCONN_POS, name=f"string_pos{n}", interface=True)
    string_neg = d.device(None, HVCONN_NEG, name=f"string_neg{n}", interface=True)
    f_pos = d.device(f"F{2 * n}", FUSE)
    f_neg = d.device(f"F{2 * n + 1}", FUSE)
    d.detail.busbar(string_pos.main["internal"], f_pos.fuse["1"])
    d.detail.busbar(f_pos.fuse["2"], q_pos.main["A1"])
    d.detail.busbar(q_pos.main["A2"], dc_pos.inner)
    d.detail.busbar(f_pos.fuse["2"], pch.hv_in.terminal["external"])
    d.detail.busbar(pch.hv_out.terminal["external"], dc_pos.inner)
    d.detail.busbar(string_neg.main["internal"], f_neg.fuse["1"])
    d.detail.busbar(f_neg.fuse["2"], sensor.current_path["HIGH"])
    d.detail.busbar(sensor.current_path["LOW"], q_neg.main["A1"])
    d.detail.busbar(q_neg.main["A2"], dc_neg.inner)
    d.series(supply.pe_bar[n], sensor.main["1"], wire=(GNYE, CHASSIS_GAUGE))
    plugs = {field: _plug(d, getattr(pcb, field), part, f"kx{n}_{field}") for field, part in HOUSING.items() if not (field == "can_out" and last)}
    pole = BOARD_POLES[n - 1]
    d.series(
        (supply.x1[pole].inner, supply.x2[pole].inner), (plugs["pwr_estop"][1], plugs["pwr_estop"][2]), wire=((RD, POWER_GAUGE), (BK, POWER_GAUGE))
    )
    for pin, sensor_pin in enumerate(SENSOR_PINS, start=1):
        d.series(plugs["current_sensor"][pin], sensor.main[sensor_pin], wire=(WHITE, SIGNAL_GAUGE))
    d.series(plugs["hvil"][2], string_pos.hvil["hvil_internal"], wire=(WHITE, POWER_GAUGE))
    d.series(string_neg.hvil["hvil_internal"], plugs["hvil"][1], wire=(WHITE, POWER_GAUGE))
    for offset, contactor in ((0, q_pos), (4, q_neg)):
        for index, (function, port) in enumerate(CONTACTOR_PINS, start=1):
            d.series(plugs["contactors"][offset + index], getattr(contactor, function)[port], wire=(WHITE, POWER_GAUGE))
    coil = _plug(d, pch.coil, PCH_COIL_HOUSING, f"pch{n}_coil")
    d.series(plugs["contactors"][9], coil[1], wire=(WHITE, POWER_GAUGE))
    d.series(plugs["contactors"][10], coil[2], wire=(WHITE, POWER_GAUGE))
    for pin, (function, port) in enumerate(BDV_CAN_PINS, start=1):
        d.series(plugs["bdv_can"][pin], getattr(bdv, function)[port], wire=(WHITE, SIGNAL_GAUGE))
    for pin, (function, port) in enumerate(BDV_J8_PINS, start=1):
        d.series(plugs["bdv"][pin], getattr(bdv, function)[port], wire=(WHITE, SIGNAL_GAUGE))
    if n == 1:
        build_ntcs(d, bdv)
    return String(
        string_pos=string_pos,
        string_neg=string_neg,
        cmu_link=bdv.J5,
        bdv=bdv,
        j1_plug=plugs["pwr_estop"],
        j2_plug=plugs["plc_io"],
        can_in=plugs["can_in"],
        can_out=plugs.get("can_out"),
    )


def wire_plc_can(d: fr.Design, strings: tuple[String, ...], plc: Any) -> None:
    for pin, plc_pin in zip((1, 2, 3), PLC_CAN_PINS, strict=True):
        d.series(strings[0].can_in[pin], plc.X4[plc_pin], wire=(WHITE, SIGNAL_GAUGE))
