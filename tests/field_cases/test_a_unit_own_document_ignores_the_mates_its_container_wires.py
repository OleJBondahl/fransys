"""Field case: a board's own document is the same with or without the container that wires it.

The engineering shape: a board unit with two four-pin headers is released alone. A cabinet unit
then nests it and wires each header through a harness plug (`d.mate`), the plugs' wires running
to a PLC output module in the cabinet.

The bug: the board's own document drew its headers as connector boxes wired across the page. The
"connector at a harness line's end" fact counted the cabinet's lines, which mate the board's
headers from outside, so the board's own drawing read what lies above it. A unit's drawing knows
only what is below it (owner 2026-09-24).

The rule: the board's own document is byte-identical to the one built without the cabinet. The
cabinet's own document still draws the lines.

The decision that fixes it: P7.4 (layout-0295 records the bar). Layout-0295 already drops the
pins only the container wires; the box stays until boxing is per document.
"""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr
import pytest
from fransys.colours import RD, WH


class _Io(NamedTuple):
    J1: fr.Device
    J2: fr.Device


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


@fr.unit(
    "demo-board",
    revision=1,
    interface_version=1,
    date="2026-10-16",
    text="first",
    by="XX",
    title="Board",
    number="B-1",
)
def _board(u: fr.Design) -> _Io:
    pcb = u.device("U9", "DEMO-PCB-IO")
    j1 = u.device("J1", "DEMO-CONN-4P", parent=pcb, interface=True)
    j2 = u.device("J2", "DEMO-CONN-4P", parent=pcb, interface=True)
    u.detail.wire(j1["1"], j2["2"], wire=(WH, 0.5))
    u.detail.wire(j1["3"], j2["4"], wire=(WH, 0.5))
    return _Io(j1, j2)


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    date="2026-10-16",
    text="first",
    by="XX",
    title="Cabinet",
    number="C-1",
)
def _cabinet(u: fr.Design) -> _Open:
    with u.function("G0", "PLC"):
        out = u.device("K1", "DEMO-PLC-DO-16P")
    board = u.add(_board, "U2")
    w4, w5 = u.harness("W4"), u.harness("W5")
    p1 = u.device("J1", "DEMO-CONN-4P", parent=w4)
    p2 = u.device("J2", "DEMO-CONN-4P", parent=w5)
    u.mate(p1, board.J1)
    u.mate(p2, board.J2)
    u.detail.wire(p1["1"], out.do_1["1"], wire=(WH, 0.5))
    u.detail.wire(p1["2"], out.do_2["2"], wire=(WH, 0.5))
    u.detail.wire(p1["3"], out.power["0V"], wire=(WH, 0.5))
    u.detail.wire(out.power["24V"], p2["1"], wire=(RD, 0.5))
    u.detail.wire(out.do_3["3"], p2["2"], wire=(WH, 0.5))
    u.detail.wire(out.do_4["4"], p2["3"], wire=(WH, 0.5))
    return _Open()


def _own_pdf(*, container: bool, tmp: Path) -> bytes:
    cover = tmp / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    d = fr.design("demo_parts")
    docs = []
    if container:
        d.add(_cabinet, "U1")
        docs.append(fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cabinet", cover=cover))
    else:
        d.add(_board, "U2")
    docs.append(fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-board", cover=cover))
    files = fr.write(fr.build(d, *docs), tmp / ("in" if container else "alone"), unit="demo-board")
    (pdf,) = (f for f in files if f.suffix == ".pdf")
    return pdf.read_bytes()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "P7.4: a unit's own document is byte-identical whatever contains it; "
        "the container still boxes the nested header (0155)"
    ),
)
def test_the_board_own_document_is_byte_identical_inside_a_container() -> None:
    with tempfile.TemporaryDirectory() as name:
        tmp = Path(name)
        assert _own_pdf(container=True, tmp=tmp) == _own_pdf(container=False, tmp=tmp)
