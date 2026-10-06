"""Junction dots (D8, render-0004): three or more directions of one net's wire leave a point."""

import itertools
from typing import TYPE_CHECKING

from fransys_model.derive import net_of
from fransys_model.layout import sheet_format_of

from ._constants import JUNCTION_DOT_DIAMETER_MM
from ._markers import marker_facing, markers_on_page, stub_end
from ._numbers import format_decimal, grid_to_mm
from ._routes import routes_on_page

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import LinkMarker, Page
    from fransys_model.vocab import Port

# A junction needs three or more directions of wire leaving one point (D8).
_JUNCTION_THRESHOLD = 3

type _Point = tuple[int, int]
type _Segment = tuple[_Point, _Point]


def _marker_stub(model: Model, marker: LinkMarker) -> _Segment:
    """`marker`'s drawn stub: out along its facing, or from `via` along the wire (I4, M7)."""
    if marker.via_x is not None and marker.via_y is not None:  # both or neither
        via = (marker.via_x, marker.via_y)
        centre = marker.box_x + marker.width // 2 if marker.box_x is not None else via[0]
        return via, (centre, via[1])
    return (marker.x, marker.y), stub_end(marker, marker_facing(model, marker))


def _directions(point: _Point, segments: list[_Segment]) -> set[_Point]:
    """The unit directions in which `segments` leave `point`."""
    found: set[_Point] = set()
    x, y = point
    for (x1, y1), (x2, y2) in segments:
        if x1 == x2 == x and y1 != y2 and min(y1, y2) <= y <= max(y1, y2):
            if max(y1, y2) > y:
                found.add((0, 1))
            if min(y1, y2) < y:
                found.add((0, -1))
        elif y1 == y2 == y and x1 != x2 and min(x1, x2) <= x <= max(x1, x2):
            if max(x1, x2) > x:
                found.add((1, 0))
            if min(x1, x2) < x:
                found.add((-1, 0))
    return found


def junction_locations(model: Model, page: Page) -> tuple[_Point, ...]:
    """Every junction dot location on `page`, ordered by `(x, y)` grid units (D11)."""
    by_net: dict[tuple[Id[Port], ...], list[_Segment]] = {}

    def add(port: Id[Port], segments: list[_Segment]) -> None:
        net = net_of(model, port)
        if net is None:
            msg = "a route's or marker's port is not a port of the model"
            raise AssertionError(msg)
        by_net.setdefault(net.ports, []).extend(segments)

    for route in routes_on_page(model, page):
        points = [(p.x, p.y) for p in route.points]
        add(route.a, list(itertools.pairwise(points)))
    for marker in markers_on_page(model, page):
        add(marker.port, [_marker_stub(model, marker)])
    dots: set[_Point] = set()
    for segments in by_net.values():
        ends = {end for segment in segments for end in segment}
        dots |= {p for p in ends if len(_directions(p, segments)) >= _JUNCTION_THRESHOLD}
    return tuple(sorted(dots))


def junctions_group(model: Model, page: Page) -> str:
    """Every junction dot on `page` as one `<circle>` each, ordered by position (D8, D11)."""
    sheet = sheet_format_of(model, page.sheet_format)
    radius_mm = format_decimal(JUNCTION_DOT_DIAMETER_MM / 2)
    circles = []
    for x, y in junction_locations(model, page):
        cx = format_decimal(grid_to_mm(sheet.content_x_mm, x, sheet.module_mm))
        cy = format_decimal(grid_to_mm(sheet.content_y_mm, y, sheet.module_mm))
        circles.append(f'<circle class="junction" cx="{cx}" cy="{cy}" r="{radius_mm}"/>')
    return "".join(circles)
