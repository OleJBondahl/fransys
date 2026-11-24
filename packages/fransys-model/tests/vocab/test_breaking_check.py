"""`check_breaking`: a protective device's breaking point against the prospective fault.

A battery bus declared by pins with no fault current; strings of modules join its plus bus
through string fuses `SF{i}`, a main fuse `FM` leaves it. Every fuse states breaking points.
"""

import dataclasses
import functools
import random
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from current_plant import changeover, device, fuse, hub, run, wire
from fault_plant import module
from plant import Plant
from rating_plant import figures, point, rail, states_block, supply

from fransys_model.checks.ratings_breaking import (
    RATING_BREAKING_BELOW_FAULT,
    check_breaking,
)
from fransys_model.checks.ratings_current import (
    LOAD_ABOVE_LIMIT,
    LOADS_ABOVE_LIMIT,
    check_load_draw,
)
from fransys_model.derive.facts.current.bounds import Tie
from fransys_model.derive.facts.current.graph import Edge, Wire
from fransys_model.derive.facts.current.states import assignments, stateful_items
from fransys_model.derive.facts.fault.graph import FaultGraph, Feed
from fransys_model.derive.facts.fault.prospective import _kind_share, _over_states, _position
from fransys_model.derive.facts.fault.solve import Fault, closed_state, highest, terminal_share
from fransys_model.elecdef import At, Current, Fuse, Range, Role, Unit
from fransys_model.kernel import Finding, Id, Model, ModelError, Severity, make_id
from fransys_model.vocab import (
    Operating,
    OperatingFacet,
)
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.templates import FunctionTemplate

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fransys_model.derive.facts.contacts import LinkState
    from fransys_model.derive.facts.fault.solve import Share


def _fn(key: str) -> Id[Function]:
    return Plant.function_id(key, "f")


_WORKED = (point("1000", "15000", "15"),)


def _states(plant: Plant, key: str, points: Sequence[Range]) -> None:
    """Make fuse `key`'s template state `points`, as a part library would."""
    states_block(plant, make_id(FunctionTemplate, (key, "f")), Fuse(breaking_capacity=tuple(points)), key=key)


def _limit(plant: Plant, key: str) -> None:
    """Give module `key` a 186 A current limit, so loops through it bound a load's draw."""
    facet_id = make_id(OperatingFacet, (key,))
    for at, record in enumerate(plant.records):
        if record.id == facet_id:
            operating = dataclasses.replace(record.operating, max_current=figures(Unit.A, None, "186"))
            plant.records[at] = dataclasses.replace(record, operating=operating)


def _battery(  # noqa: PLR0913 -- one keyword per thing a test varies
    points: Sequence[Range] = _WORKED,
    *,
    strings: int = 3,
    per: int = 4,
    volts: str = "51.2",
    fault: str | None = "6000",
    tc: str | None = "2",
    draws: Sequence[Sequence[str]] = (),
    extra: int = 0,
) -> Plant:
    """Strings of `per` modules, each through `SF{i}`; the main fuse `FM` feeds `draws` fuses.

    Each entry of `draws` is a 2 A fuse `D{n}` after `FM` with one load per draw behind it.
    Every `SF`/`FM` states `points`; the `D` fuses state none.
    """
    plant = Plant()
    plus, minus = hub(plant, "P"), hub(plant, "M")
    plant.net("bus+", (plus,), potential="B+")
    plant.net("bus-", (minus,), potential="B-")
    for n in range(extra):  # rated changeovers on the plus bus: items the fault walk enumerates
        wire(plant, changeover(plant, f"U{n}")[0], plus)
    supply(plant, "bat", {"B+": rail(volts), "B-": rail("0")}, current=Current.DC, pins=(plus, minus))
    for at in range(strings):
        modules = [module(plant, f"m{at}{n}", fault, tc) for n in range(per)]
        run(plant, minus, [*modules, fuse(plant, f"SF{at}", "125")], plus)
        _states(plant, f"SF{at}", points)
    if draws:  # a limited source adding no fault current closes the loops that bound the loads
        run(plant, minus, [module(plant, "S", "0")], plus)
        _limit(plant, "S")
    _states(plant, "FM", points)
    run(plant, plus, [fuse(plant, "FM", "125"), device(plant, "Z", kind=FunctionKind.LOAD)], minus)
    for at, loads in enumerate(draws):
        node = hub(plant, f"N{at}")
        run(plant, plus, [fuse(plant, f"D{at}", "2")], node)
        for number, draw in enumerate(loads):
            lamp = device(plant, f"L{at}{number}", kind=FunctionKind.LOAD)
            template = make_id(FunctionTemplate, (f"L{at}{number}", "f"))
            operating = Operating(nominal_current=Unit.A(draw))
            facet_id = make_id(OperatingFacet, (f"L{at}{number}", "n"))
            plant.add(OperatingFacet(id=facet_id, key=(f"L{at}{number}", "n"), subject=template, operating=operating))
            run(plant, node, [lamp], minus)
    return plant


