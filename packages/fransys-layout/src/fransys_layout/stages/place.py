"""Stage 4, place: a grid position for every drawn function on one page (design/place.md 6.4)."""

import dataclasses
from dataclasses import dataclass, field
from functools import partial
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    Orientation,
    Point,
    flow,
    hull,
    on_wiring_grid,
    snap_up,
    symbol_geometry,
)
from fransys_model.kernel import Finding, Severity

from . import lookups
from ._band_align import _band_top, _cascade_bottom, _participants
from ._bands import band_of
from .host_offsets import _next_slot, attachment_offsets
from .references.marker_boxes import FLOOR, Digits, reference_box_width
from .room import grow_keepout, room_offset
from .stack_room import make_room
from .stacking import JoinedRun, PageStack, StackedPort, blocks, gaps_below, join_offset
from .texts.stand import end_boxes
from .types import PlacedFunction

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from fransys_layout.geometry import SymbolGeometry
    from fransys_model.kernel import AuthoringKey

    from .page_stacking import PageStacking
    from .texts.stand import PageTexts
    from .types import Cell, Column, DrawnFunction, FnBoxes, Handle, PagePlan, Profile, SheetFormat

PAGE_OVERFULL = "PAGE_OVERFULL"


@dataclass(slots=True)
class _Cell:
    """One cell on its way to a position: its geometry, its band and its moving origin."""

    function: Handle
    column: AuthoringKey
    geometry: SymbolGeometry
    band: str | None
    axis_offset: int
    lane: int = 0
    side: bool = False
    low: bool = False
    carrier: Handle | None = None
    boxy: bool = False
    role: object = None  # C13(b): the column's role; a band aligns one role only
    span_port: str = ""
    host: Handle | None = None
    port: str = ""
    face: bool = False
    dx: int = 0  # the cell's axis, right of the column axis (R4 rows)
    # `field(default=...)` is not redundant: ruff RUF009 refuses a bare call as a default.
    origin: Point = field(default=Point(x=0, y=0))

    @property
    def top(self) -> int:
        """The y of the keep-out box's upper edge."""
        return self.origin.y + self.geometry.keepout.y

    @property
    def bottom(self) -> int:
        """The y of the keep-out box's lower edge."""
        return self.top + self.geometry.keepout.height

    @property
    def left_of_axis(self) -> int:
        """The keep-out box's left edge relative to the cell's own axis."""
        return self.geometry.keepout.x - self.axis_offset

    @property
    def right(self) -> int:
        """The x of the keep-out box's right edge."""
        return self.origin.x + self.geometry.keepout.x + self.geometry.keepout.width

    def at_axis(self, axis: int) -> None:
        """Put the cell's axis port on `axis`; the origin stays on the wiring grid."""
        self.origin = Point(x=axis - self.axis_offset, y=self.origin.y)

    def top_at(self, top: int) -> int:
        """The keep-out box's upper edge after `at_top(top)`: `top`, or just below on the grid."""
        return snap_up(top - self.geometry.keepout.y) + self.geometry.keepout.y

    def at_top(self, top: int) -> None:
        """Put the keep-out box's upper edge at `top`, or just below where the grid says so."""
        self.origin = Point(x=self.origin.x, y=self.top_at(top) - self.geometry.keepout.y)


def place(
    plan: PagePlan,
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    stacking: PageStacking,
    joins: tuple[JoinedRun, ...] = (),
) -> tuple[tuple[PlacedFunction, ...], tuple[Finding, ...]]:
    """Place the columns of `plan` left to right, cells top to bottom (WP7, layout-0035)."""
    drawn_of = lookups.drawn_of(drawn, "place")
    page, _, floor, gaps_of = _stacked(plan, columns, drawn_of, stacking, joins)
    # R7 B7, D3: each row's top at minimum pitch with the spacing kept (blocks `row_spacing`
    # apart, `row_gap` inside a block and in a column of only boxes): how high it can go
    stacked = {
        (c, i): min(cell.top for cell in row)
        for c, rows in enumerate(page)
        for i, row in enumerate(rows)
    }
    _align_bands(page, stacking.profile.band_ranks, gaps_of, floor=floor, stacked=stacked)
    _align_sides(page)
    _align_faces(page)
    flat = [cell for rows in page for row in rows for cell in row]
    placed = sorted(
        (
            PlacedFunction(
                function=cell.function,
                drawing_set=plan.drawing_set,
                page=plan.number,
                column=cell.column,
                at=cell.origin,
                geometry=cell.geometry,
                carrier=cell.carrier,
            )
            for cell in flat
        ),
        key=lambda function: function.function,
    )
    return tuple(placed), _overfull(flat, floor)


