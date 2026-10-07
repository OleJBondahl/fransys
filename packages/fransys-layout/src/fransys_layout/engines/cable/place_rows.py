"""The cable placer's row packing: each row's end boxes left to right (CT5-3, Q5)."""

from typing import Any

from fransys_layout.geometry import WIRING_GRID, snap_up
lazy from fransys_layout.engines.cable.values import EndFacts, PlacedEnd
lazy from fransys_model.kernel import Id

G = WIRING_GRID


def _label(end: EndFacts) -> int:
    return 0 if end.blank else end.label_width


def landing_map(
    ends: tuple[PlacedEnd, ...],
) -> dict[tuple[Id[Any], Id[Any]], tuple[int, PlacedEnd]]:
    """Per (core, port): the x of the core's place in the port's cell, and the end it stands in."""
    return {
        (place.core, cell.port): (place.x, end)
        for end in ends
        for cell in end.cells
        for place in cell.landings
    }


def row_xs(ends: tuple[EndFacts, ...], x0: int, pitch: int) -> tuple[int, ...]:
    """Each end's left edge: the first at `x0`, the next one pitch past the last box's edge.

    A gap is wider when the two labels, each centred on its box, would come nearer than one
    grid unit (CD8, no two labels overlap). Rows are packed alone; bends fall out of the gaps.
    """
    xs: list[int] = []
    for i, end in enumerate(ends):
        width = end.places * pitch
        if i == 0:
            xs.append(x0)
            continue
        before = ends[i - 1]
        before_width = before.places * pitch
        apart = (_label(before) + _label(end) + 1) // 2 + G  # centres at least this far apart
        label_x = xs[-1] + before_width // 2 + apart - width // 2
        xs.append(snap_up(max(xs[-1] + before_width + pitch, label_x)))
    return tuple(xs)
