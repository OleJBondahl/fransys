"""Field case: a terminal wired only from another function block stands there alone (layout-0214).

The engineering shape: a unit holds a part-less external strip `X2` of four terminals, made in
its own function block `JB`. Every terminal is wired on its outer side to a four-port box device
`A1` in a second block `STRING`. `order` and `break_before` put the strip's block on a page of
its own. The unit is added to a design that wires nothing to it.

The bug: the page of the strip's block draws the four terminals bare, and the parent's black box
draws them unwired: loose terminal symbols.

The rule (decision layout-0214): a terminal symbol stands only where a wire meets it. A block or
box left with nothing is not drawn, and an empty page is not emitted. The terminal table keeps
every terminal.
"""

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
            u.detail.wire(x2[n].outer, a1.clamps[str(n)], wire=(BU, 0.5))
    u.layout.order(jb, string)
    for group in (jb, string):
        u.layout.break_before(group)
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
    return _Built(result, (root / "im" / "c.typ").read_text(encoding="utf-8"))


def test_the_build_raises_nothing_and_has_no_error() -> None:
    assert [f.code for f in built().result.findings if f.severity.name == "ERROR"] == []


def test_no_page_draws_the_strips_block() -> None:
    model = built().result.model
    strip_block = next(a.id for a in aspect_nodes(model).values() if a.key[-1] == "JB")
    drawn = [
        p for p in layout_of(model, Page).values() if any(g.group == strip_block for g in p.groups)
    ]
    assert drawn == []


def test_the_parent_draws_nothing() -> None:
    model = built().result.model
    sets = layout_of(model, DrawingSet)
    unit_ids = {s.unit for s in sets.values()}
    assert {s.unit for p in layout_of(model, Page).values() for s in [sets[p.drawing_set]]} == (
        unit_ids - {None}
    )


def test_each_terminal_stands_once_on_the_page_of_its_wire() -> None:
    drawings = list(drawn_pages(built().result.model).values())
    stood = [(d, one) for d in drawings for one in d.symbols if one.key == "terminal"]
    assert len(stood) == 4
    for drawing, terminal in stood:
        assert any(t.text.endswith("-A1") for t in drawing.texts), "the page of the box device"
        assert any(
            abs(x - terminal.x) + abs(y - terminal.y) <= 24
            for wire in drawing.wires
            for x, y in (wire.points[0], wire.points[-1])
        )


def test_the_terminal_table_lists_the_strip() -> None:
    assert "X2" in built().source
