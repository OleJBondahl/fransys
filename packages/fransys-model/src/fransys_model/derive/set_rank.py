"""A page's drawing set counted among its group's sets: the set number a reference prints."""

from typing import TYPE_CHECKING

from fransys_model.layout import DrawingSet, Page, layout_of
lazy from fransys_model.kernel import Model

lazy from .document_sets import set_group

if TYPE_CHECKING:
    from collections.abc import Hashable, Mapping

__all__ = ["set_rank", "set_ranks"]


def set_ranks(units: Mapping[int, Hashable]) -> dict[int, int]:
    """Each set number's place among the sets of its group, counted from 1.

    `units` maps a set number to its `set_group` (`None` for the top level). Layout, which has no
    model, reads this with its plans' sets and units.
    """
    return {
        number: sorted(n for n, unit in units.items() if unit == units[number]).index(number) + 1
        for number in units
    }


def set_rank(model: Model, page: Page) -> int:
    """The number of `page`'s drawing set among the sets of its `set_group`, counted from 1."""
    sets = layout_of(model, DrawingSet)
    own = sets[page.drawing_set]
    groups = {s.number: set_group(model, s.unit, s.location) for s in sets.values()}
    return set_ranks(groups)[own.number]
