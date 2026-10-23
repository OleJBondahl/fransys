"""Values in, SVG out, no knowledge of the caller.

`svg` draws a `Drawing` with a symdef `Library` and a `Style`; it imports no model.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

import symdef
from symdef import Weight

from electrical_symbols import MARKER_FACING, drawn_symbol, sheet_svg

from ._drawn_text import text_tag

if TYPE_CHECKING:
    from fransys_layout.drawing import (
        Drawing,
        DrawnMarker,
        DrawnOutline,
        DrawnSymbol,
        DrawnWire,
        Style,
    )

__all__ = ["DrawError", "svg"]


class DrawError(ValueError):
    """A drawing `svg` cannot draw: the message names the thing and the fix.

    `svg` raises it for a record it cannot draw: an unknown es key, a stretch the symbol lacks,
    a bad marker side, outline points that are not a rectangle, or a symbol with bad
    `offsets`, `poles` or `leads`. The facade's `build` turns it into one `DRAW_PROBLEM` ERROR
    per drawing set, so a consumer sees a finding and never this exception.
    """


#: A frame's points: two distinct x and y; two opposite corners or all four.
_BOX_SIDES = (2, 2)
_BOX_POINTS = (2, 4)


def format_decimal(value: Decimal) -> str:
    """`value` as plain text: no exponent, no trailing zeros, `0` for any zero."""
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _mm(grid: int, style: Style) -> Decimal:
    """`grid` G as mm, in `Decimal`."""
    return Decimal(grid) * Decimal(str(style.module_mm)) / Decimal(style.g_per_module)


def _label_font(library: symdef.Library, style: Style) -> tuple[str, Decimal, float]:
    """The label's family, its font size in mm (to 0.0001) and the capital ratio."""
    label = dict(style.texts)["label"]
    font = library.font
    assert font is not None  # noqa: S101 -- a drawn library carries its font
    ratio = Decimal(font.cap_height) / Decimal(font.units_per_em)
    size = (Decimal(str(label.height_mm)) / ratio).quantize(Decimal("0.0001"))
    return label.family, size, float(ratio)


def _fragment(
    symbol: symdef.Symbol,
    library: symdef.Library,
    style: Style,
    **kwargs: object,
) -> str:
    """The toolkit's SVG body of `symbol` with the style's pens, dash and font."""
    family, size, ratio = _label_font(library, style)
    return symdef.to_fragment_mm(
        symbol,
        module_mm=style.module_mm,
        weights_mm={Weight.NORMAL: style.line_thin_mm, Weight.THICK: style.line_thick_mm},
        dash_mm=_symbol_dash(style),
        dash_dot_mm=_outline_dash(style),
        font_family=family,
        font_mm=float(size),
        cap_ratio=ratio,
        required_slots=library.required_slots,
        **kwargs,  # ty: ignore[invalid-argument-type] -- tint, muted, texts as symdef types them
    )


def _symbol_dash(style: Style) -> tuple[float, float]:
    """The `symbol` dash of the style as a (dash, gap) pair."""
    dash, gap = dict(style.dashes)["symbol"]
    return dash, gap


def _outline_dash(style: Style) -> tuple[float, float, float, float]:
    """The `outline` dash of the style as symdef's (dash, gap, dot, gap) four."""
    dash, gap, dot, dot_gap = dict(style.dashes)["outline"]
    return dash, gap, dot, dot_gap


def _stretched(symbol: symdef.Symbol, drawn: DrawnSymbol, style: Style) -> symdef.Symbol:
    """`symbol` stretched x then y; the port `offsets` (G) apply on the one stretch axis.

    A symbol with `texts` takes its offsets in `drawn_symbol`, which builds it at them.
    """
    lengths = dict(drawn.stretch)
    offsets = {} if drawn.texts else {p: at / style.g_per_module for p, at in drawn.offsets}
    if offsets and len(lengths) != 1:
        msg = (
            f"symbol {drawn.id!r} has offsets but {len(lengths)} stretch axes: offsets name"
            " the coordinate along the one stretch axis; send exactly one"
        )
        raise DrawError(msg)
    for axis in ("x", "y"):
        if axis in lengths:
            length = lengths[axis] / style.g_per_module
            symbol = symdef.stretch(symbol, axis, length, offsets=offsets or None)
    return symbol


def _built(drawn: DrawnSymbol, library: symdef.Library, style: Style) -> symdef.Symbol:
    """The `drawn_symbol` stretched, with the bound leads of `drawn.leads` only, then turned."""
    if drawn.n > 1:
        msg = f"symbol {drawn.id!r} has {drawn.n} rows: a table's rows are its `texts`; send n=1"
        raise DrawError(msg)
    made = drawn_symbol(
        drawn.key,
        drawn.texts,
        library=library,
        offsets=dict(drawn.offsets),
        sides=dict(drawn.sides),
    )
    repeated = symdef.repeat(made, drawn.poles) if drawn.poles > 1 else made
    symbol = _stretched(repeated, drawn, style)
    try:
        symbol = symdef.leads(symbol, drawn.leads)
    except symdef.UnknownNameError as error:
        msg = (
            f"symbol {drawn.id!r} ({drawn.key!r}, {drawn.poles} poles): {error};"
            " fix the record's `leads` or `poles`"
        )
        raise DrawError(msg) from error
    return symdef.orient(symbol, symdef.Orientation[drawn.orient])


