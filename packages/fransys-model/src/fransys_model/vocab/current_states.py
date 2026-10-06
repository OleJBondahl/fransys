"""The law per consistent item state (RATINGS-2 "Switch states", CONTACT-STATES CS1).

Counting every switched link closed adds false loops: a changeover's two throws would be closed
at once. So the law of `current_bounds` is evaluated for each consistent state of the items, and
all the contacts of one item move together (an item is at rest or operated). A switched link is
closed in the state `link_state` names; `both` (and a conductive link) is always closed.

The graph with every switched link closed is cut into its connected COMPONENTS (the outside does
not join them: a loop lies in one component and the outside). The enumeration runs per component,
not per block of the graph. In each component the items owning a `rest` or `operated` link are
the stateful ones. Items are still treated as independent, but every evaluated state is
consistent per item (each item is in one state, all its links agreeing):
- an item whose links there close in ONE state (only make contacts, or only break contacts) is
  HELD: it is evaluated in the one state where its links close (they count closed). Every
  evaluated state is consistent per item, so a held item can miss a finding, never invent one;
- an item with links closing in BOTH states (a changeover, or make and break contacts) is
  ENUMERATED: 2^m assignments for m such items in the component, so independent components never
  multiply. At most `MAX_ENUMERATED_ITEMS` are enumerated, the smallest item ids first. The items
  above the cap are HELD AT REST: evaluated in their rest state only (the links that close at
  rest closed, the others open), so again every evaluated state is consistent per item. Opening
  every link of such an item would not do: it is no state of the item, and opening an unrated
  link splits a node and makes a loop that exists in no state, which raises a bound (a false
  ERROR). `MAX_ENUMERATED_ITEMS` is read at call time, so a test may lower it. The cap is used
  in `_stateful_items` and `_closed` only.

A position is bounded, per current kind, by the HIGHEST bound it has over the assignments in which
it exists (its own link is closed) and has a bound: a device is below its bound in SOME state
exactly when it is below the highest one. The bound names the enumerated items that matter: among
the assignments giving that same bound, those in the same state in all of them.
"""

import dataclasses
import itertools
from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Id, UnionFind
from fransys_model.vocab.enums import Current

from .current_bounds import highest
from .current_graph import Edge, Raw, Wire, group, solve

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_model.vocab.contacts import LinkState
    from fransys_model.vocab.core import Item, Port

    from .current_bounds import CurrentBound

MAX_ENUMERATED_ITEMS: Final = 8
_THROWS: Final[tuple[LinkState, ...]] = ("rest", "operated")
type _States = tuple[tuple[Id[Item], LinkState], ...]


def _stateful_items(parts: Sequence[Edge | Wire]) -> tuple[list[Id[Item]], set[Id[Item]]]:
    """The items to enumerate, and those above the cap, among the items owning `parts`.

    An item is enumerated when its stateful parts close in both states, at most
    `MAX_ENUMERATED_ITEMS` of them, the smallest ids first; the others of that kind are capped.
    """
    states: dict[Id[Item], set[LinkState]] = {}
    for part in parts:
        if part.item is not None and part.state != "both":
            states.setdefault(part.item, set()).add(part.state)
    both = sorted(item for item, closes in states.items() if len(closes) == len(_THROWS))
    return both[:MAX_ENUMERATED_ITEMS], set(both[MAX_ENUMERATED_ITEMS:])


def _closed(part: Edge | Wire, chosen: Mapping[Id[Item], LinkState], capped: set[Id[Item]]) -> bool:
    """Whether `part` is closed under the assignment `chosen`.

    Always closed when its state is `both`; above the cap an item is held at rest, so its link
    closes only at rest. An enumerated item's link is closed in its closing state; held ones always.
    """
    if part.state == "both" or part.item is None:
        return True
    if part.item in capped:
        return part.state == "rest"
    return chosen.get(part.item, part.state) == part.state


