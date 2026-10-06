"""Black-box content (units spec U1): a boundary replica, one item or a whole drawing set.

Shared by `fransys_render`'s own outline reader and `fransys_pdf`'s replica-only
check, since neither output package may import the other (DESIGN 4).
"""

from fransys_model.layout import DrawingSet, Page, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .lookups import require

__all__ = ["drawing_set_is_replica_only", "is_black_box_item"]


def is_black_box_item(model: Model, item: Id[Item], drawing_set_unit: Id[Unit] | None) -> bool:
    """Whether an item at a drawing set of the given unit is that set's black-box content.

    True when the item's own unit is set and differs from `drawing_set_unit`
    -- the same comparison `fransys_layout`'s `replicate_boundaries` already encodes on
    the layout side, and `fransys_render`'s outline already reads on the render side;
    this is the one place both may share it (outputs never import each other).

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    found = require(items(model).get(item), "item", item)
    return found.unit is not None and found.unit != drawing_set_unit


def drawing_set_is_replica_only(model: Model, drawing_set: Id[DrawingSet]) -> bool:
    """Whether every function placed in `drawing_set` is black-box content, or none are placed.

    `fransys_pdf`'s own question: a drawing set holding nothing but replicated black-box
    boundaries has no home content of its own. Reads `is_black_box_item` for the item of every
    function placed on one of `drawing_set`'s own pages, `drawing_set.unit` the comparison
    unit; an empty drawing set gives `True`, since it has no placement that is not black-box
    content.

    Raises:
        SchemaError: `drawing_set` is not a `layout.drawing_set` of `model`.
    """
    found = require(
        layout_of(model, DrawingSet).get(drawing_set), "layout.drawing_set", drawing_set
    )
    all_functions = functions(model)
    pages = {page.id for page in layout_of(model, Page).values() if page.drawing_set == drawing_set}
    placed_items = {
        all_functions[placement.function].item
        for placement in layout_of(model, SymbolPlacement).values()
        if placement.page in pages
    }
    return all(is_black_box_item(model, item, found.unit) for item in placed_items)
