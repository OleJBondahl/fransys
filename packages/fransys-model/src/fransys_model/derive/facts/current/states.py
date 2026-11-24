"""The law per consistent item state, solved per block (RATINGS-2 "Switch states", model-0482).

Counting every switched link closed adds false loops: a changeover's two throws would be closed at
once. So the law of `bounds` is evaluated for each consistent state of the items: all the contacts
of one item move together (an item is at rest or operated), and a switched link is closed in the
state `link_state` names. `both` (and a conductive link) is always closed. Items are independent.

The states are enumerated per BLOCK of G*, not per component. G* has the always-closed classes
(`both` wires joined) as nodes; every position and every switched wire is an edge, and every open
node has an edge to the outside. A simple cycle of any state lifts to a simple cycle of G*, so a
position's bound depends only on the links in its own block of G*. In a block:
- an item with links closing in BOTH states (a changeover, or make and break contacts) is
  ENUMERATED: 2^m assignments for the m such items of that block;
- every other item acts there as a single-throw switch and is CLOSED. This is exact unless a
  position is left with no bound that a state with that item open gives it: a position shorted by a
  closed wire, or on a source loop that a closed link spoils. For such a block every item is
  enumerated (an exact search). Nothing is estimated.
A block whose search would take more than the budget (`[ratings] max_solves`, 2^n solves for n items)
is named (`evaluate`), never held: `RATING_STATES_OVER_BUDGET` is its ERROR.

A position is bounded, per current kind, by the HIGHEST bound it has over the assignments in which
it exists (its own link is closed) and has a bound: a device is below its bound in SOME state
exactly when it is below the highest one. The bound names the enumerated items that matter: among
the assignments giving that same bound, those in the same state in all of them.
"""

import dataclasses
import itertools
from typing import TYPE_CHECKING

from fransys_model.derive.facts.current.blocks import blocks
from fransys_model.derive.facts.current.bounds import highest
from fransys_model.derive.facts.current.graph import Edge, Raw, Wire, group, solve, sourced
from fransys_model.elecdef import Current
from fransys_model.kernel import Id, UnionFind
from fransys_model.vocab.roles import LINK_STATES

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping, Sequence

    from fransys_model.derive.facts.contacts import LinkState
    from fransys_model.derive.facts.current.bounds import CurrentBound
    from fransys_model.vocab.core import Item, Port

type _States = tuple[tuple[Id[Item], LinkState], ...]
type _Bounds = dict[int, tuple[CurrentBound, ...]]
type _Root = Callable[[Id[Port]], Id[Port]]


def switched(part: Edge | Wire) -> bool:
    """Whether `part` is a switched link: owned by an item and closed in one of its states only."""
    return part.item is not None and part.state != "both"


def stateful_items(parts: Sequence[Edge | Wire]) -> tuple[list[Id[Item]], list[Id[Item]]]:
    """The items owning a switched link among `parts`, and those whose links close in both states; sorted."""
    closes: dict[Id[Item], set[LinkState]] = {}
    for part in parts:
        if part.item is not None and switched(part):
            closes.setdefault(part.item, set()).add(part.state)
    return sorted(closes), sorted(item for item, states in closes.items() if len(states) == len(LINK_STATES))


def closed(part: Edge | Wire, chosen: Mapping[Id[Item], LinkState]) -> bool:
    """Whether `part` is closed when each item of `chosen` is in its state; an item not in it is closed."""
    if part.item is None or part.state == "both":
        return True
    return chosen.get(part.item, part.state) == part.state


def assignments(parts: Sequence[Edge | Wire], items: Sequence[Id[Item]]) -> Iterator[tuple[_States, list[Edge | Wire]]]:
    """Each assignment of `items`, with the parts of `parts` it closes."""
    for combo in itertools.product(LINK_STATES, repeat=len(items)):
        chosen = dict(zip(items, combo, strict=True))
        yield tuple(chosen.items()), [part for part in parts if closed(part, chosen)]


