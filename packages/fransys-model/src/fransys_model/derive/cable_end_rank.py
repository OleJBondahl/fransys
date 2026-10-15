"""The cable-end order key, one for every query that says which end of a cable is first.

Apart from `designation` so the key can read `in_reading` and stay clear of `harness` (CD4).
"""

from typing import TYPE_CHECKING

from fransys_model.derive.designation import designation_holder, product_designation
from fransys_model.derive.lookups import effective_placement, terminal_strip
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.membership import in_reading
from fransys_model.vocab.tables import aspect_nodes
lazy from fransys_model.vocab.core import Item

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey, Id, Model


def cable_end_owner(model: Model, item: Id[Item]) -> Id[Item]:
    """`item`'s strip, when it is a terminal with a parent; else the item that prints its label.

    Shared by `derive.harness` and `cable_rows`, so a landing on a terminal resolves to one end,
    and two blocks clipped on one head (`designation_holder`) are that head's one end.
    """
    strip = terminal_strip(model, item)
    return designation_holder(model, item) if strip is None else strip


def cable_end_rank(model: Model, item: Id[Item]) -> tuple[int, int, AuthoringKey, str, Id[Item]]:
    """`item`'s cable-end order key: unit member first, then location, designation text, `item`.

    An item in a unit (`in_reading`, CD4) sorts before one in none; then a located item (own or
    inherited placement). Shared by `harness` and `cable_rows`; `item` only breaks identical text.
    """
    node = effective_placement(model, item, Aspect.LOCATION)
    key: AuthoringKey = () if node is None else aspect_nodes(model)[node].key
    unit_first = 0 if in_reading(model, item, None) else 1
    return (unit_first, 0 if node is not None else 1, key, product_designation(model, item), item)
