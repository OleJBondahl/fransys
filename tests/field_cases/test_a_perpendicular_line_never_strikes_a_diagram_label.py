"""Field case: eight one-core cables between six connector devices, each drawn as a labelled block-diagram line.
The bug: a label was placed with no clearance test, so a perpendicular run of another cable's line passed through it.
Fixed by layout-0199 (LEGACY-B3 L12), the label moves clear of every line; lint/diagram.py reports DIAGRAM_LABEL_STRUCK if one remains."""

from _field_shared import cable_lines

lazy from fransys_layout import DiagramLine

_EDGES = ((6, 2), (1, 2), (2, 3), (3, 6), (2, 4), (3, 5), (5, 1), (1, 5))
_HALF_WIDTH = 8  # a label "-W1" is 15 units wide at the house text: this is a little over half
_HALF_HEIGHT = 4


def _strikes(label: DiagramLine, line: DiagramLine) -> bool:
    left, right = label.text_x - _HALF_WIDTH, label.text_x + _HALF_WIDTH
    top, bottom = label.text_y - _HALF_HEIGHT, label.text_y + _HALF_HEIGHT
    for a, b in zip(line.points, line.points[1:], strict=False):
        if a.x == b.x and left < a.x < right and min(a.y, b.y) < bottom and max(a.y, b.y) > top:
            return True
        if a.y == b.y and top < a.y < bottom and min(a.x, b.x) < right and max(a.x, b.x) > left:
            return True
    return False


def test_no_line_runs_through_a_label() -> None:
    lines = cable_lines(6, _EDGES)
    assert len(lines) == len(_EDGES)
    assert [(one.cable, other.cable) for one in lines for other in lines if _strikes(one, other)] == []
