"""The PDF link box of each cross-reference marker: its drawn outline, one module out along its facing (SY7)."""

from typing import TYPE_CHECKING

from fransys_model.kernel import render_id
from fransys_model.layout import LinkMarker, Side, layout_of

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page

__all__ = ["link_boxes"]

_STEP = {Side.N: (0, -1), Side.E: (1, 0), Side.S: (0, 1), Side.W: (-1, 0)}


def link_boxes(model: Model, drawings: Mapping[Id[Page], Drawing], library: Library) -> dict[Id[LinkMarker], tuple[int, int, int, int]]:
    """Each marker's `(x, y, width, height)` in G: the outline layout's `marker_drawn_box` gave its symbol.

    The link area stands one module (`divisions_per_module` G) out of the outline along the marker's facing.
    """
    gap = library.grid.divisions_per_module
    outlines = {s.id: s.outline for d in drawings.values() for s in d.symbols if s.outline is not None}
    found = {}
    for marker in layout_of(model, LinkMarker).values():
        outline = outlines.get(render_id(marker.id))
        if outline is not None and marker.facing is not None:
            dx, dy = _STEP[marker.facing]
            found[marker.id] = (outline.x + dx * gap, outline.y + dy * gap, outline.w, outline.h)
    return found
