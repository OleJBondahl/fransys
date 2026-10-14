"""Stage 4, place: a grid position for every drawn function on one page."""

import dataclasses
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    Orientation,
    Point,
    hull,
    on_wiring_grid,
    snap_up,
)
from fransys_model.kernel import Finding, Severity

from . import lookups
from ._band_settle import _align_bands, _cascade
from ._bands import band_of
from ._row_align import _align_faces, _align_sides, _space, _spread, _stack
from .line_room import line_room
from .references.marker_boxes import FLOOR, Digits, reference_box_width
from .room import grow_keepout, room_offset
from .row_parts import share_spacing
from .stack_room import make_room
from .stacking import JoinedRun, PageStack, StackedPort, blocks, gaps_below
from .texts.stand import end_boxes
from .turned import _turned_function
from .types import PlacedFunction

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

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
    role: object = None  # The column's role; a band aligns one role only
    span_port: str = ""
    host: Handle | None = None
    port: str = ""
    face: bool = False
    dx: int = 0  # the cell's axis, right of the column axis
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
    """Place the columns of `plan` left to right, cells top to bottom (layout-0035)."""
    drawn_of = lookups.drawn_of(drawn, "place")
    page, top, floor, gaps_of = _stacked(plan, columns, drawn_of, stacking, joins)
    # Each row's top at minimum pitch with the spacing kept (blocks `row_spacing`
    # apart, `row_gap` inside a block and in a column of only boxes): how high it can go
    stacked = {
        (c, i): min(cell.top for cell in row)
        for c, rows in enumerate(page)
        for i, row in enumerate(rows)
    }
    _align_bands(page, stacking.profile.band_ranks, gaps_of, floor=floor, stacked=stacked)
    _align_joins(page, tuple(run for run in joins if run.aside), drawn_of, top, gaps_of)
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
    """The page as `place` stacks it before its bands, but with no `texts`."""
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
    """Each joined run's ports on one y at its deepest port, before the bands."""
    by_key = {rows[0][0].column: rows for rows in page}
    for run in joins:
        ends = [
            (
                by_key[end.column],
                dict(_column_ports(by_key[end.column], drawn_of, top))[end.port],
                end.drop,
            )
            for end in run.ends
        ]
        offsets = [one.offset + drop for _, (_, one), drop in ends]
        y = next((at for at, e in zip(offsets, run.ends, strict=True) if e.anchor), max(offsets))
        for (rows, (first, one), drop), at in zip(ends, offsets, strict=True):
            if at < y:  # else at the run's y, or a branch end already deeper than its anchor
                start = next(index for index, row in enumerate(rows) if row is first)
                new_top = min(cell.top for cell in first) + y - one.offset - drop
                _cascade(rows, start, new_top, gaps_of(rows))


def _stacked(
    plan: PagePlan,
    columns: tuple[Column, ...],
    drawn_of: Mapping[Handle, DrawnFunction],
    stacking: PageStacking,
    joins: tuple[JoinedRun, ...] = (),
) -> tuple[list[list[list[_Cell]]], int, int, _GapsOf]:
    """`place`'s steps before its bands, passes included: cells stacked, top, floor, gaps."""
    narrowed: dict[AuthoringKey, int] = {}
    while True:
        gaps_of = _gaps_of(stacking.profile, narrowed)
        page, top, floor = _stack_page(plan, columns, drawn_of, stacking, narrowed)
        _align_joins(page, joins, drawn_of, top, gaps_of)
        runs = [frozenset(end.column for end in run.ends) for run in joins if not run.aside]
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
    """`narrowed` with each overfull column's spacing cut by its overhang over its gaps."""
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
    return share_spacing(again, [rows[0][0].column for rows in page], profile.row_spacing)


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
    _spread(page, profile.column_gap, sheet.inset)
    # The first rows leave room above for their texts (tags, point texts, markers on N
    # ports) and the last rows below, inside the content box
    lift, sink = _text_room(page, profile, drawn_of, texts)
    # layout-0154 (layout-0158): and room for a leaving line and its stub beyond a line's pins
    up, down = line_room(page, drawn_of, stacking.line_ends, profile)
    # Every page keeps it, a reference or none
    band = _reference_band(sheet, profile, stacking.digits)
    lift, sink = max(lift, band, up), max(sink, band, down)
    # Two ports stacked along a stub stand as far apart as the texts at them reach out
    make_room(page, drawn_of, texts, gaps_of=gaps_of, profile=profile)
    top = sheet.inset + stacking.headroom_lanes * WIRING_GRID + lift
    for rows in page:
        _stack(rows, profile.row_gap, top=top)
    floor = sheet.bottom - stacking.bottom_headroom_lanes * WIRING_GRID - sink
    _align_faces(page)  # A mated pair touches before the spacing measures it
    _space(page, profile.row_spacing, narrowed)
    return page, top, floor


def _reference_band(sheet: SheetFormat, profile: Profile, digits: Digits = FLOOR) -> int:
    """The top and bottom band height, a turned reference plus stub clearance, on every page."""
    return snap_up(WIRING_GRID + reference_box_width(sheet, profile, digits=digits))


def _in_plan_order(plan: PagePlan, columns: tuple[Column, ...]) -> list[Column]:
    """The page's columns, left to right, matched to `plan.columns` by key."""
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
    """The rows of one column (cells sharing an index are one row), left to right by lane."""
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
                    # Generic boxes, connectors and terminals are not stretched
                    boxy=function.geometry.generic_box or function.roles.boxy,
                )
            )
        _fit_row(row, drawn_of, label_boxes)
        rows.append(row)
    return rows


def _fit_row(
    row: Sequence[_Cell], drawn_of: Mapping[Handle, DrawnFunction], label_boxes: FnBoxes
) -> None:
    """Trim the tag slots of a packed row and grow every keep-out over its labels."""
    lanes = [cell for cell in row if not cell.side]
    # Lanes of one item (followers show no tag) or of terminals and pins (their
    # texts are narrow) pack tag-less; lanes of different items keep their tag
    items = {drawn_of[cell.function].item for cell in lanes}
    narrow = all(drawn_of[cell.function].roles.narrow for cell in lanes)
    tagless = len(lanes) > 1 and (len(items) == 1 or narrow)
    if tagless:
        for cell in lanes:
            cell.geometry = _without_tag(cell.geometry)
    # The keep-out grows over the labels' measured boxes (a tag-less lane's tag
    # stays out); a tag's keep-out is its measured text, not the fixed slot
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
    """How far the first rows' texts reach above their keep-outs, the last rows' below."""
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
    """The boxes of the texts `cell`'s function owns at a `facing` port; none with no texts."""
    if texts is None:
        return []
    return end_boxes(cell.geometry, drawn_of[cell.function], texts, facing, profile)


def _without_tag(geometry: SymbolGeometry) -> SymbolGeometry:
    """The geometry with a keep-out box that leaves out the tag slot."""
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
    """The x inside the symbol that goes on the column axis."""
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
