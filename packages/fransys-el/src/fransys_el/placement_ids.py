"""How symbols and pins are spelled (el-0002): a symbol is its function's Id text (S1).

A core id is the record Id's text, never a printed designation. A pin is a
`PinRef(symbol, symbol port name)`.
"""

from typing import TYPE_CHECKING

from fransys_layout.core import PinRef
from fransys_model.derive import function_ports, has_function, port_name
from fransys_model.kernel import render_id

from .placement_kit import Pick, SymbolKit, refuse

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

__all__ = ["pin_names", "symbol_ids", "symbol_of"]


def symbol_ids(model: Model, kit: SymbolKit) -> frozendict[Id[Function], str]:
    """Each picked function's symbol id: the record Id's text, unique by construction (S1)."""
    for function in sorted(kit):
        if not has_function(model, function):
            refuse(f"kit function {function}", "the kit names a function not in the model")
    return frozendict({function: render_id(function) for function in sorted(kit)})


def symbol_of(kit: SymbolKit, ids: frozendict[Id[Function], str]) -> frozendict[Id[Function], str]:
    """The symbol id that draws each function: a lead its own, a member its lead's."""
    found = {}
    for lead, pick in kit.items():
        found[lead] = ids[lead]
        found.update(dict.fromkeys(pick.members, ids[lead]))
    return frozendict(found)


def _check(model: Model, lead: Id[Function], pick: Pick, text: str) -> None:
    """Every port of the lead and its members is named, and nothing else is."""
    own = {p for f in (lead, *pick.members) for p in function_ports(model, f)}
    missing = own - set(pick.ports)
    if missing:
        refuse(
            f"function {text}, port {port_name(model, min(missing))!r}",
            f"name the port in the Pick.ports of symbol {pick.key!r}",
        )
    stray = set(pick.ports) - own
    if stray:
        refuse(
            f"function {text}, pick {pick.key!r}",
            f"remove the {len(stray)} port(s) the function does not have from Pick.ports",
        )


def pin_names(
    model: Model, kit: SymbolKit, ids: frozendict[Id[Function], str]
) -> frozendict[Id[Port], PinRef]:
    """Each port of a drawn function as the `PinRef` of its symbol and symbol port."""
    found = {}
    for lead, pick in sorted(kit.items()):
        _check(model, lead, pick, ids[lead])
        found.update({port: PinRef(ids[lead], name) for port, name in pick.ports.items()})
    return frozendict(found)
