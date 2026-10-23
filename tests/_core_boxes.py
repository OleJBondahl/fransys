"""Connector boxes and outlines as the core path's page Drawings carry them (DEL-4 lane C2).

A box is a `generic-box` symbol whose cell strings name its connector; an outline's rectangle is
the bounding box of its points. Both are in G.
"""

from fransys_model import derive

type Rect = tuple[int, int, int, int]


def connector_names(model) -> dict:
    """Each connector function's printed designation ("-U1-J1"), by function id."""
    return {
        f.id: "-" + derive.item_designation(model, derive.connector_item(model, f.id))
        for f in derive.functions(model).values()
        if f.kind is derive.FunctionKind.CONNECTOR
    }


def named_boxes(drawing, names) -> dict:
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
    return symbol.x, symbol.y, symbol.x + stretch.get("x", 0), symbol.y + stretch.get("y", 0)


def outline_rect(outline) -> Rect:
    xs = [x for x, _ in outline.points]
    ys = [y for _, y in outline.points]
    return min(xs), min(ys), max(xs), max(ys)
