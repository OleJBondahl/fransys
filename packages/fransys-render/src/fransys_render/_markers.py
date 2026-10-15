"""Link markers (layout-0038): stub, arrow box and text; size read from the record."""

import dataclasses
from itertools import pairwise
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from symdef import Direction

from electrical_symbols import WIRING_GRID
from fransys_model.derive import draws_as_line, text_room_g
from fransys_model.derive.drawing_text import marker_text
from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.marker_box import marker_box_origin
from fransys_model.derive.order import drawn_on_page
from fransys_model.derive.print_sizes import ASCENT_RATIO
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.layout import (
    HarnessLine,
    LinkMarker,
    PlacementView,
    Side,
    SymbolPlacement,
    layout_of,
    page_slice,
    profile_of_page,
    sheet_format_of,
)
from fransys_model.layout import Page as PageRecord
from fransys_model.vocab import functions, ports

from ._constants import MARKER_ARROW_DEPTH_G
from ._numbers import format_decimal, point_mm, printed_font_mm
from ._ref_fill import ref_fill
from ._symbol_geometry import oriented_symbol, to_grid

if TYPE_CHECKING:
    from collections.abc import Sequence
    from decimal import Decimal

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page, Profile, SheetFormat
    from fransys_model.vocab import Function, Item


def markers_on_page(model: Model, page: Page) -> tuple[LinkMarker, ...]:
    """Every `layout.link_marker` on `page`, top-down, left to right (`by_place`)."""
    return drawn_on_page(model, LinkMarker, page)


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
    # An item view owns the ports of all its item's functions
    found = dict(by_function.get((marker.page, function), ()))
    found.update(by_item.get((marker.page, item), ()))
    placements = [found[position] for position in sorted(found)]
    if len(placements) > 1:  # A function drawn per pin: the one whose port is here
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
    """The box's top-left corner: derive's one rule, `marker_box_origin`."""
    return marker_box_origin(marker, Side[facing.name])


def stub_end(marker: LinkMarker, facing: Direction) -> tuple[int, int]:
    """The stub's far end: one wiring-grid step out from the port, along `facing`."""
    step = WIRING_GRID + marker.stub_extra
    return marker.x + facing.dx * step, marker.y + facing.dy * step


def arrow_polygon(marker: LinkMarker, facing: Direction) -> tuple[tuple[int, int], ...]:
    """The box's outline as an arrow: 5 vertices, tip first, the tip at `stub_end`."""
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


def _box_glyph(sheet: SheetFormat, marker: LinkMarker, facing: Direction, fill: str = "") -> str:
    """The marker's box outline: one closed `<polyline>`, the arrow shape of `arrow_polygon`.

    `fill` is the net's tint as an inline style, empty for none (render-0013).
    """
    vertices = arrow_polygon(marker, facing)
    closed = (*vertices, vertices[0])
    points = " ".join(point_mm(sheet, x, y) for x, y in closed)
    return f'<polyline class="marker" points="{points}"{fill}/>'


def _shared_box_glyph(sheet: SheetFormat, marker: LinkMarker, facing: Direction) -> str:
    """A shared marker box: a closed rectangle across the bundle row (layout-0054)."""
    x, y = box_origin(marker, facing)
    w, h = marker.width, marker.height
    ring = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    corner = rail_corner(marker, facing)
    if corner is not None:
        start = ring.index(corner)
        corners = [stub_end(marker, facing), *ring[start:], *ring[:start], ring[start]]
    else:
        corners = [*ring, ring[0]]
    points = " ".join(point_mm(sheet, cx, cy) for cx, cy in corners)
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
    lines = marker_text(model, marker).split("\n")  # A star reference wraps
    font_mm = printed_font_mm(profile.text_height_mm)
    room = text_room_g(profile.text_height_mm, sheet.module_mm)
    if drawn.vertical:
        pad_x = (marker.width - len(lines) * room) // 2
        y_mm = grid_to_mm(sheet.content_y_mm, box_y + marker.height // 2, sheet.module_mm)
        return "".join(
            text_glyph(
                line,
                grid_to_mm(sheet.content_x_mm, box_x + pad_x + index * room, sheet.module_mm)
                + font_mm * ASCENT_RATIO,
                y_mm,
                font_mm,
                rotate=True,
            )
            for index, line in enumerate(lines)
        )
    center_x = box_x + marker.width // 2
    pad_g = (marker.height - len(lines) * room) // 2
    x_mm = grid_to_mm(sheet.content_x_mm, center_x, sheet.module_mm)
    glyphs = []
    for index, line in enumerate(lines):
        top_g = box_y + pad_g + index * room
        top_mm = grid_to_mm(sheet.content_y_mm, top_g, sheet.module_mm)
        glyphs.append(text_glyph(line, x_mm, top_mm + font_mm * ASCENT_RATIO, font_mm))
    return "".join(glyphs)


def _turned_glyphs(  # noqa: PLR0913, PLR0917 -- the render context, the marker, its via point and the tints
    sheet: SheetFormat,
    profile: Profile,
    model: Model,
    marker: LinkMarker,
    via: tuple[int, int],
    tints: Sequence[str],
) -> str:
    """A branch from the record's `via` on the wire, E or W, then a vertical marker."""
    at_via, side, at_end, up = turned_parts(marker, via)
    return (
        _stub_glyph(sheet, at_via, side)
        + _stub_glyph(sheet, at_end, up)
        + _box_glyph(sheet, at_end, up, ref_fill(model, marker, tints))
        + _text_element(sheet, profile, model, marker, up, at=at_end)
    )


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


def ends_a_line(model: Model, marker: LinkMarker) -> bool:
    """Whether `marker` is the stub a harness line ends in: its carrier's line runs on it.

    A per-core stub of a line's carrier stands at its port, off the line, and keeps its stub.
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


def markers_group(model: Model, page: Page, tints: Sequence[str] = ()) -> str:
    """Every marker on `page` as one stub + arrow-box + text, in id order."""
    sheet = sheet_format_of(model, page.sheet_format)
    profile = profile_of_page(model, page)
    parts = []
    stubs: set[tuple[int, int, int]] = set()  # a mate's stub is the lead's line: drawn once
    for marker in markers_on_page(model, page):
        if marker.via_x is not None and marker.via_y is not None:  # Leaves its port sideways
            if marker.lead:  # a mate of a shared box draws nothing of its own
                parts.append(
                    _turned_glyphs(
                        sheet, profile, model, marker, (marker.via_x, marker.via_y), tints
                    )
                )
            continue
        facing = marker_facing(model, marker)
        line_stub = ends_a_line(model, marker)
        stub = (marker.x, marker.y, marker.stub_extra)
        if stub not in stubs and not line_stub:  # a line runs on to its stub's box itself
            stubs.add(stub)
            parts.append(_stub_glyph(sheet, marker, facing))
        if marker.box_x is not None or line_stub:
            # The lead of a shared box draws it, as a plain rectangle, and the text;
            # a line's stub is one such box, its line meeting its edge's middle (layout-0158)
            if marker.lead:
                parts.append(_shared_box_glyph(sheet, marker, facing))
                parts.append(_text_element(sheet, profile, model, marker, facing))
            continue
        parts.append(_box_glyph(sheet, marker, facing, ref_fill(model, marker, tints)))
        parts.append(_text_element(sheet, profile, model, marker, facing))
    return "".join(parts)
