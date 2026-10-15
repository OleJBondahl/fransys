"""A page's drawn ink as plain values: each stroke and body render draws, and its owner.

An owner is the physical net a piece of ink carries (its ports), a harness for a harness line, or a
function for a symbol body. The marker ink is the one `_markers` draws (`rail_corner`,
`turned_parts`), so the drawn-short check reads what the page shows (render-0012).
"""

from itertools import pairwise
from typing import TYPE_CHECKING, Any

from symdef import body_box

from fransys_model.derive import net_of
from fransys_model.derive.order import drawn_lines_on_page, drawn_on_page
from fransys_model.layout import ConnectorBox, HarnessFanOut, PowerSymbol, SymbolPlacement
from fransys_model.vocab import conductors

from ._drawn_shorts import Body, Owner, Point, Stroke
from ._markers import (
    arrow_polygon,
    box_origin,
    ends_a_line,
    marker_facing,
    markers_on_page,
    rail_corner,
    stub_end,
    turned_parts,
)
from ._routes import routes_on_page
from ._symbol_geometry import oriented_power_symbol, oriented_symbol, to_grid
from ._symbols import power_lead_ends

if TYPE_CHECKING:
    from collections.abc import Iterable

    from symdef import Symbol

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import LinkMarker, Page
    from fransys_model.vocab import Port

    from ._drawn_shorts import Box


def page_ink(model: Model, page: Page) -> tuple[tuple[Stroke, ...], tuple[Body, ...]]:
    """Every stroke and body render draws on `page`."""
    strokes = [*_routes(model, page), *_lines(model, page), *_legs(model, page)]
    bodies = [*_symbols(model, page), *_connector_boxes(model, page)]
    for marker in markers_on_page(model, page):
        more, body = _marker(model, marker)
        strokes.extend(more)
        bodies.extend(body)
    for power in drawn_on_page(model, PowerSymbol, page):
        symbol = oriented_power_symbol(power)
        start, pin = power_lead_ends(power, symbol)
        owner = _owner(model, power.port)
        strokes.extend(_strokes("lead", owner, power.port, (start, pin)))
        box = _box(symbol, power.x, power.y)
        bodies.append(Body("power", frozenset({owner}), power.port, box, frozenset({start})))
    return tuple(strokes), _shared(tuple(bodies), model, page)


def _owner(model: Model, port: Id[Port]) -> Owner:
    net = net_of(model, port)
    return ("net", net.ports) if net is not None else ("port", port)


def _strokes(  # noqa: PLR0913 -- a stroke's own fields, the last two optional
    kind: str,
    owner: Owner,
    subject: Id[Any],
    points: Iterable[Point],
    *,
    bundle: object = None,
    fan: Point | None = None,
) -> list[Stroke]:
    """One stroke per non-empty step of the polyline `points`."""
    return [Stroke(kind, owner, subject, a, b, bundle, fan) for a, b in pairwise(points) if a != b]


def _routes(model: Model, page: Page) -> list[Stroke]:
    return [
        stroke
        for route in routes_on_page(model, page)
        for stroke in _strokes(
            "route", _owner(model, route.a), route.a, ((p.x, p.y) for p in route.points)
        )
    ]


def _lines(model: Model, page: Page) -> list[Stroke]:
    return [
        stroke
        for line in drawn_lines_on_page(model, page)
        for stroke in _strokes(
            "line",
            ("harness", line.harness),
            line.harness,
            ((p.x, p.y) for p in line.points),
            bundle=line.harness,
        )
    ]


def _legs(model: Model, page: Page) -> list[Stroke]:
    found = []
    for fan_out in drawn_on_page(model, HarnessFanOut, page):
        for leg in fan_out.legs:
            port = conductors(model)[leg.conductor].a
            found.extend(
                _strokes(
                    "leg",
                    _owner(model, port),
                    port,
                    ((p.x, p.y) for p in leg.points),
                    bundle=fan_out.harness,
                    fan=(leg.points[0].x, leg.points[0].y),
                )
            )
    return found


