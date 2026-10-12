"""Over-wide columns cut between their lanes at re-plan (decision layout-0182).

A column wider than the content box splits fill first (`lane_runs`) on its measured lanes. Each
part is a column keyed by the column's key and its first lane; a host's and a carrier's cells
go with their lane. A single lane wider than the box stays whole.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from ._polelinks import pole_links
from .extent import page_extras, room_boxes
from .lane_runs import lane_runs
from .lookups import placed_keepout
from .types import ColumnWidth

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import Box
    from fransys_model.kernel import AuthoringKey

    from .pagerun import PageRun, Placement
    from .references.types import References
    from .types import Cell, Column, DrawnFunction, Handle

    type Ink = Mapping[tuple[AuthoringKey, Handle], Sequence[Box]]

_LANE = "lane"


def lane_of(column: Column) -> dict[Handle, int]:
    """Each cell's lane: its own, a side cell its carrier's, a hosted cell its host's."""
    found = {c.function: c.lane for c in column.cells if c.host is None and not c.side}
    found |= {c.function: found[c.carrier] for c in column.cells if c.side and c.carrier}
    found |= {c.function: found[c.host] for c in column.cells if c.host is not None}
    return found


def _bundle_of(key: AuthoringKey) -> tuple[AuthoringKey, int]:
    """The key of the column a part was cut from, and the part's first lane there."""
    if len(key) > 1 and key[-2] == _LANE and key[-1].isdigit():
        return key[:-2], int(key[-1])
    return key, 0


def part_key(key: AuthoringKey, first: int) -> AuthoringKey:
    """The key of the part starting at lane `first`; a part cut again counts from its bundle."""
    base, at = _bundle_of(key)
    return (*base, _LANE, f"{at + first:04d}")


def with_parts(every: tuple[Column, ...], columns: tuple[Column, ...]) -> tuple[Column, ...]:
    """`every` with each column cut in `columns` cut by the same lanes of its bundle, in place.

    `every` holds the columns before replicas and moved far ends, so its own cells are cut.
    """
    cut: dict[AuthoringKey, list[set[int]]] = {}
    for column in columns:
        base, at = _bundle_of(column.key)
        cut.setdefault(base, []).append({at + lane for lane in lane_of(column).values()})
    return tuple(
        one
        for column in every
        for one in (
            _recut(column, cut[column.key]) if len(cut.get(column.key, ())) > 1 else (column,)
        )
    )


def _recut(column: Column, parts: Sequence[set[int]]) -> tuple[Column, ...]:
    """`column` cut by `parts` (bundle lanes); a lane in no part goes with the part before it."""
    starts = [min(part) for part in parts]
    loose = set(lane_of(column).values()).difference(*parts)
    home = {lane: max((n for n, s in enumerate(starts) if s < lane), default=0) for lane in loose}
    return split_column(
        column, [sorted(p | {x for x, at in home.items() if at == n}) for n, p in enumerate(parts)]
    )


def split_column(column: Column, parts: Sequence[Sequence[int]]) -> tuple[Column, ...]:
    """`column` as one column per part (its lanes): the first keeps the key, rows renumbered."""
    lanes = lane_of(column)
    return tuple(_part(column, lanes, part, index) for index, part in enumerate(parts))


def _part(column: Column, lanes: Mapping[Handle, int], part: Sequence[int], index: int) -> Column:
    """One part: lanes from its first, a row's hosted cells in order, empty rows dropped."""
    own, first = set(part), part[0]
    cells = [c for c in column.cells if lanes[c.function] in own]
    rows = {at: n for n, at in enumerate(sorted({c.index for c in cells}))}
    hosted: dict[int, int] = {}
    found: list[Cell] = []
    for cell in cells:  # sorted by (index, lane)
        attached = cell.host is not None and not cell.face  # an attachment's lane is its rank
        lane = hosted.get(cell.index, 0) if attached else cell.lane - first
        hosted[cell.index] = hosted.get(cell.index, 0) + attached
        found.append(replace(cell, index=rows[cell.index], lane=lane))
    key = column.key if index == 0 else part_key(column.key, first)
    return replace(column, key=key, cells=tuple(found))


