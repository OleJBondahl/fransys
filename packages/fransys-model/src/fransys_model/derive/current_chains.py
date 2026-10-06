"""Current chains, their positions in path order from the supply end (decision model-0137).

The reduction lives in `vocab` because `vocab.validators.ratings_current` reads it and `vocab`
never imports `derive` (the precedent of `derive.closure`, decision 0019). The order needs the
potential rank, which is `derive`'s, so it is applied here and `vocab` keeps the bare chains.
"""

from collections import defaultdict

from fransys_model.derive.designation import can_print_designation, port_designation
from fransys_model.derive.potential import port_potential_rank
from fransys_model.vocab.current_bounds import CurrentBound, LimitRole
from fransys_model.vocab.current_chains import (
    CurrentChain,
    CurrentPosition,
    PositionEnds,
    chain_blocks,
)
from fransys_model.vocab.tables import functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port

__all__ = ["CurrentBound", "CurrentChain", "CurrentPosition", "LimitRole", "current_chains"]

_EndKey = tuple[bool, int, str]


def _port_text(model: Model, port: Id[Port]) -> str:
    """The port's printed designation, else its id value when its item cannot print one."""
    item = functions(model)[ports(model)[port].function].item
    return port_designation(model, port) if can_print_designation(model, item) else port.value


def _end_key(model: Model, at_node: list[Id[Port]]) -> _EndKey:
    """Ranked before unranked, the best rank first, then the lowest designation text."""
    ranks = [r for r in (port_potential_rank(model, port) for port in at_node) if r is not None]
    text = min(_port_text(model, port) for port in at_node)
    return (not ranks, min(ranks, default=0), text)


def _branch_text(model: Model, end: PositionEnds) -> str:
    """A position's designation text: the lower of its two ports' texts."""
    return min(_port_text(model, end.first), _port_text(model, end.second))


def _walk(model: Model, ends: tuple[PositionEnds, ...]) -> list[int]:
    """Indexes of `ends` in a depth-first edge walk from the supply end."""
    at_node: defaultdict[Id[Port], list[Id[Port]]] = defaultdict(list)
    incident: defaultdict[Id[Port], list[int]] = defaultdict(list)
    for index, end in enumerate(ends):
        at_node[end.first_node] += [end.first]
        at_node[end.second_node] += [end.second]
        incident[end.first_node].append(index)
        incident[end.second_node].append(index)
    ends_only = [node for node, found in incident.items() if len(found) == 1]
    start = min(ends_only or incident, key=lambda node: (_end_key(model, at_node[node]), node))
    order: list[int] = []
    seen: set[int] = set()
    stack = [start]
    while stack:
        free = [i for i in incident[stack[-1]] if i not in seen]
        if not free:
            stack.pop()
            continue
        pick = min(free, key=lambda i: (_branch_text(model, ends[i]), i))
        order.append(pick)
        seen.add(pick)
        end = ends[pick]
        stack.append(end.second_node if end.first_node == stack[-1] else end.first_node)
    return order


def current_chains(model: Model) -> tuple[CurrentChain, ...]:
    """The rated current paths of `model` grouped by loop, and what bounds each.

    The result is `vocab.current_chains.chains_unordered`, whose module docstring holds the graph
    and the law, with each chain's positions run in path order from its supply end.
    A chain's positions are edges of a block; its end ports are the nodes one
    position touches. The supply end is the end with the best `port_potential_rank`; with no
    ranked end, or a tie, the lower designation text. The positions follow a walk from it.

    A block that is no path (a loop with no end, a star, a position in parallel) runs by a
    depth-first walk from its best end, or its best node when it has none; at a fork the
    position with the lower designation text goes first, function ids only on equal texts.
    Chains sort by their ordered positions'
    functions, so the result is the same for any record order. Cached
    on `model.digest`, the last few results of `chain_blocks`.
    """
    ordered = [
        CurrentChain(tuple(chain.positions[i] for i in _walk(model, ends)))
        for chain, ends in chain_blocks(model)
    ]
    return tuple(sorted(ordered, key=lambda chain: [p.functions for p in chain.positions]))
