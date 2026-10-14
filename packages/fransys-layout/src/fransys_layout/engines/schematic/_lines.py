"""The engine's glue for harness lines (layout-0154): strip, then draw.

A conductor a line carries is never a route and never a marker; its line draws it, after the
outlines and the routes, from the boxes and pins standing on each page.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from itertools import pairwise
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import OPPOSITE, WIRING_GRID, Box, Facing, pad
from fransys_layout.geometry.units import TEXT_GAP
from fransys_layout.lint import HarnessInk
from fransys_layout.stages.content import content_box, drawn_extent
from fransys_layout.stages.fan_tags import tags_out_of_fans
from fransys_layout.stages.grid_path import cells_of
from fransys_layout.stages.harness_route import Grid, line_text, text_centre
from fransys_layout.stages.line_draw import EndOnPage, PinAt, drawn_end, line_pieces
from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLine, LineStub, slant_boxes
from fransys_layout.stages.line_trunk import LEAVE_GRIDS
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.route import port_end
from fransys_layout.stages.space import Shape, Space, span
from fransys_layout.stages.texts.place_texts import place_texts
from fransys_layout.stages.types import PlacedLabel
from fransys_model.kernel import Finding, value

from .read.harness_lines import drawn_on, line_owners, line_reads
from .read.line_box_end import boxed_end, rows_of
from .read.line_texts import LineTexts, line_texts, stub_box, widest_stub
from .read.stub_places import line_spots

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_layout.stages.line_draw import Pieces
    from fransys_layout.stages.middle import MiddleUnit
    from fransys_layout.stages.types import Connection, DrawnFunction, PlacedFunction, Profile
    from fransys_model.kernel import Id, Model

    from .read import StageInputs
    from .read.harness_lines import HarnessLineEnd, LineRead, LineReads

type _Page = tuple[int, int]
type _Context = tuple[LineTexts, _World, LineScene]
type _Routed = dict[_Page, list[tuple[LineRead, Pieces]]]

BUSY = 8 * WIRING_GRID  # layout-0167: a covered cell costs eight steps; cross, never run along


def strip_lines(model: Model, inputs: StageInputs) -> tuple[StageInputs, LineReads]:
    """The run without the conductors lines carry, routed or crossing; the lines read."""
    lines = line_reads(model)
    carried = [*inputs.connections, *inputs.crossing]
    stripped = replace(
        inputs,
        connections=tuple(c for c in inputs.connections if c.handle not in lines.carried),
        crossing=tuple(c for c in inputs.crossing if c.handle not in lines.carried),
        carried=tuple(c for c in carried if c.handle in lines.carried),
    )
    return stripped, lines


@dataclass(frozen=True)
class LineScene:
    """What the lines read of the finished run, page by page."""

    placed: tuple[PlacedFunction, ...]
    drawn: tuple[DrawnFunction, ...]
    boxes: tuple[PlacedConnectorBox, ...]
    labels: tuple[PlacedLabel, ...]
    keepouts: tuple[tuple[_Page, Id[Any], Any], ...]  # marker boxes: page, owner, box
    profile: Profile
    sheet: Any
    hidden: frozenset[Id[Any]] = frozenset()  # layout-0155: boxed pin views, which draw nothing
    units: Mapping[int, Id[Any] | None] = MappingProxyType({})  # each drawing set's unit
    wires: Mapping[_Page, tuple[Any, ...]] = MappingProxyType({})  # each page's wires as spans
    sides: Mapping[_Page, tuple[Box, ...]] = MappingProxyType({})  # the boxes no line runs along


@value
class DrawnPieces:
    """Every line's drawn pieces on every page, and a `LABEL_UNPLACED` for a label with no place."""

    lines: tuple[DrawnLine, ...] = ()
    fan_outs: tuple[DrawnFanOut, ...] = ()
    stubs: tuple[LineStub, ...] = ()
    findings: tuple[Finding, ...] = ()
    labels: tuple[PlacedLabel, ...] = ()  # the page's labels, a tag a fan wraps moved aside


