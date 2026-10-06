"""RATINGS-2 C3: `derive.current_chains` groups rated current paths and bounds each position.

Every device is an item `key` with one function `f` (builders in `current_plant`). A chain is
read back as a set of positions, each a name (the item keys of its functions, "plug+sock" for a
mate) with its bounds, so neither the order of the positions nor the end a chain is read from
matters. The expected values are written by hand from the spec's law (a limit bounds a device
when every loop through it that holds a source passes the limit, the outside being one node that
holds a source), never copied from the output. A chain is a block: positions any two of which
lie on a common loop. A string ends at external items, so that the outside closes its loop; a
real dead end has no loop and no bound.
"""

import dataclasses
import itertools
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from current_plant import (
    bypass_plant,
    capped_changeover,
    changeover,
    contactor,
    device,
    external,
    fuse,
    hub,
    in_unit,
    make_and_break,
    mated,
    open_string,
    rate,
    run,
    sense_pin,
    shorted_when_closed,
    switch_string,
    wire,
    with_role,
)
from plant import Plant
from rating_plant import rail, supply

from fransys_model.derive import current_chains
from fransys_model.kernel import Id, make_id
from fransys_model.vocab import Operating, Rating, current_states
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.current_bounds import CurrentBound, LimitRole, highest
from fransys_model.vocab.current_graph import Edge, Wire, _build, raw_of
from fransys_model.vocab.current_ties import open_ends, pairs
from fransys_model.vocab.enums import Current, FunctionKind, LinkKind, PortRole
from fransys_model.vocab.facets.rating import BoundaryValuesFacet
from fransys_model.vocab.tables import functions
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab.contacts import LinkState

_Bound = tuple[str, str, str, str]
_Position = tuple[str, tuple[_Bound, ...]]
_Chain = frozenset[_Position]


def _name(model: Model, function: Id[Function], prefix: str = "") -> str:
    return functions(model)[function].key[0].removeprefix(prefix)


def _read(model: Model, prefix: str = "") -> set[_Chain]:
    """Every chain of `model` as a set of (position name, its bounds); `prefix` is dropped."""
    return {
        frozenset(
            (
                "+".join(sorted(_name(model, f, prefix) for f in position.functions)),
                tuple(
                    (b.kind.value, str(b.value), _name(model, b.by, prefix), b.role.value)
                    for b in position.bounds
                ),
            )
            for position in chain.positions
        )
        for chain in current_chains(model)
    }


def _dc(value: str, by: str, role: str = "source") -> _Bound:
    return ("dc", value, by, role)


def _at(name: str, *bounds: _Bound) -> _Position:
    return name, bounds


def _same(*names: str, bound: _Bound | None = None) -> _Chain:
    """A chain whose every position `names` has the same one `bound`, or none."""
    return frozenset(_at(name, *([bound] if bound else [])) for name in names)


def _poles(plant: Plant) -> tuple[Id[Port], Id[Port]]:
    """`K1 - F1 - S - F2 - K2`, a 186 A source between a contactor and a fuse on each pole.

    Both contactors are rated 160 A. Returns the free ends: `K1`'s first and `K2`'s last port.
    """
    k1, f1 = contactor(plant, "K1", "160"), fuse(plant, "F1")
    source = device(plant, "S", limit="186")
    f2, k2 = fuse(plant, "F2"), contactor(plant, "K2", "160")
    run(plant, k1[1], [f1], source[0])
    run(plant, source[1], [f2], k2[0])
    return k1[0], k2[1]


_POLES = ("K1", "F1", "S", "F2", "K2")


def test_a_string_bounds_every_position_by_its_source() -> None:
    """Source, fuse, switched contactor, mated plug, load: one chain, all bounded by the 186 A."""
    plant = Plant()
    source = device(plant, "S", limit="186")
    plug, socket = mated(plant, "plug", "sock", amps="100")
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [fuse(plant, "F"), contactor(plant, "K")], plug)
    load = device(plant, "Z", amps="20")
    wire(plant, socket, load[0])
    wire(plant, load[1], external(plant, "T1"))
    assert _read(plant.model()) == {_same("S", "F", "K", "plug+sock", "Z", bound=_dc("186", "S"))}


def test_two_strings_and_a_feeder_on_one_node_are_each_bounded_by_their_own_source() -> None:
    """Acceptance 3: two strings and a feeder meet at one node and end at external items.

    The three arms form one loop set through the outside, so they are one chain (a block). Each
    string's devices sit on every loop through them, and so on their own source's limit only: the
    other string's source lies on the loop through the feeder or through the other string only.
    The feeder has a source-holding loop through either string: no limit lies on all, no bound.
    """
    plant = Plant()
    bus = hub(plant, "P")
    for tag, limit in (("a", "186"), ("b", "90")):
        line = [
            fuse(plant, f"f{tag}"),
            contactor(plant, f"k{tag}"),
            device(plant, f"s{tag}", limit=limit),
        ]
        run(plant, bus, line, external(plant, f"T{tag}"))
    run(plant, bus, [device(plant, "feed", amps="20")], external(plant, "Tf"))
    assert _read(plant.model()) == {
        _same("fa", "ka", "sa", bound=_dc("186", "sa"))
        | _same("fb", "kb", "sb", bound=_dc("90", "sb"))
        | _same("feed")
    }


def test_a_precharge_branch_and_unrated_leads() -> None:
    """Acceptance 3b: one chain from source to plug; the plug's bound is the source's 186 A."""
    model = bypass_plant().model()
    assert _read(model) == {
        _same("S", "F", "K", "R", "PK", "plug+sock", "Z", bound=_dc("186", "S"))
    }


def test_the_unrated_leads_and_the_monitor_appear_nowhere() -> None:
    """The sense leads and the insulation monitor state nothing: no position, no join."""
    names = {name for chain in _read(bypass_plant().model()) for name, _ in chain}
    assert not names & {"sense1", "sense2", "imd", "N1", "N2"}


