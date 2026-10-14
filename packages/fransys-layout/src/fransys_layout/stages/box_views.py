"""Layout-0155: a boxed connector's box stands over its placed pin views, which draw no symbol."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    Point,
    contains_point,
    port_page_at,
    snap_up,
    translate,
)

from .connector_boxes import (
    CELL_ROWS,
    HALF,
    BoxCell,
    BoxSlot,
    PlacedConnectorBox,
    box_size,
    cell_width,
)
from .space import Blocks, Shape

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import PortGeometry, SymbolGeometry
    from fransys_model.kernel import Id

    from .types import LinkMarker, PlacedFunction


@dataclass(frozen=True)
class BoxSpec:
    """One boxed connector: its function, text lines, cell pins with markings, and every pin."""

    function: Id[Any]
    lines: tuple[str, ...]
    cells: tuple[tuple[Id[Any], str], ...]
    ports: tuple[Id[Any], ...]


def placed_boxes(
    placed: Sequence[PlacedFunction],
    specs: Sequence[BoxSpec],
    text_height: int,
    content: Box,
    reach: Mapping[ViewKey, tuple[Point, ...]] = frozendict(),
) -> tuple[PlacedConnectorBox, ...]:
    """Each boxed connector's box on each page its pin views stand on (a view is its port).

    `reach` holds, per pin view on its page, the points its cell's leads run to: the cells face
    them (layout-0211). A box with none keeps its cells on its pins' edge.
    """
    views: dict[Id[Any], list[PlacedFunction]] = {}
    for one in placed:
        views.setdefault(one.function, []).append(one)
    boxes = []
    for spec in specs:
        on_page: dict[tuple[int, int], list[PlacedFunction]] = {}
        for port in spec.ports:
            for one in views.get(port, ()):
                on_page.setdefault((one.drawing_set, one.page), []).append(one)
        boxes.extend(
            _box(
                spec,
                group,
                (text_height, content),
                [p for v in group for p in reach.get(_key(v), ())],
            )
            for group in on_page.values()
        )
    return tuple(sorted(boxes, key=lambda box: (box.drawing_set, box.page, box.function)))


def _key(one: PlacedFunction) -> ViewKey:
    return (one.function, one.drawing_set, one.page)


def _box(
    spec: BoxSpec, views: Sequence[PlacedFunction], room: tuple[int, Box], far: Sequence[Point]
) -> PlacedConnectorBox:
    """HL19: a box as wide as its cells and text, over the column of its first pin view.

    Each pin of it has a slot on its edge: its cell, or two grids on a cell-less box. The pin's
    view moves under its slot (`cell_views`), so the lead to its symbol is an ordinary wire.
    """
    text_height, content = room
    pin_of = {v.function: port_page_at(v.at, v.geometry.ports[0]) for v in views}
    width, height, shown, ported = _sizes(spec, pin_of, text_height)
    lead = (width - sum(w for _, w in shown)) // (2 * WIRING_GRID) * WIRING_GRID if ported else 0
    x = pin_of[shown[0][0]].x - shown[0][1] // 2 - lead
    x = min(max(x, content.x), content.x + content.width - width)
    # a pin facing up has its view below it: the box hangs from the pins' row
    down = views[0].geometry.ports[0].facing is Facing.N
    edge = (min if down else max)(pin.y for pin in pin_of.values())
    box = Box(x=x, y=edge if down else edge - height, width=width, height=height)
    top = down if ported else cells_on_top(box, far, pins_edge=down)
    slots, cells = _slots(shown, box, x + lead, top=top)
    first = box.y + HALF + (CELL_ROWS * WIRING_GRID if top and spec.cells else 0)
    texts = tuple(
        Point(x=box.x + HALF, y=first + index * (text_height + WIRING_GRID))
        for index in range(len(spec.lines))
    )
    return PlacedConnectorBox(
        function=spec.function,
        drawing_set=views[0].drawing_set,
        page=views[0].page,
        box=box,
        texts=texts,
        cells=() if ported else cells,
        slots=slots,
    )


def _sizes(
    spec: BoxSpec, pin_of: Mapping[Id[Any], Point], text_height: int
) -> tuple[int, int, list[tuple[Id[Any], int]], bool]:
    """The box's width and height, its shown pins with their widths, and whether it has no cells."""
    width, height = box_size(spec.lines, [mark for _, mark in spec.cells], text_height=text_height)
    shown = [(port, cell_width(mark, text_height)) for port, mark in spec.cells if port in pin_of]
    if shown:
        return width, height, shown, False
    order = sorted(pin_of, key=lambda port: (pin_of[port].x, pin_of[port].y))
    shown = [(port, CELL_ROWS * WIRING_GRID) for port in order]
    return max(width, snap_up(sum(w for _, w in shown))), height, shown, True


