"""Field case: a unit holds a board with mounted parts and a second top-level device, and the
board's parts are joined by two `d.detail.net`s.

The bug: the board is then an opaque black box (layout-0044), so its internal nets are dropped
with no finding, and when nothing else in the unit is drawn the build stops on `LAYOUT_MISSING`
with no hint of the cause. A consumer reads it as "my nets vanished".

Fixed by layout-0322: one `BOARD_NETS_NOT_DRAWN` WARNING per board names the board, every
dropped net and the fix (make the board its own unit's only top-level device); `LAYOUT_MISSING`
names the board and points at the new code.
"""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr


class _Io(NamedTuple):
    J1: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-18", text="first", by="XX")
def _board(u: fr.Design) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    u.device("H9", "DEMO-LAMP-24")
    j1 = u.device("J1", "DEMO-CONN-2P", parent=pcb)
    j2 = u.device("J2", "DEMO-CONN-2P", parent=pcb)
    h1 = u.device("H1", "DEMO-LAMP-24", parent=pcb)
    u.detail.net("SIG_A", j1["1"], h1["1"], kind=fr.SIGNAL)
    u.detail.net("SIG_B", j1["2"], h1["2"], j2["1"], kind=fr.SIGNAL)
    return _Io(j1)


def _findings(tmp_path: Path) -> tuple[fr.Finding, ...]:
    d = fr.design("demo_parts")
    d.add(_board, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Board\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-board", cover=cover)
    return tuple(fr.check(fr.build(d, doc)))


def test_one_warning_per_board_names_the_board_the_nets_and_the_fix(tmp_path: Path) -> None:
    found = [f for f in _findings(tmp_path) if f.code == "BOARD_NETS_NOT_DRAWN"]
    assert len(found) == 1
    assert found[0].severity is fr.Severity.WARNING
    assert "A1" in found[0].message
    assert "SIG_A" in found[0].message
    assert "SIG_B" in found[0].message
    assert "only top-level device" in found[0].fix


def test_layout_missing_names_the_board_and_the_new_code(tmp_path: Path) -> None:
    missing = [f for f in _findings(tmp_path) if f.code == "LAYOUT_MISSING"]
    assert len(missing) == 1
    assert "A1" in missing[0].message
    assert "BOARD_NETS_NOT_DRAWN" in missing[0].message