def test_a_precharge_member_with_its_own_fuse_is_bounded_by_it() -> None:
    """Acceptance 3d: `PK` sees the 10 A fuse in its member; the main pole `K` keeps 186 A."""
    model = bypass_plant(fuse_in_branch=True).model()
    ten = _dc("10", "PF", "protection")
    source = _dc("186", "S")
    assert _read(model) == {
        frozenset(
            {
                _at("S", source),
                _at("F", source),
                _at("K", source),
                _at("R", ten),
                _at("PK", ten),
                _at("PF", ten),
                _at("plug+sock", source),
                _at("Z", source),
            }
        )
    }


def test_two_strings_on_one_bus_then_a_main_fuse() -> None:
    """Acceptance 3e: each string is bounded by its own source; `X`, `MF`, `Y` by the main fuse."""
    plant = Plant()
    plus, minus = hub(plant, "P"), hub(plant, "M")
    for tag in ("a", "b"):
        line = [
            fuse(plant, f"f{tag}1"),
            contactor(plant, f"k{tag}1", "160"),
            device(plant, f"s{tag}", limit="186"),
            contactor(plant, f"k{tag}2", "160"),
            fuse(plant, f"f{tag}2"),
        ]
        run(plant, plus, line, minus)
    run(
        plant,
        plus,
        [device(plant, "X", amps="200"), fuse(plant, "MF", "150")],
        external(plant, "Tp"),
    )
    run(plant, minus, [device(plant, "Y", amps="200")], external(plant, "Tm"))
    string = {
        tag: _same(
            *(f"{n}{tag}{i}" for n, i in (("f", 1), ("k", 1), ("k", 2), ("f", 2))),
            f"s{tag}",
            bound=_dc("186", f"s{tag}"),
        )
        for tag in "ab"
    }
    main = _dc("150", "MF", "protection")
    assert _read(plant.model()) == {
        string["a"] | string["b"] | frozenset({_at("X", main), _at("MF", main), _at("Y", main)})
    }


def test_a_source_free_parallel_pair_is_bounded_from_outside_and_by_its_own_member() -> None:
    """Two fuses in parallel: the source outside bounds both; each fuse also bounds itself."""
    plant = Plant()
    u, v = hub(plant, "U"), hub(plant, "V")
    run(plant, u, [fuse(plant, "F1", "400")], v)
    run(plant, u, [fuse(plant, "F2", "100")], v)
    source = device(plant, "S", limit="186")
    wire(plant, u, source[0])
    wire(plant, source[1], external(plant, "T0"))
    load = device(plant, "Z", amps="20")
    wire(plant, v, load[0])
    wire(plant, load[1], external(plant, "T1"))
    source_bound = _dc("186", "S")
    assert _read(plant.model()) == {
        frozenset(
            {
                _at("S", source_bound),
                _at("F1", source_bound),
                _at("F2", _dc("100", "F2", "protection")),
                _at("Z", source_bound),
            }
        )
    }


def test_a_rated_tap_gives_the_string_beyond_it_no_bound() -> None:
    """A 20 A converter input on the middle node, all three arms open: the loop through the tap
    and the outside avoids the source, so `K` and `Z` are bounded by nothing; `S` and `F` are."""
    plant = Plant()
    node = hub(plant, "N")
    run(plant, node, [device(plant, "conv", amps="20")], external(plant, "Tc"))
    source = device(plant, "S", limit="186")
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [fuse(plant, "F")], node)
    run(plant, node, [contactor(plant, "K"), device(plant, "Z", amps="20")], external(plant, "T1"))
    assert _read(plant.model()) == {
        _same("S", "F", bound=_dc("186", "S")) | _same("K", "Z", "conv")
    }


def test_a_partial_range_fuse_bounds_nothing_and_a_full_range_one_does() -> None:
    """On a 150 A source: a partial 100 A fuse bounds nothing; a full 100 A fuse bounds 100 A.

    A device that is not a `protection` function bounds nothing by its rating current either.
    """
    partial = Plant()
    open_string(
        partial, device(partial, "S", limit="150"), [fuse(partial, "F", "100", partial=True)]
    )
    full = Plant()
    open_string(full, device(full, "S", limit="150"), [fuse(full, "F", "100")])
    plain = Plant()
    plain_fuse = device(plain, "F", amps="100", link=LinkKind.CONDUCTIVE)
    open_string(plain, device(plain, "S", limit="150"), [plain_fuse])
    assert _read(partial.model()) == {_same("S", "F", bound=_dc("150", "S"))}
    assert _read(full.model()) == {_same("S", "F", bound=_dc("100", "F", "protection"))}
    assert _read(plain.model()) == {_same("S", "F", bound=_dc("150", "S"))}


def test_a_partial_range_function_bounds_nothing_by_any_of_its_ratings() -> None:
    """Partial-range is a fact of the function: a boundary rating without a minimum breaking
    current does not make a partial-range fuse full-range."""
    plant = Plant()
    open_string(plant, device(plant, "S", limit="150"), [fuse(plant, "F", "400", partial=True)])
    boundary = plant.boundary(plant.unit("string"), Plant.function_id("F", "f"))
    values = Rating(current_dc_a=Decimal(100))
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, ("fb",)), key=("fb",), subject=boundary, rating=values
        )
    )
    assert _read(plant.model()) == {_same("S", "F", bound=_dc("150", "S"))}


def test_a_unit_boundarys_source_limit_bounds_the_chain_through_it() -> None:
    """A boundary function with `max_current_dc_a` in its unit's values is a source limit."""
    plant = Plant()
    edge = device(plant, "B")
    unit = plant.unit("string")
    boundary = plant.boundary(unit, Plant.function_id("B", "f"))
    values = Operating(max_current_dc_a=Decimal(186))
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, ("b",)), key=("b",), subject=boundary, operating=values
        )
    )
    open_string(plant, edge, [contactor(plant, "K"), device(plant, "Z", amps="20")])
    assert _read(plant.model()) == {_same("B", "K", "Z", bound=_dc("186", "B"))}


def test_a_source_states_both_kinds_and_a_device_sees_the_tighter_limit_per_kind() -> None:
    """Bounds hold one limit per kind, AC before DC, each the tighter of the two that reach it."""
    plant = Plant()
    source = device(plant, "S", limit="186", limit_ac="100")
    open_string(plant, source, [fuse(plant, "F", "150", amps_ac="200"), contactor(plant, "K")])
    both = (("ac", "100", "S", "source"), ("dc", "150", "F", "protection"))
    assert _read(plant.model()) == {frozenset(_at(name, *both) for name in ("S", "F", "K"))}


