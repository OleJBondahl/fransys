"""Test-side debug drawing of a stage-side `Layout` (design/package-layout.md 9, "Looking at it").

Not package code and not a renderer: boxes, ports, routes and label boxes only, so an
agent or a human can look at a page. It takes a `Layout` value, not a `Model`, so it
works before the engine and the model exist. The only place in the repo that writes a
file, and only into the directory it is given (`tmp_path`).
"""

from itertools import pairwise
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from fransys_layout.geometry import WIRING_GRID, translate
from fransys_layout.stages import MarkerSide

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from fransys_layout.geometry import Box, Point
    from fransys_layout.stages import (
        Layout,
        LinkMarker,
        PagePlan,
        PlacedFunction,
        PlacedLabel,
        Route,
        SheetFormat,
    )

# Grid units of white around the content box, so a box that runs off the page is visible.
MARGIN = 64
# One colour per physical net on the page, by the net's place in handle order.
WIRE_COLOURS = ("#2a7a4a", "#8a2a6a", "#2a5a9a", "#9a5a1a", "#4a4a4a")


def write_debug_pages(layout: Layout, directory: Path, *, sheet: SheetFormat) -> tuple[Path, ...]:
    """Write one SVG per page of `layout` into `directory` (WP7, extended by WP8, WP10).

    WP7 draws the content box and each `PlacedFunction` as its body and keep-out boxes
    with port dots. WP8 adds each `Route` as a polyline, a junction dot where a route
    ends on another route of its own net, and each `LinkMarker` as a triangle carrying
    the partner's `/page.column` and its box, dashed orange. WP10 adds each `PlacedLabel` as
    its box. All in grid units. Returns the paths sorted by `(drawing_set, page)`.
    """
    paths = []
    for page in sorted(layout.pages, key=lambda plan: (plan.drawing_set, plan.number)):
        path = directory / f"drawing_set{page.drawing_set}-page{page.number}.svg"
        path.write_text(_page(page, layout, sheet=sheet), encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def _page(page: PagePlan, layout: Layout, *, sheet: SheetFormat) -> str:
    """One page as an SVG document, drawn in grid units with a margin around the sheet.

    Each tuple of `layout` is filtered to this page, so a route or a label of another page
    is not drawn here. The canvas covers the content box and everything drawn, so a symbol
    that runs off the page (`PAGE_OVERFULL`) is visible instead of clipped away.
    """
    here = (page.drawing_set, page.number)
    placed = [one for one in layout.placed if (one.drawing_set, one.page) == here]
    routes = [one for one in layout.routes if (one.drawing_set, one.page) == here]
    markers = [one for one in layout.markers if (one.drawing_set, one.page) == here]
    labels = [one for one in layout.labels if (one.drawing_set, one.page) == here]
    boxes = (
        [_keepout(function) for function in placed]
        + [label.box for label in labels]
        + [marker.box for marker in markers]
    )
    left = min([0, *(box.x for box in boxes)]) - MARGIN
    top = min([0, *(box.y for box in boxes)]) - MARGIN
    width = max([sheet.content_width, *(box.x + box.width for box in boxes)]) - left + MARGIN
    height = max([sheet.content_height, *(box.y + box.height for box in boxes)]) - top + MARGIN
    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<g transform="translate({-left} {-top})">',
        (
            f'<rect x="0" y="0" width="{sheet.content_width}" '
            f'height="{sheet.content_height}" fill="none" stroke="#b0b0b0" stroke-width="2"/>'
        ),
        *_frame(sheet),
        *(line for function in placed for line in _function(function)),
        *(line for label in labels for line in _label(label)),
        *_wires(routes),
        *(line for marker in markers for line in _marker(marker)),
        _text(4, -16, f"drawing set {page.drawing_set} page {page.number}: {page.title}", size=20),
        "</g>",
        "</svg>",
    ]
    return "\n".join(lines) + "\n"


def _frame(sheet: SheetFormat) -> Iterator[str]:
    """The sheet's frame grid, the reference a link marker's `/page.column` text names."""
    for index in range(1, sheet.frame_columns):
        x = sheet.content_width * index // sheet.frame_columns
        yield (
            f'<line x1="{x}" y1="0" x2="{x}" y2="{sheet.content_height}" '
            'stroke="#e8e8e8" stroke-width="1"/>'
        )
    for index in range(1, sheet.frame_rows):
        y = sheet.content_height * index // sheet.frame_rows
        yield (
            f'<line x1="0" y1="{y}" x2="{sheet.content_width}" y2="{y}" '
            'stroke="#e8e8e8" stroke-width="1"/>'
        )


