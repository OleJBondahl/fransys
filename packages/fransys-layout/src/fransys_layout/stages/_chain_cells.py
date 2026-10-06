"""Row and cell assembly of chain discovery: the columns' cells, before attachments (chains.py)."""

from typing import TYPE_CHECKING, Any

from ._chain_state import _EDGE_FACE, _Cells, _Row, _Synthetic
from .types import Cell

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from ._chain_state import _Group, _Pole, _PoleId, _Poles, _Reach, _Sides, _Walks
    from .types import FunctionSpec, Handle


def _add_edge(r: _Row, pid: _PoleId, pole: _Pole, ctx: _Cells) -> None:
    """D8: an edge pole's boundary pin (a replica) stands outside the column."""
    # Above the parent-side pin at a top end, below it at a bottom end.
    upper, lower = pole.functions
    above = pid in ctx.edge_top
    r.row.append(upper)
    (r.face_above if above else r.face_row).append((_EDGE_FACE, above, lower, upper))


def _add_mate(r: _Row, pid: _PoleId, pole: _Pole, ctx: _Cells) -> None:
    """R7 A: the upper (plug) pin in this row, the lower pin face to face below it."""
    upper, lower = pole.functions
    if ctx.upper_of.get(pid, upper) != upper:
        upper, lower = lower, upper
    r.row.append(upper)
    r.face_row.append(lower)
    ctx.face_of[lower] = upper


def _add_pole(r: _Row, pid: _PoleId, pole: _Pole, ctx: _Cells) -> None:
    """Add a pole's functions to the row, and its side poles' functions to the side row."""
    if pole.kind is _Synthetic.MATE:
        if pid in ctx.edge_poles:
            _add_edge(r, pid, pole, ctx)
            return
        _add_mate(r, pid, pole, ctx)
    else:
        r.row.extend(f for f in pole.functions if f not in r.row)
    r.side_row.extend(f for f in ctx.sides.get(pid, ()) if f not in r.side_row)


def _position_rows(
    group: _Group, position: int, length: int, ctx: _Cells
) -> list[tuple[list[Any], list[Handle]]]:
    """The rows of one chain position: an edge-pin row above, its own row, a face row below."""
    r = _Row()
    for chain in group.chains:
        at = position - (length - len(chain) if group.bottom else 0)
        if not 0 <= at < len(chain):
            r.row.append(None)  # (iii): this lane has no cell in this row
            continue
        _add_pole(r, chain[at], ctx.poles[chain[at]], ctx)
    above = [(r.face_above, [])] if r.face_above else []
    below = [(r.face_row, [])] if r.face_row else []
    return [*above, (r.row, r.side_row), *below]


def _lane_rows(
    functions: Sequence[Handle], b: object, lane_hit: Mapping[tuple[Handle, int], int], lanes: int
) -> list[tuple[list[Any], list[Handle]]]:
    """C9: rows of end-reached functions, one per lane; a second one in a lane opens a row."""
    rows: list[list[Handle | None]] = []
    for function in functions:
        lane = lane_hit.get((function, b), 0) if lanes > 1 else 0
        for row in rows:
            if row[lane] is None:
                row[lane] = function
                break
        else:
            row = [None] * max(lanes, 1)
            row[lane] = function
            rows.append(row)
    return [(row, []) for row in rows]


def _candidate(
    b: object, group: _Group, ctx: _Cells
) -> tuple[AuthoringKey, list[tuple[list[Any], list[Handle]]]]:
    """A bundle's sort key and rows: the lane-end rows (C9) around its chain positions' rows."""
    length = max(len(chain) for chain in group.chains)
    rows = [r for position in range(length) for r in _position_rows(group, position, length, ctx)]
    above, below = ctx.extra.get(b, ([], []))
    lanes = len(group.chains)
    rows = [
        *_lane_rows(above, b, ctx.lane_hit, lanes),
        *rows,
        *_lane_rows(below, b, ctx.lane_hit, lanes),
    ]
    first = next(f for row, _ in rows for f in row if f is not None)
    first = first[-1] if isinstance(first, tuple) else first
    return (ctx.specs[first].key, rows)