def test_equal_limits_tie_by_role_then_by_function_id() -> None:
    """Three limits of 100 A: the protection ones beat the source, the lower function id wins."""
    assert Plant.function_id("S1", "f") < Plant.function_id("F1", "f")  # the role must decide
    plant = Plant()
    line = [fuse(plant, "F1", "100"), fuse(plant, "F2", "100"), contactor(plant, "K")]
    open_string(plant, device(plant, "S1", limit="100"), line)
    low = min("F1", "F2", key=lambda name: Plant.function_id(name, "f"))
    assert _read(plant.model()) == {
        _same("S1", "F1", "F2", "K", bound=_dc("100", low, "protection"))
    }


def test_a_switched_link_counts_closed_and_unrated_devices_do_not_cut() -> None:
    """Acceptance 3c: an unrated terminal and an unrated plug and socket are wire; the rated
    plug beyond them is still on the chain and bounded."""
    plant = Plant()
    source = device(plant, "S", limit="186")
    terminal = device(plant, "T", link=LinkKind.CONDUCTIVE, kind=FunctionKind.TERMINAL)
    plain, plain_socket = mated(plant, "plain", "plainsock")
    rated, rated_socket = mated(plant, "rated", "ratedsock", amps="100")
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [contactor(plant, "K"), terminal], plain)
    wire(plant, plain_socket, rated)
    load = device(plant, "Z", amps="20")
    wire(plant, rated_socket, load[0])
    wire(plant, load[1], external(plant, "T1"))
    assert _read(plant.model()) == {_same("S", "K", "rated+ratedsock", "Z", bound=_dc("186", "S"))}


def test_a_dead_end_has_no_loop_and_so_no_bound_and_an_open_end_has() -> None:
    """A string ending at a real dead end is silent (no loop through it), one position a chain;
    the same string ending at an external item is one chain, bounded by its source."""
    dead = Plant()
    run(dead, device(dead, "S", limit="186")[1], [fuse(dead, "F"), contactor(dead, "K")], None)
    opened = Plant()
    open_string(
        opened, device(opened, "S", limit="186"), [fuse(opened, "F"), contactor(opened, "K")]
    )
    assert _read(dead.model()) == {_same("S"), _same("F"), _same("K")}
    assert _read(opened.model()) == {_same("S", "F", "K", bound=_dc("186", "S"))}


def test_a_lone_fuse_is_bounded_by_its_own_rating_only_when_open() -> None:
    """A fuse with both pins free has no loop; on two external items it is its own bound."""
    dead = Plant()
    fuse(dead, "F", "400")
    opened = Plant()
    open_string(opened, fuse(opened, "F", "400"), [])
    assert _read(dead.model()) == {_same("F")}
    assert _read(opened.model()) == {_same("F", bound=_dc("400", "F", "protection"))}


def _crossed(plant: Plant) -> Id[Port]:
    """A part `X` (rated 50 A) whose function `a` has a pin linked to a pin of function `b`.

    Returns the pin of `a`; the pin of `b` is wired to nothing.
    """
    part = rate(plant, "X", "50")
    templates = [
        FunctionTemplate(
            id=make_id(FunctionTemplate, ("X", name)),
            key=("X", name),
            part=part,
            name=name,
            kind=FunctionKind.GENERIC,
        )
        for name in ("a", "b")
    ]
    pins = [
        PortTemplate(
            id=make_id(PortTemplate, ("X", template.name, "1")),
            key=("X", template.name, "1"),
            function=template.id,
            name="1",
            role=PortRole.GENERIC,
        )
        for template in templates
    ]
    plant.add(*templates, *pins)
    plant.link(pins[0], pins[1], LinkKind.CONDUCTIVE, key="x-link")
    item = plant.item("X", part=part)
    ports = [
        plant.port(plant.function(item, t.name, template=t.id), "1", template=p.id)
        for t, p in zip(templates, pins, strict=True)
    ]
    return ports[0]


def test_a_link_across_two_functions_is_a_wire_and_opens_nothing() -> None:
    """`T0 - S - F - N - G - Z - T1`, the pin of `X.a` on `N`: the cross-function link adds no
    position and opens no node, so the string is one loop through the outside and its devices
    are all bounded by `S`, 186 A (the smallest of 186, 400, 400 on the one loop).

    Before, the link opened `N`: a loop `N` - outside avoided `S` and `F`, so `G` and `Z` got
    400 A by `G` and `S` and `F` kept 186 A (two chains): a false bound, larger than the law's.
    """
    plant = Plant()
    node = hub(plant, "N")
    wire(plant, node, _crossed(plant))
    source = device(plant, "S", limit="186")
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [fuse(plant, "F")], node)
    run(plant, node, [fuse(plant, "G"), device(plant, "Z", amps="20")], external(plant, "T1"))
    assert _read(plant.model()) == {_same("S", "F", "G", "Z", bound=_dc("186", "S"))}


def test_a_cross_function_link_on_a_string_does_not_lift_the_bound_of_a_device() -> None:
    """Reproduction (b): `T0 - S(186) - F(100 full-range) - N - D(300) - F2(400) - T1`, the pin
    of `X.a` on `N`. One loop, so `D` and every device has the bound 100 A set by `F`. With the
    link opening `N`, `D` got 400 A by `F2`, and 300 A was reported below it."""
    plant = Plant()
    node = hub(plant, "N")
    wire(plant, node, _crossed(plant))
    source = device(plant, "S", limit="186")
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [fuse(plant, "F", "100")], node)
    run(plant, node, [device(plant, "D", amps="300"), fuse(plant, "F2")], external(plant, "T1"))
    assert _read(plant.model()) == {_same("S", "F", "D", "F2", bound=_dc("100", "F", "protection"))}


def test_a_link_from_a_ports_template_to_another_function_leaves_it_a_source() -> None:
    """Reproduction (a): a source `S` (supply, 186 A) whose part also has a function `m` with
    a pin linked to `S`'s first port. `S` stays a two-port function (no link joins its own two
    ports), so `T0 - S - K(200) - F2(400) - T1` is one loop bounded 186 A by `S`. When any link
    naming `S`'s port dropped `S`, `K` got 400 A by `F2` and 200 A was reported below it."""
    plant = Plant()
    source = device(plant, "S", limit="186", kind=FunctionKind.SUPPLY)
    sense_pin(plant, "S")
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [contactor(plant, "K", "200"), fuse(plant, "F2")], external(plant, "T1"))
    assert _read(plant.model()) == {_same("S", "K", "F2", bound=_dc("186", "S"))}


