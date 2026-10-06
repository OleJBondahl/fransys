"""RATINGS-2 acceptance 3g: the law is the oracle for `current_chains`.

The oracle below is written from the spec's text ("The outside", "The law"), not from the
implementation. A random drawing is a position MULTIgraph: at most eight nodes and a handful of
positions between them (parallel positions and a position between two open ends allowed), some
nodes flagged open. A position is a plain rated device (no limit, no source), a full-range
protective device (a limit L), or a source (with a limit L or without). DC only.

THE OUTSIDE is ONE extra node O. Every open node is unioned into it: one edge from the node to
O per open node, each holding a source and setting no limit.

- A LOOP through a device D is a simple cycle (each vertex at most once) of the multigraph that
  contains D. Two parallel positions make a 2-cycle; a position between two open nodes makes a
  cycle through O.
- The loop HOLDS A SOURCE when any edge of it is a source position or an outside edge.
- The law's bound of D is the smallest limit L such that EVERY source-holding loop through D
  contains L (D's own limit counts). When no source-holding loop passes through D, the law found
  nothing: no bound (the vacuous truth is not read). A node with one position that is not open is
  a real dead end, with no loop through that position.

The oracle enumerates every simple cycle through each device by brute force. The drawing is then
built as a real `Plant` (a node is a hub port with conductors to the positions' ports, an open
node has an external item wired to it), `current_chains` is called, and each position is mapped
back to its drawn edge by its function. The expected values never come from the model.

Two properties: (1) `current_chains` never gives a bound the law does not give; (2) it gives
exactly the law's bound (or none) whenever the drawing reduces fully, that is, when an
independent series/parallel reducer written here (`reduces_fully`) folds every connected
component, the outside merged in, to a single edge.
"""

import dataclasses
from decimal import Decimal
from itertools import chain as _chain
from itertools import product
from typing import TYPE_CHECKING

import pytest
from current_plant import device, hub, wire
from current_plant import fuse as plant_fuse
from hypothesis import event, example, given, seed, settings
from hypothesis import strategies as st
from plant import Plant

from fransys_model.derive import current_chains
from fransys_model.kernel import make_id
from fransys_model.vocab import Operating, Rating, current_states
from fransys_model.vocab import current_chains as chains_module
from fransys_model.vocab.core import Item
from fransys_model.vocab.current_bounds import LimitRole, _limits_of
from fransys_model.vocab.enums import Current, FunctionKind, LinkKind, PortRole
from fransys_model.vocab.facets.rating import BoundaryValuesFacet, RatingFacet
from fransys_model.vocab.templates import FunctionTemplate, Part, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Port

_PLAIN, _PROTECT, _SOURCE = "plain", "protect", "source"
_CONTACT, _GATE = "contact", "gate"
_REST, _OPERATED = "rest", "operated"
_OUTSIDE = -1
_LIMITS = (50, 100, 150, 186, 250)


@dataclasses.dataclass(frozen=True)
class Pos:
    """One drawn position between nodes `u` and `v`: its kind and its limit, if any.

    A stateful position (kind `contact`, or `gate` for an unrated wire) is a switched link of
    item number `item`, closed when the item is in `state` (`rest` or `operated`). `fn` names its
    function within the item: the two throws of a changeover pole share one `fn` and one common
    node `u`. A `gate` is no position: where it is closed it joins its two nodes.
    """

    u: int
    v: int
    kind: str
    limit: int | None = None
    item: int | None = None
    state: str | None = None
    fn: str | None = None


@dataclasses.dataclass(frozen=True)
class Drawing:
    """The drawn multigraph: positions by index, and the nodes that are open ends."""

    positions: tuple[Pos, ...]
    open_nodes: frozenset[int] = frozenset()


def plain(u: int, v: int) -> Pos:
    """A plain rated device between `u` and `v`."""
    return Pos(u, v, _PLAIN)


def fuse(u: int, v: int, limit: int) -> Pos:
    """A full-range protective device of `limit` amperes."""
    return Pos(u, v, _PROTECT, limit)


def source(u: int, v: int, limit: int | None = None) -> Pos:
    """A source, with a continuous limit or (`limit` None) with a rating only."""
    return Pos(u, v, _SOURCE, limit)


def contact(u: int, v: int, item: int, state: str, fn: str | None = None) -> Pos:
    """A rated contact of item `item`, closed in `state`: a NO contact (operated) or NC (rest)."""
    return Pos(u, v, _CONTACT, None, item, state, fn)


def gate(u: int, v: int, item: int, state: str, fn: str | None = None) -> Pos:
    """An unrated switched link (a wire) of item `item`, closed in `state`."""
    return Pos(u, v, _GATE, None, item, state, fn)


def gate_changeover(common: int, brk: int, make: int, item: int, fn: str) -> tuple[Pos, Pos]:
    """An unrated changeover pole: `common` joined to `brk` at rest, to `make` when operated."""
    return gate(common, brk, item, _REST, fn), gate(common, make, item, _OPERATED, fn)


def changeover(common: int, brk: int, make: int, item: int, fn: str) -> tuple[Pos, Pos]:
    """One changeover pole of item `item`: `common` to `brk` at rest, to `make` when operated."""
    return contact(common, brk, item, _REST, fn), contact(common, make, item, _OPERATED, fn)


# --- the oracle: the law by brute force -------------------------------------------------------


def _function_name(index: int, pos: Pos) -> str:
    """The name of the function that holds position `index` (within its item, if it has one)."""
    return f"e{index}" if pos.item is None else (pos.fn or f"c{index}")


def _edges(drawing: Drawing) -> list[tuple[int, int, bool, int | None]]:
    """Every edge as (a, b, holds a source, limit): the positions, then one per open node to O."""
    drawn = [(p.u, p.v, p.kind == _SOURCE, p.limit) for p in drawing.positions]
    return drawn + [(node, _OUTSIDE, True, None) for node in sorted(drawing.open_nodes)]


def _paths(
    edges: list[tuple[int, int, bool, int | None]], start: int, goal: int, banned: int
) -> Iterator[frozenset[int]]:
    """The edge sets of every simple path from `start` to `goal` that skips edge `banned`."""

    def walk(at: int, seen: frozenset[int], used: tuple[int, ...]) -> Iterator[frozenset[int]]:
        if at == goal:
            yield frozenset(used)
            return
        for index, (a, b, _, _) in enumerate(edges):
            if index == banned or index in used or at not in (a, b):
                continue
            nxt = b if at == a else a
            if nxt not in seen:
                yield from walk(nxt, seen | {nxt}, (*used, index))

    return walk(start, frozenset({start}), ())


