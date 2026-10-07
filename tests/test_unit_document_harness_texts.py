"""HA-D4 UNITTEXT, acceptance 21: a unit's own document names items unit-locally.

A cabinet unit `demo-cab` (instance `-U1`) holds a nested board unit `demo-board` (`-U2`, header
`-J2`) and a harness `-W5` whose plug mates that header. The bug: the board's own page printed
the header as `-U1-U2-J2`, and the cabinet's page printed `-U1-W5`, `-U1-W5-P5`, `-U1-U2-J2` and the
stub `-W5 <- -U1-T1`, each naming the cabinet's own tag on the cabinet's own document. The rule
(ruling 1, model-0181, layout-0159): every text takes the sheet's unit, so the board's page prints
`-J2` and the cabinet's page `-W5`, `-W5-P5`, `-U2-J2`, `-W5 <- -T1`.

The texts are the `<text>` elements of the written page SVGs, so render's own print is read.
"""

import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model import derive
from fransys_model.layout import DrawingSet, Page, layout_of


class _Io(NamedTuple):
    J2: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    pcb = u.device("U2", "DEMO-PCB-IO")
    j2 = u.device("J2", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    k1 = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.wire(j2[1], k1["1"], wire=(BK, 0.5))
    u.wire(j2[2], k1["2"], wire=(BK, 0.5))
    return _Io(j2)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cabinet(u: Any) -> _Io:
    board = u.add(_board, "U2")
    psu = u.device("T1", "DEMO-PSU-24")
    u.dc_supply("S", psu)
    harness = u.harness("W5")
    plug = u.device("P5", "DEMO-HSG-4M", parent=harness, contacts="DEMO-CRIMP-M")
    u.mate(plug, board.J2)
    u.wire(plug[1], psu.output["+"], wire=(BK, 0.5))
    u.wire(plug[2], psu.output["-"], wire=(BK, 0.5))
    return _Io(board.J2)


class _Written(NamedTuple):
    board: list[str]
    cabinet: list[str]


@pytest.fixture(scope="module")
def written() -> _Written:
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts")
    d.add(_cabinet, "U1", place=None)
    (root / "cabinet.md").write_text("# Cabinet\n", encoding="utf-8")
    (root / "board.md").write_text("# Board\n", encoding="utf-8")
    result = fr.build(
        d,
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=root / "cabinet.md"),
        fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-board", cover=root / "board.md"),
    )
    assert [f for f in result.findings if f.severity.name == "ERROR"] == []
    fr.write(result, root / "out", intermediates=root / "inter")
    model = result.model
    names = {derive.unit_release(model, u).name: u for u in derive.units(model)}
    sets = layout_of(model, DrawingSet)

    def texts(name: str) -> list[str]:
        found: list[str] = []
        for page in layout_of(model, Page).values():
            if sets[page.drawing_set].unit == names[name]:
                svg = (root / "inter" / f"layout.page-{page.id.value}.svg").read_text("utf-8")
                found += re.findall(r">([^<>]+)</text>", svg)
        return found

    return _Written(texts("demo-board"), texts("demo-cab"))


def test_the_boards_own_document_names_no_ancestor_tag(written: _Written) -> None:
    assert "-J2" in written.board  # positive half: the header box prints unit-locally
    assert [t for t in written.board if "U1" in t or "-U2" in t] == []


def test_the_cabinets_own_document_does_not_print_its_own_tag(written: _Written) -> None:
    assert {"-W5", "-W5-P5", "-U2-J2", "-W5 ← -T1"} <= set(written.cabinet)
    assert [t for t in written.cabinet if "U1" in t] == []
