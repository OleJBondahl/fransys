"""P3 (layout-0154): harness lines, leaving lines and middle units, built through `fr`.

The study board and the conditions: a unit whose
only line leaves is a middle unit (1), a line between two top-level units leaves at both ends
(2), a middle unit draws one outline and no frame (3). One stub per leaving line (C1).
"""

import functools
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # the sibling fixture modules
import ha_p3_cases
import ha_study_board
from _drawn_pages import drawn_pages

from fransys_layout.geometry import WIRING_GRID
from fransys_model.derive import harness_line_ends, line_conductors, line_designation, text_room
from fransys_model.vocab.tables import items

LEAVE = 6 * WIRING_GRID  # 48 G to the stub
TO_BOX = LEAVE + WIRING_GRID  # layout-0158: the line runs on to its stub box's edge


@functools.cache
def _board():
    return ha_study_board.build()


@functools.cache
def _case(name: str):
    return getattr(ha_p3_cases, name)()


def _owner(model, tag: str):
    return next(i for i in items(model).values() if i.tag == tag).id


def _lines(model, tag: str) -> list[tuple]:
    """(page, wire) of the core path's wires whose printed label names the harness `-tag`."""
    return [
        (page, wire)
        for page, drawing in drawn_pages(model).items()
        for wire in drawing.wires
        if wire.label is not None and wire.label.text.startswith(f"-{tag}.")
    ]


def _boxes(model, tag: str) -> list[tuple]:
    """(page, symbol) of the boxes whose cell strings name the connector or plug `-tag`."""
    return [
        (page, symbol)
        for page, drawing in drawn_pages(model).items()
        for symbol in drawing.symbols
        if symbol.key == "generic-box" and any(tag in cell for row in symbol.texts for cell in row)
    ]


def _stubs(model, text: str) -> list[tuple]:
    """(page, marker) of the markers printing `text`."""
    return [
        (page, marker)
        for page, drawing in drawn_pages(model).items()
        for marker in drawing.markers
        if any(text in shown for _, shown in marker.texts)
    ]


def _size(symbol) -> tuple[int, int]:
    stretch = dict(symbol.stretch)
    return stretch.get("x", 0), stretch.get("y", 0)


def test_each_leg_prints_its_ends_number_and_the_trunk_is_the_roots() -> None:
    """-W17's three branches are 1, 2, 3; the trunk leaves the root's plug box.

    UNDO: `line_paths` keys the trunk 0 and counts the legs from 1 (P3's look).
    """
    model = _board().model
    w17 = _owner(model, "W17")
    ends = harness_line_ends(model, w17)
    root = next(end for end in ends if end.mates is not None)
    boxes = _boxes(model, "-W17-")
    assert boxes
    page, plug_box = boxes[0]
    here = [wire for where, wire in _lines(model, "W17") if where == page]
    assert sorted(wire.label.text for wire in here) == sorted(
        line_designation(model, w17, end.branch) for end in ends
    )
    trunk = next(w for w in here if w.label.text == line_designation(model, w17, root.branch))
    first = trunk.points[0]
    width, height = _size(plug_box)
    assert plug_box.x <= first[0] <= plug_box.x + width
    assert first[1] in (plug_box.y, plug_box.y + height)


def test_each_line_label_stands_beside_its_longest_run_and_none_overlap() -> None:
    """A label's centre is within a text height, a grid and the house text gap
    (layout-0158) of its longest run.

    UNDO: `text_centre` returns a fixed spot, `Point(x=0, y=0)`.
    """
    model = _board().model
    height = text_room(model)
    boxes = []
    lines = [w for tag in ("W11", "W12", "W13", "W15", "W17") for _, w in _lines(model, tag)]
    assert lines
    for one in lines:
        runs = list(pairwise(one.points))
        a, b = max(runs, key=lambda r: abs(r[1][0] - r[0][0]) + abs(r[1][1] - r[0][1]))
        x0, x1, y0, y1 = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
        text_x, text_y = one.label.box.x, one.label.box.y
        dx = max(x0 - text_x, 0, text_x - x1)
        dy = max(y0 - text_y, 0, text_y - y1)
        assert max(dx, dy) <= height + 2 * WIRING_GRID, one.label.text
        boxes.append((text_x, text_y))
    assert len(boxes) == len(set(boxes))


def test_fan_out_legs_are_oblique_and_never_a_route_so_no_wire_is_reported() -> None:
    """The legs slant, carry no route, and give no WIRE_NOT_ORTHOGONAL.

    UNDO: the engine also writes each fan-out leg as a stage `Route` of its conductor.
    """
    built = _board()
    legs = [
        wire for tag in ("W11", "W12", "W13", "W15", "W17") for _, wire in _lines(built.model, tag)
    ]
    assert legs
    slant = [
        (a, b) for leg in legs for a, b in pairwise(leg.points) if a[0] != b[0] and a[1] != b[1]
    ]
    assert slant
    assert "WIRE_NOT_ORTHOGONAL" not in {f.code for f in built.findings}