def _main(model: Model) -> list[Finding]:
    """The findings on the main fuse: with one string the string fuse sees no source (0 A)."""
    return [f for f in check_breaking(model) if f.subjects == (_fn("FM"),)]


def test_worked_example_gives_the_three_findings() -> None:
    """The main fuse at 18000 A is over 15000 A, the string fuses at 12000 A not."""
    model = _battery(draws=(("2.5",), ("0.8", "0.8", "0.8"))).model()
    breaking = check_breaking(model)
    (below,) = breaking
    assert (below.code, below.severity, below.subjects) == (
        RATING_BREAKING_BELOW_FAULT,
        Severity.ERROR,
        (_fn("FM"),),
    )
    assert f"function {ref(_fn('FM'))} breaks 15000 A DC at 1000 V at 15 ms" in below.message
    assert "below the prospective 18000 A DC" in below.message
    assert ref(_fn("m00")) in below.message
    draw = check_load_draw(model)
    assert [(f.code, f.severity) for f in draw] == [
        (LOADS_ABOVE_LIMIT, Severity.WARNING),
        (LOAD_ABOVE_LIMIT, Severity.ERROR),
    ]
    assert draw[0].subjects == tuple(sorted(_fn(f"L1{n}") for n in range(3)))
    assert draw[1].subjects == (_fn("L00"),)


def test_the_blocks_points_decide_the_outcome() -> None:
    """The same main fuse is over its point at 15000 A and clear of it at 20000 A."""
    assert _main(_battery(points=(point("1000", "20000", "15"),)).model()) == []
    assert len(_main(_battery().model())) == 1


def test_an_unknown_time_constant_leaves_only_points_without_one() -> None:
    model = _battery(strings=1, per=1, fault="1000", tc=None).model()
    (finding,) = _main(model)
    assert "time constant of the sources, unknown" in finding.message


def test_a_min_only_point_is_no_current_and_raises_never_zero() -> None:
    """The part reader refuses such a point (BREAKING-MIN-ONLY); a model that holds one is not read as 0 A."""
    only_min = Range(Role.RATED, min=Unit.A("1000"), at=At(Current.DC, Unit.V("1000"), Unit.MS("15")))
    with pytest.raises(ModelError, match="no nom, max or typ"):
        check_breaking(_battery(points=(only_min,)).model())


# -- the chain walk against every item state ----------------------------------------

_Rails = dict["Id[Port]", frozenset[str]]
_THROWS: tuple[LinkState, ...] = ("rest", "operated")


def _rails_at(rails: _Rails, port: Id[Port]) -> frozenset[str]:
    return rails.get(port, frozenset())


def _wire(rng: random.Random, ports: Sequence[Id[Port]], item: Id[Item] | None = None, state: LinkState = "both") -> Wire:
    one, two = rng.sample(ports, 2)
    return Wire(one, two, item, state)


