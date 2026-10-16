"""A page's drawing set counted among its own unit's sets: the set number a reference prints."""

from typing import TYPE_CHECKING

from fransys_model.layout import DrawingSet, Page, layout_of
lazy from fransys_model.kernel import Model

if TYPE_CHECKING:
    from collections.abc import Hashable, Mapping

__all__ = ["set_rank", "set_ranks"]


def set_ranks(units: Mapping[int, Hashable]) -> dict[int, int]:
    """Each set number's place among the sets of its own unit, counted from 1.

    `units` maps a set number to its unit (`None` for the top level). Layout, which has no
    model, reads this with its plans' sets and units.
    """
    return {
        number: sorted(n for n, unit in units.items() if unit == units[number]).index(number) + 1
        for number in units
    }


def set_rank(model: Model, page: Page) -> int:
    """The number of `page`'s drawing set among its own unit's sets, counted from 1."""
    sets = layout_of(model, DrawingSet)
    own = sets[page.drawing_set]
    return set_ranks({s.number: s.unit for s in sets.values()})[own.number]
