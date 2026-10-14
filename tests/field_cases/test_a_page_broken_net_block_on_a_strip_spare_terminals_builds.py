"""Field case: a page-broken block holding only a net on two spare terminals of a strip.

The engineering shape: one series made outside any block runs from a DC supply through a fuse,
a contact and a coil-and-lamp pair to terminal strip X7. A block F2 holds only a signal net on
two spare terminals of X7, and the block starts a new page (`break_before`).

The bug: `fr.build` raised `KeyError` in `fransys_layout` `write/placements.py::_at`. The copies of
the X7 terminals drawn on the broken page are keyed by the cell they stand at, and that cell is an
item (the strip), but the key lookup read function ids only. Dropping the net or the page break
made it build. Found by the fuzz study 2026-10-14 (C1). Fixing decision: layout-0248.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cab(u: fr.Design) -> _Io:
    g1 = u.device("G1", "DEMO-PSU-24")
    dc = u.dc_supply("24VDC", g1.output)
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 6, interface=True)
    x7 = u.terminal_strip("X7", "DEMO-TB-2.5", 8)
    f1 = u.device("F1", "DEMO-FUSE-DC-160")
    s1 = u.device("S1", "DEMO-CTR-BLOCK-1NO1NC")
    k1 = u.device("K1", "DEMO-CTR-LEADS")
    h1 = u.device("H1", "DEMO-LAMP-24")
    u.series(dc.plus, f1.element, s1.no, u.parallel(k1.coil, h1.lamp), x7, dc.minus, wire=0.75)
    with u.function("F2", "Signal") as grp:
        u.net("SIG", x7[7], x7[8], kind=fr.SIGNAL)
    u.layout.break_before(grp)
    return _Io(x1)


def test_a_page_broken_net_block_on_a_strip_spare_terminals_builds(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover))
