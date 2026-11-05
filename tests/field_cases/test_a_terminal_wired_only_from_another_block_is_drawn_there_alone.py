"""Field case: a part-less external strip, made in its own function block, is wired on its outer side to a box in another block.
The bug: the strip's page drew its four terminals bare, and the parent's black box drew them unwired, as loose terminal symbols.
Fixed by layout-0214, a terminal symbol stands only where a wire meets it, and an empty block or page is not drawn."""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import aspect_nodes

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}


class _Io(NamedTuple):
    X2: Any


@fr.unit("demo-strip-block", text="first", by="AB", **_REL)
def _unit(u: Any) -> _Io:
    with u.function("STRING", "String") as string:
        a1 = u.device("A1", "DEMO-IO-CLAMPS")
    with u.function("JB", "Junction box") as jb:
        x2 = u.terminal_strip("X2", None, 4, external=True, interface=True)
        for n in range(1, 5):
            u.series(x2[n].outer, a1.clamps[str(n)], wire=(BU, 0.5))
    u.layout.order(jb, string)
    return _Io(x2)


class _Built(NamedTuple):
    result: fr.BuildResult
    source: str


@cache
def built() -> _Built:
    """Built in the tests' bodies, so a build error is a test FAILURE, not a fixture error."""
    root = Path(tempfile.mkdtemp())
    design = fr.design("demo_parts")
    design.add(_unit, "U1", place=None)
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-strip-block", cover=root / "c.md")
    result = fr.build(design, doc)
    fr.write(result, root / "out", intermediates=root / "im")
    return _Built(result, next((root / "im").glob("*.typ")).read_text(encoding="utf-8"))


def test_the_build_raises_nothing_and_has_no_error() -> None:
    assert [f.code for f in built().result.findings if f.severity.name == "ERROR"] == []


def test_no_page_draws_the_strips_block() -> None:
    model = built().result.model
    strip_block = next(a.id for a in aspect_nodes(model).values() if a.key[-1] == "JB")
    string = next(a.id for a in aspect_nodes(model).values() if a.key[-1] == "STRING")
    drawn = [{g.group for g in p.groups} for p in layout_of(model, Page).values() if any(g.group == strip_block for g in p.groups)]
    assert drawn == [{strip_block, string}], "the strip's terminals stand on the card's page and its title names them (R958), no page of its own"


def test_the_parent_draws_nothing() -> None:
    model = built().result.model
    sets = layout_of(model, DrawingSet)
    unit_ids = {s.unit for s in sets.values()}
    assert {s.unit for p in layout_of(model, Page).values() for s in [sets[p.drawing_set]]} == (unit_ids - {None})


def test_each_terminal_stands_once_on_the_page_of_its_wire() -> None:
    drawings = list(drawn_pages(built().result.model).values())
    stood = [(d, one) for d in drawings for one in d.symbols if one.key == "terminal"]
    assert len(stood) == 4
    for drawing, terminal in stood:
        assert any(t.text.endswith("-A1") for t in drawing.texts), "the page of the box device"
        assert any(abs(x - terminal.x) + abs(y - terminal.y) <= 24 for wire in drawing.wires for x, y in (wire.points[0], wire.points[-1]))


def test_the_terminal_table_lists_the_strip() -> None:
    assert "X2" in built().source