def _edge_cell(function: tuple[str, bool, Handle, Handle], ctx: _Cells) -> None:
    """An edge pin: its home is in its unit's chain, this is its replica."""
    _, above, pin, host = function
    cell = Cell(
        function=pin,
        index=ctx.index,
        lane=ctx.lane,
        flip=not above,
        host=host,
        port="in",
        face=True,
        replica=True,
    )
    ctx.cells.append(cell)
    ctx.step()


def _plain_cell(function: Handle, ctx: _Cells) -> None:
    """A face cell under its upper pin, or a plain cell with its flip, mirror and span port."""
    if function in ctx.face_of:
        cell = Cell(
            function=function,
            index=ctx.index,
            lane=ctx.lane,
            flip=True,
            host=ctx.face_of[function],
            port="in",
            face=True,
        )
    else:
        cell = Cell(
            function=function,
            index=ctx.index,
            lane=ctx.lane,
            flip=function in ctx.flipped,
            mirror=function in ctx.turned,
            span_port=ctx.span_symbol.get(function, ""),
        )
    ctx.cells.append(cell)
    ctx.placed.add(function)
    ctx.drawn_in[function] = ctx.cells
    ctx.step()


def _side_cell(function: Handle, ctx: _Cells, home: Sequence[Cell]) -> Cell:
    """A side element's cell: in this column's row, or beside its carrier's cell in `home`."""
    carrier = ctx.carrier_of[function]
    flip, low = ctx.side_info.get(function, (False, False))
    if home is ctx.cells:
        return Cell(
            function=function,
            index=ctx.index,
            lane=ctx.lane,
            side=True,
            flip=flip,
            low=low,
            carrier=carrier,
        )
    # D2: its carrier was drawn in an earlier column; it stands beside the carrier's cell
    # there, never in a row of this column that lacks the carrier
    row_at = next(c for c in home if c.function == carrier)
    return Cell(
        function=function,
        index=row_at.index,
        lane=1 + max(c.lane for c in home if c.index == row_at.index),
        side=True,
        flip=flip,
        low=low,
        carrier=carrier,
    )


def _place_side(function: Handle, ctx: _Cells) -> None:
    """Place a side element not placed yet, in its carrier's column."""
    if function in ctx.placed:
        return
    home = ctx.drawn_in.get(ctx.carrier_of[function], ctx.cells)
    home.append(_side_cell(function, ctx, home))
    ctx.placed.add(function)
    if home is ctx.cells:
        ctx.step()
    else:
        ctx.drawn_in[function] = home


def _place(function: Handle | tuple[str, bool, Handle, Handle] | None, ctx: _Cells) -> None:
    """Place one function of a row: an empty lane, an edge pin, or a cell not placed yet."""
    if function is None:  # (iii): an empty lane keeps its place
        ctx.lane += 1
    elif isinstance(function, tuple):
        _edge_cell(function, ctx)
    elif function not in ctx.placed:
        _plain_cell(function, ctx)


def _column_cells(rows: Sequence[tuple[list[Any], list[Handle]]], ctx: _Cells) -> list[Cell]:
    """The cells of one column: a row index per row that kept a cell, a lane per cell."""
    ctx.cells = []
    ctx.index = 0
    for row, side_row in rows:
        ctx.begin_row()
        for function in row:
            _place(function, ctx)
        for function in side_row:
            _place_side(function, ctx)
        if ctx.kept:
            ctx.index += 1
    return ctx.cells


def build_cells(
    state: _Poles,
    walks: _Walks,
    found: _Sides,
    reach: _Reach,
    specs: Mapping[Handle, FunctionSpec],
) -> list[list[Cell]]:
    """The cells of every column, columns in the order of their first function's key."""
    ctx = _Cells(
        poles=state.poles,
        edge_poles=state.edge_poles,
        edge_top=walks.edge_top,
        upper_of=walks.upper_of,
        flipped=walks.flipped,
        turned=walks.turned,
        sides=found.sides,
        side_info=found.side_info,
        carrier_of=found.carrier_of,
        extra=reach.extra,
        lane_hit=reach.lane_hit,
        span_symbol=reach.span_symbol,
        specs=specs,
    )
    candidates = [_candidate(b, group, ctx) for b, group in reach.groups.items()]
    columns = [_column_cells(rows, ctx) for _key, rows in sorted(candidates, key=lambda c: c[0])]
    return [cells for cells in columns if cells]
