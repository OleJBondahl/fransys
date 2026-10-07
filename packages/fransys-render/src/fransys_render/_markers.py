"""Link markers (D8, layout-0038): stub, arrow box and text; size read from the record."""

import dataclasses
from itertools import pairwise
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from graphical_symbols import Direction

from electrical_symbols import WIRING_GRID
from fransys_model.derive import draws_as_line
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.layout import (
    HarnessLine,
    LinkMarker,
    PlacementView,
    SymbolPlacement,
    layout_of,
    page_slice,
    profile_of,
    sheet_format_of,
)
from fransys_model.layout import Page as PageRecord
from fransys_model.vocab import functions, ports

from ._constants import ASCENT_RATIO, MARKER_ARROW_DEPTH_G
from ._numbers import format_decimal, grid_to_mm
from ._symbol_geometry import oriented_symbol, to_grid

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page, Profile, SheetFormat
    from fransys_model.vocab import Function, Item


def markers_on_page(model: Model, page: Page) -> tuple[LinkMarker, ...]:
    """Every `layout.link_marker` on `page`, ordered by `id` (D11)."""
    return page_slice(model, LinkMarker, page)


type _Indexed = list[tuple[int, SymbolPlacement]]


@digest_cached(DIGEST_CACHE_SIZE)
def _placement_index(
    model: Model,
) -> tuple[
    dict[tuple[Id[Page], Id[Function]], _Indexed], dict[tuple[Id[Page], Id[Item]], _Indexed]
]:
    """Placements by `(page, function)`, item views by `(page, item)`, with table positions."""
    by_function: dict[tuple[Id[Page], Id[Function]], _Indexed] = {}
    by_item: dict[tuple[Id[Page], Id[Item]], _Indexed] = {}
    all_functions = functions(model)
    for position, p in enumerate(layout_of(model, SymbolPlacement).values()):
        by_function.setdefault((p.page, p.function), []).append((position, p))
        if p.view is PlacementView.ITEM:
            by_item.setdefault((p.page, all_functions[p.function].item), []).append((position, p))
    return by_function, by_item


def _owning_placement(model: Model, marker: LinkMarker) -> SymbolPlacement:
    """The one `layout.symbol_placement` that owns `marker`'s port."""
    function = ports(model)[marker.port].function
    item = functions(model)[function].item
    by_function, by_item = _placement_index(model)
    # R7 B2: an item view owns the ports of all its item's functions
    found = dict(by_function.get((marker.page, function), ()))
    found.update(by_item.get((marker.page, item), ()))
    placements = [found[position] for position in sorted(found)]
    if len(placements) > 1:  # R7 A: a function drawn per pin: the one whose port is here
        placements = [p for p in placements if _port_here(model, p, marker)]
    if len(placements) != 1:
        msg = f"marker {marker.id!r} has {len(placements)} owning placements, expected exactly 1"
        raise AssertionError(msg)
    return placements[0]


def _port_here(model: Model, placement: SymbolPlacement, marker: LinkMarker) -> bool:
    symbol = oriented_symbol(model, placement)
    return symbol is not None and any(
        (placement.x + to_grid(port.position.x), placement.y + to_grid(port.position.y))
        == (marker.x, marker.y)
        for port in symbol.ports
    )


def marker_facing(model: Model, marker: LinkMarker) -> Direction:
    """The outward direction `marker`'s stub and box point along."""
    if marker.facing is not None:
        return Direction[marker.facing.name]
    return geometry_facing(model, marker)


def geometry_facing(model: Model, marker: LinkMarker) -> Direction:
    """The direction the marker's port leaves its symbol; raises unless exactly one port matches."""
    placement = _owning_placement(model, marker)
    symbol = oriented_symbol(model, placement)
    if symbol is None:
        msg = f"marker {marker.id!r}'s placement has no oriented symbol ({placement.symbol!r})"
        raise AssertionError(msg)
    matches = [
        port
        for port in symbol.ports
        if (placement.x + to_grid(port.position.x), placement.y + to_grid(port.position.y))
        == (marker.x, marker.y)
    ]
    if len(matches) != 1:
        msg = f"marker {marker.id!r} has {len(matches)} matching ports, expected exactly 1"
        raise AssertionError(msg)
    return matches[0].direction


def box_origin(marker: LinkMarker, facing: Direction) -> tuple[int, int]:
    """The box's top-left corner: `marker_box`'s own four-way match, the record's own size."""
    w, h = marker.width, marker.height
    x, y = _base_origin(marker, facing, w, h)
    stub = marker.stub_extra
    x, y = x + facing.dx * stub, y + facing.dy * stub
    if marker.box_x is not None:  # R6 D2: one box shared across a bundle row
        x = marker.box_x
    return x, y


