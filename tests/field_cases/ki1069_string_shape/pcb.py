from __future__ import annotations

from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import WH

from . import typed
from ._release import REVISION, VERSION

NAME = "dev-board"
INTERFACE = "1"
HERE = Path(__file__).parent
TITLE = "Board"
NUMBER = "TBD-2"
BOARD_PART = typed.PRT06
RELAY = typed.PRT36
RELAY_EMERGENCY_STOP = typed.PRT14
FUSE_HOLDER = typed.PRT28
CONNECTORS = {
    "X1": typed.PRT24,
    "X2": typed.PRT23,
    "X3": typed.PRT24,
    "X4": typed.PRT24,
    "X5": typed.PRT24,
    "X6": typed.PRT23,
    "X7": typed.PRT26,
    "X8": typed.PRT27,
    "X9": typed.PRT25,
}
FUSES = (("F1", typed.PRT12), ("F2", typed.PRT13))
RELAYS = (("K1", RELAY), ("K2", RELAY), ("K3", RELAY_EMERGENCY_STOP), ("K4", RELAY))
NETS = {
    "V24": ("F1.2", "F2.2", "X5.1", "K4.24", "K4.A1", "X8.8"),
    "GND": ("X1.2", "X8.7", "X9.4", "X3.2", "X4.2", "X5.4", "X6.2", "K3.A2", "K4.11"),
    "V24_IN": ("F1.1", "X1.1"),
    "V24_BDV_CU": ("F2.1", "X8.9"),
    "EM_STOP_IN": ("X1.3", "K3.A1"),
    "HVIL_OK_PLC": ("X2.1", "K4.21"),
    "CONTACTOR_EN_PLC": ("X2.2", "K1.A1", "K2.A1"),
    "Q1_AUX_A": ("X8.10", "X7.3"),
    "Q1_AUX_B": ("X8.12", "X7.4"),
    "Q1_BDV_OUT_NEG": ("X8.1", "K1.14"),
    "Q1_COIL_POS": ("X8.4", "X7.1"),
    "Q1_COIL_NEG": ("K1.11", "X7.2"),
    "Q2_AUX_A": ("X8.11", "X7.7"),
    "Q2_AUX_B": ("X8.13", "X7.8"),
    "Q2_BDV_OUT_NEG": ("X8.2", "K1.24"),
    "Q2_COIL_POS": ("X8.5", "X7.5"),
    "Q2_COIL_NEG": ("K1.21", "X7.6"),
    "PCH_BDV_OUT_POS": ("X8.6", "K2.14"),
    "PCH_BDV_OUT_NEG": ("X8.3", "K2.24"),
    "PCH_COIL_POS": ("X7.9", "K2.11"),
    "PCH_COIL_NEG": ("X7.10", "K2.21"),
    "SYSTEM_CAN_H": ("X9.5", "X3.3", "X4.3"),
    "SYSTEM_CAN_L": ("X9.2", "X3.1", "X4.1"),
    "STRING_CAN_H": ("X9.3", "X5.2"),
    "STRING_CAN_L": ("X9.1", "X5.3"),
    "HVIL_LOOP_RET": ("X6.1", "K4.A2"),
    "COIL_RET_EM_STOP": ("K1.A2", "K2.A2", "K3.14"),
    "COIL_RET_HVIL": ("K3.13", "K4.14"),
}
FED_NETS = ("V24_IN", "GND")
COPPER = (WH, 1)
COPPER_NETS = (*FED_NETS, "V24", "V24_BDV_CU")


class Interface(NamedTuple):
    pwr_estop: Any
    plc_io: Any
    can_in: Any
    can_out: Any
    current_sensor: Any
    hvil: Any
    contactors: Any
    bdv: Any
    bdv_can: Any


type Placed = Any


def _pin(device: Placed, tag: str, pin: str):
    _part, function = _function(tag, pin)
    return getattr(device, function)[int(pin) if tag[0] in "XF" else pin]


def _function(tag: str, pin: str) -> tuple[str, str]:
    if tag.startswith("X"):
        return (CONNECTORS[tag], "header")
    if tag.startswith("F"):
        return (FUSE_HOLDER, "fuse")
    part = dict(RELAYS)[tag]
    if pin in ("A1", "A2"):
        return (part, "coil")
    if tag == "K3":
        return (part, "no")
    return (part, "no_1" if pin in ("11", "14") else "no_2")


@fr.unit(NAME, version=VERSION, revision=REVISION, interface_version=INTERFACE, title=TITLE, number=NUMBER, date="2026-10-06", text="demo", by="XX")
def build(d: fr.Design) -> Interface:
    d.layout.profile(hide_unused_pins=True)
    board = d.device(None, BOARD_PART, name="board")
    interface = Interface(
        pwr_estop=d.device("X1", typed.PRT24, parent=board, interface=True),
        plc_io=d.device("X2", typed.PRT23, parent=board, interface=True),
        can_in=d.device("X3", typed.PRT24, parent=board, interface=True),
        can_out=d.device("X4", typed.PRT24, parent=board, interface=True),
        current_sensor=d.device("X5", typed.PRT24, parent=board, interface=True),
        hvil=d.device("X6", typed.PRT23, parent=board, interface=True),
        contactors=d.device("X7", typed.PRT26, parent=board, interface=True),
        bdv=d.device("X8", typed.PRT27, parent=board, interface=True),
        bdv_can=d.device("X9", typed.PRT25, parent=board, interface=True),
    )
    devices: dict[str, Placed] = dict(zip(CONNECTORS, interface, strict=True))
    for tag, link in FUSES:
        holder = d.device(tag, FUSE_HOLDER, parent=board)
        d.device(None, link, name=f"link_{tag}", parent=holder)
        devices[tag] = holder
    for tag, part in RELAYS:
        devices[tag] = d.device(tag, part, parent=board)
    for net, pins in NETS.items():
        ports = [_pin(devices[tag], tag, pin) for tag, pin in (p.split(".") for p in pins)]
        if net in COPPER_NETS:
            for a, b in pairwise(ports):
                d.detail.busbar(a, b)
        if net not in FED_NETS:
            d.series(*ports, wire=COPPER)
    return interface


def documents() -> tuple[fr.Draft, ...]:
    return (fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, NAME, cover=HERE / "documents" / "cabinet_schematic.md"),)
