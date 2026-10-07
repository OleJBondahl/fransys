"""A harness's wires beside its cables (`harness_cables`' sibling)."""

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item

from .lookups import require
from .reports import _all_wire_rows
from .wire_harness import harness_of_wire
lazy from .rows import WireRow


def harness_wires(model: Model, harness: Id[Item]) -> tuple[WireRow, ...]:
    """One `WireRow` per wire whose ends sit on the plugs of `harness`.

    The rows are the wire list's own: ends, colour, cross-section and printed label.
    A wire on no harness, or on two, is left out.

    Args:
        model: The frozen model to read.
        harness: The item whose wires to list.

    Returns:
        The harness's wires, sorted by `(from_, to, conductor)`.

    Raises:
        SchemaError: `harness` is not an item.
    """
    require(items(model).get(harness), "item", harness)
    return tuple(
        row
        for row in _all_wire_rows(model, None, None)
        if harness_of_wire(model, row.conductor) == harness
    )