def _random_graph(rng: random.Random) -> tuple[FaultGraph, _Rails]:
    """A small fault component: sources, switched edges and wires, a changeover, rails on a few nodes."""
    ports = [Id[Port](kind="port", value=f"n{i}") for i in range(rng.randint(4, 7))]
    items = [Id[Item](kind="item", value=f"k{i}") for i in range(rng.randint(1, 5))]
    plus, minus = rng.sample(ports, 2)
    mid = rng.choice([port for port in ports if port not in (plus, minus)])
    past = rng.choice([port for port in ports if port not in (minus, mid, plus)])
    series = rng.random() < 0.5  # sources in series through `mid`, with a position dangling there
    edges: list[Edge] = []
    feeds: dict[int, Feed] = {}
    for at in range(rng.randint(5, 10)):
        one, two = rng.sample(ports, 2)
        if at < 3 and series:
            one, two = ((minus, mid), (mid, past), (past, plus))[at]
        elif at < 2 and rng.random() < 0.7:
            one, two = minus, plus
        elif at == 3 and series:  # the dangling position
            one, two = mid, Id[Port](kind="port", value="leaf")
        elif at == 4 and series:  # the protective position, faulted at a rail, its other end past the joint
            one, two = plus, past
        item, state = (rng.choice(items), rng.choice(_THROWS)) if rng.random() < 0.5 else (None, "both")
        edges.append(Edge(at, one, two, Tie((), (), source=at < 3), item, state))
        if at < 3:  # the first edges are sources, one of them with no known current or time constant
            current = None if rng.random() < 0.1 else Decimal(100 * 2**at)
            tau = None if rng.random() < 0.1 else Decimal(rng.choice((1, 2, 5)))
            function = Id[Function](kind="function", value=f"s{at}")
            feeds[at] = Feed((function,), frozenset({Current.DC}), frozendict({Current.AC: None, Current.DC: current}), tau)
    wires = [_wire(rng, ports, rng.choice(items), rng.choice(_THROWS)) for _ in range(rng.randint(0, 4))]
    wires += [_wire(rng, ports) for _ in range(rng.randint(0, 2))]
    common, brk, make = rng.sample(ports, 3)
    wires += [Wire(common, brk, items[0], "rest"), Wire(common, make, items[0], "operated")]
    rails = {plus: frozenset({"P"}), minus: frozenset({"M"})}
    rails.update({port: frozenset(rng.sample(["P", "M", "Q"], rng.randint(1, 2))) for port in ports if not series and rng.random() < 0.2})
    return FaultGraph(tuple(edges), tuple(wires), frozendict(), frozendict(feeds)), rails


def _every_state(graph: FaultGraph, rails_of: Callable[[Id[Port]], frozenset[str]], edge: Edge, rails: frozenset[str]) -> Share:
    """The share of `edge` over every assignment of every item of the component: the oracle."""
    parts = [*graph.edges, *graph.wires]
    shares = []
    for _, kept in assignments(parts, stateful_items(parts)[0]):
        edges = [part for part in kept if isinstance(part, Edge)]
        if edge in edges:
            state = closed_state(edges, [part for part in kept if isinstance(part, Wire)], rails_of)
            faults = (Fault(edge.at, edge.first, edge.second, Current.DC, rails), Fault(edge.at, edge.second, edge.first, Current.DC, rails))
            shares.append(highest([terminal_share(state, graph.feeds, fault) for fault in faults]))
    return _over_states(shares)


def test_the_chain_walk_equals_every_item_state() -> None:
    """Over random fault components, a position's walk over its chain's items is its walk over all items (BLOCK-STATES oracle shape).

    A budget of one walks no item and names the chain's, which are among the component's.
    """
    named_at_all = 0
    for seed in range(400):
        graph, rails = _random_graph(random.Random(seed))  # noqa: S311 -- a reproducible graph, not cryptography
        rails_of = functools.partial(_rails_at, rails)
        own = frozenset({"P", "M"})
        for edge in (edge for edge in graph.edges if edge.at not in graph.feeds):
            pos = _position(rails_of, (list(graph.edges), list(graph.wires)), edge)
            share, named = _kind_share(graph, pos, Current.DC, own, 2**20)
            oracle = _every_state(graph, rails_of, edge, own)
            assert (share.current_a, share.time_constant_ms, share.functions) == (oracle.current_a, oracle.time_constant_ms, oracle.functions), seed
            assert named == ()
            over = _kind_share(graph, pos, Current.DC, own, 1)[1]
            assert set(over) <= set(stateful_items([*graph.edges, *graph.wires])[0])
            named_at_all += bool(over)
    assert named_at_all > 0