@dataclass(frozen=True)
class _World:
    """The scene indexed once: placements by function and page, boxes, shapes, the units."""

    where: Mapping[Id[Any], Mapping[_Page, PlacedFunction]]
    drawn_of: Mapping[Id[Any], DrawnFunction]
    boxes: Mapping[Id[Any], Mapping[_Page, PlacedConnectorBox]]
    shapes: Mapping[_Page, list[Shape]]
    refs: Mapping[Id[Any], list[tuple[Id[Any], Any]]]
    interfaces: frozenset[Id[Any]]
    leaving: frozenset[Id[Any]]
    top: frozenset[Id[Any]]  # a top-level unit's interfaces: its own sheet draws their lines leave
    owner_of: Mapping[Id[Any], Id[Any]] = MappingProxyType({})  # a line end's port, its connector


def harness_ink(
    drawn: DrawnPieces, boxes: tuple[PlacedConnectorBox, ...], hidden: Sequence[Any]
) -> HarnessInk:
    """What the geometric lint reads of the lines and boxes (layout-0158).

    `hidden` is `box_views.drawn_hidden`: a boxed pin view that draws nothing on its page.
    """
    return HarnessInk(boxes, drawn.lines, drawn.fan_outs, drawn.stubs, frozenset(hidden))


def draw_lines(
    model: Model,
    lines: LineReads,
    carried: Sequence[Connection],
    units: Sequence[MiddleUnit],
    scene: LineScene,
) -> DrawnPieces:
    """Layout-0154: each line on each page its ends stand on, its labels placed (item 4)."""
    world = replace(_world(carried, units, scene), owner_of=line_owners(model, lines))
    texts = replace(
        line_texts(model, lines), spots=line_spots(model, lines, world), sheet=scene.sheet
    )
    grid = Grid(content_box(scene.sheet), (), scene.profile.route_turn_penalty)
    pieces = _route_pages(lines, grid, (texts, world, scene))
    found = DrawnPieces()
    for page in sorted(pieces):
        found = _page_pieces(found, page, pieces[page], (texts, world, scene))
    tags = tags_out_of_fans(scene.labels, scene.placed, found.fan_outs, found.lines, scene.sheet)
    return replace(found, labels=tags)


def _route_pages(lines: LineReads, grid: Grid, context: _Context) -> _Routed:
    """Every line routed on each page its ends stand on; later lines route around earlier ones."""
    _, world, scene = context
    pieces: _Routed = defaultdict(list)
    covered: dict[_Page, frozenset[Any]] = defaultdict(frozenset)
    for line in lines.lines:
        for page in _pages(line, world):
            on = (page, *_ends_on(line.ends, page, world))
            if on[1] and drawn_on(line, scene.units.get(page[0]), lines.top):
                here = replace(_grid(grid, page, world), busy=covered[page], busy_penalty=BUSY)
                here = replace(here, sides=scene.sides.get(page, ()))
                pieces[page].append((line, made := _route_line(line, on, here, context)))
                covered[page] |= frozenset().union(*(cells_of(pts) for _, pts in made.paths))
    return pieces


def _route_line(
    line: LineRead,
    on: tuple[_Page, Sequence[Any], Sequence[int]],
    here: Grid,
    context: _Context,
) -> Pieces:
    """One line's pieces on one page; routes keep the unplaced stub width, only the box grows."""
    (page, ends, absent), (texts, world, scene) = on, context
    unit = scene.units.get(page[0])
    wide = widest_stub(replace(texts, spots={}), line, (page, unit, ()), scene.profile)
    trunk = _trunk(line, ends, (page, here), world)
    high = scene.profile.text_height + 2 * scene.profile.marker_padding
    room = widest_stub(texts, line, (page, unit, tuple(absent)), scene.profile), high
    here = replace(here, stub=room, wires=scene.wires.get(page, ()))
    return line_pieces(
        ends,
        absent[0] if absent else None,
        here,
        margin=wide // 2,
        trunk=trunk and (trunk, (wide, high)),
    )


