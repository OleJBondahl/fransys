"""The geometric lint sees harness ink (layout-0158): lines, legs, line labels, stubs, boxes.

Each case is one construct the study board's page 2 drew unseen after P3 (the designer's
defect 3): a connector box over a symbol and a label, a line label over a box text and a label,
a leg over a terminal's point label, a line along the outline's bottom edge, and a stub over the
frame (defect 1).
"""

from samples import SHEET, hid, page_plan, placed

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.lint import HarnessInk, lint_geometry
from fransys_layout.lint._harness import through
from fransys_layout.lint.codes import (
    LINE_ON_OUTLINE,
    OUT_OF_CONTENT_BOX,
    TEXT_OVERLAP,
    WIRE_OVER_LABEL,
    WIRE_THROUGH_SYMBOL,
)
from fransys_layout.stages import (
    LabelKind,
    Layout,
    PlacedLabel,
    Route,
    RoutePoint,
)
from fransys_layout.stages.connector_boxes import PlacedConnectorBox
from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLeg, DrawnLine, LineStub
from fransys_layout.stages.types import PlacedOutline

HARNESS = hid("item", 7)
BOX = hid("function", 9)
UNIT = hid("unit", 3)


def _layout(*, functions=(), labels=(), routes=(), outlines=()) -> Layout:
    return Layout(
        pages=(page_plan(("a",)),),
        placed=functions,
        routes=routes,
        decisions=(),
        markers=(),
        labels=labels,
        outlines=outlines,
    )


def _label(subject: int, box: Box) -> PlacedLabel:
    return PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", subject),
        slot="tag",
        drawing_set=1,
        page=1,
        box=box,
    )


def _box(box: Box, function=BOX) -> PlacedConnectorBox:
    return PlacedConnectorBox(function=function, drawing_set=1, page=1, box=box, texts=(), cells=())


_FAR = Box(x=600, y=600, width=8, height=8)