def _loop_plant(*, with_loop: bool) -> Plant:
    """`S - F - N - K - Z`; with `with_loop` a rated `G` has both its ports on the node `N`."""
    plant = Plant()
    node = hub(plant, "N")
    source = device(plant, "S", limit="186")
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [fuse(plant, "F")], node)
    run(plant, node, [contactor(plant, "K"), device(plant, "Z", amps="20")], external(plant, "T1"))
    if with_loop:
        first, second = device(plant, "G", amps="30")
        wire(plant, first, node)
        wire(plant, second, node)
    return plant


def test_a_rated_function_with_both_ports_on_one_node_is_no_position() -> None:
    """`G` is dropped, a self-loop has no position and no bound; the string keeps its chain."""
    expected = {_same("S", "F", "K", "Z", bound=_dc("186", "S"))}
    assert _read(_loop_plant(with_loop=True).model()) == expected
    assert _read(_loop_plant(with_loop=False).model()) == expected


def test_the_result_does_not_depend_on_the_ids_of_the_functions() -> None:
    """The same plant under another key prefix has other ids in another order, and the same chains.

    The fuse `F` and the source `S` state 186 A each, so the tie between them (the fuse wins, as
    a protection beats a source) must not follow the ids.
    """
    plain = bypass_plant(fuse_in_branch=True, main_fuse="186").model()
    renamed = bypass_plant(fuse_in_branch=True, main_fuse="186", prefix="p_").model()
    order = [_name(plain, function) for function in sorted(functions(plain))]
    other = [_name(renamed, function, "p_") for function in sorted(functions(renamed))]
    assert order.index("F") < order.index("S")
    assert other.index("S") < other.index("F")
    assert _read(plain) == _read(renamed, "p_")
    (chain,) = _read(plain)
    assert _at("K", _dc("186", "F", "protection")) in chain


def test_a_closed_ring_is_exact_too() -> None:
    """Three positions in a ring, `D1` limited to 50 A: the ring is the one loop through each,
    it holds the source `D1`, and every position is bounded by `D1`."""
    plant = Plant()
    ring = [device(plant, "D1", amps="10", limit="50")]
    ring += [device(plant, f"D{n}", amps="10") for n in "23"]
    for (_, out), (into, _) in zip(ring, ring[1:] + ring[:1], strict=True):
        wire(plant, out, into)
    assert _read(plant.model()) == {_same("D1", "D2", "D3", bound=_dc("50", "D1"))}


# -- the outside (RATINGS-2 C3, acceptance 3f) -------------------------------------------------


def test_a_string_open_at_an_external_items_two_terminals_is_bounded_by_its_source() -> None:
    """Acceptance 3f: every device is bounded 186 A DC by the source, and the outside, which
    closes the loop, is no position."""
    plant = Plant()
    plus, minus = _poles(plant)
    wire(plant, plus, external(plant, "Tp"))
    wire(plant, minus, external(plant, "Tm"))
    chains = current_chains(plant.model())
    assert _read(plant.model()) == {_same(*_POLES, bound=_dc("186", "S"))}
    assert [len(chain.positions) for chain in chains] == [5]
    assert all(position.functions for chain in chains for position in chain.positions)


def _unit_string(*, role: PortRole = PortRole.GENERIC, stray: bool = False) -> Plant:
    """The same string built alone as a unit: its two ends are ports of boundary functions.

    The boundary port on the `+` side has the role `role`. With `stray` one item outside the
    unit makes the unit not standalone.
    """
    plant = Plant()
    plus, minus = _poles(plant)
    unit = plant.unit("u")
    for tag, end in (("Bp", plus), ("Bm", minus)):
        wire(plant, end, hub(plant, tag))
        plant.boundary(unit, Plant.function_id(tag, "f"), key=tag)
    with_role(plant, make_id(Port, ("Bp", "f", "p")), role)
    in_unit(plant, unit)
    if stray:
        plant.item("stray")
    return plant


def test_the_same_string_built_alone_is_open_at_its_boundary_ports() -> None:
    """Acceptance 3f, the unit way: a standalone unit's boundary ports are open ends."""
    assert _read(_unit_string().model()) == {_same(*_POLES, bound=_dc("186", "S"))}


def test_a_boundary_ports_internal_role_is_not_an_open_end() -> None:
    """A terminal's panel-wiring side does not face the outside: with it, the string is a dead
    end on that side, has no loop, and gets no bound (one chain per position)."""
    model = _unit_string(role=PortRole.INTERNAL).model()
    assert _read(model) == {_same(name) for name in _POLES}
    assert make_id(Port, ("Bp", "f", "p")) not in open_ends(model)
    assert make_id(Port, ("Bm", "f", "p")) in open_ends(model)


def test_a_units_boundary_is_not_open_when_its_outside_is_in_the_build() -> None:
    """A unit that is not standalone has its outside in the build: no open end, so no bound."""
    model = _unit_string(stray=True).model()
    assert _read(model) == {_same(name) for name in _POLES}
    assert open_ends(model) == frozenset()


def test_the_open_ends_are_external_ports_and_outward_boundary_ports() -> None:
    """A port of an external item, or of an item under an external parent, and every
    non-INTERNAL boundary port of a standalone unit; nothing else."""
    plant = Plant()
    rack = external(plant, "rack")
    module = plant.item("module", parent=make_id(Item, ("rack",)))
    inside = plant.port(plant.function(module, "f"), "p")
    unit = plant.unit("u")
    plain, facing, wiring = hub(plant, "H"), hub(plant, "Bg"), hub(plant, "Bi")
    for tag in ("Bg", "Bi"):
        plant.boundary(unit, Plant.function_id(tag, "f"), key=tag)
    with_role(plant, wiring, PortRole.INTERNAL)
    in_unit(plant, unit)
    assert open_ends(plant.model()) == {rack, inside, facing}
    assert plain not in open_ends(plant.model())