def _lane_parts(
    column: Column, ink: Ink, links: Sequence[tuple[int, int]], room: int
) -> tuple[tuple[tuple[int, ...], int], ...]:
    """Each part's lanes and the width of its ink, fill first in `room` on the placed lanes.

    A lane with nothing placed (a dropped replica) goes with the placed lane before it.
    """
    lanes = lane_of(column)
    spans: dict[int, tuple[int, int]] = {}
    for lane in sorted(set(lanes.values())):
        boxes = [b for f, at in lanes.items() if at == lane for b in ink.get((column.key, f), ())]
        if boxes:
            spans[lane] = (min(b.x for b in boxes), max(b.x + b.width for b in boxes))
    order = list(spans)
    at = {lane: n for n, lane in enumerate(order)}
    held = [(at[a], at[b]) for a, b in links if a in at and b in at]
    runs = lane_runs([spans[lane] for lane in order], held, room)
    parts = [list(order[s:e]) for s, e in runs]
    for lane in (lane for lane in set(lanes.values()) if lane not in spans):
        next((p for p in reversed(parts) if p[0] < lane), parts[0]).append(lane)
    return tuple(
        (
            tuple(sorted(part)),
            max(spans[x][1] for x in order[s:e]) - min(spans[x][0] for x in order[s:e]),
        )
        for part, (s, e) in zip(parts, runs, strict=True)
    )


def _lane_links(
    column: Column, drawn: tuple[DrawnFunction, ...], run: PageRun
) -> tuple[tuple[int, int], ...]:
    """The pairs of lanes a pole link joins (`pole_links` over one column per lane)."""
    lanes = lane_of(column)
    alone = tuple(
        replace(
            column,
            key=(f"{at:04d}",),
            cells=tuple(c for c in column.cells if lanes[c.function] == at),
        )
        for at in sorted(set(lanes.values()))
    )
    linked = pole_links(alone, drawn, run.inputs.connections, run.inputs.net_groups)
    return tuple((int(a[0]), int(b[0])) for a, b in linked)


def _ink(
    run: PageRun, placement: Placement, references: References
) -> dict[tuple[AuthoringKey, Handle], list[Box]]:
    """Per (column, function), every box it draws: keep-out, labels, markers, image room."""
    extras = page_extras(
        run.inputs, placement.columns, placement.drawn, placement.pages, references
    )
    found = room_boxes(placement.placed_all, placement.rooms)
    for one in placement.placed_all:
        found.setdefault((one.column, one.function), []).extend(
            (placed_keepout(one), *extras.get((one.drawing_set, one.page, one.function), ()))
        )
    return found


def _wide(
    run: PageRun, placement: Placement, columns: tuple[Column, ...], grown: tuple[ColumnWidth, ...]
) -> list[Column]:
    """The planned columns of more than one lane measured wider than the content box."""
    width_of = {one.column: one.width for one in grown}
    planned = {one.column for plan in placement.plans for one in plan.columns}
    return [
        column
        for column in columns
        if column.key in planned
        and column.key not in run.inputs.middle
        and width_of[column.key] > run.inputs.sheet.content_width
        and len(set(lane_of(column).values())) > 1
    ]


def cut_wide(
    run: PageRun,
    placement: Placement,
    columns: tuple[Column, ...],
    grown: tuple[ColumnWidth, ...],
    references: References,
) -> tuple[PageRun, tuple[Column, ...], tuple[ColumnWidth, ...]] | None:
    """The run, columns and widths with each over-wide column cut in parts; `None` if none is."""
    wide = _wide(run, placement, columns, grown)
    if not wide:
        return None
    gap = run.inputs.profile.column_gap
    ink = _ink(run, placement, references)
    room = run.inputs.sheet.content_width - gap
    cut = {c.key: _lane_parts(c, ink, _lane_links(c, placement.drawn, run), room) for c in wide}
    cut = {key: parts for key, parts in cut.items() if len(parts) > 1}
    if not cut:
        return None
    found = tuple(
        part
        for column in columns
        for part in (
            split_column(column, [p for p, _ in cut[column.key]])
            if column.key in cut
            else (column,)
        )
    )
    widths = [one for one in grown if one.column not in cut]
    widths += [
        ColumnWidth(column=column.key if n == 0 else part_key(column.key, lanes[0]), width=w + gap)
        for column in wide
        if column.key in cut
        for n, (lanes, w) in enumerate(cut[column.key])
    ]
    widths.sort(key=lambda one: one.column)
    reserves, pin_requests = run.recut_of(found)
    return replace(run, reserves=reserves, pin_requests=pin_requests), found, tuple(widths)
