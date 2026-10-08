"""HL12, HL20: a middle unit's group folded on its page: bands, outline, boxes and title."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, LayoutError, Point, hull, snap_up, text_width

from ._gather import Band, Bands, banded
from .connector_boxes import HALF, PlacedConnectorBox, box_size
from .edges import along
from .lookups import placed_keepout
from .middle_cut import fold_overfull, measured, stack_lower
from .middle_replicas import replica_height, replica_places, replica_width, replicas

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey, Finding, Id

    from .middle import MiddleGroup, MiddleInterface
    from .pagerun import PageInputs
    from .types import PagePlan, PlacedFunction, Profile

FAN = 4 * WIRING_GRID  # HL17: the fan-out's split distance, the room a line needs past a box


@dataclass(frozen=True)
class GroupShape:
    """One middle outline on one page: its frame, title box, lead and the boxes on its edges."""

    unit: Id[Any]
    lead: Id[Any]
    drawing_set: int
    page: int
    outline: Box
    title: Box
    boxes: tuple[PlacedConnectorBox, ...]
    bottom: int = 0  # TALL-PAGE T1: how far down the folded group reaches
    held: bool = False  # replicas on both edges: no cut works, the group is never cut
    below: bool = (
        False  # TALL-PAGE A1: replicas in the upper band, so the cut is at the bottom edge
    )
    frame_dx: int = (
        0  # TALL-PAGE: the outline's left edge from the lower columns' (the cut's value)
    )

    def moved(self, dx: int, dy: int) -> GroupShape:
        """This shape moved by `(dx, dy)`, as `shift_pages` moves its page."""
        return replace(
            self,
            bottom=self.bottom + dy,
            outline=_by(self.outline, dx, dy),
            title=_by(self.title, dx, dy),
            boxes=tuple(
                replace(
                    one,
                    box=_by(one.box, dx, dy),
                    texts=tuple(Point(x=p.x + dx, y=p.y + dy) for p in one.texts),
                )
                for one in self.boxes
            ),
        )


@dataclass(frozen=True)
class _Page:
    """What folding reads of one page: its columns' keep-out hulls in plan order, and its frame."""

    plan: PagePlan
    hulls: Mapping[AuthoringKey, Box]
    order: tuple[AuthoringKey, ...]
    top: int
    profile: Profile
    reps: Mapping[Id[Any], tuple[list[PlacedFunction], list[PlacedFunction]]]


def shape_boxes(shapes: Sequence[GroupShape]) -> tuple[Box, ...]:
    """What a folded group's shapes keep the page's first labels out of: outline, title, boxes."""
    return tuple(
        box
        for shape in shapes
        for box in (shape.outline, shape.title, *(one.box for one in shape.boxes))
    )


def _by(box: Box, dx: int, dy: int) -> Box:
    return Box(x=box.x + dx, y=box.y + dy, width=box.width, height=box.height)


def fold_page(
    placed: tuple[PlacedFunction, ...],
    plan: PagePlan,
    groups: Mapping[AuthoringKey, tuple[MiddleGroup, ...]],
    profile: Profile,
) -> tuple[tuple[PlacedFunction, ...], tuple[GroupShape, ...]]:
    """HL20: each group on the page first, its bands about its outline; the rest to its right."""
    here = _here(placed, plan, groups)
    if not here:
        return placed, ()
    page, cursor = _page(placed, plan, here, profile)
    moves: dict[AuthoringKey, tuple[int, int]] = {}
    shapes = []
    places: dict[Id[Any], Point] = {}
    for group in here:
        shape, cursor, folded = _fold_group(group, page, cursor, frozenset(moves))
        moves.update(folded)
        shapes.append(shape)
        places.update(_replica_places(shape, page.reps[group.unit.unit], profile.column_gap))
    rest = [key for key in page.order if key not in moves]
    moves.update(_pack(rest, page.hulls, cursor, profile.column_gap)[0])
    moved = _moved(placed, moves)
    return tuple(replace(one, at=places.get(one.function, one.at)) for one in moved), tuple(shapes)


def folded_page(
    placed: tuple[PlacedFunction, ...],
    plan: PagePlan,
    inputs: PageInputs,
    found: tuple[Finding, ...],
) -> tuple[tuple[PlacedFunction, ...], tuple[GroupShape, ...], tuple[Finding, ...]]:
    """The page folded (HL20) with its `PAGE_OVERFULL` widened by the fold's reach (T6)."""
    height = inputs.sheet.content_height
    folded, shapes = fold_page(placed, plan, inputs.middle, inputs.profile)
    return folded, shapes, fold_overfull(folded, shapes, height, found)