def _in_state(drawing: Drawing, closed: Callable[[Pos], bool]) -> dict[int, Decimal | None]:
    """The law's bound of every position present when only the positions `closed` accepts close.

    A closed `gate` joins its two nodes (a wire); an open one joins nothing. A position that is
    open, or whose two ends are one node after the joins, is not present and has no entry. The
    bound is the smallest limit on all the source loops through the position, brute force.
    """
    parent: dict[int, int] = {}

    def find(node: int) -> int:
        while parent.get(node, node) != node:
            node = parent[node]
        return node

    for pos in drawing.positions:
        if pos.kind == _GATE and closed(pos):
            parent[find(pos.u)] = find(pos.v)
    edges: list[tuple[int, int, bool, int | None]] = []
    index: list[int] = []
    for at, pos in enumerate(drawing.positions):
        one, other = find(pos.u), find(pos.v)
        if pos.kind != _GATE and closed(pos) and one != other:
            edges.append((one, other, pos.kind == _SOURCE, pos.limit))
            index.append(at)
    devices = len(edges)
    edges += [
        (node, _OUTSIDE, True, None) for node in sorted({find(n) for n in drawing.open_nodes})
    ]
    bounds: dict[int, Decimal | None] = {}
    for at, (u, v, _, _) in enumerate(edges[:devices]):
        loops = [
            path | {at} for path in _paths(edges, v, u, at) if any(edges[i][2] for i in path | {at})
        ]
        common = frozenset.intersection(*loops) if loops else frozenset()
        limits = [edges[i][3] for i in common if edges[i][3] is not None]
        bounds[index[at]] = Decimal(min(limits)) if limits else None
    return bounds


def _per_state(drawing: Drawing) -> list[dict[int, Decimal | None]]:
    """`_in_state` for each of the 2^k assignments of rest or operated to the k items."""
    items = sorted({p.item for p in drawing.positions if p.item is not None})
    return [
        _in_state(drawing, _closed_in(dict(zip(items, states, strict=True))))
        for states in product((_REST, _OPERATED), repeat=len(items))
    ]


def _closed_in(state: dict[int, str]) -> Callable[[Pos], bool]:
    """Which positions are closed when each item is in the state `state` gives it."""
    return lambda pos: pos.item is None or state[pos.item] == pos.state


def _highest(
    drawing: Drawing, per_state: list[dict[int, Decimal | None]]
) -> dict[int, Decimal | None]:
    """The highest bound over the states in which a device is present and has one.

    A device is a function: the positions of one function (a changeover pole's two throws) share
    the highest of their bounds. A gate is no device. No state giving a bound gives None.
    """
    best: dict[tuple[int | None, str], Decimal] = {}
    for found in per_state:
        for at, value in found.items():
            key = (drawing.positions[at].item, _function_name(at, drawing.positions[at]))
            if value is not None:
                best[key] = max(value, best.get(key, value))
    return {
        at: best.get((pos.item, _function_name(at, pos)))
        for at, pos in enumerate(drawing.positions)
        if pos.kind != _GATE
    }


def law_bounds(drawing: Drawing) -> dict[int, Decimal | None]:
    """The law's bound of every device: the highest over the item states, None if none gives one."""
    return _highest(drawing, _per_state(drawing))


def state_values(drawing: Drawing) -> dict[int, set[Decimal]]:
    """Every bound a device has in some state where it is present (its function, all states)."""
    per_state = _per_state(drawing)
    values: dict[tuple[int | None, str], set[Decimal]] = {}
    for found in per_state:
        for at, value in found.items():
            pos = drawing.positions[at]
            bucket = values.setdefault((pos.item, _function_name(at, pos)), set())
            if value is not None:
                bucket.add(value)
    return {
        at: values.get((pos.item, _function_name(at, pos)), set())
        for at, pos in enumerate(drawing.positions)
        if pos.kind != _GATE
    }


def all_closed_bounds(drawing: Drawing) -> dict[int, Decimal | None]:
    """The bounds with every switched link counted closed: the reading the spec replaced."""
    return _highest(drawing, [_in_state(drawing, lambda _: True)])


def present(drawing: Drawing) -> set[int]:
    """The positions that exist as a position (closed, not shorted) in at least one state."""
    return {at for found in _per_state(drawing) for at in found}


def reduces_fully(drawing: Drawing) -> bool:
    """Whether series and parallel folding leaves every component as a single edge.

    Parallel: edges with the same two ends become one. Series: a node with exactly two edges is
    removed and its two neighbours joined. The outside is one node with its open edges.
    """
    edges = {frozenset((a, b)) for a, b, _, _ in _edges(drawing)}
    while True:
        degree: dict[int, list[frozenset[int]]] = {}
        for edge in edges:
            for node in edge:
                degree.setdefault(node, []).append(edge)
        middle = next((node for node, held in degree.items() if len(held) == 2), None)
        if middle is None:
            return all(len(held) == 1 for held in degree.values())
        first, second = degree[middle]
        edges -= {first, second}
        edges.add((first | second) - {middle})


# --- the black box: the drawing as a real plant ------------------------------------------------


def _external(plant: Plant, node: int, port: Id[Port]) -> None:
    """An external item with a one-port function, wired to the hub port of `node`."""
    key = f"X{node}"
    item = Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None,
        parent=None,
        position=None,
        tag=None,
        description="Invented",
        installed=True,
        unit=None,
        external=True,
    )
    plant.add(item)
    wire(plant, plant.port(plant.function(item.id, "f"), "p"), port)


