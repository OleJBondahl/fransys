"""How symbols and pins are spelled (el-0002 S1, amended by el-0006): a symbol is `symbol_key`.

A core id is the function's order text, then its Id text. A pin is a
`PinRef(symbol, symbol port name)`.
"""

from typing import TYPE_CHECKING, cast

from fransys_layout.core import PinRef
from fransys_model.derive import (
    port_name,
)
from fransys_model.derive.order import function_order_text, functions_in_order
from fransys_model.kernel import render_id

from .kit_keys import PickKey, function_of, held_ports, is_known
from .placement_kit import Pick, SymbolKit, refuse

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

__all__ = ["net_key", "net_lead", "pin_names", "symbol_ids", "symbol_key", "symbol_of"]


def symbol_key(model: Model, key: PickKey) -> str:
    """`"<function order text> [<port name>] <Id text>"`: the core breaks ties by `natural_key` of this text.

    The order text (`derive.order.function_order_text`) orders the symbols; the Id text only keeps the key unique.
    A PLC module's box takes its place from `Sym.rank` (`derive.order.plc_module_ranks`), not from this.
    """
    function = function_of(model, key)
    port = "" if function == key else f" {port_name(model, cast('Id[Port]', key))}"
    return f"{function_order_text(model, function)}{port} {render_id(key)}"


def net_lead(model: Model, ports: Iterable[Id[Port]]) -> Id[Port]:
    """The port that names a net: the least by function order text, then port name, never by Id (R1615)."""
    return cast("Id[Port]", functions_in_order(model, ports)[0])


def net_key(model: Model, ports: Iterable[Id[Port]]) -> str:
    """A net's core id, spelled as its lead port's `symbol_key`: the one spelling of a net, a bundle and a drawn wire's net."""
    return symbol_key(model, net_lead(model, ports))


def symbol_ids(model: Model, kit: SymbolKit) -> frozendict[PickKey, str]:
    """Each picked function's symbol id: the record Id's text, unique by construction (S1)."""
    for function in kit:
        if not is_known(model, function):
            refuse(
                f"kit key {function}",
                "the kit names a function or port not in the model",
                render_id(function),
            )
    return frozendict({function: symbol_key(model, function) for function in functions_in_order(model, kit)})


def symbol_of(kit: SymbolKit, ids: frozendict[PickKey, str]) -> frozendict[PickKey, str]:
    """The symbol id that draws each function: a lead its own, a member its lead's."""
    found = {}
    for lead, pick in kit.items():
        found[lead] = ids[lead]
        found.update(dict.fromkeys(pick.members, ids[lead]))
    return frozendict(found)


def _check(model: Model, lead: PickKey, pick: Pick, text: str) -> None:
    """Every port of the lead and its members is named, and nothing else is."""
    own = {p for f in (lead, *pick.members) for p in held_ports(model, f)}
    missing = own - set(pick.ports)
    if missing:
        refuse(
            f"function {text}, port {port_name(model, min(missing))!r}",
            f"name the port in the Pick.ports of symbol {pick.key!r}",
            text,
        )
    stray = set(pick.ports) - own
    if stray:
        refuse(
            f"function {text}, pick {pick.key!r}",
            f"remove the {len(stray)} port(s) the function does not have from Pick.ports",
            text,
        )


def pin_names(model: Model, kit: SymbolKit, ids: frozendict[PickKey, str]) -> frozendict[Id[Port], PinRef]:
    """Each port of a drawn function as the `PinRef` of its symbol and symbol port."""
    found = {}
    for lead in functions_in_order(model, kit):
        pick = kit[lead]
        _check(model, lead, pick, ids[lead])
        found.update({port: PinRef(ids[lead], name) for port, name in pick.ports.items()})
    return frozendict(found)