def _here(
    placed: tuple[PlacedFunction, ...],
    plan: PagePlan,
    groups: Mapping[AuthoringKey, tuple[MiddleGroup, ...]],
) -> list[MiddleGroup]:
    """The groups with a column on the page, in the page's column order, each once.

    A cut group (TALL-PAGE T2) is on the page of its lower band only, where its outline stands;
    one cut below (A1) is on the page of its upper band, where its outline stands.
    """
    columns = {one.column for one in placed}
    keys = [one.column for one in plan.columns if one.column in columns]
    found = {g.unit.unit: g for k in keys for g in groups.get(k, ())}.values()
    return [g for g in found if not g.cut or ((g.upper if g.below else g.lower) & set(keys))]


def _page(
    placed: tuple[PlacedFunction, ...],
    plan: PagePlan,
    here: Sequence[MiddleGroup],
    profile: Profile,
) -> tuple[_Page, int]:
    """The page as folding reads it, its replicas apart from its hulls; the left edge."""
    reps = {group.unit.unit: replicas(group, placed) for group in here}
    gone = {one.function for pair in reps.values() for one in (*pair[0], *pair[1])}
    hulls = _hulls([one for one in placed if one.function not in gone])
    order = tuple(one.column for one in plan.columns if one.column in hulls)
    whole = hull([placed_keepout(one) for one in placed])  # replicas too: a page may hold only them
    return _Page(plan, hulls, order, whole.y, profile, reps), whole.x


def _replica_places(
    shape: GroupShape, reps: tuple[list[PlacedFunction], list[PlacedFunction]], gap: int
) -> dict[Id[Any], Point]:
    """HL11: each replica inside the outline at its edge, after that edge's boxes."""
    frame = shape.outline
    places: dict[Id[Any], Point] = {}
    for edge, top in ((reps[0], True), (reps[1], False)):
        y = frame.y if top else frame.y + frame.height
        ends = [b.box.x + b.box.width for b in shape.boxes if y in (b.box.y, _bottom(b.box))]
        start = max(ends, default=frame.x + HALF - gap) + gap
        places.update(replica_places(edge, frame, snap_up(start), gap, top=top))
    return places


def middle_bands(groups: Mapping[AuthoringKey, tuple[MiddleGroup, ...]], profile: Profile) -> Bands:
    """HL21: each group's bands and outline width, a column gap included, packed as one unit."""
    unique = {group.unit.unit: group for found in groups.values() for group in found}.values()
    return banded(
        [
            Band(
                upper=group.upper,
                lower=group.lower,
                outline=_outline_width(group, _sides(group), profile) + profile.column_gap,
                cut=group.cut,
                below=group.below,
            )
            for group in unique
        ]
    )


def _sides(group: MiddleGroup) -> tuple[list[MiddleInterface], list[MiddleInterface]]:
    """The line interfaces on the top edge and on the bottom edge, in no particular order."""
    lines = [one for one in group.unit.interfaces if one.edge.line]
    top = [one for one in lines if one.edge.function in group.top]
    return top, [one for one in lines if one.edge.function not in group.top]


def _hulls(placed: Sequence[PlacedFunction]) -> dict[AuthoringKey, Box]:
    """Each column's keep-out hull on the page."""
    boxes: dict[AuthoringKey, list[Box]] = {}
    for one in placed:
        boxes.setdefault(one.column, []).append(placed_keepout(one))
    return {key: hull(found) for key, found in boxes.items()}


def _pack(
    keys: Sequence[AuthoringKey], hulls: Mapping[AuthoringKey, Box], left: int, gap: int
) -> tuple[dict[AuthoringKey, tuple[int, int]], int]:
    """`keys` side by side from `left`, a gap apart, moved by whole grids; the right edge."""
    moves: dict[AuthoringKey, tuple[int, int]] = {}
    right = left
    for key in keys:
        dx = snap_up(left - hulls[key].x)
        moves[key] = (dx, 0)
        right = hulls[key].x + dx + hulls[key].width
        left = right + gap
    return moves, right


def _moved(
    placed: Sequence[PlacedFunction], moves: Mapping[AuthoringKey, tuple[int, int]]
) -> tuple[PlacedFunction, ...]:
    return tuple(_step(one, *moves.get(one.column, (0, 0))) for one in placed)


def _step(one: PlacedFunction, dx: int, dy: int) -> PlacedFunction:
    return replace(one, at=Point(x=one.at.x + dx, y=one.at.y + dy)) if dx or dy else one


