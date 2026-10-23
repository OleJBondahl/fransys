"""The function each drawn symbol draws, read from the kit's picks (R467 C1, R468 S2, el-0057)."""

from typing import TYPE_CHECKING

from .drawn_ids import core_symbol_id
from .kit_keys import function_of
from .placement_ids import symbol_ids

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function

    from .placement_kit import SymbolKit

__all__ = ["drawn_subjects"]


def drawn_subjects(model: Model, kit: SymbolKit) -> dict[str, Id[Function]]:
    """For the drawn id of each symbol `kit` picks, the lead function of its pick.

    A member of a pole group has no symbol of its own and is absent; a pin view's lead is the
    function of its port. A marker, a table and a power symbol are no pick and are absent.
    The core Drawing names no model thing: this is where a drawn id meets its function.
    """
    return {
        core_symbol_id(sym): function_of(model, lead)
        for lead, sym in symbol_ids(model, kit).items()
    }