def _world(carried: Sequence[Connection], units: Sequence[MiddleUnit], scene: LineScene) -> _World:
    where: dict[Id[Any], dict[_Page, PlacedFunction]] = defaultdict(dict)
    shapes: dict[_Page, list[Shape]] = defaultdict(list)
    for one in scene.placed:
        where[one.function][one.drawing_set, one.page] = one
        if one.function not in scene.hidden:
            shapes[one.drawing_set, one.page].append(
                Shape(owner=one.function, box=placed_keepout(one))
            )
    boxes: dict[Id[Any], dict[_Page, PlacedConnectorBox]] = defaultdict(dict)
    for box in scene.boxes:
        boxes[box.function][box.drawing_set, box.page] = box
        shapes[box.drawing_set, box.page].append(Shape(owner=box.function, box=box.box))
    for label in scene.labels:
        shapes[label.drawing_set, label.page].append(Shape(owner=None, box=label.box))
    for page, owner, box in scene.keepouts:
        shapes[page].append(Shape(owner=owner, box=box))
    refs: dict[Id[Any], list[tuple[Id[Any], Any]]] = defaultdict(list)
    for one in carried:
        for ref in (one.a, one.b):
            refs[ref.port].append((one.handle, ref))
    every = [one for unit in units for one in unit.interfaces]
    return _World(
        where,
        {one.function: one for one in scene.drawn},
        boxes,
        shapes,
        refs,
        frozenset(one.edge.function for one in every),
        frozenset(one.edge.function for one in every if one.leaving),
        frozenset(one.edge.function for unit in units if unit.top for one in unit.interfaces),
    )


def _pages(line: LineRead, world: _World) -> list[_Page]:
    """The pages any end of `line` stands on: its plug's box, or a pin's placement."""
    found: dict[_Page, None] = {}
    for end in line.ends:
        if end.plug is not None:
            found.update(dict.fromkeys(world.boxes.get(end.plug, {})))
        if end.mates in world.top:
            found.update(dict.fromkeys(world.boxes.get(end.mates, {})))
        for port in end.ports:
            for _, ref in world.refs.get(port, ()):
                found.update(dict.fromkeys(world.where.get(ref.function, {})))
    return sorted(found)


def _ends_on(
    ends: Sequence[HarnessLineEnd], page: _Page, world: _World
) -> tuple[list[EndOnPage], list[int]]:
    """The line's ends drawn on `page`, and the branches of those that are not, in order.

    Layout-0206: a plug-less box end then takes the edge facing the rows of the other ends.
    """
    first = [(end, _end_on(end, page, world)) for end in ends]
    found: list[EndOnPage] = []
    for end, first_try in first:
        others = [two for other, two in first if two is not None and other is not end]
        again = first_try is not None and first_try.box is not None and end.plug is None
        placed = _end_on(end, page, world, rows_of(others)) if again else first_try
        if placed is not None:
            found.append(placed)
    return found, [end.branch for end, one in first if one is None]


def _trunk(
    line: LineRead, ends: Sequence[EndOnPage], where: tuple[_Page, Grid], world: _World
) -> Facing | None:
    """Layout-0167: the way the line enters its root's box, when the root stands on another page."""
    page, grid = where
    first = next((one for one in line.ends if one.mates in world.interfaces), line.ends[0])
    if any(one.branch == first.branch for one in ends):
        return None
    for other in (one for one in _pages(line, world) if one != page):
        found = _end_on(first, other, world)
        if found is not None:
            region = grid.region
            return OPPOSITE[drawn_end(found, (region.x, region.x + region.width), grid).end.facing]
    return None


def _end_on(
    end: HarnessLineEnd, page: _Page, world: _World, toward: tuple[int, int] | None = None
) -> EndOnPage | None:
    """One end on `page`: its plug's box with its mate's, or its pins standing there."""
    interface = end.mates in world.interfaces
    if end.plug is not None:
        box = world.boxes.get(end.plug, {}).get(page)
        mate = world.boxes.get(end.mates, {}).get(page) if end.mates is not None else None
        if box is None:
            return _own_sheet(end, mate, world)
        leaving = end.mates in world.leaving
        return EndOnPage(
            end.branch, interface, leaving, box.box, mate.box if mate is not None else None
        )
    pins = tuple(_pins(end, page, world))
    if pins:
        return EndOnPage(end.branch, interface, pins=pins)
    return boxed_end(end, page, world.boxes, world.owner_of, toward)


def _own_sheet(
    end: HarnessLineEnd, mate: PlacedConnectorBox | None, world: _World
) -> EndOnPage | None:
    """A top-level unit's own sheet has no plug: its interface's box leaves (layout-0154 item 6)."""
    if mate is None or end.mates not in world.top:
        return None
    return EndOnPage(end.branch, interface=True, leaving=True, box=mate.box)


