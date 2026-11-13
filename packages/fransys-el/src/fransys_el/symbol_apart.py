"""What a symbol must keep apart: the ports of a function that no conductive link joins (FUSE-TERMINAL, R2089)."""

from itertools import combinations
from typing import TYPE_CHECKING

from fransys_model.derive import link_groups, port_function

from .placement_ids import symbol_key
from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

__all__ = ["link_fact", "refuse_joined"]


def link_fact(model: Model, function: Function) -> str:
    """`protective` when a protective link joins two of the function's ports (a fuse in the path), else `none`."""
    found = any(g.function == function.id for g in link_groups(model, lambda role: role.protective))
    return "protective" if found else "none"


def refuse_joined(model: Model, function: Id[Function], bound: Mapping[Id[Port], str], groups: frozenset[frozenset[str]]) -> None:
    """ERROR when the symbol draws two ports of the part at one node and no conductive link of the part joins them (R2089)."""
    here = [pid for pid in bound if port_function(model, pid) == function]
    joined = {frozenset((g.ports[0], other)) for g in link_groups(model, lambda role: role.joins_net) for other in g.ports[1:]}
    for a, b in combinations(here, 2):  # in binding order
        if any({bound[a], bound[b]} <= group for group in groups) and frozenset((a, b)) not in joined:
            refuse(
                f"function {function}",
                f"the symbol draws ports {bound[a]} and {bound[b]} at one point, but no conductive link of the part joins them: "
                "a fused terminal part no longer names `symbol=`. Its protective link chooses the symbol. Delete the line",
                symbol_key(model, function),
            )
