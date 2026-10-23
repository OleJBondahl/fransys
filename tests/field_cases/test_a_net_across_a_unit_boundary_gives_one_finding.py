"""Field case: an enclosure unit nests a board unit whose connector is an interface, and a
`d.detail.net` joins the interface pin to an enclosure receptacle.

The bug: a declared net does not cross a unit boundary (only conductors and mates do), so the
build answers with a cascade, `BOUNDARY_UNCONNECTED`, `NET_SHORTED` and `NET_UNREALISED`, none of
which says the cause or the fix.

Fixed by layout-0322: one `NET_ACROSS_UNIT_BOUNDARY` ERROR per such net names the net, the
boundary pin and the fix (`d.detail.wire(a, b, wire=...)`); the three cascade findings are
not reported for that net.
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
    u.detail.net("EXT_A", io.J1["1"], x1["1"], kind=fr.SIGNAL)
    return _Io(x1)


def _findings(tmp_path: Path) -> tuple[fr.Finding, ...]:
    d = fr.design("demo_parts")
    d.add(_encl, "E1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Enclosure\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-encl", cover=cover)
    return tuple(fr.check(fr.build(d, doc)))


def test_one_error_names_the_net_the_boundary_pin_and_detail_wire(tmp_path: Path) -> None:
    found = [f for f in _findings(tmp_path) if f.code == "NET_ACROSS_UNIT_BOUNDARY"]
    assert len(found) == 1
    assert found[0].severity is fr.Severity.ERROR
    assert "EXT_A" in found[0].message
    assert "J1" in found[0].message
    assert "d.detail.wire" in found[0].fix


def test_the_cascade_is_not_reported_for_that_net(tmp_path: Path) -> None:
    codes = {f.code for f in _findings(tmp_path)}
    assert "NET_ACROSS_UNIT_BOUNDARY" in codes
    assert not codes & {"BOUNDARY_UNCONNECTED", "NET_SHORTED", "NET_UNREALISED"}
