"""Stage 9, geometric lint: how a laid-out page looks (docs/design/lint.md 6.8).

A report, never an optimiser objective, and never evidence that the wiring is right:
that is `coherence`.

Text crossed by a route is split by what crosses it, so one defect is one finding: a route run
through a label or marker box is `WIRE_OVER_LABEL` (`_wires`); a link marker's stub, which
render draws and the layout does not store, through a text box is `TEXT_CROSSED_BY_ROUTE`
(`_texts`). Their union is the designer's review metric `text_crossed_by_route`. `TEXT_OVERLAP`
(`_texts`) is the designer's review metric of the same name: two texts of a page that overlap,
or one over a symbol body it does not belong to.
"""

from dataclasses import dataclass
from itertools import combinations, pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, LayoutError, Point, contains, overlaps, translate
from fransys_layout.stages.content import content_box
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.slices import by_key, page_of
from fransys_layout.stages.space import (
    Shape,
    Space,
    crosses,
    crosses_unless_leaving,
    span,
)
from fransys_model.kernel import Finding, Severity

from ._foreign import box_on_symbols, stub_through_symbols
from ._jogs import routes_with_a_jog
from ._segments import own_ends_at, runs_of
from ._texts import text_crossings, text_overlaps
from .codes import (
    OUT_OF_CONTENT_BOX,
    REDUNDANT_JOG,
    SYMBOL_OVERLAP,
    WIRE_NOT_ORTHOGONAL,
    WIRE_OVER_LABEL,
    WIRE_THROUGH_SYMBOL,
)

if TYPE_CHECKING:
    from fransys_layout.stages import (
        Handle,
        Layout,
        LinkMarker,
        PlacedFunction,
        PlacedLabel,
        Route,
        SheetFormat,
    )


_MIN_POINTS = 2  # a route is at least its two ends, even `[p, p]`


@dataclass(frozen=True, slots=True)
class _Page:
    """Everything of one `(drawing_set, page)`; `placed` is in handle order."""

    placed: tuple[PlacedFunction, ...]
    boxes: tuple[tuple[PlacedFunction, Box], ...]
    bodies: tuple[tuple[PlacedFunction, Box], ...]
    routes: tuple[Route, ...]
    labels: tuple[PlacedLabel, ...]
    markers: tuple[LinkMarker, ...]
    content: Box


def lint_geometry(layout: Layout, *, sheet: SheetFormat) -> tuple[Finding, ...]:
    """Report geometric defects of `layout`, sorted by `(code, subjects)` (design/lint.md 6.8)."""
    content = content_box(sheet)
    placed_on = by_key(layout.placed, page_of)
    routes_on = by_key(layout.routes, page_of)
    labels_on = by_key(layout.labels, page_of)
    markers_on = by_key(layout.markers, page_of)
    pages = sorted({*placed_on, *routes_on, *labels_on, *markers_on})
    findings: list[Finding] = []
    for here in pages:
        placed = tuple(sorted(placed_on.get(here, ()), key=lambda one: one.function))
        if any(one.function == other.function for one, other in pairwise(placed)):
            msg = "one function is placed twice on one page"
            raise LayoutError(msg)
        routes = tuple(routes_on.get(here, ()))
        if any(len(route.points) < _MIN_POINTS for route in routes):
            msg = "a route has fewer than two points"
            raise LayoutError(msg)
        page = _Page(
            placed=placed,
            boxes=tuple((one, placed_keepout(one)) for one in placed),
            bodies=tuple(
                (one, translate(one.geometry.body, dx=one.at.x, dy=one.at.y)) for one in placed
            ),
            routes=routes,
            labels=tuple(labels_on.get(here, ())),
            markers=tuple(markers_on.get(here, ())),
            content=content,
        )
        findings.extend(_wires(page))
        findings.extend(_jogs(page))
        findings.extend(_symbols(page))
        findings.extend(_content(page))
        findings.extend(text_crossings(page.labels, page.markers))
        findings.extend(text_overlaps(page.labels, page.markers, page.bodies))
        findings.extend(stub_through_symbols(page.markers, page.placed, page.bodies))
        findings.extend(box_on_symbols(page.markers, page.placed, page.bodies))
    return tuple(sorted(findings, key=lambda finding: (finding.code, finding.subjects)))


def _identity(route: Route) -> tuple[Handle, Handle, Handle]:
    """What a finding about a route names: its `(connection, a, b)`."""
    return route.connection, route.a, route.b


