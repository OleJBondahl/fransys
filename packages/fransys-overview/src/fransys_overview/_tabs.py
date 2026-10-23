"""Which tab of a box carries the text of a cable line's end (display matching, no fact).

The rows give a line's tab text at each end and the placed view its route and the box's tabs.
A line's end point lies on the tab it ends on, so the tab nearest that point is its tab.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fransys_model.derive import PlacedBox, PlacedView, ViewRows


def _nearest(box: PlacedBox, point: tuple[int, int], height: int) -> int | None:
    """The `index` of the tab of `box` nearest `point`, taking a tab's centre to be its text's."""
    best: tuple[int, int] | None = None
    for tab in box.tabs:
        dist = abs(point[0] - tab.x - tab.text_width // 2) + abs(point[1] - tab.y - height // 2)
        if best is None or dist < best[0]:
            best = (dist, tab.index)
    return None if best is None else best[1]


def tab_texts(rows: ViewRows, placed: PlacedView, height: int) -> dict[tuple[int, int], str]:
    """The text of each tab, keyed by (box position, tab index), from the lines that end on it."""
    found: dict[tuple[int, int], str] = {}
    for line, record in zip(rows.lines, placed.lines, strict=True):
        ends = ((record.a, line.tab_a, record.points[0]), (record.b, line.tab_b, record.points[-1]))
        for at, text, point in ends:
            tab = None if text is None else _nearest(placed.boxes[at], (point.x, point.y), height)
            if tab is not None and text is not None:
                found[(at, tab)] = text
    return found