def _base_origin(marker: LinkMarker, facing: Direction, w: int, h: int) -> tuple[int, int]:
    match facing:
        case Direction.E:
            return marker.x + WIRING_GRID, marker.y - h // 2
        case Direction.W:
            return marker.x - WIRING_GRID - w, marker.y - h // 2
        case Direction.N:
            return marker.x - w // 2, marker.y - WIRING_GRID - h
        case Direction.S:
            return marker.x - w // 2, marker.y + WIRING_GRID
    msg = f"unhandled facing {facing!r}"
    raise AssertionError(msg)


def stub_end(marker: LinkMarker, facing: Direction) -> tuple[int, int]:
    """The stub's far end: one wiring-grid step out from the port, along `facing`."""
    step = WIRING_GRID + marker.stub_extra
    return marker.x + facing.dx * step, marker.y + facing.dy * step


def arrow_polygon(marker: LinkMarker, facing: Direction) -> tuple[tuple[int, int], ...]:
    """The box's outline as an arrow: 5 vertices, tip first (D8), the tip at `stub_end`."""
    box_x, box_y = box_origin(marker, facing)
    w, h, depth = marker.width, marker.height, MARKER_ARROW_DEPTH_G
    tip = stub_end(marker, facing)
    match facing:
        case Direction.E:
            return (
                tip,
                (box_x + depth, box_y),
                (box_x + w, box_y),
                (box_x + w, box_y + h),
                (box_x + depth, box_y + h),
            )
        case Direction.W:
            return (
                tip,
                (box_x + w - depth, box_y),
                (box_x, box_y),
                (box_x, box_y + h),
                (box_x + w - depth, box_y + h),
            )
        case Direction.N:
            return (
                tip,
                (box_x, box_y + h - depth),
                (box_x, box_y),
                (box_x + w, box_y),
                (box_x + w, box_y + h - depth),
            )
        case Direction.S:
            return (
                tip,
                (box_x, box_y + depth),
                (box_x, box_y + h),
                (box_x + w, box_y + h),
                (box_x + w, box_y + depth),
            )
    msg = f"unhandled facing {facing!r}"
    raise AssertionError(msg)


def _point_mm(sheet: SheetFormat, x: int, y: int) -> str:
    """One point converted to an `"x,y"` mm pair (D5), mirroring `_routes._point_mm`."""
    x_mm = grid_to_mm(sheet.content_x_mm, x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)
    return f"{format_decimal(x_mm)},{format_decimal(y_mm)}"


def _stub_glyph(sheet: SheetFormat, marker: LinkMarker, facing: Direction) -> str:
    """The marker's stub: one `<line>` from the port to the box's near edge."""
    end_x, end_y = stub_end(marker, facing)
    x1_mm = grid_to_mm(sheet.content_x_mm, marker.x, sheet.module_mm)
    y1_mm = grid_to_mm(sheet.content_y_mm, marker.y, sheet.module_mm)
    x2_mm = grid_to_mm(sheet.content_x_mm, end_x, sheet.module_mm)
    y2_mm = grid_to_mm(sheet.content_y_mm, end_y, sheet.module_mm)
    return (
        f'<line class="marker" x1="{format_decimal(x1_mm)}" y1="{format_decimal(y1_mm)}" '
        f'x2="{format_decimal(x2_mm)}" y2="{format_decimal(y2_mm)}"/>'
    )


def _box_glyph(sheet: SheetFormat, marker: LinkMarker, facing: Direction) -> str:
    """The marker's box outline: one closed `<polyline>`, the arrow shape of `arrow_polygon`."""
    vertices = arrow_polygon(marker, facing)
    closed = (*vertices, vertices[0])
    points = " ".join(_point_mm(sheet, x, y) for x, y in closed)
    return f'<polyline class="marker" points="{points}"/>'


def _shared_box_glyph(sheet: SheetFormat, marker: LinkMarker, facing: Direction) -> str:
    """A shared marker box: a closed rectangle across the bundle row (R6 D2, layout-0054)."""
    x, y = box_origin(marker, facing)
    w, h = marker.width, marker.height
    ring = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    end_x, end_y = stub_end(marker, facing)
    if facing.dy and not x <= end_x <= x + w:
        start = ring.index((x if end_x < x else x + w, end_y))
        corners = [(end_x, end_y), *ring[start:], *ring[:start], ring[start]]
    else:
        corners = [*ring, ring[0]]
    points = " ".join(_point_mm(sheet, cx, cy) for cx, cy in corners)
    return f'<polyline class="marker" points="{points}"/>'


def text_glyph(
    text: str, x_mm: Decimal, y_mm: Decimal, font_size_mm: Decimal, *, rotate: bool = False
) -> str:
    """One marker-text `<text>` element: escaped, `class="label"`, centred."""
    x, y = format_decimal(x_mm), format_decimal(y_mm)
    turn = f' transform="rotate(-90 {x} {y})"' if rotate else ""
    return (
        f'<text class="label" text-anchor="middle"{turn} x="{x}" '
        f'y="{y}" font-size="{format_decimal(font_size_mm)}">'
        f"{escape(text)}</text>"
    )


