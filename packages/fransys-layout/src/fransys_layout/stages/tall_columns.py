"""LC1 (layout-0215): a column taller than its sheet continues as the next column, at re-plan.

A column whose placed ink runs below the content box is cut between its rows, fill first
(`lane_runs` over the rows' heights). Each part is a column keyed by the column's key and its
first row; it stands as the next column of its group, on the same sheet while there is room.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import WIRING_GRID

from .lane_runs import lane_runs
from .lookups import placed_keepout
from .place import _reference_band
from .row_parts import row_part_key, row_parts
from .types import ColumnWidth

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import Box
    from fransys_model.kernel import AuthoringKey

    from .pagerun import PageInputs, PageRun, Placement
    from .types import Column, Handle

    type Boxes = Mapping[tuple[AuthoringKey, Handle], Sequence[Box]]


def row_extents(column: Column, boxes: Boxes) -> dict[int, tuple[int, int]]:
    """Each placed row's top and bottom, over its cells' keep-outs."""
    found: dict[int, tuple[int, int]] = {}
    for cell in column.cells:
        for box in boxes.get((column.key, cell.function), ()):
            low, high = found.get(cell.index, (box.y, box.y + box.height))
            found[cell.index] = (min(low, box.y), max(high, box.y + box.height))
    return found


def held_rows(column: Column) -> tuple[tuple[int, int], ...]:
    """The pairs of rows a cut must not part: an attachment's row and its host's."""
    row_of = {cell.function: cell.index for cell in column.cells if cell.host is None}
    return tuple(
        (row_of[cell.host], cell.index)
        for cell in column.cells
        if cell.host is not None and cell.host in row_of and row_of[cell.host] != cell.index
    )


def _runs(column: Column, boxes: Boxes, floor: int) -> list[list[int]]:
    """The column's rows in runs that each fit from the column's top down to `floor`."""
    extents = row_extents(column, boxes)
    order = sorted(extents)
    if not order or max(high for _, high in extents.values()) <= floor:
        return []
    at = {row: n for n, row in enumerate(order)}
    held = [(at[a], at[b]) for a, b in held_rows(column) if a in at and b in at]
    runs = lane_runs([extents[row] for row in order], held, floor - extents[order[0]][0])
    parts = [order[s:e] for s, e in runs]
    for row in sorted({c.index for c in column.cells} - set(order)):  # a row with nothing placed
        next((p for p in reversed(parts) if p[0] < row), parts[0]).append(row)
    return [sorted(part) for part in parts]


def page_floor(inputs: PageInputs) -> int:
    """The lowest a part's keep-outs reach: above the bottom headroom and the reference band.

    The band holds the markers of the wires crossing the cut (`place._reference_band`).
    """
    band = _reference_band(inputs.sheet, inputs.profile)
    return inputs.sheet.bottom - inputs.bottom_headroom_lanes * WIRING_GRID - band


def cut_tall(
    run: PageRun,
    placement: Placement,
    columns: tuple[Column, ...],
    grown: tuple[ColumnWidth, ...],
    floor: int,
) -> tuple[PageRun, tuple[Column, ...], tuple[ColumnWidth, ...]] | None:
    """The run, columns and widths with each column reaching below `floor` cut; else `None`.

    `floor` is the column height, the caller's value (`page_floor` for a schematic page).
    """
    planned = {one.column for plan in placement.plans for one in plan.columns}
    boxes: dict[tuple[AuthoringKey, Handle], list[Box]] = {}
    for one in placement.placed_all:
        boxes.setdefault((one.column, one.function), []).append(placed_keepout(one))
    cut = {
        column.key: runs
        for column in columns
        if column.key in planned and column.key not in run.inputs.middle
        if len(runs := _runs(column, boxes, floor)) > 1
    }
    if not cut:
        return None
    found = tuple(
        part
        for column in columns
        for part in (row_parts(column, cut[column.key]) if column.key in cut else (column,))
    )
    width_of = {one.column: one.width for one in grown}
    widths = [*grown]
    widths += [
        ColumnWidth(column=row_part_key(key, rows[0]), width=width_of[key])
        for key, parts in cut.items()
        for rows in parts[1:]
    ]
    widths.sort(key=lambda one: one.column)
    reserves, pin_requests = run.recut_of(found)
    return replace(run, reserves=reserves, pin_requests=pin_requests), found, tuple(widths)