NEAR = (CELL_ROWS + 1) * WIRING_GRID  # a cell row and two wiring lanes: a point closer cannot route


def cells_on_top(box: Box, far: Sequence[Point], *, pins_edge: bool) -> bool:
    """Layout-0211: the cells take the edge more of `far` lie beyond, by count.

    A tie, no point, or a point on, in or within `NEAR` of the box (a slot there would meet
    its port, or leave no lane) keeps them on the pins' edge (`pins_edge`: the top one).
    """
    middle = box.y + box.height // 2
    above = sum(point.y < middle for point in far)
    below = sum(point.y > middle for point in far)
    near = replace(box, y=box.y - NEAR, height=box.height + 2 * NEAR)
    if above == below or any(contains_point(near, p.x, p.y) for p in far):
        return pins_edge
    return above > below


def _slots(
    shown: Sequence[tuple[Id[Any], int]], box: Box, left: int, *, top: bool
) -> tuple[tuple[BoxSlot, ...], tuple[BoxCell, ...]]:
    """The slot and the cell of each shown pin, side by side from `left` on its cells' edge."""
    row = box.y if top else box.y + box.height - CELL_ROWS * WIRING_GRID
    edge, facing = (box.y, Facing.N) if top else (box.y + box.height, Facing.S)
    slots: list[BoxSlot] = []
    cells: list[BoxCell] = []
    for port, wide in shown:
        slots.append(BoxSlot(port=port, x=left + wide // 2, y=edge, facing=facing))
        cells.append(BoxCell(port=port, box=_cell(left, row, wide)))
        left += wide
    return tuple(slots), tuple(cells)


def _cell(left: int, row: int, width: int) -> Box:
    return Box(x=left, y=row, width=width, height=CELL_ROWS * WIRING_GRID)


type ViewKey = tuple[Id[Any], int, int]
type Move = tuple[int, int, Facing, Point]


def _port(one: PlacedFunction, facing: Facing) -> PortGeometry:
    """The view's pin turned to face `facing`: it draws nothing, so it may stand either way."""
    port = one.geometry.ports[0]
    if port.facing is facing:
        return port
    return replace(port, at=Point(x=-port.at.x, y=-port.at.y), facing=facing)


def cell_views(
    placed: Sequence[PlacedFunction], boxes: Sequence[PlacedConnectorBox]
) -> dict[ViewKey, Move]:
    """HL19: how each pin view moves to stand on its slot, and the way its pin then faces.

    A pin faces away from the box, so no lead has to enter it, whichever way the view faced.
    """
    at = {(one.function, one.drawing_set, one.page): one for one in placed}
    moves = {}
    for box in boxes:
        for slot in box.slots:
            one = at.get(key := (slot.port, box.drawing_set, box.page))
            if one is not None:
                pin = _port(one, slot.facing).at
                dx, dy = slot.x - pin.x - one.at.x, slot.y - pin.y - one.at.y
                moves[key] = (dx, dy, slot.facing, Point(x=slot.x, y=slot.y))
    return moves


def moved_views[T: PlacedFunction](placed: Sequence[T], moves: Mapping[ViewKey, Move]) -> list[T]:
    """`placed` with each view in `moves` moved; it draws nothing, so its keep-out is empty."""
    return [
        replace(
            one,
            at=Point(x=one.at.x + move[0], y=one.at.y + move[1]),
            geometry=_bare(one.geometry, _port(one, move[2])),
        )
        if (move := moves.get((one.function, one.drawing_set, one.page)))
        else one
        for one in placed
    ]


def _bare(geometry: SymbolGeometry, port: PortGeometry) -> SymbolGeometry:
    return replace(
        geometry, ports=(port, *geometry.ports[1:]), keepout=Box(x=0, y=0, width=0, height=0)
    )


def moved_markers(
    markers: Sequence[LinkMarker], moves: Mapping[ViewKey, Move]
) -> tuple[LinkMarker, ...]:
    """`markers` with each one on a moved pin view moved with it, turned to leave the box."""
    return tuple(
        _carried(marker, move)
        if (move := moves.get((marker.port, marker.drawing_set, marker.page)))
        else marker
        for marker in markers
    )


def _carried(marker: LinkMarker, move: Move) -> LinkMarker:
    """The marker on its slot (its turned pin's point); its box mirrored to the side it faces."""
    at = move[3]
    dx, dy = at.x - marker.at.x, at.y - marker.at.y
    box = translate(marker.box, dx=dx, dy=dy)
    turn = None if marker.turn is None else Point(x=marker.turn.x + dx, y=marker.turn.y + dy)
    below = box.y >= at.y
    if marker.vertical and below is (move[2] is Facing.N):
        box = replace(box, y=2 * at.y - box.y - box.height)
        turn = None if turn is None else Point(x=turn.x, y=2 * at.y - turn.y)
    return replace(marker, at=at, box=box, turn=turn)


def slot_rows(boxes: Sequence[PlacedConnectorBox]) -> dict[tuple[int, int], Blocks]:
    """HL19: per page, the cells between a box's slots (hard) and its rectangle (soft)."""
    rows: dict[tuple[int, int], list[Blocks]] = {}
    for box in boxes:
        xs = {slot.x for slot in box.slots}
        gaps = range(min(xs) + WIRING_GRID, max(xs), WIRING_GRID) if xs else ()
        hard = tuple(
            Shape(owner=None, box=Box(x=x, y=box.slots[0].y, width=0, height=0))
            for x in gaps
            if x not in xs
        )
        rows.setdefault((box.drawing_set, box.page), []).append(
            Blocks(hard=hard, soft=(Shape(owner=None, box=box.box),))
        )
    return {
        here: Blocks(
            hard=tuple(s for b in blocks for s in b.hard),
            soft=tuple(s for b in blocks for s in b.soft),
        )
        for here, blocks in rows.items()
    }


def hidden_views(specs: Sequence[BoxSpec]) -> frozenset[Id[Any]]:
    """Every boxed pin view: drawn as its box, never as a pin symbol, and labelled by none."""
    return frozenset(port for spec in specs for port in spec.ports)


def drawn_hidden(
    placed: Sequence[PlacedFunction], hidden: frozenset[Id[Any]], markers: Sequence[Any]
) -> tuple[tuple[Id[Any], int, int], ...]:
    """Each hidden view's (port, set, page), but where a marker stands at it on its page."""
    marked = {(marker.port, marker.drawing_set, marker.page) for marker in markers}
    return tuple(
        sorted(
            where
            for one in placed
            if one.function in hidden
            and (where := (one.function, one.drawing_set, one.page)) not in marked
        )
    )


def face_plugs(
    boxes: Sequence[PlacedConnectorBox], mates: Mapping[Id[Any], Id[Any]]
) -> tuple[PlacedConnectorBox, ...]:
    """A plug's box touches its mate's box with cells, on the side away from them.

    The cells face the component's symbols (layout-0211); the line comes from the other side.
    """
    by_page = {(one.function, one.drawing_set, one.page): one for one in boxes}
    found = []
    for one in boxes:
        mate = by_page.get((mates.get(one.function), one.drawing_set, one.page))
        found.append(_faced(one, mate) if mate is not None and mate.cells else one)
    return tuple(found)


def _faced(plug: PlacedConnectorBox, mate: PlacedConnectorBox) -> PlacedConnectorBox:
    """`plug` centred on `mate`, touching the edge of it its cells are not on.

    Its slots stand on its outer edge, facing out, whichever edge its own pins gave them.
    """
    box, at = plug.box, mate.box
    below = mate.cells[0].box.y == at.y
    y = at.y + at.height if below else at.y - box.height
    x = at.x + (at.width - box.width) // 2
    dx, dy = x - box.x, y - box.y
    outer, facing = (y + box.height, Facing.S) if below else (y, Facing.N)
    return PlacedConnectorBox(
        function=plug.function,
        drawing_set=plug.drawing_set,
        page=plug.page,
        box=Box(x=x, y=y, width=box.width, height=box.height),
        texts=tuple(Point(x=p.x + dx, y=p.y + dy) for p in plug.texts),
        cells=plug.cells,
        slots=tuple(
            BoxSlot(port=one.port, x=one.x + dx, y=outer, facing=facing) for one in plug.slots
        ),
    )
