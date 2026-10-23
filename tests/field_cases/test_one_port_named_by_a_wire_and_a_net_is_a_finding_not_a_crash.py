"""Field case: a board unit joins two of its parts with a `d.detail.net`, one end being an
interface pin, and the enclosure unit wires that same pin to a receptacle with `d.detail.wire`.

The bug: the pin is then named by a net group and by a conductor with different physical nets,
and layout raises `LayoutError` ("one port of one function is named with two different physical
nets"), which ends the build with a traceback.

Fixed by layout-0322: a `PORT_IN_NET_AND_WIRE` WARNING names the port and both nets and the fix,
and the build continues without the second name.
"""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
from fransys.colours import BK


class _Io(NamedTuple):
    J1: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-18", text="first", by="XX")
def _board(u: fr.Design) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    j1 = u.device("J1", "DEMO-CONN-2P", parent=pcb, interface=True)
    h1 = u.device("H1", "DEMO-LAMP-24", parent=pcb)
    u.detail.net("SIG_A", j1["1"], h1["1"], kind=fr.SIGNAL)
    return _Io(j1)


@fr.unit("demo-encl", revision=1, interface_version=1, date="2026-10-18", text="first", by="XX")
def _encl(u: fr.Design) -> _Io:
    io = u.add(_board, "U1")
    x1 = u.device("X1", "DEMO-CONN-2P")
    u.detail.wire(io.J1["1"], x1["1"], wire=(BK, 0.75))
    return _Io(x1)


def test_the_build_reports_the_port_and_continues(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_encl, "E1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Enclosure\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-encl", cover=cover)
    found = [f for f in fr.check(fr.build(d, doc)) if f.code == "PORT_IN_NET_AND_WIRE"]
    assert len(found) == 1
    assert "J1" in found[0].message
    assert "d.detail.wire" in found[0].fix
