"""P3 (layout-0154): harness lines, leaving lines and middle units, built through `fr`.

The study board (acceptance 17, 18, Part 2a's 6) and the designer's P3 conditions: a unit whose
only line leaves is a middle unit (1), a line between two top-level units leaves at both ends
(2), a middle unit draws one outline and no D11 frame (3). One stub per leaving line (C1).
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

from fransys_layout.geometry import WIRING_GRID
from fransys_model.derive import harness_line_ends, line_conductors, line_designation
from fransys_model.derive.drawing_text import off_stub_text
from fransys_model.layout import (
    ConnectorBox,
    HarnessFanOut,
    HarnessLine,
    LinkMarker,
    Outline,
    Route,
    StarKind,
    SymbolPlacement,
    default_profile,
    layout_of,
)
from fransys_model.vocab.tables import boundaries, functions, items

LEAVE = 6 * WIRING_GRID  # HL18: 48 G to the stub
TO_BOX = LEAVE + WIRING_GRID  # layout-0158: the line runs on to its stub box's edge


@functools.cache
def _board():
    return ha_study_board.build()


@functools.cache
def _case(name: str):
    return getattr(ha_p3_cases, name)()


def _owner(model, tag: str):
    return next(i for i in items(model).values() if i.tag == tag).id


def _lines(model, harness) -> list[HarnessLine]:
    return [one for one in layout_of(model, HarnessLine).values() if one.harness == harness]


def _plug_page(model, tag: str):
    """The page the harness plug `tag`'s box stands on: the drawing the line is drawn across."""
    plug = next(f.id for f in functions(model).values() if items(model)[f.item].tag == tag)
    return next(b.page for b in layout_of(model, ConnectorBox).values() if b.function == plug)


def _line_stubs(model) -> list[LinkMarker]:
    return [m for m in layout_of(model, LinkMarker).values() if "line_stub" in m.key]


def test_each_leg_prints_its_ends_number_and_the_trunk_is_the_roots() -> None:
    """Acceptance 18: -W17's three branches are 1, 2, 3; the trunk leaves the root's plug box.

    UNDO: `line_paths` keys the trunk 0 and counts the legs from 1 (P3's look).
    """
    model = _board().model
    w17 = _owner(model, "W17")
    ends = harness_line_ends(model, w17)
    root = next(end for end in ends if end.mates is not None and _is_interface(model, end.mates))
    plug_box = next(b for b in layout_of(model, ConnectorBox).values() if b.function == root.plug)
    here = [one for one in _lines(model, w17) if one.page == plug_box.page]
    assert sorted(one.branch for one in here) == [end.branch for end in ends]
    trunk = next(one for one in here if one.branch == root.branch)
    first = trunk.points[0]
    assert plug_box.x <= first.x <= plug_box.x + plug_box.width
    assert first.y in (plug_box.y, plug_box.y + plug_box.height)
    assert line_designation(model, w17, trunk.branch) == f"-W17.{root.branch}"


def _is_interface(model, function) -> bool:
    return any(b.function == function for b in boundaries(model).values())


def test_each_line_label_stands_beside_its_longest_run_and_none_overlap() -> None:
    """Acceptance 17: a label's centre is within a text height, a grid and the house text gap
    (layout-0158) of its longest run.

    UNDO: `text_centre` returns a fixed spot, `Point(x=0, y=0)`.
    """
    model = _board().model
    height = default_profile().text_height
    boxes = []
    for one in layout_of(model, HarnessLine).values():
        points = [(p.x, p.y) for p in one.points]
        runs = list(pairwise(points))
        a, b = max(runs, key=lambda r: abs(r[1][0] - r[0][0]) + abs(r[1][1] - r[0][1]))
        x0, x1, y0, y1 = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
        dx = max(x0 - one.text_x, 0, one.text_x - x1)
        dy = max(y0 - one.text_y, 0, one.text_y - y1)
        assert max(dx, dy) <= height + 2 * WIRING_GRID, (one.harness, one.branch)
        boxes.append((one.text_x, one.text_y))
    assert len(boxes) == len(set(boxes))


def test_fan_out_legs_are_oblique_and_never_a_route_so_no_wire_is_reported() -> None:
    """Part 2a acceptance 6: the legs slant, carry no route, and give no WIRE_NOT_ORTHOGONAL.

    UNDO: the engine also writes each fan-out leg as a stage `Route` of its conductor.
    """
    built = _board()
    model = built.model
    legs = [leg for fan in layout_of(model, HarnessFanOut).values() for leg in fan.legs]
    assert legs
    slant = [(a, b) for leg in legs for a, b in pairwise(leg.points) if a.x != b.x and a.y != b.y]
    assert slant
    carried = {leg.conductor for leg in legs}
    assert not {r.conductor for r in layout_of(model, Route).values()} & carried
    assert "WIRE_NOT_ORTHOGONAL" not in {f.code for f in built.findings}


