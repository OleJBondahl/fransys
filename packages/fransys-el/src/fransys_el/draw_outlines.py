"""One frame per core Outline, its es symbol and title from `frame_titles` (UO7, R900).

The hull and the label room come from the core and the library; this draws them and computes none.
"""

from typing import TYPE_CHECKING

from fransys_layout.core import Box
from fransys_layout.drawing import DrawnOutline, DrawnText
from fransys_layout.symbols import outline_room, text_width_g

from .drawn_ids import outline_id

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from electrical_symbols import Library
    from fransys_layout.core import CoreLayout
    from fransys_model.kernel import Id
    from fransys_model.layout import Page

__all__ = ["drawn_outlines"]


def drawn_outlines(
    layout: CoreLayout, pages: Mapping[int, Page], titles: Mapping[str, tuple[str, str]], library: Library
) -> Iterator[tuple[Id[Page], DrawnOutline]]:
    """The frames of the layout, each on its page, its title in the label slot at the top left."""
    slot = outline_room(library).label
    for o in layout.annotations.outlines:
        b = o.box
        key, text = titles[o.key]
        label = Box(b.x + slot.x, b.y + slot.y, text_width_g(library.font, text, height=slot.h), slot.h)
        corners = ((b.x, b.y), (b.x + b.w, b.y), (b.x + b.w, b.y + b.h), (b.x, b.y + b.h))
        ident = outline_id(o.key, o.page, o.run)
        yield pages[o.page].id, DrawnOutline(ident, key, corners, DrawnText(text, label, "TAG", "NW", ident))
