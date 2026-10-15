"""Field case: a strip supplied by others is marked "by others" in the unit's own documents.

The engineering shape: a cabinet unit holds two relays `K1` and `K2`, a part-less terminal strip
`X90` supplied by others (`external=True`, the customer's strip in this cabinet), one wire from
`X90:1` to a coil, and a 4-core cable `W1` from `X90:2` and `X90:3` to the two coils. The unit
gets a cabinet schematic with its block diagram, and a harness drawing.

The bug: only the system document marked an external item. The unit's schematic drew `X90`'s
terminals as plain symbols, its block diagram a solid box and its cable drawing a solid end box,
so the cabinet drawings showed the customer's strip as ours.

Rule (OUTLINES BO1 to BO4): every symbol of an external item a schematic page draws gets a dashed
outline, one per run, with one "by others" note per item and page. The unit's block diagram and
cable drawing mark the item as the system document does.
"""

import tempfile
from functools import cache
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

from fransys_layout.geometry import Box, overlaps, symbol_geometry, translate
from fransys_model import layout
from fransys_model.derive.drawing_text import external_note, label_text
from fransys_model.layout import (
    CableBlock,
    DiagramBox,
    EndBox,
    EndStyle,
    HarnessFanOut,
    HarnessLine,
    Label,
    Route,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import items


class _Open(NamedTuple):
    pass


@fr.unit("demo-ext", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _ext(u: Any) -> _Open:
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    k2 = u.device("K2", "DEMO-RLY-2CO-24")
    x90 = u.terminal_strip("X90", None, 3, external=True)
    u.detail.wire(x90[1].outer, k1.coil["A1"], wire=("WH", 0.5))
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=2)
    cable.core(1, x90[2].outer, k1.coil["A2"])
    cable.core(2, x90[3].outer, k2.coil["A1"])
    return _Open()


@cache
def _built() -> fr.BuildResult:
    """Built in the tests' bodies, so a build error is a test FAILURE, not a fixture error."""
    root = Path(tempfile.mkdtemp())
    (root / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    (root / "looms.md").write_text("# Looms\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.location("CAB", "Cabinet")
    d.add(_ext, "U1", place="CAB")
    schematic = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        "demo-ext",
        cover=root / "cover.md",
        add=(fr.PageKind.BLOCK_DIAGRAM,),
    )
    looms = fr.document(fr.DocumentPreset.HARNESS_DRAWING, "demo-ext", cover=root / "looms.md")
    return fr.build(d, schematic, looms)


def _strip_functions() -> set[Any]:
    """The functions of `X90`'s terminals."""
    model = _built().model
    strip = next(i.id for i in items(model).values() if i.tag == "X90")
    terminals = {i.id for i in items(model).values() if i.parent == strip}
    return {f.id for f in fr.derive.functions(model).values() if f.item in terminals}


def test_the_strips_terminals_stand_in_dashed_outlines_with_one_note() -> None:
    """Each terminal is inside an outline, no other symbol is, and the strip has one note."""
    model = _built().model
    outlines = list(layout_of(model, layout.ExternalOutline).values())
    assert outlines
    strip = _strip_functions()

    def inside(s: SymbolPlacement) -> bool:
        return any(
            o.page == s.page and o.x <= s.x <= o.x + o.width and o.y <= s.y <= o.y + o.height
            for o in outlines
        )

    placements = layout_of(model, SymbolPlacement).values()
    assert [s.function in strip for s in placements if inside(s)] == [True] * 3
    notes = [lb for lb in layout_of(model, Label).values() if lb.slot == "external_note"]
    assert len(notes) == 1
    assert label_text(model, notes[0]) == external_note()


def test_the_unit_block_diagram_dashes_the_strip() -> None:
    """The unit's block diagram draws `X90` as a dashed box."""
    boxes = layout_of(_built().model, DiagramBox).values()
    assert sum(box.dashed for box in boxes) == 1


def test_the_cable_end_box_of_the_strip_is_dashed() -> None:
    """In the unit's own cable block the end box of `X90` is dashed; the relays' are not."""
    model = _built().model
    in_unit = {b.id for b in layout_of(model, CableBlock).values() if b.unit is not None}
    styles = [e.style for e in layout_of(model, EndBox).values() if e.block in in_unit]
    assert styles.count(EndStyle.DASHED) == 1


def test_no_outline_box_holds_a_foreign_symbol() -> None:
    """BO6: the strip's terminals stand in two chain columns; a run is cut where K2 falls inside."""
    model = _built().model
    strip = _strip_functions()
    outlines = [
        (o.page, Box(x=o.x, y=o.y, width=o.width, height=o.height))
        for o in layout_of(model, layout.ExternalOutline).values()
    ]
    foreign = [
        (
            s.page,
            translate(
                symbol_geometry(s.symbol, poles=s.poles, orientation=s.orientation).body,
                dx=s.x,
                dy=s.y,
            ),
        )
        for s in layout_of(model, SymbolPlacement).values()
        if s.function not in strip
    ]
    assert foreign
    assert [(p, q) for p, o in outlines for r, q in foreign if p == r and overlaps(o, q)] == []


def _edges(box: Box) -> list[tuple[int, int, int, int]]:
    """A box's four edges as segments (x1, y1, x2, y2)."""
    right, bottom = box.x + box.width, box.y + box.height
    return [
        (box.x, box.y, right, box.y),
        (box.x, bottom, right, bottom),
        (box.x, box.y, box.x, bottom),
        (right, box.y, right, bottom),
    ]


def _lies_on(one: tuple[int, int, int, int], two: tuple[int, int, int, int]) -> bool:
    """Whether two orthogonal segments share a line and a stretch of positive length."""
    (ax, ay, bx, by), (cx, cy, dx, dy) = one, two
    if ax == bx == cx == dx:
        return min(max(ay, by), max(cy, dy)) > max(min(ay, by), min(cy, dy))
    if ay == by == cy == dy:
        return min(max(ax, bx), max(cx, dx)) > max(min(ax, bx), min(cx, dx))
    return False


def _segments(lines: list[tuple[Any, Any]]) -> list[tuple[Any, tuple[int, int, int, int]]]:
    """Each polyline's segments (x1, y1, x2, y2), by page."""
    return [(page, (a.x, a.y, b.x, b.y)) for page, points in lines for a, b in pairwise(points)]


def _routes(model: Any) -> list[tuple[Any, tuple[int, int, int, int]]]:
    """Every routed wire's segments by page."""
    return _segments([(r.page, r.points) for r in layout_of(model, Route).values()])


def _cables(model: Any) -> list[tuple[Any, tuple[int, int, int, int]]]:
    """Every harness line's and fan-out leg's segments by page."""
    lines = [(h.page, h.points) for h in layout_of(model, HarnessLine).values()]
    lines += [
        (f.page, leg.points) for f in layout_of(model, HarnessFanOut).values() for leg in f.legs
    ]
    return _segments(lines)


def test_no_outline_edge_lies_on_a_wire_or_a_symbol_body_edge() -> None:
    """BO6-SHRINK: an outline edge never lies on a wire, nor on a symbol body's edge.

    -X90:1's tag ends at 188 and the gap puts its edge at 192, where W1's trunk ran; the routers
    now refuse a run along an outline by others, so the trunk moves off it.
    """
    model = _built().model
    bodies = [
        (
            s.page,
            translate(
                symbol_geometry(s.symbol, poles=s.poles, orientation=s.orientation).body,
                dx=s.x,
                dy=s.y,
            ),
        )
        for s in layout_of(model, SymbolPlacement).values()
    ]
    marks = (
        _routes(model)
        + _cables(model)
        + [(page, edge) for page, box in bodies for edge in _edges(box)]
    )
    outlines = layout_of(model, layout.ExternalOutline).values()
    edges = [
        (o.page, e)
        for o in outlines
        for e in _edges(Box(x=o.x, y=o.y, width=o.width, height=o.height))
    ]
    assert edges
    assert [(e, s) for p, e in edges for q, s in marks if p == q and _lies_on(e, s)] == []


def test_no_harness_line_runs_along_a_routed_wire() -> None:
    """BO6-SHRINK: W1's trunk, moved off -X90:1's outline, never runs along the K1 to X90:1 wire."""
    model = _built().model
    wires = _routes(model)
    assert wires
    assert [(c, w) for p, c in _cables(model) for q, w in wires if p == q and _lies_on(c, w)] == []


# BO6-SHRINK ratchet: harness lines drawn at tier 2 (along an outline by others); may only fall
_TIER_TWO_LINES = 0


def test_the_lines_along_an_outline_by_others_only_fall() -> None:
    """BO6-SHRINK: a line runs along an outline only where tier 1 found no path; ratchet, never up.

    Measured 0 over every field case's build (2026-10-14).
    """
    model = _built().model
    sides = [
        (o.page, e)
        for o in layout_of(model, layout.ExternalOutline).values()
        for e in _edges(Box(x=o.x, y=o.y, width=o.width, height=o.height))
    ]
    lines = [(h.page, h.points) for h in layout_of(model, HarnessLine).values()]
    along = [
        points
        for page, points in lines
        if any(
            p == page and _lies_on((a.x, a.y, b.x, b.y), e)
            for a, b in pairwise(points)
            for p, e in sides
        )
    ]
    assert len(along) <= _TIER_TWO_LINES
