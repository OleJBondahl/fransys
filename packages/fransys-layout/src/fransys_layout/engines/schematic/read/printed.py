"""The numbers of the drawing sets some document prints, read from a laid-out model (model-0201)."""

from typing import TYPE_CHECKING

from fransys_model.derive import printed_drawing_sets
from fransys_model.vocab import documents

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def printed_set_numbers(laid: Model) -> frozenset[int] | None:
    """`derive.printed_drawing_sets` as set numbers; `None` (every set) with no document.

    Laying out a model with no document is a test fixture (decision 0037): nothing to skip.
    """
    if not documents(laid):
        return None
    return frozenset(found.number for found in printed_drawing_sets(laid))
