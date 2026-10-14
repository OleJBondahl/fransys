"""The lane texts of a lanes view (O4): text from `derive`, corner from the layout record."""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import lane_head

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import OverviewView


def heads_data(model: Model, view: OverviewView) -> list[list[Any]]:
    """`[text, x, y]` per lane that prints one: `x`, `y` the top-left corner, from the record."""
    heads: Any = view.ext.get("lane_heads", ())
    return [[lane_head(model, node), x, y] for node, x, y in heads]


__all__ = ["heads_data"]
