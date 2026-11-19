from __future__ import annotations

from typing import Any, NamedTuple

import fransys as fr

from . import typed
from ._release import REVISION, VERSION

NAME = "dev-pre"
INTERFACE = "1"
TITLE = "Pre board"
NUMBER = "TBD-3"
COIL_CONNECTOR = typed.PRT23
BOARD_PART = typed.PRT35
HV_TERMINAL = typed.PRT03


class Interface(NamedTuple):
    coil: Any
    hv_in: Any
    hv_out: Any


@fr.unit(NAME, version=VERSION, revision=REVISION, interface_version=INTERFACE, title=TITLE, number=NUMBER, date="2026-10-06", text="demo", by="XX")
def build(d: fr.Design) -> Interface:
    coil = d.device("J3", COIL_CONNECTOR, interface=True)
    board = d.device("A1", BOARD_PART)
    hv_in = d.device("HV_IN", HV_TERMINAL, parent=board, interface=True)
    hv_out = d.device("HV_OUT", HV_TERMINAL, parent=board, interface=True)
    return Interface(coil=coil, hv_in=hv_in, hv_out=hv_out)


def documents() -> tuple[fr.Draft, ...]:
    return ()