def _add_function(
    plant: Plant, item: int, name: str, members: list[Pos], hubs: dict[int, Id[Port]]
) -> None:
    """Item `I{item}`'s contact function `name`, holding the drawn positions `members`.

    One member is a NO (operated) or NC (rest) contact with a switched link between two ports.
    Two members are the throws of one changeover pole: a common port and a break and a make port
    with role templates, and a switched link from the common to each throw. It is rated (a
    template rating, so it states a current) unless it is a `gate`.
    """
    key = f"I{item}"
    part = make_id(Part, (f"part-{key}",))
    item_id = make_id(Item, (key,))
    pole = len(members) == 2
    if pole:
        (brk,) = [m for m in members if m.state == _REST]
        (make,) = [m for m in members if m.state == _OPERATED]
        ends = [(members[0].u, "c", PortRole.COMMON), (brk.v, "b", PortRole.BREAK)]
        ends.append((make.v, "m", PortRole.MAKE))
        links = [("c", "b"), ("c", "m")]
        kind = FunctionKind.CONTACT_CO
    else:
        only = members[0]
        ends = [(only.u, "1", PortRole.GENERIC), (only.v, "2", PortRole.GENERIC)]
        links = [("1", "2")]
        operated = only.state == _OPERATED
        kind = FunctionKind.CONTACT_NO if operated else FunctionKind.CONTACT_NC
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, name)),
        key=(key, name),
        part=part,
        name=name,
        kind=kind,
    )
    pins = {
        pin: PortTemplate(
            id=make_id(PortTemplate, (key, name, pin)),
            key=(key, name, pin),
            function=template.id,
            name=pin,
            role=role,
        )
        for _, pin, role in ends
    }
    plant.add(template, *pins.values())
    for at, (first, second) in enumerate(links):
        plant.link(pins[first], pins[second], LinkKind.SWITCHED, key=f"link-{key}-{name}-{at}")
    if members[0].kind == _CONTACT:
        rating = Rating(current_dc_a=Decimal(999))
        facet_id = make_id(RatingFacet, (key, name))
        plant.add(RatingFacet(id=facet_id, key=(key, name), subject=template.id, rating=rating))
    function = plant.function(item_id, name, template=template.id, kind=kind)
    for node, pin, _ in ends:
        wire(plant, plant.port(function, pin, template=pins[pin].id), hubs[node])


def _add_items(plant: Plant, drawing: Drawing, hubs: dict[int, Id[Port]]) -> None:
    """The stateful items: item `I{j}` owns the contact functions of the positions with item j."""
    for item in sorted({p.item for p in drawing.positions if p.item is not None}):
        plant.item(f"I{item}", part=plant.part(f"I{item}"))
        groups: dict[str, list[Pos]] = {}
        for at, pos in enumerate(drawing.positions):
            if pos.item == item:
                groups.setdefault(_function_name(at, pos), []).append(pos)
        for name, members in groups.items():
            _add_function(plant, item, name, members, hubs)


def build(drawing: Drawing) -> Model:
    """The drawing as a `Plant` model: position `i` is item `e{i}`, node `n` is hub `N{n}`.

    The stateful positions are the contact functions of items `I{j}` instead (`_add_items`).
    """
    plant = Plant()
    used = sorted({n for p in drawing.positions for n in (p.u, p.v)})
    hubs = {node: hub(plant, f"N{node}") for node in used}
    _add_items(plant, drawing, hubs)
    for index, pos in enumerate(drawing.positions):
        key = f"e{index}"
        if pos.item is not None:
            continue
        if pos.kind == _PLAIN:
            ports = device(plant, key, amps="999")
        elif pos.kind == _PROTECT:
            ports = device(plant, key, amps=str(pos.limit), kind=FunctionKind.PROTECTION)
        elif pos.limit is None:
            ports = device(plant, key, amps="999", kind=FunctionKind.SUPPLY)
        else:
            ports = device(plant, key, limit=str(pos.limit), kind=FunctionKind.SUPPLY)
        wire(plant, ports[0], hubs[pos.u])
        wire(plant, ports[1], hubs[pos.v])
    for node in sorted(drawing.open_nodes & set(used)):
        _external(plant, node, hubs[node])
    return plant.model()


def chain_bounds(drawing: Drawing, *, strict: bool = True) -> dict[int, Decimal | None]:
    """What `current_chains` gives each device: the highest DC bound of its positions, or None.

    A device is a function, as in `law_bounds`. With `strict`, a function that is in no chain
    must be one the oracle says is never a position (always open or always shorted); it gets
    None. Without it (held items may drop a position the law counts) a missing one gets None.
    """
    model = build(drawing)
    by_function: dict[object, Decimal | None] = {}
    for found in current_chains(model):
        for position in found.positions:
            dc = [b.value for b in position.bounds if b.kind is Current.DC]
            assert len(dc) <= 1
            for function in position.functions:
                old = by_function.get(function)
                by_function[function] = max((v for v in (old, *dc) if v is not None), default=None)
    exists = present(drawing)
    result: dict[int, Decimal | None] = {}
    for index, pos in enumerate(drawing.positions):
        if pos.kind == _GATE:
            continue
        owner = f"e{index}" if pos.item is None else f"I{pos.item}"
        function = Plant.function_id(owner, "f" if pos.item is None else _function_name(index, pos))
        assert function in by_function or index not in exists or not strict, (
            f"position {index} is in no chain of {drawing}"
        )
        result[index] = by_function.get(function)
    return result


def check(drawing: Drawing) -> bool:
    """Assert (1) never a bound the law does not give; (2) exactly the law's when it reduces fully.

    Returns whether the drawing reduced fully.
    """
    law = law_bounds(drawing)
    got = chain_bounds(drawing)
    exact = reduces_fully(drawing)
    for index, expected in law.items():
        if exact:
            assert got[index] == expected, f"e{index}: got {got[index]}, law {expected}: {drawing}"
        else:
            assert got[index] in (None, expected), (
                f"e{index}: got {got[index]}, law {expected}: {drawing}"
            )
    return exact


# --- the random drawings -----------------------------------------------------------------------


@st.composite
def _kinds(draw: st.DrawFn, u: int, v: int) -> Pos:
    kind = draw(st.sampled_from((_PLAIN, _PROTECT, _SOURCE)))
    limit = draw(st.sampled_from(_LIMITS))
    if kind == _PLAIN:
        return plain(u, v)
    if kind == _PROTECT:
        return fuse(u, v, limit)
    return source(u, v, draw(st.one_of(st.none(), st.just(limit))))


@st.composite
def drawings(draw: st.DrawFn) -> Drawing:
    """A random multigraph: up to eight nodes, one to seven positions, up to four open nodes."""
    nodes = draw(st.integers(2, 8))
    positions = []
    for _ in range(draw(st.integers(1, 7))):
        u = draw(st.integers(0, nodes - 1))
        v = (u + draw(st.integers(1, nodes - 1))) % nodes
        positions.append(draw(_kinds(u, v)))
    used = {n for p in positions for n in (p.u, p.v)}
    opened = draw(st.frozensets(st.sampled_from(sorted(used)), max_size=4))
    return Drawing(tuple(positions), opened)


