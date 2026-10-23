"""The MARKING strings of a drawn symbol: `marking.<symbol port>` where the symbol declares it.

layout-0027: a MARKING text exists only where the drawn symbol defines the slot. The text is
`derive.port_marking`. The power slot (`marking_text`) is declared by no library symbol. A box's
own markings stay with `electrical_symbols.drawn_slots`.
"""

from typing import TYPE_CHECKING

from electrical_symbols import is_generic_box
from fransys_layout.symbols import library_symbol
from fransys_model.derive.drawing_text import port_marking

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_model.kernel import Model

    from .placement_kit import Pick

__all__ = ["marking_slots"]


def marking_slots(model: Model, pick: Pick, library: Library) -> dict[str, str]:
    """`marking.<symbol port>` to its text, for each port of `pick` whose slot the symbol declares.

    A generic box is left to `drawn_slots`; a port the part marks with nothing prints nothing.
    """
    if is_generic_box(pick.key):
        return {}
    declared = {slot.id for slot in library_symbol(library, pick.key, pick.poles).slots}
    found = {}
    for port, name in pick.ports.items():
        slot = f"marking.{name}"
        text = port_marking(model, port)
        if slot in declared and text:
            found[slot] = text
    return found
