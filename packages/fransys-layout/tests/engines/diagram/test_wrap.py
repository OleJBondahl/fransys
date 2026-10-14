"""A placed sheet wider than its limit wraps into rows (OVERVIEW-C1), on plain boxes and lines.

Each test names what breaks it. The sheets are rows of boxes `PITCH` apart, joined in a chain.
"""

from typing import Any

from fransys_layout.engines.diagram.values import PlacedBox, PlacedLine, PlacedSheet
from fransys_layout.engines.diagram.wrap import extent, wrapped
from fransys_layout.engines.diagram.wrap_route import clear
from fransys_layout.geometry import Point
from fransys_model.kernel import make_id
from fransys_model.layout import DiagramBox

PITCH = 112
BOX_W, BOX_H = 32, 48
WIDTH = 480


def _box(n: int) -> PlacedBox:
    return PlacedBox(
        box=make_id(DiagramBox, ("b", str(n))),
        dashed=False,
        x=16 + n * PITCH,
        y=56,
        width=BOX_W,
        height=BOX_H,
        tabs=(),
    )


def _line(a: int, b: int) -> PlacedLine:
    start, end = _box(a), _box(b)
    points = (Point(x=start.x + BOX_W, y=80), Point(x=end.x, y=80))
    return PlacedLine(
        cable=make_id(DiagramBox, ("c", str(a))),
        a=start.box,
        b=end.box,
        points=points,
        text_x=0,
        text_y=0,
    )


def _sheet(count: int, extra: tuple[PlacedLine, ...] = ()) -> PlacedSheet:
    boxes = tuple(_box(n) for n in range(count))
    lines = tuple(_line(n, n + 1) for n in range(count - 1)) + extra
    return PlacedSheet(number=1, boxes=boxes, lines=lines, markers=())


def _rows(sheet: PlacedSheet) -> list[list[Any]]:
    rows: dict[int, list[Any]] = {}
    for box in sheet.boxes:
        rows.setdefault(box.y, []).append(box)
    return [sorted(rows[y], key=lambda b: b.x) for y in sorted(rows)]


def test_a_sheet_within_its_width_is_returned_as_it_is() -> None:
    """Breaks if a sheet that fits is moved or copied."""
    sheet = _sheet(3)
    assert wrapped(sheet, WIDTH, 8) is sheet


def test_a_wide_row_wraps_to_the_width() -> None:
    """Breaks if the sheet stays wider than the limit or stays one row."""
    out = wrapped(_sheet(12), WIDTH, 8)
    left, _, right, _ = extent(out)
    assert right - left <= WIDTH
    assert len(_rows(out)) > 1


def test_the_rows_keep_the_chain_order_and_the_boxes_keep_their_size() -> None:
    """Breaks if a wrap shuffles boxes or resizes one."""
    out = wrapped(_sheet(12), WIDTH, 8)
    assert [b.box for row in _rows(out) for b in row] == [
        make_id(DiagramBox, ("b", str(n))) for n in range(12)
    ]
    assert {(b.width, b.height) for b in out.boxes} == {(BOX_W, BOX_H)}


def test_a_folded_line_runs_from_one_box_edge_to_the_next_and_touches_no_box() -> None:
    """Breaks if a fold route leaves its box's side, misses the next box, or crosses a box."""
    out = wrapped(_sheet(12), WIDTH, 8)
    boxes = {b.box: b for b in out.boxes}
    folded = [ln for ln in out.lines if len(ln.points) > 2]
    assert folded
    for ln in folded:
        assert ln.points[0].x == boxes[ln.a].x + BOX_W
        assert ln.points[-1] == Point(x=boxes[ln.b].x, y=ln.points[-1].y)
    assert clear([ln.points for ln in folded], out.boxes, [ln.points for ln in out.lines])


def test_a_line_over_more_than_one_row_leaves_the_sheet_as_it_was() -> None:
    """Breaks if a wrap routes a line it cannot, instead of keeping the sheet."""
    sheet = _sheet(12, (_line(0, 11),))
    assert wrapped(sheet, WIDTH, 8) is sheet


def test_a_column_wider_than_the_limit_leaves_the_sheet_as_it_was() -> None:
    """Breaks if a wrap cuts inside a column."""
    sheet = _sheet(12)
    assert wrapped(sheet, BOX_W - 8, 8) is sheet