@st.composite
def series_parallel_drawings(draw: st.DrawFn) -> Drawing:
    """A drawing series-parallel by construction: one edge, then edges replaced by two.

    An edge (u, v) becomes (u, w), (w, v) in series, or is doubled in parallel. The outside is
    either not used or joined at both terminals of the first edge (which keeps it series-parallel).
    """
    edges = [(0, 1)]
    count = 2
    for _ in range(draw(st.integers(0, 6))):
        at = draw(st.integers(0, len(edges) - 1))
        u, v = edges[at]
        if count < 8 and draw(st.booleans()):
            edges[at : at + 1] = [(u, count), (count, v)]
            count += 1
        else:
            edges.append((u, v))
    positions = tuple(draw(_kinds(u, v)) for u, v in edges)
    return Drawing(positions, draw(st.sampled_from((frozenset(), frozenset({0, 1})))))


@st.composite
def stateful_drawings(draw: st.DrawFn) -> Drawing:
    """A random multigraph with up to three stateful items (zero items: no state at all).

    Up to four state-free positions, then per item one or two contacts: a NO, an NC, a changeover
    pole (two positions on one common node), an unrated wire that closes in one state, or an
    unrated changeover pole (two wires on one common node, one closing at rest, one operated).
    A wire's ends are any two nodes, so it often sits on a hub between rated positions.
    """
    nodes = draw(st.integers(2, 6))

    def pair() -> tuple[int, int]:
        u = draw(st.integers(0, nodes - 1))
        return u, (u + draw(st.integers(1, nodes - 1))) % nodes

    positions = [draw(_kinds(*pair())) for _ in range(draw(st.integers(0, 4)))]
    for item in range(draw(st.integers(0, 3))):
        for at in range(draw(st.integers(1, 2))):
            how = draw(st.sampled_from(("no", "nc", "co", "wire_no", "wire_nc", "wire_co")))
            u, v = pair()
            if how in ("co", "wire_co"):
                make = (u + draw(st.integers(1, nodes - 1))) % nodes
                pole = changeover if how == "co" else gate_changeover
                positions += pole(u, v, make, item, f"k{at}")
            elif how.startswith("wire"):
                positions.append(gate(u, v, item, _OPERATED if how == "wire_no" else _REST))
            else:
                positions.append(contact(u, v, item, _OPERATED if how == "no" else _REST))
    used = {n for p in positions for n in (p.u, p.v)}
    opened = draw(st.frozensets(st.sampled_from(sorted(used or {0})), max_size=3))
    return Drawing(tuple(positions), opened & used)


# --- the properties ----------------------------------------------------------------------------

_FIXED = {
    # (a) the orchestrator's two open ends: + is node 0, - is node 1; source between + and -.
    "two_open_ends": Drawing(
        (source(1, 4, 186), plain(4, 0), plain(0, 2), plain(0, 3)), frozenset({1, 2, 3})
    ),
    "plus_open_itself": Drawing(
        (source(1, 4, 186), plain(4, 0), plain(0, 2)), frozenset({0, 1, 2})
    ),
    "twin_without_t1": Drawing((source(1, 4, 186), plain(4, 0), plain(0, 2)), frozenset({1, 2})),
    # (b) a lone open string: a ring through the outside.
    "lone_open_string": Drawing(
        (source(0, 1, 186), plain(1, 2), fuse(2, 3, 250)), frozenset({0, 3})
    ),
    # (c) a string with a real dead end.
    "dead_end_closed": Drawing((source(0, 1, 186), plain(1, 2), plain(2, 3)), frozenset()),
    "dead_end_one_open": Drawing((source(0, 1, 186), plain(1, 2), plain(2, 3)), frozenset({0})),
    # (d) a load across both poles of an open string.
    "load_across_poles": Drawing(
        (source(0, 1, 186), plain(0, 2), plain(1, 3), plain(2, 3)), frozenset({2, 3})
    ),
    # (e) two 186 A strings on one bus (+ 0, - 1), then a 150 A full-range main fuse.
    "two_strings_main_fuse": Drawing(
        (
            plain(0, 2),
            source(2, 3, 186),
            plain(3, 1),
            plain(0, 4),
            source(4, 5, 186),
            plain(5, 1),
            plain(0, 6),
            fuse(6, 7, 150),
        ),
        frozenset({1, 7}),
    ),
    # Pendant edges and branching nodes. Positions are listed by index in the hand values below.
    # A theta: three paths between 0 and 1 (source and plain, plain and 100 A fuse, one plain).
    "theta": Drawing(
        (source(0, 2, 186), plain(2, 1), plain(0, 3), fuse(3, 1, 100), plain(0, 1)), frozenset()
    ),
    # A cut vertex (0) joining a ring with a source and a ring with none.
    "cut_vertex_one_source": Drawing(
        (
            source(0, 1, 186),
            plain(1, 2),
            plain(2, 0),
            fuse(0, 3, 100),
            plain(3, 4),
            plain(4, 0),
        ),
        frozenset(),
    ),
    # The same cut vertex, the second ring holding a 50 A source of its own.
    "cut_vertex_two_sources": Drawing(
        (
            source(0, 1, 186),
            plain(1, 2),
            plain(2, 0),
            fuse(0, 3, 100),
            source(3, 4, 50),
            plain(4, 0),
        ),
        frozenset(),
    ),
    # A ring with a pendant edge on a node of it.
    "ring_with_pendant": Drawing(
        (source(0, 1, 186), plain(1, 2), plain(2, 0), plain(2, 3)), frozenset()
    ),
    # A bridge (index 3) between a ring with a source and a ring with none.
    "bridge_between_rings": Drawing(
        (
            source(0, 1, 186),
            plain(1, 2),
            plain(2, 0),
            plain(2, 3),
            plain(3, 4),
            fuse(4, 5, 100),
            plain(5, 3),
        ),
        frozenset(),
    ),
    # A bridge between two open nodes: a loop through the outside, no limit on it.
    "bridge_between_open_nodes": Drawing((plain(0, 1),), frozenset({0, 1})),
    "fuse_bridge_between_open_nodes": Drawing((fuse(0, 1, 100),), frozenset({0, 1})),
    # K4 (not series-parallel): the source across 1-2, a 100 A fuse on 0-2.
    "k4_with_source_and_fuse": Drawing(
        (
            plain(0, 1),
            fuse(0, 2, 100),
            plain(1, 3),
            plain(2, 3),
            source(1, 2, 186),
            plain(0, 3),
        ),
        frozenset(),
    ),
}

