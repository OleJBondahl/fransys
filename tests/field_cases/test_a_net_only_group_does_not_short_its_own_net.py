"""Field case: a board unit's parts are joined by `d.detail.net`s alone, with no conductor, and
the board is the unit's only top-level device so its nets are drawn.

The bug: a net with no conductor has no realised net, so `DRAWING_SHORTS_NETS` keys each pin as its
own owner and reads the ink of one net, where two runs touch, as two nets joined. No drawing
joins two nets.

Fixed by layout-0322: the ink owner is the declared net group when no realised net exists.
"""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr


class _Io(NamedTuple):
    J1: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-18", text="first", by="XX")
def _board(u: fr.Design) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    j1 = u.device("J1", "DEMO-CONN-2P", parent=pcb)
    h1 = u.device("H1", "DEMO-LAMP-24", parent=pcb)
    j2 = u.device("J2", "DEMO-CONN-2P", parent=pcb)
    u.detail.net("SIG_A", j1["1"], h1["1"], kind=fr.SIGNAL)
    u.detail.net("SIG_B", j1["2"], h1["2"], j2["1"], kind=fr.SIGNAL)
    return _Io(j1)


def test_no_drawing_shorts_nets_on_net_only_groups(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_board, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Board\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-board", cover=cover)
    codes = {f.code for f in fr.check(fr.build(d, doc))}
    assert "DRAWING_SHORTS_NETS" not in codes
