"""Field case: an enclosure unit nests a board unit whose connector is an interface. A
`d.detail.net` named EXT_A joins the interface pin to an enclosure receptacle, and a wire joins
that same pin to a receptacle on a differently named net OTHER.

The bug: `NET_ACROSS_UNIT_BOUNDARY` replaced the whole `NET_SHORTED` check for a physical net that
holds a net across a boundary, so a real short between two named nets was hidden.

Fixed by layout-0322: the crossing finding replaces only the cascade an unrealised net causes.
`NET_SHORTED` still fires when two differently named nets meet, boundary or not.
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
    u.detail.wire(j1["1"], h1["1"], wire=(BK, 0.75))
    return _Io(j1)


@fr.unit("demo-encl", revision=1, interface_version=1, date="2026-10-18", text="first", by="XX")
def _encl(u: fr.Design) -> _Io:
    io = u.add(_board, "U1")
    x1 = u.device("X1", "DEMO-CONN-2P")
    x2 = u.device("X2", "DEMO-CONN-2P")
    u.detail.net("EXT_A", io.J1["1"], x1["1"], kind=fr.SIGNAL)
    u.detail.net("OTHER", x2["1"], kind=fr.SIGNAL)
    u.detail.wire(io.J1["1"], x2["1"], wire=(BK, 0.75))
    return _Io(x1)


def _codes(tmp_path: Path) -> set[str]:
    d = fr.design("demo_parts")
    d.add(_encl, "E1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Enclosure\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-encl", cover=cover)
    return {f.code for f in fr.check(fr.build(d, doc))}


def test_two_differently_named_nets_meeting_across_a_boundary_are_shorted(tmp_path: Path) -> None:
    codes = _codes(tmp_path)
    assert "NET_ACROSS_UNIT_BOUNDARY" in codes
    assert "NET_SHORTED" in codes