_HAND = {
    "two_open_ends": {0: 186, 1: 186, 2: None, 3: None},
    "plus_open_itself": {0: 186, 1: 186, 2: None},
    "twin_without_t1": {0: 186, 1: 186, 2: 186},
    "lone_open_string": {0: 186, 1: 186, 2: 186},
    "dead_end_closed": {0: None, 1: None, 2: None},
    "dead_end_one_open": {0: None, 1: None, 2: None},
    "load_across_poles": {0: 186, 1: 186, 2: 186, 3: None},
    "two_strings_main_fuse": {0: 186, 1: 186, 2: 186, 3: 186, 4: 186, 5: 186, 6: 150, 7: 150},
    # Only loops with a source count. Path 2-3 (with the 100 A fuse) forms a loop only with the
    # source's path (bound 100 there); path 4 forms one only with the source's path (186).
    "theta": {0: 186, 1: 186, 2: 100, 3: 100, 4: 186},
    # A cycle cannot pass a cut vertex twice: the second ring's loops are its own.
    "cut_vertex_one_source": {0: 186, 1: 186, 2: 186, 3: None, 4: None, 5: None},
    "cut_vertex_two_sources": {0: 186, 1: 186, 2: 186, 3: 50, 4: 50, 5: 50},
    "ring_with_pendant": {0: 186, 1: 186, 2: 186, 3: None},
    "bridge_between_rings": {0: 186, 1: 186, 2: 186, 3: None, 4: None, 5: None, 6: None},
    "bridge_between_open_nodes": {0: None},
    "fuse_bridge_between_open_nodes": {0: 100},
    # Source loops through 1: {1,0,4} and {1,4,2,5}, sharing 1 and 4: min(100, 186). Through
    # 0, 2, 3 and 5 the shared edges are the source and the position itself: 186.
    "k4_with_source_and_fuse": {0: 186, 1: 100, 2: 186, 3: 186, 4: 186, 5: 186},
}


@example(_FIXED["two_open_ends"])
@example(_FIXED["plus_open_itself"])
@example(_FIXED["twin_without_t1"])
@example(_FIXED["lone_open_string"])
@example(_FIXED["dead_end_closed"])
@example(_FIXED["dead_end_one_open"])
@example(_FIXED["load_across_poles"])
@example(_FIXED["two_strings_main_fuse"])
@settings(max_examples=150, deadline=None, database=None, derandomize=True)
@given(drawings())
def test_the_chains_never_beat_the_law_and_match_it_when_the_drawing_reduces(
    drawing: Drawing,
) -> None:
    """(1) no bound the law does not give; (2) exactly the law's when it reduces fully."""
    event("reduces fully" if check(drawing) else "does not reduce fully")


@settings(max_examples=150, deadline=None, database=None, derandomize=True)
@given(drawings())
def test_the_chains_give_exactly_the_laws_bound_on_every_drawing(drawing: Drawing) -> None:
    """The strongest statement: exactly the law's bound or none, on ALL drawings."""
    assert chain_bounds(drawing) == law_bounds(drawing), drawing


@settings(max_examples=100, deadline=None, database=None, derandomize=True)
@given(series_parallel_drawings())
def test_series_parallel_drawings_get_exactly_the_laws_bound(drawing: Drawing) -> None:
    """(2) alone: a drawing built by series and parallel steps gets exactly the law's bounds."""
    assert reduces_fully(drawing)
    check(drawing)


def test_the_exact_half_is_not_vacuous() -> None:
    """Of 200 seeded drawings at least 20 reduce fully, so property (2) really runs."""
    reached: list[bool] = []

    @settings(max_examples=200, deadline=None, database=None, derandomize=True)
    @given(drawings())
    def draw_them(drawing: Drawing) -> None:
        reached.append(reduces_fully(drawing))

    draw_them()
    assert sum(reached) >= 20


def test_the_reducer_can_fail() -> None:
    """A star of three dead ends does not reduce; a ring, a theta and a lone edge do."""
    star = Drawing((plain(0, 1), plain(0, 2), plain(0, 3)))
    ring = Drawing((plain(0, 1), plain(1, 2), plain(2, 0)))
    theta = Drawing((plain(0, 1), plain(0, 2), plain(2, 1), plain(0, 3), plain(3, 1)))
    k4 = Drawing(tuple(plain(a, b) for a in range(4) for b in range(a + 1, 4)))
    assert [reduces_fully(d) for d in (star, ring, theta, k4, Drawing((plain(0, 1),)))] == [
        False,
        True,
        True,
        False,
        True,
    ]


def test_the_oracle_can_fail() -> None:
    """The oracle gives a bound only through source loops: a ring without a source has none."""
    assert law_bounds(Drawing((fuse(0, 1, 100), plain(1, 2), plain(2, 0)))) == {
        0: None,
        1: None,
        2: None,
    }
    assert law_bounds(Drawing((fuse(0, 1, 100), source(1, 2), plain(2, 0)))) == {
        0: Decimal(100),
        1: Decimal(100),
        2: Decimal(100),
    }


def test_the_hand_made_values_are_the_laws() -> None:
    """The fixed drawings' hand-made bounds equal the brute-force oracle's."""
    for name, drawing in _FIXED.items():
        hand = {i: None if v is None else Decimal(v) for i, v in _HAND[name].items()}
        assert law_bounds(drawing) == hand, name


def test_two_open_ends_leave_the_device_without_a_bound() -> None:
    """(a) `D` between + and a second open end has no bound; without the T1 end it has 186 A."""
    both = chain_bounds(_FIXED["two_open_ends"])
    twin = chain_bounds(_FIXED["twin_without_t1"])
    assert (both[2], both[3]) == (None, None)
    assert (both[0], both[1]) == (Decimal(186), Decimal(186))
    assert [twin[i] for i in range(3)] == [Decimal(186)] * 3


def test_the_fixed_drawings_get_the_hand_made_bounds() -> None:
    """(a) to (e): `current_chains` gives exactly the hand-made value for every device."""
    for name, drawing in _FIXED.items():
        hand = {i: None if v is None else Decimal(v) for i, v in _HAND[name].items()}
        assert chain_bounds(drawing) == hand, name