def page_stack(
    plan: PagePlan,
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    stacking: PageStacking,
) -> PageStack:
    """S12: the page as `place` stacks it before its bands, but with no `texts` (4b6c, 4b6d)."""
    drawn_of = lookups.drawn_of(drawn, "place")
    page, top, floor, _ = _stacked(plan, columns, drawn_of, stacking)
    ports: dict[tuple[AuthoringKey, Handle], StackedPort] = {}
    heights: dict[AuthoringKey, int] = {}
    last: dict[AuthoringKey, int] = {}
    for rows in page:
        key = rows[0][0].column
        ports.update(((key, port), one) for port, (_, one) in _column_ports(rows, drawn_of, top))
        heights[key] = max(cell.bottom for row in rows for cell in row) - top
        last[key] = len(blocks(rows)) - 1
    return PageStack(frozendict(ports), frozendict(heights), frozendict(last), floor - top)


def _column_ports(
    rows: Sequence[list[_Cell]], drawn_of: Mapping[Handle, DrawnFunction], top: int
) -> list[tuple[Handle, tuple[list[_Cell], StackedPort]]]:
    """Each drawn port of one stacked column, with its block's first row and its `StackedPort`."""
    found = []
    for number, block in enumerate(blocks(rows)):
        for cell in (cell for row in block for cell in row):
            at = {g.name: g for g in cell.geometry.ports}
            for port in drawn_of[cell.function].ports:
                g = at.get(port.symbol_port)
                if g is not None:
                    one = StackedPort(
                        row=number,
                        offset=cell.origin.y + g.at.y - top,
                        x=cell.origin.x + g.at.x,
                        facing=g.facing,
                    )
                    found.append((port.port, (block[0], one)))
    return found


def _align_joins(
    page: Sequence[list[list[_Cell]]],
    joins: tuple[JoinedRun, ...],
    drawn_of: Mapping[Handle, DrawnFunction],
    top: int,
    gaps_of: _GapsOf,
) -> None:
    """S12: each joined run's ports on one y at its deepest port, before the bands (D1)."""
    by_key = {rows[0][0].column: rows for rows in page}
    for run in joins:
        ends = [
            (by_key[end.column], dict(_column_ports(by_key[end.column], drawn_of, top))[end.port])
            for end in run.ends
        ]
        y = join_offset(one.offset for _, (_, one) in ends)
        for rows, (first, one) in ends:
            if one.offset == y:
                continue
            start = next(index for index, row in enumerate(rows) if row is first)
            new_top = min(cell.top for cell in first) + y - one.offset
            _cascade(rows, start, new_top, gaps_of(rows))


def _stacked(
    plan: PagePlan,
    columns: tuple[Column, ...],
    drawn_of: Mapping[Handle, DrawnFunction],
    stacking: PageStacking,
    joins: tuple[JoinedRun, ...] = (),
) -> tuple[list[list[list[_Cell]]], int, int, _GapsOf]:
    """`place`'s steps before its bands, M11 passes included: cells stacked, top, floor, gaps."""
    narrowed: dict[AuthoringKey, int] = {}
    while True:
        gaps_of = _gaps_of(stacking.profile, narrowed)
        page, top, floor = _stack_page(plan, columns, drawn_of, stacking, narrowed)
        _align_joins(page, joins, drawn_of, top, gaps_of)
        runs = [frozenset(end.column for end in run.ends) for run in joins]
        again = _narrowed(page, floor, narrowed, stacking.profile, runs)
        if again == narrowed:
            return page, top, floor, gaps_of
        narrowed = again


type _GapsOf = Callable[[list[list[_Cell]]], list[int]]


def _gaps_of(profile: Profile, narrowed: Mapping[AuthoringKey, int]) -> _GapsOf:
    """A column's gaps (`gaps_below`) at `row_gap` and the column's spacing, narrowed or not."""

    def gaps_of(rows: Sequence[list[_Cell]]) -> list[int]:
        spacing = narrowed.get(rows[0][0].column, profile.row_spacing)
        return gaps_below(rows, profile.row_gap, spacing)

    return gaps_of


