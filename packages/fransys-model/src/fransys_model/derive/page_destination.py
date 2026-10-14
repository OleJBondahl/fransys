"""The label of a drawing page's PDF named destination, one fact in one place (OVERVIEW O21).

It is `position_text`'s set-and-page form. The set is counted among its own unit's sets, never
the design-wide number, so a unit's PDF reads nothing above it (layout-0177) and nesting moves
no label.
"""

from fransys_model.layout import DrawingSet, Page, layout_of
lazy from fransys_model.kernel import Model

from .drawing_text import position_text

__all__ = ["page_destination", "set_rank"]


def set_rank(model: Model, page: Page) -> int:
    """The number of `page`'s drawing set among its own unit's sets, counted from 1."""
    sets = layout_of(model, DrawingSet)
    own = sets[page.drawing_set]
    return sorted(s.number for s in sets.values() if s.unit == own.unit).index(own.number) + 1


def page_destination(model: Model, page: Page) -> str:
    """`p<k>.<page>`: the destination label of `page`; `k` ranks its set among its unit's sets."""
    return position_text(page.number, None, None, (), set_number=set_rank(model, page))