def test_every_device_is_in_a_chain() -> None:
    """Every drawn position appears in some chain, so a missing bound is never a missing device."""
    for drawing in _FIXED.values():
        model = build(drawing)
        seen = set(
            _chain.from_iterable(p.functions for c in current_chains(model) for p in c.positions)
        )
        assert {Plant.function_id(f"e{i}", "f") for i in range(len(drawing.positions))} <= seen


# --- item states (spec C3 "Switch states", acceptance 3g's last sentences and 3i) -----------------
# Per consistent assignment of rest or operated to the (at most three) items, the oracle deletes
# the positions open in that state, joins the nodes of the closed wires, and runs the same brute
# force. A device's bound is the highest over the states in which it is present and has one.
#
# HELD items. The spec (C3 "Switch states") says: "an item whose links in the block all close in
# one state (only make, or only break) is held in that state. Its other state has fewer real
# loops, so this can only miss a finding, never invent one". A rated NO or NC contact, or an
# unrated wire that closes in one state only, is such a link. So the law over ALL states is
# exact only for drawings whose items all have links closing in both states and no one-state
# wire; with a held item the code may give less than the law (the miss is spec-permitted), and
# the tests assert the SOUND form: none, or a value the law itself gives in some state.

_STATE_FIXED = {
    # 3i: main 100 A on the make throw, emergency 120 A on the break throw of one changeover pole
    # (common 3), then a 400 A full-range fuse (index 4) and a device D (index 5).
    "changeover_3i": Drawing(
        (
            source(0, 1, 100),
            source(0, 2, 120),
            *changeover(3, 2, 1, 0, "k"),
            fuse(3, 4, 400),
            plain(4, 5),
        ),
        frozenset({0, 5}),
    ),
    # (b) item 0 owns a NO contact (index 1) and an NC contact (index 2) in series: they are
    # never both closed, so the string 0-2-1 is never a loop, and 186 A never bounds the rest.
    "no_and_nc_of_one_item": Drawing(
        (
            source(0, 1, 186),
            contact(0, 2, 0, _OPERATED),
            contact(2, 1, 0, _REST),
            plain(0, 3),
            fuse(3, 1, 100),
        ),
    ),
    # (c) a held item, only NC contacts: the all-closed result.
    "held_nc_item": Drawing(
        (source(0, 1, 186), contact(1, 2, 0, _REST), plain(2, 3)), frozenset({0, 3})
    ),
    # A wire that closes only when operated (index 1, no device): open, both halves dead-end.
    "wire_closing_when_operated": Drawing(
        (source(0, 1, 186), gate(1, 2, 0, _OPERATED), plain(2, 3)), frozenset({0, 3})
    ),
}

# Held items where the code MISSES what the law over both states gives (spec-permitted).
_HELD_FIXED = {
    # A wire that closes at rest (held closed) shorts the device D1 (index 1): the code drops the
    # shorted position. The law over both states counts D1 when the wire is open: 186 A.
    "wire_shorting_a_device_at_rest": Drawing(
        (source(0, 1, 186), plain(1, 2), gate(1, 2, 0, _REST), plain(2, 3)), frozenset({0, 3})
    ),
    # A 50 A fuse (0), a source with no limit (1) and a NO contact (2), all parallel. Held
    # operated, the contact adds a loop that avoids the fuse, so the source has no bound. At rest
    # (contact open) the loop is fuse and source alone, and the law gives the source 50 A.
    "no_contact_parallel_to_source_and_fuse": Drawing(
        (fuse(0, 1, 50), source(0, 1), contact(0, 1, 0, _OPERATED))
    ),
}

# What the law gives (highest over both states) and what the code gives, by hand, for each.
_HELD_LAW = {
    "wire_shorting_a_device_at_rest": {0: 186, 1: 186, 3: 186},
    "no_contact_parallel_to_source_and_fuse": {0: 50, 1: 50, 2: None},
}
_HELD_CODE = {
    "wire_shorting_a_device_at_rest": {0: 186, 1: None, 3: 186},
    "no_contact_parallel_to_source_and_fuse": {0: 50, 1: None, 2: None},
}

_STATE_HAND = {
    # D and the fuse: 100 A operated (main), 120 A at rest (emergency); highest 120. The pole's
    # throws are one device: the highest of its two throws (100 and 120). Main: 100 (operated
    # only, at rest it dead-ends); emergency: 120.
    "changeover_3i": {0: 100, 1: 120, 2: 120, 3: 120, 4: 120, 5: 120},
    # Either state leaves the source and the fuse path as the only loop: 100 A. The contacts
    # never carry one (dead ends in both states).
    "no_and_nc_of_one_item": {0: 100, 1: None, 2: None, 3: 100, 4: 100},
    "held_nc_item": {0: 186, 1: 186, 2: 186},
    "wire_closing_when_operated": {0: 186, 2: 186},
}


def _hand(
    name: str, table: Mapping[str, Mapping[int, int | None]] = _STATE_HAND
) -> dict[int, Decimal | None]:
    return {i: None if v is None else Decimal(v) for i, v in table[name].items()}


def _two_sided(drawing: Drawing) -> bool:
    """Whether every item has links closing in both states (a held item has only one)."""
    items = {p.item for p in drawing.positions if p.item is not None}
    return all(
        {p.state for p in drawing.positions if p.item == item} == {_REST, _OPERATED}
        for item in items
    )


def _has_gate(drawing: Drawing) -> bool:
    return any(p.kind == _GATE for p in drawing.positions)


def _explain(
    drawing: Drawing, got: dict[int, Decimal | None], law: dict[int, Decimal | None]
) -> str:
    return f"got {got}, law {law}: {drawing}"


@example(_STATE_FIXED["changeover_3i"])
@example(_STATE_FIXED["no_and_nc_of_one_item"])
@settings(max_examples=60, deadline=None, database=None, derandomize=True)
@given(stateful_drawings().filter(lambda d: _two_sided(d) and not _has_gate(d)))
def test_exactly_the_laws_bound_when_every_item_has_both_states(drawing: Drawing) -> None:
    """No held item (each has links closing in both states) and no wire: exactly the law's."""
    law = law_bounds(drawing)
    event("states matter" if law != all_closed_bounds(drawing) else "no difference")
    got = chain_bounds(drawing)
    assert got == law, _explain(drawing, got, law)