def _pins(end: HarnessLineEnd, page: _Page, world: _World) -> list[PinAt]:
    found = []
    for port in end.ports:
        for conductor, ref in world.refs.get(port, ()):
            placed = world.where.get(ref.function, {}).get(page)
            if placed is not None:
                at = port_end(ref, {ref.function: placed}, world.drawn_of)
                found.append(PinAt(conductor, at, *_rows(placed_keepout(placed), at.facing)))
    return found


def _rows(keepout: Box, facing: Facing) -> tuple[tuple[int, int], tuple[int, int]]:
    """A pin's rows (layout-0154 item 5): its keep-out along the facing axis, then across."""
    along = (keepout.y, keepout.y + keepout.height), (keepout.x, keepout.x + keepout.width)
    return along if facing in (Facing.N, Facing.S) else (along[1], along[0])


def _grid(grid: Grid, page: _Page, world: _World) -> Grid:
    """The page's keep-outs, the line's own boxes and pins too (ruled choice 1, layout-0158).

    A line starts on a box's edge or a split outside its pins, and leaves them outward.
    """
    shapes = tuple(world.shapes.get(page, ()))
    region = drawn_extent(grid.region, (one.box for one in shapes), LEAVE_GRIDS * WIRING_GRID)
    return replace(grid, region=region, obstacles=Space(shapes=shapes).obstacles({}, region))


def _page_pieces(
    found: DrawnPieces,
    page: _Page,
    pieces: Sequence[tuple[LineRead, Pieces]],
    run: _Context,
) -> DrawnPieces:
    """One page's lines with their labels placed in one `place_texts` call, fans and stubs."""
    texts, world, scene = run
    paths = [(line.owner, branch, points) for line, one in pieces for branch, points in one.paths]
    legs = [leg.points for _, one in pieces for fan in one.fans for leg in fan.legs]
    stubs = tuple(
        stub_box(
            texts,
            line,
            stub,
            (page, scene.units.get(page[0]), tuple(_ends_on(line.ends, page, world)[1])),
            scene.profile,
        )
        for line, one in pieces
        for stub in one.stubs
    )
    # layout-0206: a label keeps the house text gap off every stub box
    stub_boxes = (Shape(owner=None, box=pad(stub.box, TEXT_GAP)) for stub in stubs)
    shapes = [*world.shapes.get(page, []), *stub_boxes]
    centres, unplaced = _label_boxes(paths, legs, texts, shapes, scene)
    lines = tuple(
        DrawnLine(
            harness=owner,
            branch=branch,
            drawing_set=page[0],
            page=page[1],
            points=points,
            text=text_centre(centres[owner, branch]),
            label=centres[owner, branch].box,
        )
        for owner, branch, points in paths
    )
    fans = tuple(
        DrawnFanOut(
            harness=line.owner,
            branch=fan.branch,
            drawing_set=page[0],
            page=page[1],
            at=fan.at,
            legs=fan.legs,
        )
        for line, one in pieces
        for fan in one.fans
    )
    return DrawnPieces(
        lines=(*found.lines, *lines),
        fan_outs=(*found.fan_outs, *fans),
        stubs=(*found.stubs, *stubs),
        findings=(*found.findings, *unplaced),
    )


def _label_boxes(
    paths: Sequence[tuple[Id[Any], int, tuple[Any, ...]]],
    legs: Sequence[tuple[Any, ...]],
    texts: LineTexts,
    shapes: Sequence[Shape],
    scene: LineScene,
) -> tuple[dict[tuple[Id[Any], int], Any], tuple[Finding, ...]]:
    """Each path's designation at the first free candidate along its longest run.

    Every run keeps every label the house text gap off (layout-0158); a fan-out leg is kept clear
    along its slant, sampled every `WIRING_GRID // 2`.
    """
    runs = [
        Shape(owner=None, box=pad(span(first, second), TEXT_GAP))
        for _, _, points in paths
        for first, second in pairwise(points)
    ]
    runs += [Shape(owner=None, box=box) for leg in legs for box in slant_boxes(leg)]
    to_place = tuple(
        line_text(owner, branch, points, texts.size(owner, branch, scene.profile))
        for owner, branch, points in paths
    )
    space = Space(shapes=(*shapes, *runs), content=content_box(scene.sheet))
    placed, unplaced = place_texts(to_place, space, scene.profile.texts)
    return {(one.handle, int(one.slot)): one for one in placed}, unplaced
