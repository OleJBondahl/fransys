"""Stage 4, place: the rows' vertical offsets, spreads, band and face alignment (place.py)."""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import Facing, Point, flow, snap_up

from .host_offsets import _next_slot, attachment_offsets
from .stacking import blocks

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import SymbolGeometry
    from fransys_model.kernel import AuthoringKey

    from .place import _Cell


def _pole_pitch(rows: Sequence[list[_Cell]]) -> int | None:
    """The x distance between pole 1 and pole 2 of the column's first multi-pole symbol."""
    for row in rows:
        for cell in row:
            if cell.geometry.poles < 2 or cell.geometry.through is None:  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
                continue
            name = cell.geometry.through.start
            at = {port.name: port.at.x for port in cell.geometry.ports}
            if f"1.{name}" in at and f"2.{name}" in at:
                return at[f"2.{name}"] - at[f"1.{name}"]
    return None


def _lane_offsets(rows: Sequence[list[_Cell]]) -> None:
    """Each cell's axis right of the column axis: pole lanes at the pole pitch, sides packed."""
    pitch = _pole_pitch(rows) or _widest_step(rows)
    for row in rows:
        if all(cell.host is not None for cell in row):
            continue
        if pitch and not row[0].side:  # A row's first cell may sit in a later lane
            row[0].dx = row[0].lane * pitch
        for previous, cell in pairwise(row):
            packed = _next_slot(previous, cell)
            # Pole lanes sit exactly at the pole pitch, never inside the cell before
            # (a multi-pole cell's keep-out spans several lanes); a lane after a multi-pole
            # cell gives up the exact pole pitch to avoid that overlap
            cell.dx = max(cell.lane * pitch, packed) if pitch and not cell.side else packed
    _span_offsets(rows, pitch)
    _keep_gap(rows)
    attachment_offsets(rows)


def _keep_gap(rows: Sequence[list[_Cell]]) -> None:
    """Two neighbours never touch: a cell the span offsets left too close moves right."""
    for row in rows:
        free = [cell for cell in row if cell.host is None]
        for previous, cell in pairwise(free):
            cell.dx = max(cell.dx, _next_slot(previous, cell))


def _span_offsets(rows: Sequence[list[_Cell]], pitch: int | None) -> None:
    """A function spanning lanes has its reached port under its lane."""
    for row in rows:
        for cell in row:
            if cell.span_port and cell.host is None:
                port_x = next(p.at.x for p in cell.geometry.ports if p.name == cell.span_port)
                cell.dx = (cell.lane * pitch if pitch else 0) + cell.axis_offset - port_x


def _widest_step(rows: Sequence[list[_Cell]]) -> int | None:
    """With no pole pitch, one pitch for every pole-lane row: the widest step per lane it spans."""
    steps = [
        snap_up(-(-_next_slot(previous, cell, 0) // max(1, cell.lane - previous.lane)))
        for row in rows
        if not all(cell.host is not None for cell in row)
        for previous, cell in pairwise(row)
        if not cell.side and not previous.side
    ]
    return max(steps, default=None)


def _spread(page: Sequence[list[list[_Cell]]], column_gap: int, left: int = 0) -> None:
    """Give every column its axis, left to right, keep-out edges a column gap apart."""
    for rows in page:
        _lane_offsets(rows)
        cells = [cell for row in rows for cell in row]
        axis = snap_up(left - min(cell.dx + cell.left_of_axis for cell in cells))
        for cell in cells:
            cell.at_axis(axis + cell.dx)
        left = max(cell.right for cell in cells) + column_gap


def _row_bottom(row: Sequence[_Cell], floor: int) -> int:
    """The keep-out bottom of `row` once its top is at `floor`, snapped as `at_top` snaps."""
    return max(cell.top_at(floor) + cell.geometry.keepout.height for cell in row)


def _apply(rows: Sequence[list[_Cell]], moves: Sequence[tuple[int, int]]) -> None:
    """Put each moved row's top at its new top."""
    for index, top in moves:
        for cell in rows[index]:
            cell.at_top(top)


def _stack(rows: Sequence[list[_Cell]], row_gap: int, *, top: int) -> None:
    """The longest-path pass down one column: the first row's top is `top`, the headroom."""
    _apply(rows, flow(rows, floor=top, gaps=[row_gap] * len(rows), far_edge=_row_bottom))


def _space(
    page: Sequence[list[list[_Cell]]], spacing: int, narrowed: Mapping[AuthoringKey, int]
) -> None:
    """A column's rows stack from the top at `spacing` (or its `narrowed` one)."""
    for column in page:
        if all(cell.boxy for row in column for cell in row):
            continue
        apart = narrowed.get(column[0][0].column, spacing)
        floor = None
        for block in blocks(column):
            cells = [cell for row in block for cell in row]
            if floor is not None:
                shift = floor - min(cell.top for cell in cells)
                for cell in cells:
                    cell.at_top(cell.top + shift)
            floor = max(cell.bottom for cell in cells) + apart


def _align_sides(page: Sequence[list[list[_Cell]]]) -> None:
    """Put each side element's port on its host's port y."""
    for rows in page:
        for row in rows:
            hosts = [cell for cell in row if not cell.side]
            if not hosts:
                continue
            host = hosts[-1]
            host_top = host.origin.y + _port_y(host.geometry, Facing.N, top=True)
            host_bottom = host.origin.y + _port_y(host.geometry, Facing.S, top=False)
            for cell in row:
                if not cell.side:
                    continue
                target = host_bottom if cell.low else host_top
                own = _port_y(cell.geometry, Facing.N, top=True)
                cell.origin = Point(x=cell.origin.x, y=target - own)


def _align_faces(page: Sequence[list[list[_Cell]]]) -> None:
    """A lower pin's mating face on its upper pin's, touching."""
    for rows in page:
        by_function = {cell.function: cell for row in rows for cell in row}
        row_of = {cell.function: at for at, row in enumerate(rows) for cell in row}
        for row in rows:
            for cell in row:
                if not cell.face or cell.host is None:
                    continue
                host = by_function[cell.host]
                if row_of[cell.function] < row_of[cell.host]:
                    target = host.origin.y + host.geometry.body.y
                    body = cell.geometry.body
                    cell.origin = Point(x=cell.origin.x, y=target - body.y - body.height)
                    continue
                target = host.origin.y + host.geometry.body.y + host.geometry.body.height
                cell.origin = Point(x=cell.origin.x, y=target - cell.geometry.body.y)


def _port_y(geometry: SymbolGeometry, facing: Facing, *, top: bool) -> int:
    """The y of the topmost port facing `facing` (or the bottommost), else of any port."""
    ys = [port.at.y for port in geometry.ports if port.facing is facing]
    ys = ys or [port.at.y for port in geometry.ports]
    return min(ys) if top else max(ys)
