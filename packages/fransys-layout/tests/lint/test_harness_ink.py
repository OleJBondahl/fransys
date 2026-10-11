"""The geometric lint sees harness ink (layout-0158): lines, legs, line labels, stubs, boxes.

Each case is one construct the study board's page 2 drew unseen (review
defect 3): a connector box over a symbol and a label, a line label over a box text and a label,
a leg over a terminal's point label, a line along the outline's bottom edge, and a stub over the
frame (defect 1).
"""

from samples import SHEET, hid, page_plan

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.lint import HarnessInk, lint_geometry
from fransys_layout.lint.codes import (
    LINE_ON_OUTLINE,
    TEXT_OVERLAP,
    WIRE_OVER_LABEL,
)
from fransys_layout.stages import (
    LabelKind,
    Layout,
    PlacedLabel,
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


# --- line labels: -W12.1 over the -W12-P12 box, -W17.1 over a 24V --------------------------


def test_a_line_label_over_a_connector_box_is_a_text_overlap() -> None:
    line = _line((Point(x=0, y=40), Point(x=0, y=80)), Box(x=110, y=110, width=24, height=8))
    ink = HarnessInk(boxes=(_box(Box(x=100, y=100, width=72, height=32)),), lines=(line,))
    assert _found(_layout(), ink, TEXT_OVERLAP) == [tuple(sorted((BOX, HARNESS)))]


# --- runs: a leg over the `9` of `-X1 9`, a route through a stub ---------------------------


def test_an_oblique_leg_through_a_label_is_wire_over_label() -> None:
    """The leg's slant crosses the point label beside its pin."""
    layout = _layout(labels=(_label(4, Box(x=588, y=474, width=4, height=8)),))
    fan = _fan((Point(x=592, y=464), Point(x=584, y=488), Point(x=584, y=496)))
    assert _found(layout, HarnessInk(fan_outs=(fan,)), WIRE_OVER_LABEL) == [
        tuple(sorted((HARNESS, hid("function", 4))))
    ]


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


# --- defect 1: the stub over the frame -----------------------------------------------------


# --- the crossing test ---------------------------------------------------------------------
