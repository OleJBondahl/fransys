"""Field case: five connector devices joined by six one-core cables, with P4 and P1 joined by two of them.
The bug: lines of two different cables ran along the same coordinate over a stretch, so the drawing showed one line where there were two.
Fixed by layout-0199 (LEGACY-B3 L12), the lines take separate tracks; lint/diagram.py reports DIAGRAM_LINES_SHARE_TRACK otherwise."""

from itertools import combinations

from _field_shared import cable_lines

lazy from fransys_layout import DiagramLine

_EDGES = ((4, 1), (2, 3), (2, 1), (5, 4), (2, 4), (1, 4))


def _runs(line: DiagramLine) -> list[tuple[int, int, int, int]]:
    """Each run as `(x, y, to_x, to_y)` with its ends ordered."""
    return [(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)) for a, b in zip(line.points, line.points[1:], strict=False)]


def _shared(one: tuple[int, int, int, int], other: tuple[int, int, int, int]) -> bool:
    if one[0] == one[2] and other[0] == other[2]:
        return one[0] == other[0] and min(one[3], other[3]) > max(one[1], other[1])
    if one[1] == one[3] and other[1] == other[3]:
        return one[1] == other[1] and min(one[2], other[2]) > max(one[0], other[0])
    return False


def test_no_two_cables_share_a_track() -> None:
    lines = cable_lines(5, _EDGES)
    assert len(lines) == len(_EDGES)
    shared = [
        (one.cable, other.cable)
        for one, other in combinations(lines, 2)
        if one.cable != other.cable and any(_shared(r, s) for r in _runs(one) for s in _runs(other))
    ]
    assert shared == []
