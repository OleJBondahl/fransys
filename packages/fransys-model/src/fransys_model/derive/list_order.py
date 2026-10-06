"""The one order of an exported list of items: by printed designation, then id (model-0153)."""

from typing import TYPE_CHECKING

from .designation import item_designation
from .natural_order import natural_key

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item


def in_designation_order(model: Model, listed: Iterable[Id[Item]]) -> tuple[Id[Item], ...]:
    """`listed` sorted by `natural_key` of its designation (`-X2` before `-X10`), then id."""
    return tuple(
        sorted(listed, key=lambda item: (natural_key(item_designation(model, item)), item))
    )