@example(_STATE_FIXED["held_nc_item"])
@example(_STATE_FIXED["wire_closing_when_operated"])
@example(_HELD_FIXED["wire_shorting_a_device_at_rest"])
@example(_HELD_FIXED["no_contact_parallel_to_source_and_fuse"])
@settings(max_examples=60, deadline=None, database=None, derandomize=True)
@given(stateful_drawings())
def test_a_held_item_never_invents_a_bound(drawing: Drawing) -> None:
    """On ALL drawings, held items and one-state wires included, for every device the code gives
    none, or a bound the law itself gives in at least one state where the device exists (so at
    most the law's highest). Where no state gives a bound, the code gives none."""
    law = law_bounds(drawing)
    got = chain_bounds(drawing, strict=False)
    given_by_states = state_values(drawing)
    for at, value in got.items():
        assert value is None or value in given_by_states[at], _explain(drawing, got, law)
        ceiling = law[at]
        assert value is None or (ceiling is not None and value <= ceiling)


def _three_items(drawing: Drawing) -> bool:
    return len({p.item for p in drawing.positions if p.item is not None}) == 3


def _capped_bounds(drawing: Drawing, cap: int) -> dict[int, Decimal | None]:
    """`chain_bounds` with the enumeration cap lowered to `cap` (the cache is emptied around it)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(current_states, "MAX_ENUMERATED_ITEMS", cap)
        chains_module.chain_blocks.cache_clear()
        try:
            return chain_bounds(drawing, strict=False)
        finally:
            chains_module.chain_blocks.cache_clear()


@example(  # the shrunk example of the probe "a capped item opens both its links"
    Drawing(
        (
            source(0, 1, 50),
            contact(0, 1, 0, _OPERATED),
            contact(0, 1, 0, _REST),
            *gate_changeover(0, 1, 1, 1, "k0"),
            contact(0, 1, 2, _OPERATED),
        )
    ),
    1,
)
@settings(max_examples=60, deadline=None, database=None, derandomize=True)
@given(stateful_drawings().filter(_three_items), st.sampled_from((1, 2)))
def test_items_above_the_cap_are_held_at_rest_and_never_invent_a_bound(
    drawing: Drawing, cap: int
) -> None:
    """Spec C3 "Switch states": the items above `MAX_ENUMERATED_ITEMS` are HELD AT REST (their
    rest links closed, their operated links open), the others enumerated, and every evaluated
    state is consistent. So with three stateful items and a cap of 1 or 2 no bound is above the
    law's highest over ALL consistent assignments, and a bound the code gives is the law's bound
    in at least one consistent assignment (the capped items at rest). Which items are capped
    goes by item id, which the oracle does not know: it checks against every assignment.
    """
    law = law_bounds(drawing)
    got = _capped_bounds(drawing, cap)
    for at, value in got.items():
        ceiling = law[at]
        assert value is None or (
            value in state_values(drawing)[at] and ceiling is not None and value <= ceiling
        ), f"cap {cap}: {_explain(drawing, got, law)}"


# A second, independent changeover (different sources, fuse and node numbers than
# _STATE_FIXED["changeover_3i"]): a changeover pole's make/break throws are mutually exclusive
# by construction, so the law's per-state bound differs from the all-closed one on any such
# drawing. Kept out of _STATE_FIXED (whose keys test_the_state_hand_values_are_the_laws and
# test_the_stateful_fixed_drawings_get_the_hand_made_bounds iterate exhaustively against
# _STATE_HAND) since only test_the_state_drawings_are_not_vacuous needs it (P14).
_VACUITY_EXTRA_EXAMPLE = Drawing(
    (
        source(0, 1, 50),
        source(0, 2, 75),
        *changeover(3, 2, 1, 0, "k2"),
        fuse(3, 4, 200),
        plain(4, 5),
    ),
    frozenset({0, 5}),
)

_VACUITY_EXAMPLES = (
    _STATE_FIXED["changeover_3i"],
    _STATE_FIXED["no_and_nc_of_one_item"],
    _VACUITY_EXTRA_EXAMPLE,
    _HELD_FIXED["wire_shorting_a_device_at_rest"],
    _HELD_FIXED["no_contact_parallel_to_source_and_fuse"],
)

# `derandomize=True` derived its seed from the decorated function's compiled bytecode, which is
# not the same on every platform (observed: WSL/Linux and Windows disagreed on this exact
# property, both on Python 3.15.0rc2 / Hypothesis 6.168.0 -- the code object's embedded absolute
# file path differs between checkouts). A fixed @seed is an explicit constant, independent of
# platform or checkout path; chosen so the GENERATED draws alone (the five @examples below are
# excluded from the counts) clear both thresholds identically on Windows and in the mutmut
# recipe's WSL clone (verified; see the P14b commit message for both platforms' counts).
_VACUITY_SEED = 20260926


def test_the_state_drawings_are_not_vacuous() -> None:
    """Of 100 seeded drawings, many have stateful items and many bound differently by state.

    Five explicit `@example`s, each independently confirmed both stateful and law-differing,
    are excluded from the counts (identified by object identity, never generated by the
    strategy): only the GENERATED draws are checked against both thresholds, with a fixed
    `@seed` (`_VACUITY_SEED`) chosen so that holds identically on every platform this order
    runs on (P14b; P14's `derandomize=True` form is `git show 6931f3b6` if this ever needs
    reverting to the examples-guarantee-everything form instead).
    """
    seen: list[tuple[bool, bool]] = []

    @example(_VACUITY_EXAMPLES[0])
    @example(_VACUITY_EXAMPLES[1])
    @example(_VACUITY_EXAMPLES[2])
    @example(_VACUITY_EXAMPLES[3])
    @example(_VACUITY_EXAMPLES[4])
    @seed(_VACUITY_SEED)
    @settings(max_examples=100, deadline=None, database=None)
    @given(stateful_drawings())
    def draw_them(drawing: Drawing) -> None:
        if any(drawing is example_drawing for example_drawing in _VACUITY_EXAMPLES):
            return
        stateful = any(p.item is not None for p in drawing.positions)
        seen.append((stateful, law_bounds(drawing) != all_closed_bounds(drawing)))

    draw_them()
    assert sum(s for s, _ in seen) >= 50
    assert sum(d for _, d in seen) >= 5


def test_the_state_oracle_by_hand() -> None:
    """3i state by state: 100 A operated, 120 A at rest, 400 A when both throws count closed."""
    drawing = _STATE_FIXED["changeover_3i"]
    operated = _in_state(drawing, _closed_in({0: _OPERATED}))
    at_rest = _in_state(drawing, _closed_in({0: _REST}))
    assert (operated[5], at_rest[5]) == (Decimal(100), Decimal(120))
    assert 2 not in operated
    assert 3 not in at_rest
    assert all_closed_bounds(drawing)[5] == Decimal(400)


def test_the_state_hand_values_are_the_laws() -> None:
    """The fixed stateful drawings' hand-made bounds equal the oracle's."""
    for name, drawing in _STATE_FIXED.items():
        assert law_bounds(drawing) == _hand(name), name


def test_a_held_item_gives_the_all_closed_result() -> None:
    """(c) an item with only NC contacts: the highest over its states is the all-closed bound."""
    drawing = _STATE_FIXED["held_nc_item"]
    assert law_bounds(drawing) == all_closed_bounds(drawing)
    assert chain_bounds(drawing) == _hand("held_nc_item")


def test_the_changeover_example_is_not_400() -> None:
    """3i: D gets 120 A, not the 400 A of both throws counted closed, and no bound is lost."""
    got = chain_bounds(_STATE_FIXED["changeover_3i"])
    assert got[5] == Decimal(120)
    assert got[4] == Decimal(120)


def test_the_stateful_fixed_drawings_get_the_hand_made_bounds() -> None:
    """(a) to (c) and the wire: `current_chains` gives exactly the hand-made value."""
    for name, drawing in _STATE_FIXED.items():
        assert chain_bounds(drawing) == _hand(name), name


def test_the_held_item_misses_are_spec_permitted_and_pinned() -> None:
    """The law over both states gives more than the code, where a held item hides a state.

    Pinned as the code's SOUND value (the spec: the other state "can only miss a finding, never
    invent one"), so a change of the held rule shows here. The code's value is at most the law's
    and is a value the law gives in some state.
    """
    for name, drawing in _HELD_FIXED.items():
        law = law_bounds(drawing)
        assert law == _hand(name, _HELD_LAW), name
        got = chain_bounds(drawing, strict=False)
        assert got == _hand(name, _HELD_CODE), name
        assert got != law, name
        for at, value in got.items():
            assert value is None or value in state_values(drawing)[at], name


# --- `_limits_of` directly (RATINGS-2 C3): source envelopes, protection ratings, partial-range --
# `_limits_of` reads a function's SOURCE limits from every operating envelope it states
# (`function_operatings`: the template's own, then one per boundary that states one) and,
# unless `partial`, its PROTECTION limits from every rating it states (`function_ratings`: the
# same two sources). Both loops accumulate (`found += ...`); a function with two envelopes or
# two ratings must keep every one of them, not just the last found.


def test_a_functions_two_operating_envelopes_both_bound_it() -> None:
    """The template's own envelope and a boundary's each add a SOURCE bound; neither replaces
    the other (mutmut id 6 of `_limits_of`: `found += _bounds(...)` in the envelope loop)."""
    plant = Plant()
    device(plant, "S", limit="50", limit_ac="40")
    function = Plant.function_id("S", "f")
    unit = plant.unit("U")
    boundary_id = plant.boundary(unit, function)
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, ("S", "boundary")),
            key=("S", "boundary"),
            subject=boundary_id,
            operating=Operating(max_current_dc_a=Decimal(75), max_current_ac_a=Decimal(65)),
        )
    )
    model = plant.model()
    found = _limits_of(model, function)
    source = {(b.kind, b.value) for b in found if b.role is LimitRole.SOURCE}
    assert source == {
        (Current.DC, Decimal(50)),
        (Current.AC, Decimal(40)),
        (Current.DC, Decimal(75)),
        (Current.AC, Decimal(65)),
    }


def test_a_protection_functions_two_ratings_both_bound_it() -> None:
    """The part's own rating and a boundary's each add a PROTECTION bound; neither replaces
    the other (mutmut id 28 of `_limits_of`: `found += _bounds(...)` in the ratings loop)."""
    plant = Plant()
    plant_fuse(plant, "F", "50", amps_ac="40")
    function = Plant.function_id("F", "f")
    unit = plant.unit("U")
    boundary_id = plant.boundary(unit, function)
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, ("F", "boundary")),
            key=("F", "boundary"),
            subject=boundary_id,
            rating=Rating(current_dc_a=Decimal(90), current_ac_a=Decimal(80)),
        )
    )
    model = plant.model()
    found = _limits_of(model, function)
    protection = {(b.kind, b.value) for b in found if b.role is LimitRole.PROTECTION}
    assert protection == {
        (Current.DC, Decimal(50)),
        (Current.AC, Decimal(40)),
        (Current.DC, Decimal(90)),
        (Current.AC, Decimal(80)),
    }


def test_a_protection_ratings_ac_current_bounds_it_too() -> None:
    """A rating's `current_ac_a` reaches the PROTECTION bound, not only its `current_dc_a`
    (mutmut id 32 of `_limits_of`: the AC argument of the ratings loop's `_bounds` call)."""
    plant = Plant()
    plant_fuse(plant, "F", "50", amps_ac="40")
    function = Plant.function_id("F", "f")
    model = plant.model()
    found = _limits_of(model, function)
    protection = {(b.kind, b.value) for b in found if b.role is LimitRole.PROTECTION}
    assert (Current.AC, Decimal(40)) in protection
    assert (Current.DC, Decimal(50)) in protection


def test_one_partial_rating_hides_every_protection_bound_of_the_function() -> None:
    """The partial flag is function-wide (RATINGS-2 C3): one rating's `min_breaking_current_a`
    blanks ALL of the function's protection bounds, even a rating that states none of its own.
    Kills no listed survivor of `_limits_of`; pins the function-wide gate directly."""
    plant = Plant()
    plant_fuse(plant, "F", "50", amps_ac="40")  # the part's own rating: no min_breaking_current_a
    function = Plant.function_id("F", "f")
    unit = plant.unit("U")
    boundary_id = plant.boundary(unit, function)
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, ("F", "boundary")),
            key=("F", "boundary"),
            subject=boundary_id,
            rating=Rating(current_dc_a=Decimal(90), min_breaking_current_a=Decimal(4000)),
        )
    )
    model = plant.model()
    found = _limits_of(model, function)
    assert not any(b.role is LimitRole.PROTECTION for b in found)