def _line(points: tuple[Point, ...], label: Box = _FAR) -> DrawnLine:
    return DrawnLine(
        harness=HARNESS,
        branch=1,
        drawing_set=1,
        page=1,
        points=points,
        text=Point(x=label.x + label.width // 2, y=label.y + label.height // 2),
        label=label,
    )


def _fan(*legs: tuple[Point, ...]) -> DrawnFanOut:
    return DrawnFanOut(
        harness=HARNESS,
        branch=2,
        drawing_set=1,
        page=1,
        at=legs[0][0],
        legs=tuple(DrawnLeg(conductor=hid("conductor", n), points=p) for n, p in enumerate(legs)),
    )


def _stub(box: Box) -> LineStub:
    return LineStub(
        harness=HARNESS,
        branch=1,
        drawing_set=1,
        page=1,
        port=hid("port", 1),
        far=hid("port", 2),
        at=Point(x=box.x + box.width // 2, y=box.y + box.height + 8),
        facing=Facing.N,
        box=box,
    )


def _found(layout: Layout, ink: HarnessInk, code: str) -> list[tuple]:
    """Each finding's subjects as a sorted tuple, as `Finding` keeps them."""
    return [
        tuple(sorted(f.subjects))
        for f in lint_geometry(layout, sheet=SHEET, ink=ink)
        if f.code == code
    ]


# --- connector boxes: K1's coil and its A2 under the stretched -K1-J10 box ----------------


def test_a_connector_box_over_a_foreign_symbol_is_a_text_overlap() -> None:
    """The box is a text: over K1's body it fires once, naming the box and the symbol."""
    layout = _layout(functions=(placed(1, x=200, y=200),))
    ink = HarnessInk(boxes=(_box(Box(x=150, y=190, width=200, height=24)),))
    assert _found(layout, ink, TEXT_OVERLAP) == [tuple(sorted((BOX, hid("function", 1))))]


def test_a_connector_box_over_its_own_hidden_pin_view_is_no_finding() -> None:
    """A boxed pin view draws nothing (HL6), so the box may stand on it."""
    layout = _layout(functions=(placed(1, x=200, y=200),))
    box = _box(Box(x=150, y=190, width=200, height=24))
    ink = HarnessInk(boxes=(box,), hidden=frozenset({(hid("function", 1), 1, 1)}))
    assert _found(layout, ink, TEXT_OVERLAP) == []


def test_a_connector_box_over_a_label_is_a_text_overlap() -> None:
    layout = _layout(labels=(_label(4, Box(x=120, y=104, width=13, height=8)),))
    ink = HarnessInk(boxes=(_box(Box(x=100, y=100, width=64, height=32)),))
    assert _found(layout, ink, TEXT_OVERLAP) == [tuple(sorted((BOX, hid("function", 4))))]


def test_a_plug_box_touching_its_mate_is_no_finding() -> None:
    """Face to face (HL4): the two boxes share an edge, never interior."""
    mate = _box(Box(x=100, y=100, width=64, height=48), hid("function", 10))
    plug = _box(Box(x=96, y=148, width=72, height=32))
    assert _found(_layout(), HarnessInk(boxes=(mate, plug)), TEXT_OVERLAP) == []


# --- line labels: -W12.1 over the -W12-P12 box, -W17.1 over a 24V --------------------------


def test_a_line_label_over_a_connector_box_is_a_text_overlap() -> None:
    line = _line((Point(x=0, y=40), Point(x=0, y=80)), Box(x=110, y=110, width=24, height=8))
    ink = HarnessInk(boxes=(_box(Box(x=100, y=100, width=72, height=32)),), lines=(line,))
    assert _found(_layout(), ink, TEXT_OVERLAP) == [tuple(sorted((BOX, HARNESS)))]


def test_a_line_label_over_a_label_is_a_text_overlap() -> None:
    layout = _layout(labels=(_label(4, Box(x=449, y=462, width=14, height=8)),))
    line = _line((Point(x=456, y=440), Point(x=456, y=480)), Box(x=456, y=460, width=24, height=8))
    assert _found(layout, HarnessInk(lines=(line,)), TEXT_OVERLAP) == [
        tuple(sorted((HARNESS, hid("function", 4))))
    ]


# --- runs: a leg over the `9` of `-X1 9`, a route through a stub ---------------------------


def test_an_oblique_leg_through_a_label_is_wire_over_label() -> None:
    """The leg's slant crosses the point label beside its pin."""
    layout = _layout(labels=(_label(4, Box(x=588, y=474, width=4, height=8)),))
    fan = _fan((Point(x=592, y=464), Point(x=584, y=488), Point(x=584, y=496)))
    assert _found(layout, HarnessInk(fan_outs=(fan,)), WIRE_OVER_LABEL) == [
        tuple(sorted((HARNESS, hid("function", 4))))
    ]


def test_a_trunk_beside_a_label_is_no_finding() -> None:
    layout = _layout(labels=(_label(4, Box(x=100, y=100, width=16, height=8)),))
    line = _line((Point(x=96, y=80), Point(x=96, y=160)))
    assert _found(layout, HarnessInk(lines=(line,)), WIRE_OVER_LABEL) == []


def test_a_route_through_a_line_stub_is_wire_over_label() -> None:
    route = Route(
        connection=hid("conductor", 1),
        a=hid("port", 5),
        b=hid("port", 6),
        physical_net=hid("net", 1),
        drawing_set=1,
        page=1,
        points=(
            RoutePoint(index=0, at=Point(x=80, y=104)),
            RoutePoint(index=1, at=Point(x=200, y=104)),
        ),
    )
    ink = HarnessInk(stubs=(_stub(Box(x=100, y=96, width=48, height=16)),))
    found = _found(_layout(routes=(route,)), ink, WIRE_OVER_LABEL)
    assert len(found) == 1
    assert HARNESS in found[0]


def test_a_trunk_through_a_foreign_symbol_is_wire_through_symbol() -> None:
    layout = _layout(functions=(placed(1, x=200, y=200),))
    line = _line((Point(x=160, y=200), Point(x=240, y=200)))
    assert _found(layout, HarnessInk(lines=(line,)), WIRE_THROUGH_SYMBOL) == [
        tuple(sorted((HARNESS, hid("function", 1))))
    ]


def test_a_leg_ending_on_its_own_pin_is_no_wire_through_symbol() -> None:
    """The leg enters its pin's port from inside the body's span: its own end."""
    layout = _layout(functions=(placed(1, x=200, y=200),))
    fan = _fan((Point(x=200, y=240), Point(x=200, y=224), Point(x=200, y=216)))
    assert _found(layout, HarnessInk(fan_outs=(fan,)), WIRE_THROUGH_SYMBOL) == []


# --- -W12 along the outline's bottom edge --------------------------------------------------


def test_a_line_along_an_outline_edge_is_line_on_outline() -> None:
    outline = PlacedOutline(
        unit=UNIT,
        lead=hid("function", 1),
        drawing_set=1,
        page=1,
        box=Box(x=312, y=296, width=296, height=128),
    )
    line = _line((Point(x=344, y=472), Point(x=344, y=424), Point(x=32, y=424)))
    assert _found(_layout(outlines=(outline,)), HarnessInk(lines=(line,)), LINE_ON_OUTLINE) == [
        tuple(sorted((HARNESS, UNIT)))
    ]


def test_a_line_crossing_an_outline_edge_is_no_line_on_outline() -> None:
    outline = PlacedOutline(
        unit=UNIT,
        lead=hid("function", 1),
        drawing_set=1,
        page=1,
        box=Box(x=312, y=296, width=296, height=128),
    )
    line = _line((Point(x=344, y=472), Point(x=344, y=400)))
    assert _found(_layout(outlines=(outline,)), HarnessInk(lines=(line,)), LINE_ON_OUTLINE) == []


# --- defect 1: the stub over the frame -----------------------------------------------------


def test_a_stub_over_the_frame_is_out_of_content_box() -> None:
    ink = HarnessInk(stubs=(_stub(Box(x=100, y=-8, width=48, height=16)),))
    assert _found(_layout(), ink, OUT_OF_CONTENT_BOX) == [(HARNESS,)]


def test_a_line_point_over_the_frame_is_out_of_content_box() -> None:
    line = _line((Point(x=100, y=40), Point(x=100, y=-8)))
    assert _found(_layout(), HarnessInk(lines=(line,)), OUT_OF_CONTENT_BOX) == [(HARNESS,)]


# --- the crossing test ---------------------------------------------------------------------


def test_through_counts_interior_only_and_oblique_runs() -> None:
    box = Box(x=0, y=0, width=10, height=10)
    assert through((Point(x=-5, y=5), Point(x=15, y=5)), box)
    assert through((Point(x=-5, y=-5), Point(x=15, y=15)), box)
    assert not through((Point(x=-5, y=0), Point(x=15, y=0)), box)  # along the top edge
    assert not through((Point(x=-5, y=5), Point(x=0, y=5)), box)  # ends on the edge
    assert not through((Point(x=-5, y=15), Point(x=15, y=25)), box)


def test_a_boxed_pin_view_that_draws_nothing_is_never_out_of_the_content_box() -> None:
    """HL6: a hidden view's keep-out is no ink; the same view drawn is a finding."""
    layout = _layout(functions=(placed(1, x=200, y=-40),))
    hidden = HarnessInk(hidden=frozenset({(hid("function", 1), 1, 1)}))
    assert _found(layout, hidden, OUT_OF_CONTENT_BOX) == []
    assert _found(layout, HarnessInk(), OUT_OF_CONTENT_BOX) == [(hid("function", 1),)]