def _fold_group(
    group: MiddleGroup, page: _Page, cursor: int, taken: frozenset[AuthoringKey]
) -> tuple[GroupShape, int, dict[AuthoringKey, tuple[int, int]]]:
    """One group from `cursor`: its upper band, its outline below it, its lower band below that.

    A column an earlier group took stays there (HL20), and one in both bands stands below.
    """
    gap, height = page.profile.column_gap, page.profile.text_height
    lower = [key for key in page.order if key in group.lower and key not in taken]
    upper = [k for k in page.order if k in group.upper and k not in taken and k not in lower]
    up_moves, up_right = _pack(upper, page.hulls, cursor, gap)
    low_moves, low_right = _pack(lower, page.hulls, cursor, gap)
    top, bottom = _edges(group, page, {**up_moves, **low_moves})
    wide = _outline_width(group, (top, bottom), page.profile, page.reps[group.unit.unit])
    left, span = _frame_left(group, (cursor, up_right, low_right), wide)
    above = max((_bottom(page.hulls[key]) for key in upper), default=page.top)
    frame = _frame(group, page, Point(x=left, y=above), wide)
    deepest = frame.y + frame.height + _plug_room(bottom, page.reps[group.unit.unit][1], height)
    moves = {**up_moves, **stack_lower(lower, page.hulls, low_moves, deepest)}
    shape = measured(_shape(group, page, frame, (top, bottom)), group, page, (lower, moves))
    shape = replace(shape, frame_dx=left - cursor)
    return shape, cursor + span + gap, moves


def _frame_left(group: MiddleGroup, edges: tuple[int, int, int], wide: int) -> tuple[int, int]:
    """The outline's left edge, centred on the bands, and the span from `cursor` it ends.

    A group cut at its top edge (TALL-PAGE) has no upper band on its page: the outline stands
    where the uncut fold put it (`frame_dx`, measured by the first pass).
    """
    cursor, up_right, low_right = edges
    span = max(up_right, low_right, cursor + wide) - cursor
    left = cursor + (span - wide) // 2
    if group.cut and not group.below:
        left = cursor + group.frame_dx
    left = snap_up(left)
    return left, max(span, left + wide - cursor)


def _outline_width(
    group: MiddleGroup,
    sides: tuple[Sequence[MiddleInterface], Sequence[MiddleInterface]],
    profile: Profile,
    reps: tuple[list[PlacedFunction], list[PlacedFunction]] | None = None,
) -> int:
    """HL11: the wider edge's natural width, its boxes then its replicas, never under the title."""
    gap, height = profile.column_gap, profile.text_height
    reps = reps or ([], [])
    wide = max(
        _edge_width(sides[0], gap, height) + replica_width(reps[0], gap),
        _edge_width(sides[1], gap, height) + replica_width(reps[1], gap),
    )
    return snap_up(max(wide, text_width(group.unit.title, height=height) + 2 * HALF))


def _bottom(box: Box) -> int:
    return box.y + box.height


def _edges(
    group: MiddleGroup, page: _Page, moves: Mapping[AuthoringKey, tuple[int, int]]
) -> tuple[list[MiddleInterface], list[MiddleInterface]]:
    """The page's line interfaces on each edge, in the x order of the columns their lines reach.

    A group split over pages draws on each only the interfaces reaching it (HL21 ruling (a)).
    """
    lines = {
        one.edge.function: one
        for one in group.unit.interfaces
        if one.edge.line and (group.cut or _reaches(group.reach.get(one.edge.function, ()), page))
    }
    reach_x = {
        function: min(
            (page.hulls[key].x + moves[key][0] for key in group.reach[function] if key in moves),
            default=0,
        )
        for function in lines
    }
    top = along([f for f in lines if f in group.top], reach_x)
    bottom = along([f for f in lines if f not in group.top], reach_x)
    return [lines[f] for f in top], [lines[f] for f in bottom]


def _reaches(keys: Sequence[AuthoringKey], page: _Page) -> bool:
    """An interface reaching no column at all stands on every page of its group."""
    return not keys or any(key in page.hulls for key in keys)


