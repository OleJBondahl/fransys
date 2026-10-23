"""The kit key of each symbol id, for the label texts of a core layout (CORE-TEXTS A)."""

from typing import TYPE_CHECKING

from .placement_ids import symbol_key

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Model

    from .placement_kit import PickKey

__all__ = ["symbol_keys"]


def symbol_keys(model: Model, kit: Mapping[PickKey, object]) -> dict[str, PickKey]:
    """Each kit key by its symbol id."""
    return {symbol_key(model, f): f for f in kit}