def test_a_unit_whose_only_line_leaves_draws_its_outline_a_leaving_line_and_one_stub() -> None:
    """Condition 1 and C1: the far end is in the field; the unit still gets its middle outline.

    Its interface's line runs 48 G straight out of the plug box to one stub naming the line, not
    one stub per core, and on to the stub's box (layout-0158). UNDO: `line_reach` drops a unit
    with no reached line (P2b).
    """
    model = _case("leaving").model
    w3 = _owner(model, "W3")
    x1 = next(f.id for f in functions(model).values() if items(model)[f.item].tag == "X1")
    page = _plug_page(model, "W3P1")
    box = next(
        b for b in layout_of(model, ConnectorBox).values() if (b.function, b.page) == (x1, page)
    )
    outlines = [o for o in layout_of(model, Outline).values() if o.page == box.page]
    assert len(outlines) == 1
    here = [one for one in _lines(model, w3) if one.page == box.page]
    assert len(here) == 1
    (a, b) = here[0].points
    assert a.x == b.x
    assert abs(b.y - a.y) == TO_BOX
    stubs = [m for m in _line_stubs(model) if m.page == box.page]
    assert len(stubs) == 1
    assert stubs[0].star is StarKind.OFF
    assert stubs[0].carrier == w3
    assert (stubs[0].x, abs(stubs[0].y - a.y)) == (b.x, LEAVE)
    assert off_stub_text(model, stubs[0]) == "-W3 → +FLD-Q1"


def test_a_line_between_two_top_level_units_leaves_at_both_ends() -> None:
    """Condition 2: two stubs, each at the end of a 48 G straight line; nothing drawn across.

    Each unit's own sheet draws its interface's line leaving too. UNDO: `_far` lets one
    top-level unit's interface reach the other's.
    """
    model = _case("two_units").model
    w5 = _owner(model, "W5")
    page = _plug_page(model, "P1")
    own = Counter(one.page for one in _lines(model, w5) if one.page != page)
    assert len(own) == 2
    assert set(own.values()) == {1}
    lines = [one for one in _lines(model, w5) if one.page == page]
    assert len(lines) == 2
    assert all(len(one.points) == 2 for one in lines)
    assert all(
        abs(one.points[1].y - one.points[0].y) + abs(one.points[1].x - one.points[0].x) == TO_BOX
        for one in lines
    )
    stubs = [m for m in _line_stubs(model) if m.carrier == w5 and m.page == page]
    assert len(stubs) == 2
    # the stub stands one grid back from the line's end, which meets its box (layout-0158)
    back = {
        (b.x, b.y + (WIRING_GRID if a.y > b.y else -WIRING_GRID))
        for a, b in (one.points for one in lines)
    }
    assert {(m.x, m.y) for m in stubs} == back


def test_a_middle_unit_has_one_outline_per_page_and_no_d11_frame() -> None:
    """Condition 3: the single-wire interface X2 stands inside the one outline, at an edge.

    UNDO: `_unit_members` keeps the middle unit's members (today's D11 frames kept).
    """
    model = _case("mixed").model
    outlines = Counter(o.page for o in layout_of(model, Outline).values())
    page = _plug_page(model, "W3P1")
    assert outlines[page] == 1
    (outline,) = (o for o in layout_of(model, Outline).values() if o.page == page)
    x2 = [
        s
        for s in layout_of(model, SymbolPlacement).values()
        if s.page == page and items(model)[functions(model)[s.function].item].tag == "X2"
    ]
    assert x2
    for one in x2:
        assert outline.x <= one.x <= outline.x + outline.width
        assert outline.y <= one.y <= outline.y + outline.height


@pytest.mark.parametrize("name", ["leaving", "two_units", "mixed"])
def test_no_conductor_a_line_carries_is_routed(name: str) -> None:
    """HL1: a line's conductors are drawn by the line, never as routes."""
    model = _case(name).model
    carried = {c for ids in line_conductors(model).values() for c in ids}
    assert carried
    assert not {r.conductor for r in layout_of(model, Route).values()} & carried


def test_a_nested_units_harness_is_drawn_on_the_sheet_that_holds_both_its_ends() -> None:
    """Risk 9a (layout-0158): `io` owns W7, whose plug is `io`'s boundary; its cores go to X2.

    The cabinet's sheet draws W7 from the plug's box to X2's terminals, with no stub. `io`'s
    own sheet shows the plug's box only: no line, no stub; a unit drawing shows nothing above
    it. UNDO: `line_reads` keeps the owner's unit as the line's sheet (a leaving line on `io`'s
    sheet with a stub to `+CAB`, nothing on the cabinet's).
    """
    model = _case("owned_by_nested").model
    w7 = _owner(model, "W7")
    plug = next(f.id for f in functions(model).values() if items(model)[f.item].tag == "W7P1")
    x2 = {f.id for f in functions(model).values() if "X2" in items(model)[f.item].key}
    terminals = {p.page for p in layout_of(model, SymbolPlacement).values() if p.function in x2}
    plug_boxes = {b.page: b for b in layout_of(model, ConnectorBox).values() if b.function == plug}
    assert len(plug_boxes) == 2  # the cabinet's replica and `io`'s own sheet
    cabinet = terminals & set(plug_boxes)  # the cabinet unit's own sheet holds both ends
    assert len(cabinet) == 1
    (own,) = set(plug_boxes) - cabinet
    lines = _lines(model, w7)
    assert lines
    assert {one.page for one in lines} == cabinet
    box = plug_boxes[next(iter(cabinet))]
    edge = {(box.x + box.width // 2 - (box.x + box.width // 2) % WIRING_GRID, box.y)}
    assert edge & {(p.x, p.y) for one in lines for p in one.points}
    fans = [f for f in layout_of(model, HarnessFanOut).values() if f.harness == w7]
    assert {f.page for f in fans} == cabinet
    assert sum(len(f.legs) for f in fans) == 2
    assert [m for m in _line_stubs(model) if m.carrier == w7] == []
    assert [m for m in layout_of(model, LinkMarker).values() if m.page == own] == []