def _symbol(drawn: DrawnSymbol, library: symdef.Library, style: Style) -> str:
    """`<g>` of one symbol, translated to its position."""
    body = _fragment(
        _built(drawn, library, style),
        library,
        style,
        tint=drawn.tint,
        muted=style.muted_colour if drawn.muted else None,
        texts=dict(drawn.slots) or None,
    )
    return _placed(body, drawn.x, drawn.y, style)


def content_group(body: str, x_mm: float, y_mm: float) -> str:
    """`body` in a `<g>` translated to the content box at (`x_mm`, `y_mm`)."""
    return f'<g transform="translate({x_mm} {y_mm})">{body}</g>'


def _placed(body: str, x: int, y: int, style: Style) -> str:
    """`body` in a `<g>` translated to (x, y) G."""
    x_mm, y_mm = format_decimal(_mm(x, style)), format_decimal(_mm(y, style))
    return f'<g transform="translate({x_mm},{y_mm})">{body}</g>'


def _library_symbol(key: str, what: str, id_: str, library: symdef.Library) -> symdef.Symbol:
    """The library symbol `key` of a drawn `what`, or a DrawError naming the record and the key."""
    try:
        return library.get(key)
    except symdef.UnknownSymbolError as error:
        msg = f"{what} {id_!r}: {error}; fix the es key {key!r}"
        raise DrawError(msg) from error


def _outline(outline: DrawnOutline, library: symdef.Library, style: Style) -> str:
    """The frame symbol `outline.key` stretched to the box of its points, then its label."""
    symbol = _library_symbol(outline.key, "outline", outline.id, library)
    xs, ys = {x for x, _ in outline.points}, {y for _, y in outline.points}
    if (len(xs), len(ys)) != _BOX_SIDES or len(set(outline.points)) not in _BOX_POINTS:
        msg = (
            f"outline {outline.id!r} has points {outline.points}: a frame symbol draws a"
            " rectangle; send its four corners (closed or not) or two opposite ones"
        )
        raise DrawError(msg)
    g = style.g_per_module
    try:
        for axis, extent in (("x", xs), ("y", ys)):
            symbol = symdef.stretch(symbol, axis, (max(extent) - min(extent)) / g)
    except symdef.SymdefError as error:
        msg = f"outline {outline.id!r} ({outline.key!r}): {error}; use a frame es key"
        raise DrawError(msg) from error
    body = _fragment(symbol, library, style)
    placed = _placed(body, min(xs), min(ys), style)
    return placed + (text_tag(outline.label, library, style) if outline.label else "")


def _marker(marker: DrawnMarker, library: symdef.Library, style: Style) -> str:
    """The marker symbol `marker.key` turned to face `marker.side`, its texts in its slots."""
    symbol = _library_symbol(marker.key, "marker", marker.id, library)
    if marker.side not in MARKER_FACING:
        msg = f"marker {marker.id!r} faces {marker.side!r}: use one of {tuple(MARKER_FACING)}"
        raise DrawError(msg)
    turned = symdef.orient(symbol, symdef.Orientation[MARKER_FACING[marker.side]])
    body = _fragment(turned, library, style, tint=marker.tint, texts=dict(marker.texts) or None)
    return _placed(body, marker.x, marker.y, style)


def _wire(wire: DrawnWire, library: symdef.Library, style: Style) -> str:
    """The library wire style through the wire's points, in absolute mm, then its label."""
    points = [(x / style.g_per_module, y / style.g_per_module) for x, y in wire.points]
    try:
        drawn = symdef.wire(library, wire.style, points, lanes=wire.lanes)
    except symdef.InvalidValueError as error:
        msg = f"wire {wire.id!r} ({wire.lanes} lanes) cannot be drawn: {error}"
        raise DrawError(msg) from error
    line = _fragment(drawn, library, style)
    return line + (text_tag(wire.label, library, style) if wire.label else "")


def svg(
    drawing: Drawing,
    library: symdef.Library,
    style: Style,
    *,
    sheet_mm: tuple[int, int, int, int] | None = None,
) -> str:
    """The `<svg>` text of `drawing`: every symbol, every wire with its label, then every text.

    `sheet_mm` is (width, height, content_x, content_y) of the paper: the SVG is then the whole
    sheet with the drawing at the content box, as `diagram_sheets` draws it (render-0027).
    Without it the SVG is the drawing's area alone.
    """
    parts = [_outline(outline, library, style) for outline in drawing.outlines]
    parts += [_symbol(sym, library, style) for sym in drawing.symbols]
    parts += [_wire(wire, library, style) for wire in drawing.wires]
    parts += [_marker(marker, library, style) for marker in drawing.markers]
    parts += [text_tag(text, library, style) for text in drawing.texts]
    body = "".join(parts)
    if sheet_mm is not None:
        width, height, x, y = sheet_mm
        return sheet_svg(width, height, content_group(body, x, y), margin_mm=0)
    width_mm, height_mm = (
        format_decimal(_mm(drawing.area.w, style)),
        format_decimal(_mm(drawing.area.h, style)),
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm"'
        f' viewBox="0 0 {width_mm} {height_mm}">{body}</svg>'
    )