def test_a_load_across_both_poles_gets_no_bound_and_the_string_keeps_its_own() -> None:
    """The outside can feed the load as well as the string: no limit lies on every loop through
    the load. The string's devices still have their 186 A."""
    plant = Plant()
    plus, minus = _poles(plant)
    wire(plant, plus, external(plant, "Tp"))
    wire(plant, minus, external(plant, "Tm"))
    load = device(plant, "L", amps="20")
    wire(plant, plus, load[0])
    wire(plant, minus, load[1])
    assert _read(plant.model()) == {_same(*_POLES, bound=_dc("186", "S")) | _same("L")}


def _two_open_ends(*, with_t1: bool) -> Plant:
    """The string between `+` and `-`, `-` open at `T3`; `+ - D - T2` (`D` rated 160 A) and,
    with `with_t1`, `+ - T1`, a second way out at `+` (an unrated terminal of an external item)."""
    plant = Plant()
    plus, minus = _poles(plant)
    wire(plant, minus, external(plant, "T3"))
    run(plant, plus, [contactor(plant, "D", "160")], external(plant, "T2"))
    if with_t1:
        wire(plant, plus, external(plant, "T1"))
    return plant


def test_a_device_on_a_second_way_out_of_the_pole_gets_no_bound() -> None:
    """With `T1` the loop `T2 - D - + - T1` holds the outside and never passes the string's
    limit: `D` has no bound. The devices inside the string keep 186 A."""
    assert _read(_two_open_ends(with_t1=True).model()) == {
        _same(*_POLES, bound=_dc("186", "S")) | _same("D")
    }


def test_the_twin_without_the_second_way_out_bounds_the_device_in_series() -> None:
    """No `T1`: `D` is in series with the string on the only loop and is bounded 186 A."""
    assert _read(_two_open_ends(with_t1=False).model()) == {
        _same(*_POLES, "D", bound=_dc("186", "S"))
    }


# -- the law per consistent item state (RATINGS-2 "Switch states", CONTACT-STATES CS1) ------------


def _bounds_of(model: Model, name: str) -> list[tuple[CurrentBound, ...]]:
    """The bounds of every position of the item `name`, one tuple per position, sorted by them."""
    found = [
        position.bounds
        for chain in current_chains(model)
        for position in chain.positions
        if {_name(model, f) for f in position.functions} == {name}
    ]
    return sorted(found, key=lambda bounds: [(b.value, b.by) for b in bounds])


def _state(item: str, state: str) -> tuple[Id[Item], str]:
    return make_id(Item, (item,)), state


def _changeover_plant(*, with_e: bool = True) -> Plant:
    """`M` (100 A) on a changeover's make throw, `E` (120 A) on its break throw, the common
    through a 400 A fuse `F` to a 200 A `D`, all ends at external items. Without `with_e` the
    break throw is wired to nothing."""
    plant = Plant()
    common, make, brk = changeover(plant, "CO")
    for tag, throw, limit in (("M", make, "100"), ("E", brk, "120")):
        if tag == "M" or with_e:
            source = device(plant, tag, limit=limit)
            wire(plant, source[0], external(plant, f"T{tag}"))
            wire(plant, source[1], throw)
    run(plant, common, [fuse(plant, "F"), device(plant, "D", amps="200")], external(plant, "Td"))
    return plant


def test_a_changeovers_two_positions_exist_in_different_states() -> None:
    """Operated, only the make link is closed: `M`, that link, `F` and `D` are on the one loop,
    bounded 100 A by `M`. At rest the break link and `E` give 120 A. A position is bounded by
    the highest of its states, so `F` and `D` get 120 A by `E`; each link position exists in one
    state only and gets that state's bound."""
    hundred, hundred_twenty = _dc("100", "M"), _dc("120", "E")
    assert _read(_changeover_plant().model()) == {
        frozenset(
            {
                _at("M", hundred),
                _at("E", hundred_twenty),
                _at("CO", hundred),
                _at("CO", hundred_twenty),
                _at("F", hundred_twenty),
                _at("D", hundred_twenty),
            }
        )
    }


def test_the_bound_names_the_item_states_that_give_it() -> None:
    """`D`'s 120 A comes from the state in which `CO` is at rest, `M`'s 100 A from operated."""
    model = _changeover_plant().model()
    ((bound,),) = _bounds_of(model, "D")
    assert (bound.value, bound.states) == (120, (_state("CO", "rest"),))
    ((own,),) = _bounds_of(model, "M")
    assert (own.value, own.states) == (100, (_state("CO", "operated"),))


def test_a_position_with_a_bound_in_one_state_only_gets_that_bound() -> None:
    """The break throw is wired to nothing: at rest no loop passes `D`, operated it is bounded
    100 A by `M`. `D` gets 100 A, and the break link's position, which exists at rest only, none."""
    model = _changeover_plant(with_e=False).model()
    ((bound,),) = _bounds_of(model, "D")
    assert (bound.value, bound.by, bound.states) == (
        100,
        Plant.function_id("M", "f"),
        (_state("CO", "operated"),),
    )
    break_link, make_link = _bounds_of(model, "CO")
    assert break_link == ()
    assert make_link == (bound,)


def _make_and_break_plant() -> Plant:
    """`M` (100 A) through the make contact and `E` (120 A) through the break contact of ONE item
    `K`, both to a node `N`, then a 400 A fuse `F` and a 200 A `D` to an external item."""
    plant = Plant()
    make, brk = make_and_break(plant, "K")
    node = hub(plant, "N")
    for tag, contact, limit in (("M", make, "100"), ("E", brk, "120")):
        source = device(plant, tag, limit=limit)
        wire(plant, source[0], external(plant, f"T{tag}"))
        run(plant, source[1], [contact], node)
    run(plant, node, [fuse(plant, "F"), device(plant, "D", amps="200")], external(plant, "Td"))
    return plant


def test_a_make_and_a_break_contact_of_one_item_move_together() -> None:
    """CS1: the two contacts are functions of one item, so never both closed. `D` is bounded
    100 A operated and 120 A at rest, so 120 A; were they independent it would be 400 A."""
    hundred, hundred_twenty = _dc("100", "M"), _dc("120", "E")
    assert _read(_make_and_break_plant().model()) == {
        frozenset(
            {
                _at("M", hundred),
                _at("E", hundred_twenty),
                _at("K", hundred),
                _at("K", hundred_twenty),
                _at("F", hundred_twenty),
                _at("D", hundred_twenty),
            }
        )
    }


