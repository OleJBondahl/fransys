"""Where each function is placed: its Membership rows in reader order (model-0423)."""

from collections import defaultdict

from fransys_model.derive.order import placement_key
from fransys_model.layout import FrameCell, Membership, Page, layout_of
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

__all__ = ["function_placements"]


def function_placements(model: Model) -> dict[Id[Function], tuple[tuple[Id[Page], FrameCell], ...]]:
    """Each function's placements, one (page, cell) per Membership function row, ordered by `placement_key`.

    The one source of a function's other placements: a reader drops its own page and iterates the rest as given.
    """
    found: dict[Id[Function], list[tuple[Id[Page], FrameCell]]] = defaultdict(list)
    for row in layout_of(model, Membership).values():
        if row.function is not None and row.page is not None:
            found[row.function].append((row.page, row.cell))
    return {f: tuple(sorted(rows, key=lambda r: placement_key(model, *r))) for f, rows in found.items()}
