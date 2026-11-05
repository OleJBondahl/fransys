"""Connector boxes and outlines as the core path's page Drawings carry them (DEL-4 lane C2).

A box is a `generic-box` symbol whose cell strings name its connector; an outline's rectangle is
the bounding box of its points. Both are in G.
"""

from typing import Any

from fransys_model import derive

type Rect = tuple[int, int, int, int]


def connector_names(model) -> dict[Any, Any]:
    """Each connector function's printed designation ("-U1-J1"), by function id."""
    return {
        f.id: "-" + derive.item_designation(model, derive.connector_item(model, f.id))
        for f in derive.functions(model).values()
        if f.kind is derive.FunctionKind.CONNECTOR
    }


def named_boxes(drawing, names) -> dict[Any, Any]:
    """The generic boxes of `drawing` that print one of `names`, by that name."""
    found = {}
    for symbol in drawing.symbols:
        if symbol.key != "generic-box":
            continue
        for cell in (cell for row in symbol.texts for cell in row):
            if cell in names:
                found[cell] = symbol
    return found


def box_rect(symbol) -> Rect:
    stretch = dict(symbol.stretch)
    return int(symbol.x), int(symbol.y), int(symbol.x + stretch.get("x", 0)), int(symbol.y + stretch.get("y", 0))


def outline_rect(outline) -> Rect:
    xs = [x for x, _ in outline.points]
    ys = [y for _, y in outline.points]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def overlaps(a: Rect, b: Rect) -> bool:
    """Whether the rectangles (x0, y0, x1, y1) share area."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