def _named(options: Sequence[tuple[CurrentBound, _States]]) -> CurrentBound:
    """The highest of the bounds in `options`, naming the items that all of its states agree on.

    `options` are one position's bound of one kind, each with the item assignment that gave it.
    `states` are the (item, state) pairs shared by every assignment giving that bound.
    """
    chosen = highest(bound for bound, _ in options)
    same = [
        set(states)
        for bound, states in options
        if (bound.value, bound.by, bound.role) == (chosen.value, chosen.by, chosen.role)
    ]
    return dataclasses.replace(chosen, states=tuple(sorted(set.intersection(*same))))


def _component(
    edges: Sequence[Edge],
    wires: Sequence[Wire],
    opens: Sequence[Id[Port]],
    root: Callable[[Id[Port]], Id[Port]],
) -> dict[int, tuple[CurrentBound, ...]]:
    """The bounds of the positions of one component, the highest over its item assignments.

    A position present in some assignment has an entry, empty if no assignment bounds it.
    """
    enumerated, capped = _stateful_items((*edges, *wires))
    options: dict[tuple[int, Current], list[tuple[CurrentBound, _States]]] = {}
    seen: set[int] = set()
    for combo in itertools.product(_THROWS, repeat=len(enumerated)):
        chosen = dict(zip(enumerated, combo, strict=True))
        found = solve(
            [e for e in edges if _closed(e, chosen, capped)],
            [w for w in wires if _closed(w, chosen, capped)],
            opens,
            root,
        )
        seen.update(found)
        for at, bounds in found.items():
            for bound in bounds:
                options.setdefault((at, bound.kind), []).append((bound, tuple(chosen.items())))
    return {
        at: tuple(_named(options[at, kind]) for kind in Current if (at, kind) in options)
        for at in seen
    }


def _by_component(
    raw: Raw, allc: UnionFind[Id[Port]], stateful: Sequence[Wire]
) -> tuple[dict[Id[Port], list[Edge]], dict[Id[Port], list[Wire]], dict[Id[Port], list[Id[Port]]]]:
    """The edges, the stateful wires and the open ports of each component with a position.

    A component is a connected part of the all-closed graph (`allc` joins every wire) whose edges
    are the positions; the outside vertex does not join components.
    """
    comps: UnionFind[Id[Port]] = UnionFind()
    for edge in raw.edges:
        comps.union(allc.find(edge.first), allc.find(edge.second))

    def home(port: Id[Port]) -> Id[Port]:
        return comps.find(allc.find(port))

    edges: dict[Id[Port], list[Edge]] = {}
    for edge in raw.edges:
        edges.setdefault(home(edge.first), []).append(edge)
    wires: dict[Id[Port], list[Wire]] = {}
    for wire in stateful:
        if home(wire.first) in edges:
            wires.setdefault(home(wire.first), []).append(wire)
    opens: dict[Id[Port], list[Id[Port]]] = {}
    for port in sorted(raw.opens):
        if home(port) in edges:
            opens.setdefault(home(port), []).append(port)
    return edges, wires, opens


def evaluate(raw: Raw) -> tuple[dict[int, tuple[CurrentBound, ...]], list[list[int]]]:
    """The bounds of every position by `Edge.at`, and the blocks of the all-closed graph.

    The blocks only group. A position present in some state has an entry, empty when no state bounds
    it, even when the all-closed graph shorts it.
    """
    base: UnionFind[Id[Port]] = UnionFind()
    allc: UnionFind[Id[Port]] = UnionFind()
    for wire in raw.wires:
        allc.union(wire.first, wire.second)
        if wire.state == "both":
            base.union(wire.first, wire.second)
    stateful = [wire for wire in raw.wires if wire.state != "both"]
    edges, wires, opens = _by_component(raw, allc, stateful)
    bounds: dict[int, tuple[CurrentBound, ...]] = {}
    for key, members in edges.items():
        bounds.update(_component(members, wires.get(key, []), opens.get(key, []), base.find))
    return bounds, group(raw.edges, stateful, raw.opens, base.find)