def _keepout(function: PlacedFunction) -> Box:
    """The function's keep-out box in page coordinates."""
    return translate(function.geometry.keepout, dx=function.at.x, dy=function.at.y)


def _function(function: PlacedFunction) -> Iterator[str]:
    """One placed function: its keep-out box dashed, its body solid, a dot per port."""
    geometry = function.geometry
    keepout = _keepout(function)
    body = geometry.body
    yield (
        f'<rect x="{keepout.x}" y="{keepout.y}" '
        f'width="{keepout.width}" height="{keepout.height}" fill="none" stroke="#c08080" '
        'stroke-width="1" stroke-dasharray="6 4"/>'
    )
    yield (
        f'<rect x="{function.at.x + body.x}" y="{function.at.y + body.y}" '
        f'width="{body.width}" height="{body.height}" fill="#eef2f8" stroke="#2a4a7a" '
        'stroke-width="2"/>'
    )
    for port in geometry.ports:
        yield (
            f'<circle cx="{function.at.x + port.at.x}" cy="{function.at.y + port.at.y}" '
            'r="4" fill="#c03030"/>'
        )
    yield _text(function.at.x + body.x + 2, function.at.y + body.y - 4, geometry.key, size=10)


def _wires(routes: list[Route]) -> Iterator[str]:
    """Every route as a polyline in its net's colour, then the junction dots on top."""
    nets = sorted({one.physical_net for one in routes})
    for one in routes:
        points = " ".join(f"{point.at.x},{point.at.y}" for point in one.points)
        colour = WIRE_COLOURS[nets.index(one.physical_net) % len(WIRE_COLOURS)]
        yield f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2"/>'
    for at in sorted(_junctions(routes), key=lambda point: (point.x, point.y)):
        yield f'<circle cx="{at.x}" cy="{at.y}" r="5" fill="#101010"/>'


def _junctions(routes: list[Route]) -> set[Point]:
    """Where a route ends on a cell another route of its own net covers: a real junction."""
    covered = {id(one): _covered(one) for one in routes}
    found = set()
    for one in routes:
        for other in routes:
            if other is one or other.physical_net != one.physical_net:
                continue
            for end in (one.points[0].at, one.points[-1].at):
                if (end.x, end.y) in covered[id(other)]:
                    found.add(end)
    return found


def _covered(one: Route) -> set[tuple[int, int]]:
    """Every wiring-grid cell one route's polyline covers."""
    cells = set()
    for first, second in pairwise([point.at for point in one.points]):
        along = max(abs(second.x - first.x), abs(second.y - first.y)) // WIRING_GRID
        dx = (second.x - first.x) // along if along else 0
        dy = (second.y - first.y) // along if along else 0
        cells.update((first.x + dx * i, first.y + dy * i) for i in range(along + 1))
    return cells


def _label(label: PlacedLabel) -> Iterator[str]:
    """One reserved label box, named by its kind, under the wires so a crossing shows."""
    box = label.box
    yield (
        f'<rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" '
        'fill="#f4eefa" stroke="#7a3a9a" stroke-width="1"/>'
    )
    yield _text(box.x + 1, box.y + box.height - 2, label.kind.value, size=6)


def _marker(marker: LinkMarker) -> Iterator[str]:
    """One severed signal: its text box, dashed, and a triangle at its port pointing away."""
    at = marker.at
    tip = 16 if marker.side is MarkerSide.OWNER else -16
    box = marker.box
    yield (
        f'<rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" '
        'fill="none" stroke="#b06020" stroke-width="1" stroke-dasharray="3 2"/>'
    )
    yield (
        f'<polygon points="{at.x},{at.y - 8} {at.x},{at.y + 8} {at.x + tip},{at.y}" '
        'fill="#b06020"/>'
    )
    yield _text(
        at.x + (tip if tip > 0 else tip - 28),
        at.y - 10,
        # A visual aid only, the page: LD3's `#n-p<sheet>:<col><row>` needs the persisted
        # model's numbering and row, which this stage-side debug helper has no `Model` to
        # read (decision layout-0089). `marker_text` on the written model is the real text.
        f"p{marker.partner_page}",
        size=10,
    )


def _text(x: int, y: int, text: str, *, size: int) -> str:
    """A label in the page's own coordinates; the text is escaped, never trusted markup."""
    return (
        f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" '
        f'fill="#404040">{escape(text)}</text>'
    )