def _narrowed(
    page: Sequence[list[list[_Cell]]],
    floor: int,
    narrowed: Mapping[AuthoringKey, int],
    profile: Profile,
    runs: Sequence[frozenset[AuthoringKey]],
) -> dict[AuthoringKey, int]:
    """M11: `narrowed` with each overfull column's spacing cut by its overhang over its gaps."""
    over = {
        rows[0][0].column: max(cell.bottom for row in rows for cell in row) - floor for rows in page
    }
    for run in runs:
        worst = max(over.get(key, 0) for key in run)
        over.update(dict.fromkeys(run & over.keys(), worst))
    again = dict(narrowed)
    for rows in page:
        key = rows[0][0].column
        spacing = narrowed.get(key, profile.row_spacing)
        between = len(blocks(rows)) - 1
        excess = over[key]
        if excess > 0 and between > 0 and spacing > profile.row_gap:
            if all(cell.boxy for row in rows for cell in row):
                continue
            again[key] = max(profile.row_gap, spacing - -(-excess // between))
    return again


def _stack_page(
    plan: PagePlan,
    columns: tuple[Column, ...],
    drawn_of: Mapping[Handle, DrawnFunction],
    stacking: PageStacking,
    narrowed: Mapping[AuthoringKey, int],
) -> tuple[list[list[list[_Cell]]], int, int]:
    """One stacking of the page, each column at its spacing (`_stacked`)."""
    profile, sheet, texts = stacking.profile, stacking.sheet, stacking.texts
    gaps_of = _gaps_of(profile, narrowed)
    page = [
        _cells(column, drawn_of, profile, stacking.label_boxes)
        for column in _in_plan_order(plan, columns)
    ]
    _spread(page, profile.column_gap)
    # C14: the first rows leave room above for their texts (tags, point texts, markers on N
    # ports) and the last rows below, inside the content box
    lift, sink = _text_room(page, profile, drawn_of, texts)
    # M4: every page keeps it, a reference or none
    band = _reference_band(sheet, profile, stacking.digits)
    lift, sink = max(lift, band), max(sink, band)
    # M9: two ports stacked along a stub stand as far apart as the texts at them reach out
    make_room(page, drawn_of, texts, gaps_of=gaps_of, profile=profile)
    top = stacking.headroom_lanes * WIRING_GRID + lift
    for rows in page:
        _stack(rows, profile.row_gap, top=top)
    floor = sheet.content_height - stacking.bottom_headroom_lanes * WIRING_GRID - sink
    _align_faces(page)  # R13: a mated pair touches before the spacing measures it
    _space(page, profile.row_spacing, narrowed)
    return page, top, floor


def _reference_band(sheet: SheetFormat, profile: Profile, digits: Digits = FLOOR) -> int:
    """M4: the top and bottom band height, a turned reference plus stub clearance, on every page."""
    return snap_up(WIRING_GRID + reference_box_width(sheet, profile, digits=digits))


def _in_plan_order(plan: PagePlan, columns: tuple[Column, ...]) -> list[Column]:
    """The page's columns, left to right, matched to `plan.columns` by key (columns.md 6.2)."""
    by_key: dict[AuthoringKey, Column] = {}
    for column in columns:
        if column.key in by_key:
            msg = "two columns carry one authoring key, and keys are unique within an engine run"
            raise LayoutError(msg)
        by_key[column.key] = column
    ordered = []
    for planned in plan.columns:
        found = by_key.get(planned.column)
        if found is None or found in ordered:
            msg = "the page plan names a column key that no single Column value carries"
            raise LayoutError(msg)
        ordered.append(found)
    return ordered


def _cells(
    column: Column, drawn_of: Mapping[Handle, DrawnFunction], profile: Profile, label_boxes: FnBoxes
) -> list[list[_Cell]]:
    """The rows of one column (cells sharing an index are one row, R4), left to right by lane."""
    if not column.cells:
        msg = "a column has no cells, so it has nothing to place"
        raise LayoutError(msg)
    grouped: dict[int, list[Cell]] = {}
    for cell in column.cells:
        grouped.setdefault(cell.index, []).append(cell)
    rows = []
    for index, (_, row_cells) in enumerate(sorted(grouped.items())):
        row: list[_Cell] = []
        for cell in sorted(row_cells, key=lambda cell: cell.lane):
            function = drawn_of.get(cell.function)
            if function is None:
                msg = "a column cell names a function that is not drawn"
                raise LayoutError(msg)
            function = _turned_function(function, cell)
            band = None
            if not row and cell.host is None:
                band = band_of(function.kind, profile.band_ranks, index=index, of=len(grouped))
            row.append(
                _Cell(
                    function=cell.function,
                    column=column.key,
                    geometry=function.geometry,
                    band=band,
                    role=column.role,
                    axis_offset=axis_offset(function),
                    lane=cell.lane,
                    side=cell.side,
                    low=cell.low,
                    carrier=cell.carrier,
                    host=cell.host,
                    port=cell.port,
                    face=cell.face,
                    span_port=cell.span_port,
                    # R6 D4, R7 B6a: generic boxes, connectors and terminals are not stretched
                    boxy=function.geometry.generic_box or function.roles.boxy,
                )
            )
        _fit_row(row, drawn_of, label_boxes)
        rows.append(row)
    return rows


def _turned_function(function: DrawnFunction, cell: Cell) -> DrawnFunction:
    """`function`, its symbol turned when `cell` is a flipped one (`references.joins` reads it)."""
    if not cell.flip or function.geometry.generic_box:
        return function
    # R5 rule 3: the side element's other port on top. D1: a turned directed pole
    # is mirrored as well (MR180), so top and bottom swap and its poles, markings
    # and tag keep their left-to-right places; every other flip is R180
    flipped = symbol_geometry(
        function.geometry.key,
        poles=function.geometry.poles,
        orientation=Orientation.MR180 if cell.mirror else Orientation.R180,
    )
    return dataclasses.replace(function, geometry=flipped)


def _fit_row(
    row: Sequence[_Cell], drawn_of: Mapping[Handle, DrawnFunction], label_boxes: FnBoxes
) -> None:
    """Trim the tag slots of a packed row and grow every keep-out over its labels."""
    lanes = [cell for cell in row if not cell.side]
    # R5.2: lanes of one item (followers show no tag) or of terminals and pins (their
    # texts are narrow) pack tag-less; C1 (iii): lanes of different items keep their tag
    items = {drawn_of[cell.function].item for cell in lanes}
    narrow = all(drawn_of[cell.function].roles.narrow for cell in lanes)
    tagless = len(lanes) > 1 and (len(items) == 1 or narrow)
    if tagless:
        for cell in lanes:
            cell.geometry = _without_tag(cell.geometry)
    # C8(b): the keep-out grows over the labels' measured boxes (a tag-less lane's tag
    # stays out); the designer: a tag's keep-out is its measured text, not the fixed slot
    for cell in row:
        boxes = [
            box
            for slot, box in label_boxes.get(cell.function, ())
            if not (tagless and not cell.side and slot == "tag")
        ]
        if boxes and cell.geometry.orientation is Orientation.R0:
            trimmed = tagless and not cell.side  # already without its tag slot
            if not trimmed and any(slot == "tag" for slot, _ in label_boxes[cell.function]):
                cell.geometry = _without_tag(cell.geometry)
            cell.geometry = grow_keepout(cell.geometry, boxes)


def _text_room(
    page: Sequence[list[list[_Cell]]],
    profile: Profile,
    drawn_of: Mapping[Handle, DrawnFunction],
    texts: PageTexts | None,
) -> tuple[int, int]:
    """C14, S16: how far the first rows' texts reach above their keep-outs, the last rows' below."""
    marker = WIRING_GRID + profile.text_height + 2 * profile.marker_padding
    lift = sink = 0
    for rows in page:
        if not rows:
            continue
        for cell in rows[0]:
            k = cell.geometry.keepout
            body = cell.geometry.body
            mid = 2 * body.y + body.height  # a blocked label is reflected across the body
            tops = [slot.box.y for slot in cell.geometry.slots]  # oriented, tag included
            tops += [mid - slot.box.y - slot.box.height for slot in cell.geometry.slots]
            tops += [p.at.y - marker for p in cell.geometry.ports if p.facing is Facing.N]
            boxes = [Box(x=k.x, y=t, width=k.width, height=0) for t in tops]
            boxes += _owned(cell, drawn_of, texts, Facing.N, profile)
            up, _ = room_offset(cell.geometry, boxes)
            lift = max(lift, up)
        for cell in rows[-1]:
            k = cell.geometry.keepout
            body = cell.geometry.body
            mid = 2 * body.y + body.height
            ends = [slot.box.y + slot.box.height for slot in cell.geometry.slots]
            ends += [mid - slot.box.y for slot in cell.geometry.slots]
            ends += [p.at.y + marker for p in cell.geometry.ports if p.facing is Facing.S]
            boxes = [Box(x=k.x, y=e, width=k.width, height=0) for e in ends]
            boxes += _owned(cell, drawn_of, texts, Facing.S, profile)
            _, down = room_offset(cell.geometry, boxes)
            sink = max(sink, down)
    return snap_up(lift), snap_up(sink)


def _owned(
    cell: _Cell,
    drawn_of: Mapping[Handle, DrawnFunction],
    texts: PageTexts | None,
    facing: Facing,
    profile: Profile,
) -> list[Box]:
    """S16: the boxes of the texts `cell`'s function owns at a `facing` port; none with no texts."""
    if texts is None:
        return []
    return end_boxes(cell.geometry, drawn_of[cell.function], texts, facing, profile)


def _without_tag(geometry: SymbolGeometry) -> SymbolGeometry:
    """The geometry with a keep-out box that leaves out the tag slot (R5 rule 2)."""
    full = hull([geometry.body, *(slot.box for slot in geometry.slots)])
    trimmed = hull([geometry.body, *(s.box for s in geometry.slots if s.slot != "tag")])
    k = geometry.keepout
    left, top = full.x - k.x, full.y - k.y
    right = k.x + k.width - (full.x + full.width)
    bottom = k.y + k.height - (full.y + full.height)
    keepout = Box(
        x=trimmed.x - left,
        y=trimmed.y - top,
        width=trimmed.width + left + right,
        height=trimmed.height + top + bottom,
    )
    return dataclasses.replace(geometry, keepout=keepout)


def axis_offset(function: DrawnFunction) -> int:
    """The x inside the symbol that goes on the column axis (place.md 6.4, geometry.md 5.2)."""
    for name in (function.primary_in, function.primary_out):
        if name is None:
            continue
        port = next((port for port in function.geometry.ports if port.name == name), None)
        if port is None:
            msg = "a drawn function's primary port is not a port of its symbol"
            raise LayoutError(msg)
        if not on_wiring_grid(port.at):
            msg = "a drawn function's primary port is off the wiring grid"
            raise LayoutError(msg)
        return port.at.x
    body = function.geometry.body
    return snap_up(body.x + body.width // 2)


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
        if pitch and not row[0].side:  # C1 (iii): a row's first cell may sit in a later lane
            row[0].dx = row[0].lane * pitch
        for previous, cell in pairwise(row):
            packed = _next_slot(previous, cell)
            # R5 rule 2: pole lanes sit exactly at the pole pitch, never inside the cell before
            # (a multi-pole cell's keep-out spans several lanes, D2); a lane after a multi-pole
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
    """C12: a function spanning lanes has its reached port under its lane."""
    for row in rows:
        for cell in row:
            if cell.span_port and cell.host is None:
                port_x = next(p.at.x for p in cell.geometry.ports if p.name == cell.span_port)
                cell.dx = (cell.lane * pitch if pitch else 0) + cell.axis_offset - port_x


def _widest_step(rows: Sequence[list[_Cell]]) -> int | None:
    """R7 A6: with no pole pitch, one pitch for every pole-lane row: the widest packed step."""
    steps = [
        _next_slot(previous, cell, 0)
        for row in rows
        if not all(cell.host is not None for cell in row)
        for previous, cell in pairwise(row)
        if not cell.side and not previous.side
    ]
    return max(steps, default=None)


def _spread(page: Sequence[list[list[_Cell]]], column_gap: int) -> None:
    """Give every column its axis, left to right, keep-out edges a column gap apart."""
    left = 0
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
    """R13: a column's rows stack from the top at `spacing` (or its `narrowed` one, M11)."""
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
    """Put each side element's port on its host's port y (R5 rule 3)."""
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
    """R7 A: a lower pin's mating face on its upper pin's, touching (mated-pair J1, J3, D8)."""
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


def _align_bands(
    page: Sequence[list[list[_Cell]]],
    ranks: frozendict[str, int],
    gaps_of: _GapsOf,
    *,
    floor: int,
    stacked: Mapping[tuple[int, int], int],
) -> None:
    """Align each band's participants, top band first, after spacing (R7 B7, A9, layout-0061)."""
    found = _participants(page)
    aligned: dict[int, set[int]] = {}
    blocks = partial(_blocks, page, gaps_of, aligned)
    fits = partial(_fits, page, gaps_of, floor)
    for band in sorted(found, key=lambda key: (ranks[key[0]], key[0], str(key[1]))):
        if band[0].endswith(".last"):
            continue
        top, members = _settle_band(page, found[band], stacked, blocks, fits)
        if len(members) < 2:  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
            continue
        for column, index in members:
            _bring_to(page[column], index, top, gaps_of(page[column]))
            aligned.setdefault(column, set()).add(index)


_Member = tuple[int, int]


def _blocks(
    page: Sequence[list[list[_Cell]]],
    gaps_of: _GapsOf,
    aligned: Mapping[int, set[int]],
    member: _Member,
    top: int,
) -> bool:
    """Whether bringing `member` to `top` would move a row some band already aligned."""
    rows = page[member[0]]
    return _moves_an_aligned_row(rows, member[1], top, gaps_of(rows), aligned.get(member[0], set()))


def _fits(
    page: Sequence[list[list[_Cell]]], gaps_of: _GapsOf, floor: int, member: _Member, top: int
) -> bool:
    """Whether lowering `member` to `top` keeps its column above `floor`."""
    rows = page[member[0]]
    return _cascade_bottom(rows, member[1], top, gaps_of(rows)) <= floor


def _settle_band(
    page: Sequence[list[list[_Cell]]],
    members: Sequence[_Member],
    stacked: Mapping[_Member, int],
    blocks: Callable[[_Member, int], bool],
    fits: Callable[[_Member, int], bool],
) -> tuple[int, list[_Member]]:
    """Drop participants until the rest share one top; return that top and who stays."""
    top = 0
    members = list(members)
    while len(members) > 1:
        top = _band_top(page, members, stacked)
        blockers = [m for m in members if blocks(m, top)]
        if not blockers and all(fits(m, top) for m in members):
            break
        # the participant that can rise least leaves the band (A9)
        members.remove(max(blockers or members, key=lambda m: (stacked[m], m)))
    return top, members


def _bring_to(rows: Sequence[list[_Cell]], index: int, top: int, gaps: Sequence[int]) -> None:
    """Move `rows[index]` to `top`: raise it from below, cascade it from above."""
    current = min(cell.top for cell in rows[index])
    if current > top:
        _raise(rows, index, top, gaps)
    elif current < top:
        _cascade(rows, index, top, gaps)


def _moves_an_aligned_row(
    rows: Sequence[list[_Cell]],
    index: int,
    top: int,
    gaps: Sequence[int],
    aligned: AbstractSet[int],
) -> bool:
    """Whether bringing `rows[index]` to `top` would move a row of `aligned` (D3, layout-0061)."""
    current = min(cell.top for cell in rows[index])
    if current > top:
        moves = _raise_plan(rows, index, top, gaps)
    elif current < top:
        moves = _cascade_plan(rows, index, top, gaps)
    else:
        return False
    return any(row in aligned for row, _ in moves)


def _raise(rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]) -> None:
    """Raise `rows[start]` to `top`; the rows above it move up only as far as they must."""
    for index, shift in _raise_plan(rows, start, top, gaps):
        for cell in rows[index]:
            cell.at_top(cell.top - shift)


def _raise_plan(
    rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]
) -> list[tuple[int, int]]:
    """The moves of `_raise` as (row index, shift up), the start row first (D3)."""
    shift = min(cell.top for cell in rows[start]) - top
    moves = [(start, shift)]
    below = min(cell.top_at(cell.top - shift) for cell in rows[start])
    for index in range(start - 1, -1, -1):
        excess = max(cell.bottom for cell in rows[index]) - (below - gaps[index])
        if excess <= 0:
            break
        moves.append((index, excess))
        below = min(cell.top_at(cell.top - excess) for cell in rows[index])
    return moves


def _cascade(rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]) -> None:
    """Lower `rows[start]` to `top` and push the rows below just far enough to follow."""
    _apply(rows, _cascade_plan(rows, start, top, gaps))


def _cascade_plan(
    rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]
) -> list[tuple[int, int]]:
    """The moves of `_cascade` as (row index, new top), the start row first (D3)."""
    moves = flow(
        rows[start:],
        floor=top,
        gaps=gaps[start:],
        far_edge=_row_bottom,
        near_edge=lambda row: min(cell.top for cell in row),
    )
    return [(start + index, new_top) for index, new_top in moves]


def _overfull(cells: Sequence[_Cell], content_height: int) -> tuple[Finding, ...]:
    """One `PAGE_OVERFULL` naming every cell whose keep-out reaches below the page (layout-0083)."""
    below = sorted(cell.function for cell in cells if cell.bottom > content_height)
    if not below:
        return ()
    return (
        Finding(
            code=PAGE_OVERFULL,
            severity=Severity.WARNING,
            subjects=tuple(below),
            message="page content is taller than the content box: nothing is scaled",
        ),
    )
