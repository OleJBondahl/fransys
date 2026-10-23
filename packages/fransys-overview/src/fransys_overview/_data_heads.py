"""The lane texts of a lanes view (O4): text from `derive`, corner from the view."""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import lane_head

if TYPE_CHECKING:
    from fransys_model.derive import PlacedHead
    from fransys_model.kernel import Model


def heads_data(model: Model, heads: tuple[PlacedHead, ...]) -> list[list[Any]]:
    """`[text, x, y]` per lane that prints one: `x`, `y` the top-left corner, from the view."""
    return [[lane_head(model, h.node), h.x, h.y] for h in heads]


__all__ = ["heads_data"]
