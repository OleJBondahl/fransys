"""HL6: a boxed connector's box stands over its placed pin views, which draw no symbol."""

from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point, port_page_at, translate, union

from .connector_boxes import CELL_ROWS, HALF, BoxCell, PlacedConnectorBox, box_size, cell_width

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import Id

    from .types import PlacedFunction


@dataclass(frozen=True)
class BoxSpec:
    """One boxed connector: its function, text lines, cell pins with markings, and every pin."""

    function: Id[Any]
    lines: tuple[str, ...]
    cells: tuple[tuple[Id[Any], str], ...]
    ports: tuple[Id[Any], ...]


def placed_boxes(
    placed: Sequence[PlacedFunction], specs: Sequence[BoxSpec], text_height: int, content: Box
) -> tuple[PlacedConnectorBox, ...]:
    """Each boxed connector's box on each page its pin views stand on (a view is its port)."""
    views: dict[Id[Any], list[PlacedFunction]] = {}
    for one in placed:
        views.setdefault(one.function, []).append(one)
    boxes = []
    for spec in specs:
        on_page: dict[tuple[int, int], list[PlacedFunction]] = {}
        for port in spec.ports:
            for one in views.get(port, ()):
                on_page.setdefault((one.drawing_set, one.page), []).append(one)
        boxes.extend(_box(spec, views, text_height, content) for views in on_page.values())
    return tuple(sorted(boxes, key=lambda box: (box.drawing_set, box.page, box.function)))


def _box(
    spec: BoxSpec, views: Sequence[PlacedFunction], text_height: int, content: Box
) -> PlacedConnectorBox:
    """The box at `views`' pins, on their body side, centred over them; cells on the pins' edge."""
    width, height = box_size(spec.lines, [mark for _, mark in spec.cells], text_height=text_height)
    room = reduce(union, (translate(v.geometry.body, dx=v.at.x, dy=v.at.y) for v in views))
    pin_of = {v.function: port_page_at(v.at, v.geometry.ports[0]) for v in views}
    # a pin facing up has its view below it: the box hangs from the pins' row
    down = views[0].geometry.ports[0].facing is Facing.N
    edge = (min if down else max)(pin.y for pin in pin_of.values())
    wide = max(width, room.width)
    top = edge if down else edge - height
    # centred over the views, but never past the content box's side (R3)
    x = min(max(room.x + (room.width - wide) // 2, content.x), content.x + content.width - wide)
    box = Box(x=x, y=top, width=wide, height=height)
    row = box.y if down else box.y + box.height - CELL_ROWS * WIRING_GRID
    cells = tuple(
        BoxCell(port=port, box=_cell(pin_of[port].x, row, cell_width(marking, text_height)))
        for port, marking in spec.cells
        if port in pin_of
    )
    first = box.y + HALF + (CELL_ROWS * WIRING_GRID if down and cells else 0)
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
        cells=cells,
    )


def _cell(centre: int, row: int, width: int) -> Box:
    return Box(x=centre - width // 2, y=row, width=width, height=CELL_ROWS * WIRING_GRID)


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
    """HL4, HL19: a plug's box touches its mate's box with cells, on the side away from them.

    The cells stand on the pins' edge, toward the component's symbols; the line comes from the
    other side, so the symbols stand on the far side of the box from it.
    """
    by_page = {(one.function, one.drawing_set, one.page): one for one in boxes}
    found = []
    for one in boxes:
        mate = by_page.get((mates.get(one.function), one.drawing_set, one.page))
        found.append(_faced(one, mate) if mate is not None and mate.cells else one)
    return tuple(found)


def _faced(plug: PlacedConnectorBox, mate: PlacedConnectorBox) -> PlacedConnectorBox:
    """`plug` centred on `mate`, touching the edge of it its cells are not on."""
    box, at = plug.box, mate.box
    cells_on_top = mate.cells[0].box.y == at.y
    y = at.y + at.height if cells_on_top else at.y - box.height
    x = at.x + (at.width - box.width) // 2
    dx, dy = x - box.x, y - box.y
    return PlacedConnectorBox(
        function=plug.function,
        drawing_set=plug.drawing_set,
        page=plug.page,
        box=Box(x=x, y=y, width=box.width, height=box.height),
        texts=tuple(Point(x=p.x + dx, y=p.y + dy) for p in plug.texts),
        cells=plug.cells,
    )
