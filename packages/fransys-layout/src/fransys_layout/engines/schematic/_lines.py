"""The engine's glue for harness lines (HL1, HL15 to HL18, layout-0154): strip, then draw.

A conductor a line carries is never a route and never a marker; its line draws it, after the
outlines and the routes, from the boxes and pins standing on each page.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from itertools import pairwise
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import Box, Facing, pad
from fransys_layout.geometry.units import TEXT_GAP
from fransys_layout.lint import HarnessInk
from fransys_layout.stages.content import content_box
from fransys_layout.stages.harness_route import Grid, line_text, text_centre
from fransys_layout.stages.line_draw import EndOnPage, PinAt, line_pieces
from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLine, LineStub
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.route import port_end
from fransys_layout.stages.space import Shape, Space, span
from fransys_layout.stages.texts.candidates import DEFAULT_TABLE
from fransys_layout.stages.texts.place_texts import place_texts
from fransys_model.kernel import Finding, value

from .read.harness_lines import drawn_on, line_reads
from .read.line_texts import LineTexts, line_texts, stub_box, widest_stub

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_layout.stages.line_draw import Pieces
    from fransys_layout.stages.middle import MiddleUnit
    from fransys_layout.stages.types import (
        Connection,
        DrawnFunction,
        PlacedFunction,
        PlacedLabel,
        Profile,
    )
    from fransys_model.kernel import Id, Model

    from .read import StageInputs
    from .read.harness_lines import HarnessLineEnd, LineRead, LineReads

type _Page = tuple[int, int]


def strip_lines(model: Model, inputs: StageInputs) -> tuple[StageInputs, LineReads]:
    """HL1: the run without the conductors lines carry, routed or crossing; the lines read."""
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
    hidden: frozenset[Id[Any]] = frozenset()  # HL6: boxed pin views, which draw nothing
    units: Mapping[int, Id[Any] | None] = MappingProxyType({})  # each drawing set's unit


@value
class DrawnPieces:
    """Every line's drawn pieces on every page, and a `LABEL_UNPLACED` for a label with no place."""

    lines: tuple[DrawnLine, ...] = ()
    fan_outs: tuple[DrawnFanOut, ...] = ()
    stubs: tuple[LineStub, ...] = ()
    findings: tuple[Finding, ...] = ()


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
    """HL15 to HL18: each line on each page its ends stand on, its labels placed (HL16)."""
    world = _world(carried, units, scene)
    texts = line_texts(model, lines)
    grid = Grid(content_box(scene.sheet), (), scene.profile.route_turn_penalty)
    pieces: dict[_Page, list[tuple[LineRead, Pieces]]] = defaultdict(list)
    for line in lines.lines:
        for page in _pages(line, world):
            if not drawn_on(line, scene.units.get(page[0]), lines.top):
                continue
            ends, absent = _ends_on(line.ends, page, world)
            if ends:
                here = _grid(grid, page, world)
                half = widest_stub(texts, line, scene.units.get(page[0]), scene.profile) // 2
                pieces[page].append((line, line_pieces(ends, absent, here, margin=half)))
    found = DrawnPieces()
    for page in sorted(pieces):
        found = _page_pieces(found, page, pieces[page], (texts, world, scene))
    return found


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
    for page, label in _labels(scene):
        shapes[page].append(Shape(owner=None, box=label.box))
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


def _labels(scene: LineScene) -> list[tuple[_Page, Any]]:
    return [((label.drawing_set, label.page), label) for label in scene.labels]


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
) -> tuple[list[EndOnPage], int | None]:
    """The line's ends drawn on `page`, and the first end's branch that is not."""
    found: list[EndOnPage] = []
    absent: int | None = None
    for end in ends:
        one = _end_on(end, page, world)
        if one is None:
            absent = end.branch if absent is None else absent
        else:
            found.append(one)
    return found, absent


def _end_on(end: HarnessLineEnd, page: _Page, world: _World) -> EndOnPage | None:
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
    return EndOnPage(end.branch, interface, pins=pins) if pins else None


def _own_sheet(
    end: HarnessLineEnd, mate: PlacedConnectorBox | None, world: _World
) -> EndOnPage | None:
    """A top-level unit's own sheet has no plug: its interface's box leaves (HL18)."""
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
                found.append(PinAt(conductor, at, _row(placed_keepout(placed), at.facing)))
    return found


def _row(keepout: Box, facing: Facing) -> tuple[int, int]:
    """A pin's row for its fan (HL17): its symbol's keep-out along the facing axis."""
    if facing in (Facing.N, Facing.S):
        return keepout.y, keepout.y + keepout.height
    return keepout.x, keepout.x + keepout.width


def _grid(grid: Grid, page: _Page, world: _World) -> Grid:
    """The page's keep-outs, the line's own boxes and pins too (ruled choice 1, layout-0158).

    A line starts on a box's edge or a split outside its pins, and leaves them outward.
    """
    shapes = tuple(world.shapes.get(page, ()))
    return replace(grid, obstacles=Space(shapes=shapes).obstacles({}, grid.region))


def _page_pieces(
    found: DrawnPieces,
    page: _Page,
    pieces: Sequence[tuple[LineRead, Pieces]],
    run: tuple[LineTexts, _World, LineScene],
) -> DrawnPieces:
    """One page's lines with their labels placed in one `place_texts` call, fans and stubs."""
    texts, world, scene = run
    paths = [(line.owner, branch, points) for line, one in pieces for branch, points in one.paths]
    centres, unplaced = _label_boxes(paths, texts, world.shapes.get(page, []), scene)
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
    stubs = tuple(
        stub_box(texts, line, stub, (page, scene.units.get(page[0])), scene.profile)
        for line, one in pieces
        for stub in one.stubs
    )
    return DrawnPieces(
        lines=(*found.lines, *lines),
        fan_outs=(*found.fan_outs, *fans),
        stubs=(*found.stubs, *stubs),
        findings=(*found.findings, *unplaced),
    )


def _label_boxes(
    paths: Sequence[tuple[Id[Any], int, tuple[Any, ...]]],
    texts: LineTexts,
    shapes: Sequence[Shape],
    scene: LineScene,
) -> tuple[dict[tuple[Id[Any], int], Any], tuple[Finding, ...]]:
    """HL16: each path's designation at the first free candidate along its longest run.

    Every run keeps every label the house text gap off, its own line's too (layout-0158).
    """
    runs = [
        Shape(owner=None, box=pad(span(first, second), TEXT_GAP))
        for _, _, points in paths
        for first, second in pairwise(points)
    ]
    to_place = tuple(
        line_text(owner, branch, points, texts.size(owner, branch, scene.profile))
        for owner, branch, points in paths
    )
    space = Space(shapes=(*shapes, *runs), content=content_box(scene.sheet))
    placed, unplaced = place_texts(to_place, space, DEFAULT_TABLE)
    return {(one.handle, int(one.slot)): one for one in placed}, unplaced