def _warn(code: str, subjects: tuple[Handle, ...], message: str) -> Finding:
    return Finding(code=code, severity=Severity.WARNING, subjects=subjects, message=message)


def _space(page: _Page) -> Space:
    """The page's placed shapes, the boxes the router was given; `_wires` and `_jogs` share it."""
    return Space(
        shapes=(
            *(Shape(owner=one.function, box=box) for one, box in page.boxes),
            *(Shape(owner=None, box=label.box) for label in page.labels),
            *(Shape(owner=marker.port, box=marker.box) for marker in page.markers),
        )
    )


def _wires(page: _Page) -> list[Finding]:
    """`WIRE_NOT_ORTHOGONAL`, `WIRE_THROUGH_SYMBOL` and `WIRE_OVER_LABEL`."""
    findings = []
    space = _space(page)
    for route in page.routes:
        identity = _identity(route)
        if any(
            first.at.x != second.at.x and first.at.y != second.at.y
            for first, second in pairwise(route.points)
        ):
            findings.append(
                _warn(WIRE_NOT_ORTHOGONAL, identity, "a route has a segment that is not orthogonal")
            )
        runs = runs_of(route)
        own = own_ends_at((route.points[0].at, route.points[-1].at), page.placed, ())
        xs = [one.at.x for one in route.points]
        ys = [one.at.y for one in route.points]
        region = span(Point(x=min(xs), y=min(ys)), Point(x=max(xs), y=max(ys)))
        lanes = {obstacle.box: obstacle.lanes for obstacle in space.obstacles(own, region)}
        findings.extend(
            _warn(
                WIRE_THROUGH_SYMBOL,
                (*identity, one.function),
                "a route runs through the keep-out box of a symbol that is not its endpoint",
            )
            for one, box in page.boxes
            if any(crosses_unless_leaving(box, run, lanes.get(box, ())) for run in runs)
        )
        hit = {
            label.subject for label in page.labels if any(crosses(label.box, run) for run in runs)
        } | {
            marker.port for marker in page.markers if any(crosses(marker.box, run) for run in runs)
        }
        findings.extend(
            _warn(WIRE_OVER_LABEL, (*identity, subject), "a route runs through a label box")
            for subject in sorted(hit)
        )
    return findings


def _jogs(page: _Page) -> list[Finding]:
    """`REDUNDANT_JOG`: one finding per joined polyline of a physical net that holds one."""
    space = _space(page)
    findings = []
    for net in sorted({route.physical_net for route in page.routes}):
        same = tuple(route for route in page.routes if route.physical_net == net)
        findings.extend(
            _warn(
                REDUNDANT_JOG,
                tuple(handle for route in chain for handle in _identity(route)),
                "a route leaves a line and returns to it where a straight run was free",
            )
            for chain in routes_with_a_jog(same, space, page.placed, page.markers)
        )
    return findings


def _symbols(page: _Page) -> list[Finding]:
    """`SYMBOL_OVERLAP`: two keep-out boxes of the page share interior, the pair in handle order."""
    return [
        _warn(
            SYMBOL_OVERLAP,
            (one.function, other.function),
            "the keep-out boxes of two symbols overlap",
        )
        for (one, box), (other, other_box) in combinations(page.boxes, 2)
        if overlaps(box, other_box)
    ]


def _content(page: _Page) -> list[Finding]:
    """`OUT_OF_CONTENT_BOX`: a keep-out box, a label or marker box or a route vertex outside it."""
    findings = [
        _warn(OUT_OF_CONTENT_BOX, (one.function,), "a symbol's keep-out box leaves the content box")
        for one, box in page.boxes
        if not contains(page.content, box)
    ]
    findings.extend(
        _warn(OUT_OF_CONTENT_BOX, (label.subject,), "a label box leaves the content box")
        for label in page.labels
        if not contains(page.content, label.box)
    )
    findings.extend(
        _warn(OUT_OF_CONTENT_BOX, (marker.port,), "a link marker's box leaves the content box")
        for marker in page.markers
        if not contains(page.content, marker.box)
    )
    findings.extend(
        _warn(OUT_OF_CONTENT_BOX, _identity(route), "a route leaves the content box")
        for route in page.routes
        if any(
            not contains(page.content, Box(x=point.at.x, y=point.at.y, width=0, height=0))
            for point in route.points
        )
    )
    return findings
