"""PIN_MARKING_WRONG: the marking text a drawn symbol prints at each pin, read back against `port_marking` (READ-IDENTITY, R1).

The expected side is the drawer's own: `derive.port_marking` of the port the kit gives that pin, for each slot the symbol declares.
"""

from typing import TYPE_CHECKING

from electrical_symbols import is_generic_box, marking_slot
from fransys_layout.symbols import library_symbol
from fransys_model.derive import hidden_pins, port_marking

from .drawn_finding import drawn_finding

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Port

    from .drawn_netlist import Netlist

__all__ = ["declared_marks", "marking_findings"]


def declared_marks(drawings: Mapping[Id[Page], Drawing], by: Mapping[str, Mapping[str, Id[Port]]], library: Library) -> dict[str, str]:
    """Each port to the marking slot id its symbol declares at that pin; a generic box declares none (`drawn_slots` owns its markings)."""
    found = {}
    for drawing in drawings.values():
        for symbol in drawing.symbols:
            if symbol.id not in by or is_generic_box(symbol.key):
                continue
            declared = {slot.id for slot in library_symbol(library, symbol.key, symbol.poles).slots}
            found.update({port.value: slot for pin, port in by[symbol.id].items() if (slot := marking_slot(pin)) in declared})
    return found


def marking_findings(net: Netlist, model: Model) -> tuple[Finding, ...]:
    """PIN_MARKING_WRONG per declared marking slot whose drawn text is not `port_marking` of its port (hidden pins skipped)."""
    hidden = hidden_pins(model)
    drawn = {(symbol.id, slot): text for part in net.pages.values() for symbol in part.drawing.symbols for slot, text in symbol.slots}
    found = []
    for port, slot in net.marks.items():
        if net.ids[port] in hidden:
            continue
        want, got = port_marking(model, net.ids[port]) or "", drawn.get((net.owners[port], slot), "")
        if want != got:
            found.append(
                drawn_finding(
                    "PIN_MARKING_WRONG",
                    (net.ids[port],),
                    f"symbol {net.owners[port]} prints {got!r} in slot {slot} where the port is marked {want!r}",
                )
            )
    return tuple(found)
