"""An authored `Chain` as symbol ids, and the box-drawn end that anchors it (layout-0181, 0396)."""

from typing import TYPE_CHECKING

from electrical_symbols import is_generic_box
from fransys_layout import HintError
from fransys_layout.core import Series
from fransys_model.layout import Chain, layout_of

from .placement_kit import refuse

if TYPE_CHECKING:
    from .placement_env import Env

__all__ = ["anchored", "chain_of"]


def _boxes(env: Env) -> set[str]:
    """The symbol ids of the box-drawn functions (a PLC channel or an item box)."""
    return {env.ids[k] for k, p in env.kit.items() if is_generic_box(p.key) and k in env.ids}


def chain_of(env: Env, record: Chain) -> tuple[str, ...]:
    """The chain's symbol ids in `index` order; `ProblemError` for a function with no symbol.

    A box-drawn function stands only at the head or tail (layout-0181): else `HintError` (0184).
    """
    found = []
    for entry in sorted(record.entries, key=lambda e: e.index):
        if entry.function not in env.owner:
            refuse(f"chain names function {entry.function}", "add a pick for it to the SymbolKit")
        found.append(env.owner[entry.function])
    if _boxes(env).intersection(found[1:-1]):
        text = (
            "a chain names a box-drawn function (a PLC channel or an item box) only at its head "
            "or its tail; put the box first or last in d.layout.chain"
        )
        raise HintError(text, subjects=(record.id,))
    return tuple(found)


def _anchor(ids: tuple[str, ...], boxes: set[str]) -> Series | None:
    """The lone step before a box-drawn tail, anchored at the tail; else none.

    A head box anchors nothing (R502): its channel pin has its circuit above the box
    (BOX-SIDES), so the free build is the flow. A longer chain closed by a box keeps its flow.
    """
    *lone, last = ids
    if len(lone) != 1 or last not in boxes or lone[0] in boxes:
        return None
    return Series((lone[0],), "tail")


def anchored(env: Env) -> tuple[Series, ...]:
    """One `Series` per authored chain that has a box-drawn end; the core reads them by symbol."""
    boxes = _boxes(env)
    found = (_anchor(chain_of(env, c), boxes) for c in layout_of(env.model, Chain).values())
    return tuple(s for s in found if s is not None)
