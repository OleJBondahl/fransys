"""Shorts census: count the joins of two nets a design's pages draw (DRAWING_SHORTS_NETS), per page.

Runs against an INSTALLED fransys: the public API plus the installed packages, no repo files.

    uv run --with "fransys @ git+https://github.com/OleJBondahl/fransys@v0.18.5#subdirectory=packages/fransys" \
        python shorts_census.py DESIGN.py [DESIGN.py ...] [--list]

DESIGN.py defines `d` (the design, `fr.design(...)`) and optionally `documents` (a tuple); it is
built as `fr.build(d, *documents)`. Its folder goes on `sys.path`, so it can import its parts.
It prints one table per design: the joins on each page, pages in id order, and the total. `--list`
adds each join's two subjects, for a local fix; the counts alone are what a census reports.

The rule is a verbatim copy of `fransys_render._drawn_shorts`, `fransys_render._ink` and two
`fransys_render._markers` helpers (render-0012), since the installed version may predate them.
`internal/tests/test_shorts_census.py` fails when the copy drifts from the package.
"""  # noqa: E501 - the install command is one line

# ruff: noqa: PLC2701 - the census reads the render package's private drawing rules

import argparse
import dataclasses
import runpy
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys
from fransys_render import _markers
from fransys_render._markers import (
    arrow_polygon,
    box_origin,
    marker_facing,
    markers_on_page,
    stub_end,
)
from fransys_render._routes import routes_on_page
from fransys_render._symbol_geometry import oriented_power_symbol, oriented_symbol, to_grid
from fransys_render._symbols import power_lead_ends
from symdef import Direction, body_box

from electrical_symbols import WIRING_GRID
from fransys_model.derive import function_designation, item_designation, net_of
from fransys_model.derive.order import drawn_lines_on_page, drawn_on_page
from fransys_model.layout import (
    ConnectorBox,
    HarnessFanOut,
    Page,
    PowerSymbol,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab import conductors, functions, items, ports

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from symdef import Symbol

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import LinkMarker
    from fransys_model.vocab import Port

# Its private name up to v0.18.5; the package's public one after.
ends_a_line = getattr(_markers, "ends_a_line", None) or getattr(_markers, "_ends_a_line")  # noqa: B009 - absent in one of the two versions


type Point = tuple[int, int]


type Box = tuple[int, int, int, int]  # x0, y0, x1, y1, edges included


type Owner = tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Stroke:
    """One straight piece of drawn wire: `kind` route, stub, rail, lead, leg or line.

    `bundle` is the harness a line, its legs and a stub it carries belong to; `fan` is a leg's fan
    point, its first point, where the legs of one fan-out leave their line (render-0010).
    """

    kind: str
    owner: Owner
    subject: Id[Any]
    a: Point
    b: Point
    bundle: object = None
    fan: Point | None = None


@dataclass(frozen=True, slots=True)
class Body:
    """One drawn body: `kind` flag, power or symbol; a shared flag box's `owners` are its nets."""

    kind: str
    owners: frozenset[Owner]
    subject: Id[Any]
    box: Box
    ports: frozenset[Point] = frozenset()
    bundle: object = None


_MARKER_INK = frozenset({"stub", "rail"})


_JOINS_POWER = frozenset({"power", "flag"})


@dataclass(frozen=True, slots=True)
class Short:
    """Where the page joins two owners' ink: the two subjects, sorted, and one point of it."""

    subjects: tuple[Id[Any], ...]
    at: Point


def drawn_shorts(strokes: Sequence[Stroke], bodies: Sequence[Body]) -> tuple[Short, ...]:
    """One `Short` per pair of subjects whose ink the page joins, by subjects."""
    items: list[Stroke | Body] = [*strokes, *bodies]
    found: dict[tuple[Id[Any], ...], Point] = {}
    for one, other in _near(items):
        at = _join(one, other)
        if at is not None:
            found.setdefault(tuple(sorted((one.subject, other.subject))), at)
    return tuple(Short(subjects, at) for subjects, at in sorted(found.items()))


def _near(items: Sequence[Stroke | Body]) -> Iterator[tuple[Stroke | Body, Stroke | Body]]:
    """Every pair of items whose bounding boxes meet, by a sweep along x."""
    boxes = [_extent(one) for one in items]
    order = sorted(range(len(items)), key=lambda index: boxes[index][0])
    for rank, index in enumerate(order):
        box = boxes[index]
        for other in order[rank + 1 :]:
            if boxes[other][0] > box[2]:
                break
            if boxes[other][1] <= box[3] and box[1] <= boxes[other][3]:
                yield items[index], items[other]


def _extent(one: Stroke | Body) -> Box:
    if isinstance(one, Body):
        return one.box
    (ax, ay), (bx, by) = one.a, one.b
    return (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))