def _text_element(  # noqa: PLR0913 -- the full render context (sheet, profile, model), the marker and its facing, and the optional `at` box override are each independently needed
    sheet: SheetFormat,
    profile: Profile,
    model: Model,
    marker: LinkMarker,
    facing: Direction,
    *,
    at: LinkMarker | None = None,
) -> str:
    """The marker's own text, centred in the box; a `vertical` one is turned (render-0005)."""
    drawn = marker if at is None else at
    box_x, box_y = box_origin(drawn, facing)
    lines = marker_text(model, marker).split("\n")  # R7 B4: a star reference wraps
    if drawn.vertical:
        font_mm = grid_to_mm(0, profile.text_height, sheet.module_mm)
        pad_x = (marker.width - len(lines) * profile.text_height) // 2
        y_mm = grid_to_mm(sheet.content_y_mm, box_y + marker.height // 2, sheet.module_mm)
        return "".join(
            text_glyph(
                line,
                grid_to_mm(
                    sheet.content_x_mm, box_x + pad_x + index * profile.text_height, sheet.module_mm
                )
                + font_mm * ASCENT_RATIO,
                y_mm,
                font_mm,
                rotate=True,
            )
            for index, line in enumerate(lines)
        )
    center_x = box_x + marker.width // 2
    pad_g = (marker.height - len(lines) * profile.text_height) // 2
    font_size_mm = grid_to_mm(0, profile.text_height, sheet.module_mm)
    x_mm = grid_to_mm(sheet.content_x_mm, center_x, sheet.module_mm)
    glyphs = []
    for index, line in enumerate(lines):
        top_g = box_y + pad_g + index * profile.text_height
        top_mm = grid_to_mm(sheet.content_y_mm, top_g, sheet.module_mm)
        glyphs.append(text_glyph(line, x_mm, top_mm + font_size_mm * ASCENT_RATIO, font_size_mm))
    return "".join(glyphs)


def _turned_glyphs(
    sheet: SheetFormat, profile: Profile, model: Model, marker: LinkMarker, via: tuple[int, int]
) -> str:
    """M7: a branch from the record's `via` on the wire, E or W, then a vertical marker."""
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
        "facing": None,
    }
    at_via = dataclasses.replace(
        marker,
        x=via[0],
        y=via[1],
        vertical=False,
        **{**base, "stub_extra": abs(centre - via[0]) - WIRING_GRID},
    )
    at_end = dataclasses.replace(marker, x=centre, y=via[1], **base)
    return (
        _stub_glyph(sheet, at_via, side)
        + _stub_glyph(sheet, at_end, up)
        + _box_glyph(sheet, at_end, up)
        + _text_element(sheet, profile, model, marker, up, at=at_end)
    )


def _ends_a_line(model: Model, marker: LinkMarker) -> bool:
    """Whether `marker` is the stub a harness line ends in (HL18): its carrier's line runs on it.

    A per-core stub of a line's carrier (C21) stands at its port, off the line, and keeps its stub.
    """
    if marker.carrier is None or not draws_as_line(model, marker.carrier):
        return False
    page = layout_of(model, PageRecord)[marker.page]
    return any(
        min(a.x, b.x) <= marker.x <= max(a.x, b.x) and min(a.y, b.y) <= marker.y <= max(a.y, b.y)
        for line in page_slice(model, HarnessLine, page)
        if line.harness == marker.carrier
        for a, b in pairwise(line.points)
    )


def markers_group(model: Model, page: Page) -> str:
    """Every marker on `page` as one stub + arrow-box + text, D11 id order."""
    sheet = sheet_format_of(model, page.sheet_format)
    profile = profile_of(model)
    parts = []
    stubs: set[tuple[int, int, int]] = set()  # a mate's stub is the lead's line: drawn once
    for marker in markers_on_page(model, page):
        if marker.via_x is not None and marker.via_y is not None:  # I4: leaves its port sideways
            if marker.lead:  # a mate of a shared box draws nothing of its own
                parts.append(
                    _turned_glyphs(sheet, profile, model, marker, (marker.via_x, marker.via_y))
                )
            continue
        facing = marker_facing(model, marker)
        line_stub = _ends_a_line(model, marker)
        stub = (marker.x, marker.y, marker.stub_extra)
        if stub not in stubs and not line_stub:  # a line runs on to its stub's box itself
            stubs.add(stub)
            parts.append(_stub_glyph(sheet, marker, facing))
        if marker.box_x is not None or line_stub:
            # R6 D2: the lead of a shared box draws it, as a plain rectangle, and the text;
            # a line's stub is one such box, its line meeting its edge's middle (layout-0158)
            if marker.lead:
                parts.append(_shared_box_glyph(sheet, marker, facing))
                parts.append(_text_element(sheet, profile, model, marker, facing))
            continue
        parts.append(_box_glyph(sheet, marker, facing))
        parts.append(_text_element(sheet, profile, model, marker, facing))
    return "".join(parts)
