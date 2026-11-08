"""The designations of the items a drawing names by id text (R1949)."""

lazy from collections.abc import Iterable

from fransys_model.derive.designation import item_designation
from fransys_model.kernel import Model, render_id

__all__ = ["drawn_designations"]


def drawn_designations(model: Model, ids: Iterable[str]) -> tuple[str, ...]:
    """The designation of each item whose id is written as `render_id` text, as `item_designation` prints it (`"U1-K1"`).

    A `DrawnRow.devices` entry is such a text. Raises `KeyError` for text that names no item of `model`.

    Example: `fr.derive.drawn_designations(result.model, row.devices)`.
    """
    items = {render_id(i): i for i in model.tables.get("item", {})}
    return tuple(item_designation(model, items[x]) for x in ids)