def _join(one: Stroke | Body, other: Stroke | Body) -> Point | None:
    """Where `one` and `other` join on the page, or `None`."""
    if isinstance(one, Stroke) and isinstance(other, Stroke):
        return _strokes_join(one, other)
    if isinstance(one, Body) and isinstance(other, Body):
        return _bodies_join(one, other)
    if isinstance(one, Stroke) and isinstance(other, Body):
        return _stroke_meets(one, other)
    if isinstance(one, Body) and isinstance(other, Stroke):
        return _stroke_meets(other, one)
    return None


def _strokes_join(one: Stroke, other: Stroke) -> Point | None:
    if one.owner == other.owner or _same_bundle(one, other):
        return None
    run = _overlap(one, other)
    if run is not None:
        return run
    at = _end_on(one, other) or _end_on(other, one)
    if at is not None:
        return None if _fan_joint(one, other, at) else at
    if _MARKER_INK & {one.kind, other.kind}:
        return _crossing(one, other)
    return None


def _fan_joint(one: Stroke, other: Stroke, at: Point) -> bool:
    """Two legs of one fan-out touching at the point where both leave their line, and only there."""
    return one.bundle == other.bundle and one.fan is not None and one.fan == other.fan == at


def _same_bundle(one: Stroke, other: Stroke) -> bool:
    """A line with its own legs or carried stubs: the one-line cable form."""
    return (
        one.bundle is not None and one.bundle == other.bundle and "line" in {one.kind, other.kind}
    )


def _stroke_meets(stroke: Stroke, body: Body) -> Point | None:
    if stroke.owner in body.owners or (body.bundle is not None and body.bundle == stroke.bundle):
        return None
    if body.kind == "symbol":
        if stroke.kind in _MARKER_INK or {stroke.a, stroke.b} & body.ports:
            return None
        return stroke.a if _meets(stroke.a, stroke.b, body.box, closed=False) else None
    return stroke.a if _meets(stroke.a, stroke.b, body.box, closed=True) else None


def _bodies_join(one: Body, other: Body) -> Point | None:
    kinds = {one.kind, other.kind}
    if "power" not in kinds or not kinds <= _JOINS_POWER or one.owners & other.owners:
        return None
    a, b = one.box, other.box
    if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
        return (max(a[0], b[0]), max(a[1], b[1]))
    return None


