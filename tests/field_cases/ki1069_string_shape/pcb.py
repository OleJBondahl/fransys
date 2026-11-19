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
    "J1": typed.PRT24,
    "J2": typed.PRT23,
    "J3": typed.PRT24,
    "J4": typed.PRT24,
    "J5": typed.PRT24,
    "J6": typed.PRT23,
    "J7": typed.PRT26,
    "J8": typed.PRT27,
    "J9": typed.PRT25,
}
FUSES = (("F1", typed.PRT12), ("F2", typed.PRT13))
RELAYS = (("K1", RELAY), ("K2", RELAY), ("K3", RELAY_EMERGENCY_STOP), ("K4", RELAY))
NETS = {
    "V24": ("F1.2", "F2.2", "J5.1", "K4.24", "K4.A1", "J8.8"),
    "GND": ("J1.2", "J8.7", "J9.4", "J3.2", "J4.2", "J5.4", "J6.2", "K3.A2", "K4.11"),
    "V24_IN": ("F1.1", "J1.1"),
    "V24_BDV_CU": ("F2.1", "J8.9"),
    "EM_STOP_IN": ("J1.3", "K3.A1"),
    "HVIL_OK_PLC": ("J2.1", "K4.21"),
    "CONTACTOR_EN_PLC": ("J2.2", "K1.A1", "K2.A1"),
    "Q1_AUX_A": ("J8.10", "J7.3"),
    "Q1_AUX_B": ("J8.12", "J7.4"),
    "Q1_BDV_OUT_NEG": ("J8.1", "K1.14"),
    "Q1_COIL_POS": ("J8.4", "J7.1"),
    "Q1_COIL_NEG": ("K1.11", "J7.2"),
    "Q2_AUX_A": ("J8.11", "J7.7"),
    "Q2_AUX_B": ("J8.13", "J7.8"),
    "Q2_BDV_OUT_NEG": ("J8.2", "K1.24"),
    "Q2_COIL_POS": ("J8.5", "J7.5"),
    "Q2_COIL_NEG": ("K1.21", "J7.6"),
    "PCH_BDV_OUT_POS": ("J8.6", "K2.14"),
    "PCH_BDV_OUT_NEG": ("J8.3", "K2.24"),
    "PCH_COIL_POS": ("J7.9", "K2.11"),
    "PCH_COIL_NEG": ("J7.10", "K2.21"),
    "SYSTEM_CAN_H": ("J9.5", "J3.3", "J4.3"),
    "SYSTEM_CAN_L": ("J9.2", "J3.1", "J4.1"),
    "STRING_CAN_H": ("J9.3", "J5.2"),
    "STRING_CAN_L": ("J9.1", "J5.3"),
    "HVIL_LOOP_RET": ("J6.1", "K4.A2"),
    "COIL_RET_EM_STOP": ("K1.A2", "K2.A2", "K3.14"),
    "COIL_RET_HVIL": ("K3.13", "K4.14"),
}
FED_NETS = ("V24_IN", "GND")
COPPER = (WH, 1)
COPPER_NETS = (*FED_NETS, "V24", "V24_BDV_CU")
NO_CONNECT = ("J1.4", "J9.6", "J3.4", "J4.4", "J8.14")


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
    return getattr(device, function)[int(pin) if tag[0] in "JF" else pin]


def _function(tag: str, pin: str) -> tuple[str, str]:
    if tag.startswith("J"):
        return (CONNECTORS[tag], "header")
    if tag.startswith("F"):
        return (FUSE_HOLDER, "fuse")
    part = dict(RELAYS)[tag]
    if pin in ("A1", "A2"):
        return (part, "coil")
    if tag == "K3":
        return (part, "no")
    return (part, "no_1" if pin in ("11", "14") else "no_2")


def _j1_nets() -> set[str]:
    nets = {n for n, pins in NETS.items() if any(p.startswith("J1.") for p in pins)}
    grown = True
    while grown:
        grown = False
        for net, pins in NETS.items():
            fuses = {p.split(".")[0] for p in pins if p.startswith("F")}
            reached = {p.split(".")[0] for n in nets for p in NETS[n] if p.startswith("F")}
            if net not in nets and fuses & reached:
                nets.add(net)
                grown = True
    return nets


@fr.unit(NAME, version=VERSION, revision=REVISION, interface_version=INTERFACE, title=TITLE, number=NUMBER, date="2026-10-06", text="demo", by="XX")
def build(d: fr.Design) -> Interface:
    d.layout.profile(hide_unused_pins=True)
    board = d.device(None, BOARD_PART, name="board")
    interface = Interface(
        pwr_estop=d.device("J1", typed.PRT24, parent=board, interface=True),
        plc_io=d.device("J2", typed.PRT23, parent=board, interface=True),
        can_in=d.device("J3", typed.PRT24, parent=board, interface=True),
        can_out=d.device("J4", typed.PRT24, parent=board, interface=True),
        current_sensor=d.device("J5", typed.PRT24, parent=board, interface=True),
        hvil=d.device("J6", typed.PRT23, parent=board, interface=True),
        contactors=d.device("J7", typed.PRT26, parent=board, interface=True),
        bdv=d.device("J8", typed.PRT27, parent=board, interface=True),
        bdv_can=d.device("J9", typed.PRT25, parent=board, interface=True),
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