def _symbols(model: Model, page: Page) -> list[Body]:
    found = []
    for placement in drawn_on_page(model, SymbolPlacement, page):
        symbol = oriented_symbol(model, placement)
        if symbol is not None:
            at = frozenset(
                (placement.x + to_grid(p.position.x), placement.y + to_grid(p.position.y))
                for p in symbol.ports
            )
            box = _box(symbol, placement.x, placement.y)
            owner = ("function", placement.function)
            found.append(Body("symbol", frozenset({owner}), placement.function, box, at))
    return found


def _connector_boxes(model: Model, page: Page) -> list[Body]:
    """A connector box at a line's end is its connector's drawn body."""
    return [
        Body("symbol", frozenset({("function", box.function)}), box.function, _rect(box))
        for box in drawn_on_page(model, ConnectorBox, page)
    ]


def _rect(box: ConnectorBox) -> Box:
    return (box.x, box.y, box.x + box.width, box.y + box.height)


def _box(symbol: Symbol, x: int, y: int) -> Box:
    box = body_box(symbol)
    return (
        x + to_grid(box.min.x),
        y + to_grid(box.min.y),
        x + to_grid(box.max.x),
        y + to_grid(box.max.y),
    )


def _marker(model: Model, marker: LinkMarker) -> tuple[list[Stroke], list[Body]]:
    """The marker's drawn stubs and rail, and its box when it draws one."""
    owner, port = _owner(model, marker.port), marker.port
    if marker.via_x is not None and marker.via_y is not None:
        return _turned(marker, owner, (marker.via_x, marker.via_y)) if marker.lead else ([], [])
    facing = marker_facing(model, marker)
    line_stub = ends_a_line(model, marker)
    stub = [] if line_stub else [(marker.x, marker.y), stub_end(marker, facing)]
    strokes = _strokes("stub", owner, port, stub, bundle=marker.carrier)
    if marker.box_x is None and not line_stub:
        return strokes, _flag(marker, owner, _hull(arrow_polygon(marker, facing)))
    if not marker.lead:  # a mate draws its stub; its box and rail are its lead's
        return strokes, []
    corner = rail_corner(marker, facing)
    if corner is not None:
        strokes += _strokes("rail", owner, port, (stub_end(marker, facing), corner))
    x, y = box_origin(marker, facing)
    return strokes, _flag(marker, owner, (x, y, x + marker.width, y + marker.height))


def _turned(marker: LinkMarker, owner: Owner, via: Point) -> tuple[list[Stroke], list[Body]]:
    """A turned marker's branch and upright stub, and its arrow box (a mate draws none)."""
    at_via, side, at_end, up = turned_parts(marker, via)
    ends = ((at_via.x, at_via.y), stub_end(at_via, side), stub_end(at_end, up))
    strokes = _strokes("stub", owner, marker.port, ends)
    return strokes, _flag(marker, owner, _hull(arrow_polygon(at_end, up)))


def _flag(marker: LinkMarker, owner: Owner, box: Box) -> list[Body]:
    return [Body("flag", frozenset({owner}), marker.port, box, bundle=marker.carrier)]


def _hull(points: tuple[Point, ...]) -> Box:
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _shared(bodies: tuple[Body, ...], model: Model, page: Page) -> tuple[Body, ...]:
    """Each flag box with every net whose marker shares it (a mate draws none of its own)."""
    sharing: dict[Box, set[Owner]] = {}
    for marker in markers_on_page(model, page):
        if marker.box_x is not None and marker.via_x is None:
            x, y = box_origin(marker, marker_facing(model, marker))
            box = (x, y, x + marker.width, y + marker.height)
            sharing.setdefault(box, set()).add(_owner(model, marker.port))
    return tuple(
        Body(one.kind, one.owners | sharing[one.box], one.subject, one.box, one.ports, one.bundle)
        if one.kind == "flag" and one.box in sharing
        else one
        for one in bodies
    )