def _side(o: Point, a: Point, b: Point) -> int:
    """The sign of the turn from `o`->`a` to `o`->`b`: 0 when the three points are on one line."""
    turn = (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    return (turn > 0) - (turn < 0)


def _on(point: Point, a: Point, b: Point) -> bool:
    """Whether `point` lies on the closed segment `a`-`b`."""
    return (
        _side(a, b, point) == 0
        and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def _end_on(one: Stroke, other: Stroke) -> Point | None:
    """An end of `one` that lies on `other`."""
    return next((end for end in (one.a, one.b) if _on(end, other.a, other.b)), None)


def _overlap(one: Stroke, other: Stroke) -> Point | None:
    """The start of a run the two strokes share on one line, of positive length."""
    if _side(one.a, one.b, other.a) or _side(one.a, one.b, other.b):
        return None
    axis = 0 if one.a[0] != one.b[0] else 1
    first = max(
        min(one.a, one.b, key=lambda p: p[axis]),
        min(other.a, other.b, key=lambda p: p[axis]),
        key=lambda p: p[axis],
    )
    last = min(
        max(one.a, one.b, key=lambda p: p[axis]),
        max(other.a, other.b, key=lambda p: p[axis]),
        key=lambda p: p[axis],
    )
    return first if first[axis] < last[axis] else None


def _crossing(one: Stroke, other: Stroke) -> Point | None:
    """Where the two strokes cross inside both, or `None`."""
    if _side(one.a, one.b, other.a) * _side(one.a, one.b, other.b) >= 0:
        return None
    if _side(other.a, other.b, one.a) * _side(other.a, other.b, one.b) >= 0:
        return None
    upright = one if one.a[0] == one.b[0] else other
    level = other if upright is one else one
    return (upright.a[0], level.a[1])


def _meets(a: Point, b: Point, box: Box, *, closed: bool) -> bool:
    """Whether the segment `a`-`b` meets `box`: its edges included when `closed`, else inside it."""
    low, high = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for step, room in (
        (-dx, a[0] - box[0]),
        (dx, box[2] - a[0]),
        (-dy, a[1] - box[1]),
        (dy, box[3] - a[1]),
    ):
        if step == 0:
            if room < 0 or (room == 0 and not closed):
                return False
            continue
        ratio = room / step
        if step < 0:
            low = max(low, ratio)
        else:
            high = min(high, ratio)
    return low <= high if closed else low < high


def rail_corner(marker: LinkMarker, facing: Direction) -> tuple[int, int] | None:
    """The shared box's corner its rail runs to from the stub end, or `None` when it has none."""
    x, _ = box_origin(marker, facing)
    end_x, end_y = stub_end(marker, facing)
    if facing.dy and not x <= end_x <= x + marker.width:
        return (x if end_x < x else x + marker.width, end_y)
    return None


def turned_parts(
    marker: LinkMarker, via: tuple[int, int]
) -> tuple[LinkMarker, Direction, LinkMarker, Direction]:
    """A turned marker as two plain ones: the branch at `via`, the box end, each with its way."""
    centre = marker.box_x + marker.width // 2 if marker.box_x is not None else via[0]
    side = Direction.E if centre > via[0] else Direction.W
    up = Direction.N if via[1] < marker.y else Direction.S
    base = {
        "box_x": None,
        "lead": True,
        "stub_extra": 0,
        "via_x": None,
        "via_y": None,
        "star": None,
        "far": None,
        "carrier": None,
    }
    at_via = dataclasses.replace(
        marker,
        x=via[0],
        y=via[1],
        vertical=False,
        **{**base, "stub_extra": abs(centre - via[0]) - WIRING_GRID},
    )
    at_end = dataclasses.replace(marker, x=centre, y=via[1], **base)
    return at_via, side, at_end, up


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


def shorts(model: Model) -> list[tuple[int, Short]]:
    """Each drawn short with its page's position in id order, the order the check reads them."""
    pages = sorted(layout_of(model, Page).values(), key=lambda one: one.id)
    return [
        (number, short)
        for number, page in enumerate(pages, 1)
        for short in drawn_shorts(*page_ink(model, page))
    ]


def report(label: str, found: Sequence[tuple[int, Short]]) -> str:
    """One markdown table: the joins per page and the total."""
    per_page = Counter(number for number, _ in found)
    rows = [f"| {label} | {number} | {count} |" for number, count in sorted(per_page.items())]
    return "\n".join(
        [
            "| design | page | joins |",
            "|---|---|---|",
            *(rows or [f"| {label} | none | 0 |"]),
            f"| {label} | total | {len(found)} |",
        ]
    )


def name(model: Model, subject: Id[Any]) -> str:
    """A subject as printed: a port as `designation:port`, a function or item by its designation."""
    port = ports(model).get(subject)
    if port is not None:
        return f"{function_designation(model, port.function)}:{port.name}"
    if subject in functions(model):
        return function_designation(model, subject)
    if subject in items(model):
        return item_designation(model, subject)
    return str(subject)


def load(path: Path) -> dict[str, Any]:
    """Run the design file; its folder goes on `sys.path` for its parts. Its globals come back."""
    sys.path.insert(0, str(path.parent))
    return runpy.run_path(str(path))


def main(argv: Sequence[str] | None = None) -> None:
    """Build each design and print its table, and with `--list` each join's subjects."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("designs", type=Path, nargs="+")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    for path in args.designs:
        scope = load(path.resolve())
        model = fransys.build(scope["d"], *scope.get("documents", ())).model
        found = shorts(model)
        print(report(path.stem, found))  # noqa: T201 - CLI output
        for number, short in found if args.list else ():
            joined = " / ".join(name(model, one) for one in short.subjects)
            print(f"page {number}: {joined}")  # noqa: T201 - CLI output


if __name__ == "__main__":
    main()
