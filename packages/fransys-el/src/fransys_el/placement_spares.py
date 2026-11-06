"""A spare terminal: a terminal none of whose nets has a second end (R356, SPARE-TERMINALS)."""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_model.derive import PowerKind, drawn_physical_nets, function_item, stands, terminal_items

from .kit_keys import function_of
from .placement_skips import SPARE_TERMINAL

if TYPE_CHECKING:
    from fransys_layout.core import PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

    from .placement_kit import PickKey, SymbolKit

__all__ = ["spare_leads"]


def spare_leads(
    model: Model,
    kit: SymbolKit,
    ids: frozendict[PickKey, str],
    pins: frozendict[Id[Port], PinRef],
) -> frozendict[PickKey, str]:
    """Each kit key left off the page, with its reason (R356, R364).

    A terminal whose every net ends on it alone, and none of whose pins stands on the PE net, is a spare terminal. A function on no net is
    unwired, or a spare function when `derive.carried_functions` names it (an unwired contact).
    """
    met: dict[str, set[str]] = defaultdict(set)  # a symbol with a net that reaches past it
    for ports in (net.ports for net in drawn_physical_nets(model)):  # a bridge is no wire (R705)
        ends = {pins[p].sym if p in pins else None for p in ports}  # None: not drawn
        if len(ends) > 1:
            for sym in filter(None, ends):
                met[sym].add("")
    for port, kind in stands(model).items():  # a PE terminal joined by d.earth ends on the PE net
        if kind is PowerKind.PE and port in pins:
            met[pins[port].sym].add("")
    terminals = terminal_items(model)
    out: dict[PickKey, str] = {}
    for key, pick in kit.items():
        item = function_item(model, function_of(model, key))
        if not pick.members and not met[ids[key]] and item in terminals:
            out[key] = SPARE_TERMINAL
    return frozendict(out)
