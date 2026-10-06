"""Field case: a unit's own instance tag stays out of its own document and exports.

The engineering shape: a cabinet unit, instance `U1`, holds an I/O board unit, instance `U2`,
and a PLC rack. The board's relay drives one of the rack's output channels, and the cabinet's
own relay drives another.

The bug: the cabinet's own drawings printed the board's boundary texts as `-U1-U2-J1:1`, and its
own WAGO xml named the channels `U1_K2_RUN` and `U1_U2_K1_RUN`. The cabinet's own instance tag
leaked into its own document, because the black box's tag texts and the rack's channel names did
not take the unit they are printed for.

The rule (UT2, "a unit knows only below"): the cabinet's own document prints the board as
`-U2-J1:1` and names the channels `K2_RUN` and `U2_K1_RUN`; the system's document keeps `-U1-U2`.

The decision that fixes it: model-0142.
"""

import re
import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import system_document
from fransys.colours import BU

from fransys_model.derive.drawing_text import label_text
from fransys_model.layout import DrawingSet, Label, Page, layout_of


class _Io(NamedTuple):
    J1: Any
    K1: Any


class _Cab(NamedTuple):
    X1: Any


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    root = u.device("U9", "DEMO-PCB-IO")
    j1 = u.device("J1", "DEMO-CONN-2P", parent=root, interface=True)
    return _Io(j1, u.device("K1", "DEMO-RLY-2CO-24", parent=root))


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Cab:
    rack = u.device("R1", "DEMO-PCB-IO")
    u.device("DO1", "DEMO-PLC-DO-2", name="do", parent=rack, position=1)
    board = u.add(_board, "U2")
    plug = u.device("P1", "DEMO-CONN-2P")
    u.mate(plug, board.J1)
    own = u.device("K2", "DEMO-RLY-2CO-24")
    board.K1.coil.plc(fr.DO, "BOARD_RUN", priority=1)
    own.coil.plc(fr.DO, "OWN_RUN", priority=2)
    u.wire(plug["1"], own.coil["A1"], wire=(BU, 0.5))
    return _Cab(u.device("X1", "DEMO-CONN-2P", interface=True))


@cache
def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.project(title="Tag", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-05", text="First issue", created="XX")
    d.location("C1", "Cabinet")
    d.add(_cab, "U1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    own = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover)
    return fr.build(d, own, system_document())


def _texts(model: fr.Model, release: str | None) -> list[str]:
    """The label texts of the drawing sets of the unit release `release`, or of the system."""
    sets = layout_of(model, DrawingSet)
    pages = layout_of(model, Page)

    def of(label: Label) -> str | None:
        unit = sets[pages[label.page].drawing_set].unit
        return None if unit is None else fr.derive.unit_release(model, unit).name

    return [label_text(model, la) for la in layout_of(model, Label).values() if of(la) == release]


def test_the_own_document_prints_the_board_without_the_cabinet_tag() -> None:
    texts = _texts(_build().model, "demo-cab")
    assert "-U2-J1:1" in texts
    assert [t for t in texts if t.startswith("-U1")] == []


def test_the_system_document_still_prints_the_cabinet_tag() -> None:
    assert "-U1-X1:1" in _texts(_build().model, None)


def test_the_own_wago_xml_names_no_channel_after_the_cabinet_tag(tmp_path: Path) -> None:
    files = fr.write(_build(), tmp_path, unit="demo-cab")
    xml = next(f for f in files if f.suffix == ".xml").read_text(encoding="utf-8")
    names = re.findall(r'Name="([A-Z0-9_]+)"', xml)
    assert "U2_K1_BOARD_RUN" in names
    assert [n for n in names if n.startswith("U1_")] == []
