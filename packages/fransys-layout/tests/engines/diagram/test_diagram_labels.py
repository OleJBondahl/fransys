"""Diagram line labels: a label stands clear of other lines' runs and of taken boxes."""

from fransys_layout.engines.diagram.labels import label_at, label_box, label_clear
from fransys_layout.geometry import Box, Point
from fransys_layout.stages.space import run_of

_LINE = (Point(x=0, y=40), Point(x=96, y=40))
_TH = 8
_W = 16


def test_a_free_label_keeps_the_longest_runs_middle_above() -> None:
    assert label_clear(_LINE, _TH, _W, [], []) == label_at(_LINE, _TH)


def test_a_label_struck_by_another_line_moves_along_the_run() -> None:
    x, y = label_at(_LINE, _TH)
    blocked = [run_of(Point(x=x, y=y - 20), Point(x=x, y=y + 20))]
    nx, ny = label_clear(_LINE, _TH, _W, blocked, [])
    assert (nx, ny) != (x, y)
    box = label_box(nx, ny, _W, _TH)
    assert not (box.x < x < box.x + box.width)


def test_a_label_over_a_taken_box_moves_off_it() -> None:
    x, y = label_at(_LINE, _TH)
    taken = [label_box(x, y, _W, _TH)]
    nx, ny = label_clear(_LINE, _TH, _W, [], taken)
    box = label_box(nx, ny, _W, _TH)
    assert not (
        box.x < taken[0].x + taken[0].width
        and taken[0].x < box.x + box.width
        and box.y == taken[0].y
    )


def test_a_label_boxed_in_everywhere_keeps_its_default_place() -> None:
    wall = [Box(x=-40, y=0, width=200, height=80)]
    assert label_clear(_LINE, _TH, _W, [], wall) == label_at(_LINE, _TH)