def _named(options: Sequence[tuple[CurrentBound, _States]]) -> CurrentBound:
    """The highest of the bounds in `options`, naming the items that all of its states agree on.

    `options` are one position's bound of one kind, each with the item assignment that gave it.
    `states` are the (item, state) pairs shared by every assignment giving that bound.
    """
    chosen = highest(bound for bound, _ in options)
    same = [set(states) for bound, states in options if (bound.value, bound.by, bound.role) == (chosen.value, chosen.by, chosen.role)]
    return dataclasses.replace(chosen, states=tuple(sorted(set.intersection(*same))))


def _over(parts: Sequence[Edge | Wire], opens: Sequence[Id[Port]], root: _Root, items: Sequence[Id[Item]]) -> _Bounds:
    """The bounds of the positions of one block, the highest over the assignments of `items`.

    A position present in some assignment has an entry, empty if no assignment bounds it.
    """
    options: dict[tuple[int, Current], list[tuple[CurrentBound, _States]]] = {}
    seen: set[int] = set()
    for chosen, kept in assignments(parts, items):
        found = solve([p for p in kept if isinstance(p, Edge)], [p for p in kept if isinstance(p, Wire)], opens, root)
        seen.update(found)
        for at, bounds in found.items():
            for bound in bounds:
                options.setdefault((at, bound.kind), []).append((bound, chosen))
    return {at: tuple(_named(options[at, kind]) for kind in Current if (at, kind) in options) for at in seen}


def _unfinished(found: _Bounds, parts: Sequence[Edge | Wire], opens: Sequence[Id[Port]], root: _Root) -> bool:
    """Whether a position has no bound that some state of the closed items could give it.

    A position with no entry is shorted by a closed wire; one with an empty entry counts only on a source
    loop of the all-closed block (a state is a subgraph of it).
    """
    edges = [part for part in parts if isinstance(part, Edge)]
    lacking = [edge.at for edge in edges if not found.get(edge.at)]
    if not lacking:
        return False
    on_loop = sourced(edges, [part for part in parts if isinstance(part, Wire)], opens, root)
    return any(at not in found or at in on_loop for at in lacking)


def _block(parts: Sequence[Edge | Wire], opens: Sequence[Id[Port]], root: _Root, budget: int) -> tuple[_Bounds, tuple[Id[Item], ...]]:
    """The bounds of one block of G*, and the items it names when it is too large to enumerate."""
    items, both = stateful_items(parts)
    if 2 ** len(both) > budget:
        return _over(parts, opens, root, []), tuple(both)
    found = _over(parts, opens, root, both)
    if len(items) == len(both) or not _unfinished(found, parts, opens, root):
        return found, ()
    if 2 ** len(items) > budget:
        return found, tuple(items)
    return _over(parts, opens, root, items), ()


def evaluate(raw: Raw, budget: int) -> tuple[_Bounds, list[list[int]], list[tuple[Id[Item], ...]]]:
    """The bounds of every position by `Edge.at`, the blocks of the all-closed graph, the oversized blocks.

    A position present in some state has an entry, empty when no state bounds it. An oversized block
    (a search of more than `budget` solves) is solved with its items closed, and its items are named.
    """
    base: UnionFind[Id[Port]] = UnionFind()
    for wire in raw.wires:
        if wire.state == "both":
            base.union(wire.first, wire.second)
    switched = [wire for wire in raw.wires if wire.state != "both"]
    parts = [part for part in (*raw.edges, *switched) if base.find(part.first) != base.find(part.second)]
    nodes = sorted({base.find(port) for port in raw.opens})
    ends = [(base.find(part.first), base.find(part.second)) for part in parts] + [(node, None) for node in nodes]
    bounds: _Bounds = {}
    oversized: list[tuple[Id[Item], ...]] = []
    for block in blocks(ends):
        inside = [parts[at] for at in sorted(block) if at < len(parts)]
        reached = {ends[at][0] for at in block if at >= len(parts)}
        found, named = _block(inside, [port for port in sorted(raw.opens) if base.find(port) in reached], base.find, budget)
        bounds.update(found)
        oversized += [named] if named else []
    return bounds, group(raw.edges, switched, raw.opens, base.find), oversized