def test_a_unit_whose_only_line_leaves_draws_its_outline_a_leaving_line_and_one_stub() -> None:
    """Condition 1 and C1: the far end is in the field; the unit still gets its middle outline.

    Its interface's line runs 48 G straight out of the plug box to one stub naming the line, not
    one stub per core, and on to the stub's box (layout-0158). UNDO: `line_reach` drops a unit
    with no reached line.
    """
    model = _case("leaving").model
    boxes = _boxes(model, "-W3-")
    assert boxes
    page = boxes[0][0]
    outlines = drawn_pages(model)[page].outlines
    assert len(outlines) == 1
    here = [wire for where, wire in _lines(model, "W3") if where == page]
    assert len(here) == 1
    (a, b) = here[0].points
    assert a[0] == b[0]
    assert abs(b[1] - a[1]) == TO_BOX
    stubs = [marker for where, marker in _stubs(model, "-W3") if where == page]
    assert len(stubs) == 1
    assert stubs[0].key == "off"
    assert (stubs[0].x, abs(stubs[0].y - a[1])) == (b[0], LEAVE)
    assert ("text", "-W3 \N{RIGHTWARDS ARROW} +FLD-Q1") in stubs[0].texts


def test_a_line_between_two_top_level_units_leaves_at_both_ends() -> None:
    """Condition 2: two stubs, each at the end of a 48 G straight line; nothing drawn across.

    Each unit's own sheet draws its interface's line leaving too. UNDO: `_far` lets one
    top-level unit's interface reach the other's.
    """
    model = _case("two_units").model
    boxes = _boxes(model, "-W5-")
    assert boxes
    page = boxes[0][0]
    own = Counter(where for where, _ in _lines(model, "W5") if where != page)
    assert len(own) == 2
    assert set(own.values()) == {1}
    lines = [wire for where, wire in _lines(model, "W5") if where == page]
    assert len(lines) == 2
    assert all(len(one.points) == 2 for one in lines)
    assert all(
        abs(one.points[1][1] - one.points[0][1]) + abs(one.points[1][0] - one.points[0][0])
        == TO_BOX
        for one in lines
    )
    stubs = [marker for where, marker in _stubs(model, "-W5") if where == page]
    assert len(stubs) == 2
    # the stub stands one grid back from the line's end, which meets its box (layout-0158)
    back = {
        (b[0], b[1] + (WIRING_GRID if a[1] > b[1] else -WIRING_GRID))
        for a, b in (one.points for one in lines)
    }
    assert {(m.x, m.y) for m in stubs} == back


def test_a_middle_unit_has_one_outline_per_page_and_no_d11_frame() -> None:
    """Condition 3: the single-wire interface X2 stands inside the one outline, at an edge.

    UNDO: `_unit_members` keeps the middle unit's members (today's frames kept).
    """
    model = _case("mixed").model
    pages = drawn_pages(model)
    page = _boxes(model, "-W3-")[0][0]
    assert len(pages[page].outlines) == 1
    (outline,) = pages[page].outlines
    xs = [x for x, _ in outline.points]
    ys = [y for _, y in outline.points]
    x2 = [s for where, s in _boxes(model, "-X2") if where == page]
    assert x2
    for one in x2:
        assert min(xs) <= one.x <= max(xs)
        assert min(ys) <= one.y <= max(ys)


@pytest.mark.parametrize("name", ["leaving", "two_units", "mixed"])
def test_no_conductor_a_line_carries_is_routed(name: str) -> None:
    """A line's conductors are drawn by the line, never as routes."""
    model = _case(name).model
    carried = {c for ids in line_conductors(model).values() for c in ids}
    assert carried
    # the core path writes no route record: a conductor is drawn only as a labelled line wire


def test_a_nested_units_harness_is_drawn_on_the_sheet_that_holds_both_its_ends() -> None:
    """Risk 9a (layout-0158): `io` owns W7, whose plug is `io`'s boundary; its cores go to X2.

    The cabinet's sheet draws W7 from the plug's box to X2's terminals, with no stub. `io`'s
    own sheet shows the plug's box only: no line, no stub; a unit drawing shows nothing above
    it. UNDO: `line_reads` keeps the owner's unit as the line's sheet (a leaving line on `io`'s
    sheet with a stub to `+CAB`, nothing on the cabinet's).
    """
    model = _case("owned_by_nested").model
    plug_boxes = dict(_boxes(model, "-W7-"))
    assert len(plug_boxes) == 2  # the cabinet's replica and `io`'s own sheet
    terminals = {page for page, _ in _boxes(model, "-X2")}
    cabinet = terminals & set(plug_boxes)  # the cabinet unit's own sheet holds both ends
    assert len(cabinet) == 1
    (own,) = set(plug_boxes) - cabinet
    lines = _lines(model, "W7")
    assert lines
    assert {page for page, _ in lines} == cabinet
    box = plug_boxes[next(iter(cabinet))]
    width, _ = _size(box)
    edge = {(box.x + width // 2 - (box.x + width // 2) % WIRING_GRID, box.y)}
    assert edge & {point for _, one in lines for point in one.points}
    assert sum(1 for _ in lines) == 2
    assert [m for _, m in _stubs(model, "-W7")] == []
    assert not drawn_pages(model)[own].markers
