"""The one reader of a terminal's strip: the parent of a terminal item, else none."""

from fransys_model.derive.facts.item_predicates import terminal_items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item

from .children import parent_item


def strip_of(model: Model, item: Id[Item]) -> Id[Item] | None:
    """`item`'s strip when it is a terminal: its `Item.parent`; `None` for anything else."""
    if item not in terminal_items(model):
        return None
    return parent_item(model, item)
