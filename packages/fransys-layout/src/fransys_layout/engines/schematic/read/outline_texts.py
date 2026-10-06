"""Reads of the model's texts for the unit outlines (D6): a unit's title."""

from functools import partial
from typing import TYPE_CHECKING, Any

from fransys_model.derive.drawing_text import outline_title

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Id, Model


def outline_titles(model: Model) -> Callable[[Id[Any]], str]:
    """A unit's outline title of `model`, computed when `unit_outlines` asks for it."""
    return partial(outline_title, model)
