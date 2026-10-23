"""Field case: a motor in the plant room, fed from a cabinet unit, is drawn on a printed page.

The engineering shape: a cabinet unit U1 with an outgoing terminal strip X1, and a motor M1 in
the plant room (a top-level location) on a cable from X1. The one document is the cabinet's.

The bug (R311): the motor is laid out as drawing set 1 (the plant room, no unit) and gets a page,
but `document_drawing_sets` gives a unit document only the sets of its own unit, so no document
prints that page. On the old engine the motors stood on the cabinet's schematic pages. Fixed by
R316 (decision model-0360): a unit document prints the sets of the top-level items its strips feed.
"""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
from fransys.colours import WH

from fransys_model.derive import document_drawing_sets, printed_drawing_sets
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import documents


class _Io(NamedTuple):
    out: fr.TerminalStrip


@fr.unit("demo-mini-mcc", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cabinet(c: fr.Design) -> _Io:
    x = c.terminal_strip("X1", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5", interface=True)
    c.earth(x.run("PE", 1)[1])
    return _Io(x)


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="PLANT")
    d.location("PLANT", "Plant room")
    strip = d.add(_cabinet, "U1", place=None)
    m = d.device("M1", "DEMO-MOTOR-4KW")
    cable = d.cable("W11", "DEMO-CBL-4G1.5", length_m=25)
    d.series(strip.out, cable, m.motor, wire=2.5)
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, "demo-mini-mcc", cover=tmp_path / "c.md"))


def test_a_motor_outside_the_cabinet_is_drawn_on_a_printed_page(tmp_path: Path) -> None:
    model = _build(tmp_path).model
    pages = layout_of(model, Page).values()
    drawn = {p.drawing_set for p in pages}
    printed = {s.id for s in printed_drawing_sets(model)}
    unprinted = [s.number for s in layout_of(model, DrawingSet).values() if s.id in drawn - printed]
    assert unprinted == [], f"drawing sets with a page that no document prints: {unprinted}"


def test_the_fed_motor_gives_no_unprinted_set_warning(tmp_path: Path) -> None:
    findings = _build(tmp_path).findings
    assert [f.code for f in findings if f.code == "UNPRINTED_SET"] == []


def test_a_motor_no_unit_feeds_gives_the_unprinted_set_warning(tmp_path: Path) -> None:
    d = fr.design("demo_parts", place="PLANT")
    d.location("PLANT", "Plant room")
    d.location("FIELD", "Field")
    strip = d.add(_cabinet, "U1", place=None)
    m = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(strip.out, d.cable("W11", "DEMO-CBL-4G1.5", length_m=25), m.motor, wire=2.5)
    a = d.device("M2", "DEMO-MOTOR-4KW", place="FIELD")
    b = d.device("M3", "DEMO-MOTOR-4KW", place="FIELD")
    d.series(a.motor, d.cable("W12", "DEMO-CBL-4G1.5", length_m=5), b.motor, wire=2.5)
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, "demo-mini-mcc", cover=tmp_path / "c.md"))
    (found,) = [f for f in result.findings if f.code == "UNPRINTED_SET"]
    assert found.severity is fr.Severity.WARNING
    assert "M2" in found.message
    assert "Add a document for" in found.message


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


class _Board(NamedTuple):
    J1: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-16", text="x", by="XX")
def _board(u: fr.Design) -> _Board:
    pcb = u.device("U9", "DEMO-PCB-IO")
    j1 = u.device("J1", "DEMO-CONN-4P", parent=pcb, interface=True)
    j2 = u.device("J2", "DEMO-CONN-4P", parent=pcb)
    u.detail.wire(j1["1"], j2["2"], wire=(WH, 0.5))
    return _Board(j1)


@fr.unit("demo-outer", revision=1, interface_version=1, date="2026-10-16", text="x", by="XX")
def _outer(u: fr.Design) -> _Open:
    board = u.add(_board, "U2")
    plug = u.device("J1", "DEMO-CONN-4P", parent=u.harness("W4"))
    u.mate(plug, board.J1)
    u.detail.wire(plug["1"], u.device("K1", "DEMO-PLC-DO-16P").do_1["1"], wire=(WH, 0.5))
    return _Open()


def test_a_nested_unit_with_its_own_document_is_printed_by_that_document_alone(
    tmp_path: Path,
) -> None:
    d = fr.design("demo_parts")
    d.add(_outer, "U1")
    (tmp_path / "c.md").write_text("# Cover\n", encoding="utf-8")
    cover = tmp_path / "c.md"
    outer = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-outer", cover=cover)
    inner = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-board", cover=cover)
    built = fr.build(d, outer, inner)
    model = built.model
    printed = [s.id for doc in documents(model) for s in document_drawing_sets(model, doc)]
    assert printed
    assert len(printed) == len(set(printed))