def _sizes(one: MiddleInterface, height: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """The interface box's and its plug box's (width, height); a plug of none is (0, 0)."""
    plug = box_size(one.plug_lines, [], text_height=height) if one.plug_lines else (0, 0)
    return box_size(one.lines, [], text_height=height), plug


def _edge_width(edge: Sequence[MiddleInterface], gap: int, height: int) -> int:
    """HL11: an edge's natural width: boxes side by side, a column gap apart, half a grid out."""
    boxes = [_sizes(one, height)[0][0] for one in edge]
    return sum(boxes) + gap * max(len(boxes) - 1, 0) + 2 * HALF


def _tallest(edge: Sequence[MiddleInterface], height: int, *, plug: bool) -> int:
    return max((_sizes(one, height)[plug][1] for one in edge), default=0)


def _edge_tall(edge: Sequence[MiddleInterface], reps: Sequence[PlacedFunction], height: int) -> int:
    """An edge's depth inside the outline: its tallest box, or its replicas a grid in."""
    tall = _tallest(edge, height, plug=False)
    return max(tall, replica_height(reps) + WIRING_GRID) if reps else tall


def _plug_room(edge: Sequence[MiddleInterface], reps: Sequence[PlacedFunction], height: int) -> int:
    """The band gap (HL20): the plug box, the line's fan-out room and one grid.

    An edge of replicas also gets a track for each, the most wires that can need one at once (RR2).
    """
    line = _tallest(edge, height, plug=True) + FAN + WIRING_GRID
    return snap_up(max(line, len(reps) * WIRING_GRID))


def _frame(group: MiddleGroup, page: _Page, at: Point, wide: int) -> Box:
    """The outline below the upper band's deepest keep-out, at `at.x`, `wide` across (HL11)."""
    height = page.profile.text_height
    top, bottom = _edges(group, page, {})
    reps = page.reps[group.unit.unit]
    tall = _edge_tall(top, reps[0], height) + _edge_tall(bottom, reps[1], height)
    y = snap_up(at.y + _plug_room(top, reps[0], height))
    return Box(x=at.x, y=y, width=wide, height=snap_up(tall + height + 2 * WIRING_GRID + 2 * HALF))


def _shape(
    group: MiddleGroup,
    page: _Page,
    frame: Box,
    sides: tuple[Sequence[MiddleInterface], Sequence[MiddleInterface]],
) -> GroupShape:
    """The outline's boxes on its edges, the plugs outside them, the title inside left (HL11)."""
    height = page.profile.text_height
    boxes = [*_edge_boxes(sides[0], frame, page, top=True), *_edge_boxes(sides[1], frame, page)]
    tall = _edge_tall(sides[0], page.reps[group.unit.unit][0], height)
    title = Box(
        x=frame.x + HALF,
        y=frame.y + tall + WIRING_GRID,
        width=text_width(group.unit.title, height=height),
        height=height,
    )
    lead = _lead(group, sides, page.reps[group.unit.unit])
    plan = page.plan
    return GroupShape(
        group.unit.unit, lead, plan.drawing_set, plan.number, frame, title, tuple(boxes)
    )


def _lead(
    group: MiddleGroup,
    sides: tuple[Sequence[MiddleInterface], Sequence[MiddleInterface]],
    reps: tuple[list[PlacedFunction], list[PlacedFunction]],
) -> Id[Any]:
    """layout-0164: the first interface of the group on the page: lines by edge, then replicas."""
    owner = {view: one.edge.function for one in group.unit.interfaces for view in one.views}
    found = [one.edge.function for one in (*sides[0], *sides[1])]
    found += [owner[one.function] for one in (*reps[0], *reps[1]) if one.function in owner]
    if not found:
        msg = f"the unit group {group.unit.title!r} draws no interface on its page"
        raise LayoutError(msg)
    return found[0]


def _edge_boxes(
    edge: Sequence[MiddleInterface], frame: Box, page: _Page, *, top: bool = False
) -> list[PlacedConnectorBox]:
    """One edge's interface boxes, centred along it, and each plug's box face to face outside."""
    height, gap = page.profile.text_height, page.profile.column_gap
    x = frame.x + snap_up((frame.width - _edge_width(edge, gap, height)) // 2) + HALF
    found = []
    for one in edge:
        (wide, tall), (plug_wide, plug_tall) = _sizes(one, height)
        y = frame.y if top else frame.y + frame.height - tall
        found.append(
            _box(one.edge.function, one.lines, Box(x=x, y=y, width=wide, height=tall), page)
        )
        if one.plug is not None:
            plug_y = y - plug_tall if top else y + tall
            at = Box(x=x + (wide - plug_wide) // 2, y=plug_y, width=plug_wide, height=plug_tall)
            found.append(_box(one.plug, one.plug_lines, at, page))
        x += wide + gap
    return found


def _box(function: Id[Any], lines: Sequence[str], box: Box, page: _Page) -> PlacedConnectorBox:
    """A cell-less box (HL5) at `box`, its text lines from the top, padded by half a grid."""
    step = page.profile.text_height + WIRING_GRID
    return PlacedConnectorBox(
        function=function,
        drawing_set=page.plan.drawing_set,
        page=page.plan.number,
        box=box,
        texts=tuple(Point(x=box.x + HALF, y=box.y + HALF + i * step) for i in range(len(lines))),
        cells=(),
    )
