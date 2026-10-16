"""Whether an item is installed: the one reading of `Item.installed` that drawings share."""

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item

__all__ = ["item_installed"]


def item_installed(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is installed; a drawing greys an item that is not (`installed=False`)."""
    return items(model)[item].installed