def test_a_held_contact_and_a_link_of_both_states_stay_closed_and_name_no_item() -> None:
    """A make contact alone is held: closed, no enumeration, no state named. A switched link of a
    generic function closes in `both` states, so it stays closed too."""
    held = _read(_held_plant().model())
    assert held == {_same("S", "K", "X", "Z", bound=_dc("186", "S"))}
    (bounds,) = _bounds_of(_held_plant().model(), "K")
    assert bounds[0].states == ()


def _held_plant() -> Plant:
    plant = Plant()
    line = [contactor(plant, "K"), device(plant, "X", amps="100", link=LinkKind.SWITCHED)]
    open_string(plant, device(plant, "S", limit="186"), [*line, device(plant, "Z", amps="20")])
    return plant


def _solve_counter(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Count the calls of `current_states.solve`: one per item assignment of each component."""
    calls: list[int] = []
    original = current_states.solve

    def counting(*args: Any) -> Any:
        calls.append(1)
        return original(*args)

    monkeypatch.setattr(current_states, "solve", counting)
    return calls


def test_independent_components_do_not_multiply_the_states(monkeypatch: pytest.MonkeyPatch) -> None:
    """Twelve changeover items in two components of six give 2 * 2**6 assignments, not 2**12.
    Each load is bounded 186 A, and only when every changeover of its string is operated."""
    plant = Plant()
    switch_string(plant, "a", 6)
    switch_string(plant, "b", 6)
    calls = _solve_counter(monkeypatch)
    model = plant.model()
    ((bound,),) = _bounds_of(model, "aD")
    assert len(calls) == 2 * 2**6
    assert bound.value == 186
    assert bound.states == tuple(
        sorted((_state(f"aC{at:02d}", "operated") for at in range(6)), key=lambda s: s[0])
    )


def test_items_above_the_cap_are_held_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two changeovers above the cap in series in ONE component: the `MAX_ENUMERATED_ITEMS` with
    the smallest item ids are enumerated, the other two are held at rest, where their make
    links are open. So the string of make throws can never close: the source `S` and the load
    `D` both lose their bound (with the old rule, all links open, the same). The twin with
    exactly the cap (all enumerated, all operated closes the loop) bounds both at 186 A."""
    cap = current_states.MAX_ENUMERATED_ITEMS
    plant_over, plant_within = Plant(), Plant()
    switch_string(plant_over, "x", cap + 2)
    switch_string(plant_within, "y", cap)
    over, within = plant_over.model(), plant_within.model()
    calls = _solve_counter(monkeypatch)
    assert [_bounds_of(over, name) for name in ("xS", "xD")] == [[()], [()]]
    assert len(calls) == 2**cap
    calls.clear()
    assert [[b[0].value for b in _bounds_of(within, name)] for name in ("yS", "yD")] == [
        [186],
        [186],
    ]
    assert len(calls) == 2**cap


def test_the_cap_is_read_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test may lower `current_states.MAX_ENUMERATED_ITEMS`: with 1, two changeovers in one
    component cost 2**1 assignments (one enumerated, one held at rest)."""
    monkeypatch.setattr(current_states, "MAX_ENUMERATED_ITEMS", 1)
    plant = Plant()
    switch_string(plant, "x", 2)
    calls = _solve_counter(monkeypatch)
    _bounds_of(plant.model(), "xD")
    assert len(calls) == 2


def test_an_item_above_the_cap_at_rest_still_closes_a_string_of_break_throws() -> None:
    """The items above the cap are held at rest, so a string of break throws (closed at rest)
    stays closed through them: `D` is bounded 186 A, and only the enumerated items, all at
    rest (an operated one opens the string), are named. Opening their links would lose it."""
    cap = current_states.MAX_ENUMERATED_ITEMS
    plant = Plant()
    switch_string(plant, "x", cap + 2, through="break")
    ((bound,),) = _bounds_of(plant.model(), "xD")
    enumerated = sorted(make_id(Item, (f"xC{at:02d}",)) for at in range(cap + 2))[:cap]
    assert bound.value == 186
    assert bound.states == tuple((item, "rest") for item in enumerated)


@pytest.mark.parametrize("above_the_cap", [False, True])
def test_opening_a_capped_items_links_would_raise_a_bound(*, above_the_cap: bool) -> None:
    """Acceptance 3j: `CO`, an unrated changeover, enumerated (`above_the_cap` false) or above
    the cap: every state has `L` (100 A) on each loop through `D`, so `D` is bounded 100 A by
    `L`, in both. Opening all of `CO`'s links splits its node and makes the loop `D, P, R, S, Q`
    that exists in no state, and avoids `L`: `D` would get 400 A by `S`."""
    cap = current_states.MAX_ENUMERATED_ITEMS
    plant = Plant()
    capped_changeover(plant, cap if above_the_cap else cap - 1, device(plant, "S", limit="400"))
    ((bound,),) = _bounds_of(plant.model(), "D")
    assert (bound.value, bound.by, bound.states) == (100, Plant.function_id("L", "f"), ())


def test_stateful_items_needs_both_an_item_and_a_non_both_state() -> None:
    """`_stateful_items`'s clause is `item is not None and state != "both"`: an `or` would count
    two item-less parts (`item=None`) of the two different throw states as one enumerated item
    under the key `None`, since either clause alone would let them in."""
    p1, p2 = Id(kind="port", value="p1"), Id(kind="port", value="p2")
    p3, p4 = Id(kind="port", value="p3"), Id(kind="port", value="p4")
    parts = [Wire(p1, p2, state="rest"), Wire(p3, p4, state="operated")]
    assert current_states._stateful_items(parts) == ([], set())


def test_stateful_items_a_both_state_part_of_an_item_names_it_no_state() -> None:
    """The literal `"both"` must be matched exactly: a mutated string would let a `both`-state
    part of an item add a spurious second "state", making a held item (one real throw only)
    look enumerated."""
    item = make_id(Item, ("k",))
    p1, p2 = Id(kind="port", value="p1"), Id(kind="port", value="p2")
    p3, p4 = Id(kind="port", value="p3"), Id(kind="port", value="p4")
    parts = [Wire(p1, p2, item, "both"), Wire(p3, p4, item, "rest")]
    assert current_states._stateful_items(parts) == ([], set())


def test_closed_is_always_true_for_a_both_state_part_regardless_of_the_chosen_state() -> None:
    """The first clause `state == "both" or item is None` must short-circuit: an `and`, or a
    mutated `"both"` literal, would fall through to the assignment lookup and disagree with a
    chosen state that differs from the part's own."""
    item = make_id(Item, ("k",))
    part = Wire(Id(kind="port", value="p1"), Id(kind="port", value="p2"), item, "both")
    assert current_states._closed(part, {item: "rest"}, set()) is True


def test_a_position_shorted_only_when_every_link_is_closed_keeps_its_state_bound() -> None:
    """`T0 - S - CO.common`, `D` from the common to the make port, `T1` on the make port: at rest
    `D` is on the loop with `S` (bound 186 A), operated the make link shorts it, and with every
    link closed it is shorted too. `D` has its bound, at rest, in a chain of its own."""
    plant = Plant()
    shorted_when_closed(plant, device(plant, "S", limit="186"))
    model = plant.model()
    assert _read(model) == {
        frozenset({_at("S", _dc("186", "S"))}),
        frozenset({_at("D", _dc("186", "S"))}),
    }
    ((bound,),) = _bounds_of(model, "D")
    assert bound.states == (_state("CO", "rest"),)


def test_the_bound_names_only_the_items_that_matter() -> None:
    """`D`'s 120 A holds at rest whatever an unrelated second changeover `U` in the same
    component does, so only `CO` is named; the assignments differing in `U` all give it."""
    plant = _changeover_plant()
    wire(plant, changeover(plant, "U", None)[0], make_id(Port, ("Td", "f", "p")))
    ((bound,),) = _bounds_of(plant.model(), "D")
    assert (bound.value, bound.states) == (120, (_state("CO", "rest"),))


def test_the_highest_bound_is_chosen_by_value_then_role_then_setter_then_states() -> None:
    """The one choice `current_states` and the check both make (`current_bounds.highest`)."""
    low, high = sorted((make_id(Function, ("a", "f")), make_id(Function, ("b", "f"))))
    item = make_id(Item, ("k",))

    def bound(value: int, by: Id[Function], role: LimitRole, *states: LinkState) -> CurrentBound:
        return CurrentBound(
            Current.DC, Decimal(value), by, role, tuple((item, state) for state in states)
        )

    ordered = [
        bound(120, low, LimitRole.PROTECTION, "operated"),
        bound(120, low, LimitRole.PROTECTION, "rest"),
        bound(120, high, LimitRole.PROTECTION),
        bound(120, low, LimitRole.SOURCE),
        bound(100, low, LimitRole.PROTECTION),
    ]
    # Best first: the higher value, then the role name (protection before source), then the
    # setter id, then the states; whatever order the bounds come in.
    for shuffled in itertools.permutations(ordered):
        assert highest(shuffled) == ordered[0]
        assert highest(b for b in shuffled if b is not ordered[0]) == ordered[1]


def test_pairs_mates_every_equal_named_pair_and_skips_the_rest() -> None:
    """`pairs` ties a mate's ports by name: a mate whose functions each carry two same-named
    ports (`1`, `2`) joins both pairs, not just the first found; a name one side lacks (`3`,
    only on the plug) joins nothing."""
    plant = Plant()
    plug = plant.function(plant.item("PL"), "f", kind=FunctionKind.CONNECTOR)
    sock = plant.function(plant.item("SK"), "f", kind=FunctionKind.CONNECTOR)
    p1, p2, p3 = (plant.port(plug, name) for name in ("1", "2", "3"))
    s1, s2 = (plant.port(sock, name) for name in ("1", "2"))
    plant.mate(plug, sock, key="mate-pl-sk")
    _, matched = pairs(plant.model())
    assert {frozenset((joint.first, joint.second)) for joint in matched} == {
        frozenset((p1, s1)),
        frozenset((p2, s2)),
    }
    assert p3 not in {port for joint in matched for port in (joint.first, joint.second)}


def test_pairs_skips_a_mate_whose_far_side_has_no_ports() -> None:
    """A mate to a function with no ports at all: the `.get(mate.b, ())` default must stay an
    empty tuple (never `None`), so `pairs` finds no match on that side and raises nothing."""
    plant = Plant()
    near = plant.function(plant.item("NR"), "f", kind=FunctionKind.CONNECTOR)
    far = plant.function(plant.item("FR"), "f", kind=FunctionKind.CONNECTOR)
    plant.port(near, "1")
    plant.mate(near, far, key="mate-nr-fr")
    _, matched = pairs(plant.model())
    assert matched == []


def test_pairs_skips_a_mate_whose_near_side_has_no_ports() -> None:
    """A mate from a function with no ports at all: the `.get(mate.a, ())` default must stay an
    empty tuple (never `None`), so `pairs` finds no match and raises nothing."""
    plant = Plant()
    near = plant.function(plant.item("NR2"), "f", kind=FunctionKind.CONNECTOR)
    far = plant.function(plant.item("FR2"), "f", kind=FunctionKind.CONNECTOR)
    plant.port(far, "1")
    plant.mate(near, far, key="mate-nr2-fr2")
    _, matched = pairs(plant.model())
    assert matched == []


def _two_positions(plant: Plant) -> tuple[Edge, Edge]:
    """Two unrelated, unlinked, rated two-port devices: `raw_of` reads each as one position."""
    device(plant, "P", amps="10")
    device(plant, "Q", amps="10")
    first, second = raw_of(plant.model()).edges
    return first, second


def test_build_drops_a_position_whose_ends_share_one_node() -> None:
    """`_build`'s self-loop filter (`p[0] != p[1]`) drops a position both of whose ends land on
    the same node after the always-closed links join, and keeps a genuine one untouched."""
    plant = Plant()
    looped, open_edge = _two_positions(plant)
    same = Id(kind="probe", value="node")
    first, second = Id(kind="probe", value="a"), Id(kind="probe", value="b")
    nodes = {
        looped.first: same,
        looped.second: same,
        open_edge.first: first,
        open_edge.second: second,
    }
    kept, ends, ties = _build((looped, open_edge), (), (), nodes.__getitem__)
    assert [edge.at for edge in kept] == [open_edge.at]
    assert ends == [(first, second)]
    assert ties == [open_edge.tie]


def test_build_sorts_kept_positions_by_their_first_node() -> None:
    """`_build` sorts the kept positions by `(first node, second node, Edge.at)`: `edge_p`'s
    FIRST node (`a`) sorts before `edge_q`'s (`b`), so `edge_p` comes first, even though
    `edge_p`'s SECOND node (`d`) sorts after `edge_q`'s (`c`) -- a tuple-index swap on the sort
    key would flip the order."""
    plant = Plant()
    edge_p, edge_q = _two_positions(plant)
    a, b, c, d = (Id(kind="probe", value=value) for value in "abcd")
    nodes = {edge_p.first: a, edge_p.second: d, edge_q.first: b, edge_q.second: c}
    kept, ends, _ = _build((edge_p, edge_q), (), (), nodes.__getitem__)
    assert [edge.at for edge in kept] == [edge_p.at, edge_q.at]
    assert ends == [(a, d), (b, c)]


def _named_end(plant: Plant, key: str, tag: str, potential: str | None = None) -> Id[Port]:
    """An external item `key` printed as `tag`, its one port on `potential` when given."""
    plant.add(
        Item(
            id=make_id(Item, (key,)),
            key=(key,),
            part=None,
            parent=None,
            position=None,
            tag=tag,
            description="Invented",
            external=True,
        )
    )
    port = plant.port(plant.function(make_id(Item, (key,)), "f"), "p")
    if potential is not None:
        plant.net(f"net-{key}", (port,), potential=potential)
    return port


def _line(plant: Plant, left: Id[Port], right: Id[Port]) -> None:
    """`left - D1 - D2 - D3 - right`, three rated two-port devices in a line."""
    run(plant, left, [device(plant, name, amps="10") for name in ("D1", "D2", "D3")], right)


def _order(model: Model) -> list[str]:
    (chain,) = current_chains(model)
    return [_name(model, position.functions[0]) for position in chain.positions]


def _dc_supply(plant: Plant) -> None:
    rails = {"+24V": rail("24"), "0V": rail("0")}
    supply(plant, "S", rails, current=Current.DC)


@pytest.mark.parametrize("plus_on_left", [True, False])
def test_a_chain_runs_from_its_supply_end_whichever_way_its_function_ids_order(
    *, plus_on_left: bool
) -> None:
    """The ranked end starts the chain: the rail at 24 V first, in both orientations.

    The same devices are built both ways round, so one orientation runs against the order of
    their function ids; the chain still starts at the `+24V` end and walks to the `0V` end.
    """
    plant = Plant()
    _dc_supply(plant)
    plus = _named_end(plant, "TP", "-X1", "+24V")
    zero = _named_end(plant, "TZ", "-X2", "0V")
    _line(plant, *((plus, zero) if plus_on_left else (zero, plus)))
    expected = ["D1", "D2", "D3"] if plus_on_left else ["D3", "D2", "D1"]
    assert _order(plant.model()) == expected


def _tag(plant: Plant, key: str, tag: str) -> None:
    """Give the item `key` the designation `tag`."""
    at = next(i for i, record in enumerate(plant.records) if record.id == make_id(Item, (key,)))
    plant.records[at] = dataclasses.replace(plant.records[at], tag=tag)


@pytest.mark.parametrize("low_on_left", [True, False])
def test_a_chain_with_no_ranked_end_starts_at_the_lower_designation_text(
    *, low_on_left: bool
) -> None:
    """No end carries a ranked potential: the end device printed `-A1` comes before `-A2`."""
    plant = Plant()
    _line(plant, _named_end(plant, "TA", "-X1"), _named_end(plant, "TB", "-X2"))
    low, high = ("D1", "D3") if low_on_left else ("D3", "D1")
    _tag(plant, low, "-A1")
    _tag(plant, high, "-A2")
    assert _order(plant.model()) == [low, "D2", high]


def test_a_ranked_end_wins_over_a_lower_designation_text() -> None:
    """The end device printed `-A9` on `+24V` starts the chain before the unranked `-A1`."""
    plant = Plant()
    _dc_supply(plant)
    unranked = _named_end(plant, "TA", "-X1")
    ranked = _named_end(plant, "TB", "-X9", "+24V")
    _line(plant, unranked, ranked)
    _tag(plant, "D1", "-A1")
    _tag(plant, "D3", "-A9")
    assert _order(plant.model()) == ["D3", "D2", "D1"]


def test_a_ring_with_no_end_runs_round_it() -> None:
    """Four positions in a ring have no end: the walk goes round, never across (D1, D3)."""
    plant = Plant()
    devices = [device(plant, f"D{n}", amps="10") for n in (1, 2, 3, 4)]
    for here, there in itertools.pairwise([*devices, devices[0]]):
        wire(plant, here[1], there[0])
    order = _order(plant.model())
    assert sorted(order) == ["D1", "D2", "D3", "D4"]
    next_of = {"D1": "D2", "D2": "D3", "D3": "D4", "D4": "D1"}
    assert all(next_of[a] == b or next_of[b] == a for a, b in itertools.pairwise(order))


def test_at_a_fork_the_branch_with_the_lower_designation_text_goes_first() -> None:
    """A star: the branch printed `-K1` is walked before `-K2`, though D2 has the lower id."""
    plant = Plant()
    _dc_supply(plant)
    junction = hub(plant, "J")
    d1, d2, d3 = (device(plant, f"D{n}", amps="10") for n in (1, 2, 3))
    run(plant, _named_end(plant, "TP", "-X1", "+24V"), [d1], junction)
    run(plant, junction, [d2], _named_end(plant, "TB", "-X2"))
    run(plant, junction, [d3], _named_end(plant, "TC", "-X3"))
    _tag(plant, "D2", "-K2")
    _tag(plant, "D3", "-K1")
    assert _order(plant.model()) == ["D1", "D3", "D2"]
