"""WP12 tests: what net closure joins and what it leaves apart (design/connectivity.md)."""

import dataclasses
from decimal import Decimal
from typing import Any, cast

import pytest
from plant import Plant

from fransys_model.derive import (
    PhysicalNet,
    SupplySystem,
    closure,
    net_of,
    physical_nets,
    port_rails,
    rail_pairs,
)
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, make_id
from fransys_model.vocab import closure as vocab_closure
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import Current, FunctionKind, LinkKind, PortRole
from fransys_model.vocab.supply_system import Rail
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate


def _rail(value: str) -> Rail:
    """A DC rail at `value` volts: DC needs no phase, so this never trips the phase rule."""
    return Rail(max_v=Decimal(value), phase=None)


def _groups(plant: Plant) -> set[frozenset[Id[Port]]]:
    return {frozenset(net.ports) for net in physical_nets(plant.model())}


def _fuse(kind: LinkKind, *names: str) -> tuple[Plant, dict[str, tuple[Id[Port], Id[Port]]]]:
    """A part whose two pins are linked as `kind`, and one instance of it per name."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, kind)
    ports = {}
    for name in names:
        function = plant.function(plant.item(name, part=part.id), "fn", template=template.id)
        ports[name] = (
            plant.port(function, "1", template=first.id),
            plant.port(function, "2", template=second.id),
        )
    return plant, ports


def test_a_model_without_ports_has_no_physical_nets() -> None:
    """Nothing to join."""
    assert physical_nets(Plant().model()) == ()


def test_a_port_alone_is_its_own_physical_net() -> None:
    """No connectivity is still a net, of one."""
    plant = Plant()
    lone = plant.pin("a", "f", "1")
    assert physical_nets(plant.model()) == (PhysicalNet(ports=(lone,)),)


def test_conductors_join_transitively() -> None:
    """Three ports on two wires are one net; a fourth, alone, is another."""
    plant = Plant()
    a, b, c, d = (plant.pin(item, "f", "1") for item in "abcd")
    plant.wire(a, b, key="w1")
    plant.wire(b, c, key="w2")
    assert _groups(plant) == {frozenset({a, b, c}), frozenset({d})}


def test_a_switched_link_never_joins() -> None:
    """The relay contact stays two nets."""
    plant, ports = _fuse(LinkKind.SWITCHED, "k1")
    one, two = ports["k1"]
    assert _groups(plant) == {frozenset({one}), frozenset({two})}


def test_a_conductive_link_joins_with_no_conductor_at_all() -> None:
    """The fuse is one net."""
    plant, ports = _fuse(LinkKind.CONDUCTIVE, "f1")
    assert _groups(plant) == {frozenset(ports["f1"])}


def test_a_link_joins_within_one_item_never_across_two() -> None:
    """Two fuses of one part: pin 1 of the first is not pin 2 of the second."""
    plant, ports = _fuse(LinkKind.CONDUCTIVE, "f1", "f2")
    assert _groups(plant) == {frozenset(ports["f1"]), frozenset(ports["f2"])}


def test_a_link_between_two_functions_of_one_part_joins_their_ports() -> None:
    """A part-level jumper between two functions: the item is the scope, not the function."""
    plant = Plant()
    part, template, first, _ = plant.relay_part()
    second_function = FunctionTemplate(
        id=make_id(FunctionTemplate, ("relay", "fn2")),
        key=("relay", "fn2"),
        part=part.id,
        name="fn2",
        kind=FunctionKind.GENERIC,
    )
    far_pin = PortTemplate(
        id=make_id(PortTemplate, ("relay", "fn2", "3")),
        key=("relay", "fn2", "3"),
        function=second_function.id,
        name="3",
        role=PortRole.GENERIC,
    )
    plant.add(second_function, far_pin)
    plant.link(first, far_pin, LinkKind.CONDUCTIVE)
    item = plant.item("k1", part=part.id)
    one = plant.port(plant.function(item, "fn", template=template.id), "1", template=first.id)
    three = plant.port(
        plant.function(item, "fn2", template=second_function.id), "3", template=far_pin.id
    )
    other_item = plant.item("k2", part=part.id)
    apart = plant.port(
        plant.function(other_item, "fn2", template=second_function.id), "3", template=far_pin.id
    )
    assert _groups(plant) == {frozenset({one, three}), frozenset({apart})}


def test_a_port_without_a_template_never_joins_through_a_link() -> None:
    """The link is a fact of the part; a hand-added port has no part."""
    plant, ports = _fuse(LinkKind.CONDUCTIVE, "f1")
    function = plant.function_id("f1", "fn")
    stray = plant.port(function, "3")
    assert _groups(plant) == {frozenset(ports["f1"]), frozenset({stray})}


def test_two_ports_of_one_template_join_the_other_end_whole() -> None:
    """A part-conformance defect (a repeated port) is not closure's to refuse: the group joins."""
    plant, ports = _fuse(LinkKind.CONDUCTIVE, "f1")
    part_pin = make_id(PortTemplate, ("relay", "fn", "1"))
    again = plant.port(plant.function_id("f1", "fn"), "1", template=part_pin, again="b")
    assert _groups(plant) == {frozenset({*ports["f1"], again})}


def test_a_mate_joins_ports_of_equal_name_only() -> None:
    """Pins 1 of both connectors meet; pin 2 of one and pin 3 of the other stay apart."""
    plant = Plant()
    a1, a2 = plant.pin("board", "j1", "1"), plant.pin("board", "j1", "2")
    b1, b3 = plant.pin("harness", "p1", "1"), plant.pin("harness", "p1", "3")
    plant.mate(plant.function_id("board", "j1"), plant.function_id("harness", "p1"))
    assert _groups(plant) == {frozenset({a1, b1}), frozenset({a2}), frozenset({b3})}


def test_a_mate_joins_every_port_of_one_name_on_both_functions() -> None:
    """Two ports called `1` on one connector are, through the mate, one net with the other's."""
    plant = Plant()
    first = plant.pin("board", "j1", "1")
    twin = plant.port(plant.function_id("board", "j1"), "1", again="b")
    other = plant.pin("harness", "p1", "1")
    plant.mate(plant.function_id("board", "j1"), plant.function_id("harness", "p1"))
    assert _groups(plant) == {frozenset({first, twin, other})}


def test_mates_chain() -> None:
    """A to B and B to C: the equal-named pins of all three are one net."""
    plant = Plant()
    pins = [plant.pin(name, "c", "1") for name in ("a", "b", "c")]
    plant.mate(plant.function_id("a", "c"), plant.function_id("b", "c"), key="m1")
    plant.mate(plant.function_id("b", "c"), plant.function_id("c", "c"), key="m2")
    assert _groups(plant) == {frozenset(pins)}


def test_conductor_link_and_mate_combine() -> None:
    """A wire, a fuse and a connector in series: one net from end to end."""
    plant, ports = _fuse(LinkKind.CONDUCTIVE, "f1")
    one, two = ports["f1"]
    source = plant.pin("source", "s", "1")
    plug = plant.pin("plug", "p", "1")
    socket = plant.pin("socket", "s", "1")
    plant.wire(source, one, key="w1")
    plant.wire(two, plug, key="w2")
    plant.mate(plant.function_id("plug", "p"), plant.function_id("socket", "s"))
    assert _groups(plant) == {frozenset({source, one, two, plug, socket})}


def test_a_mate_between_two_functions_with_no_ports_at_all_is_a_no_op() -> None:
    """A mate joining two empty connectors mates fine: nothing anywhere to join.

    `Mate.__post_init__` stores `a`/`b` in id order, so which side lands as `a` after
    freezing is not under this test's control; both ends are portless here, so either
    `by_function` lookup meets a function with no key at all.
    """
    plant = Plant()
    lone = plant.pin("board", "j1", "1")
    empty_a = plant.function(plant.item("cap"), "j2")
    empty_b = plant.function(plant.item("cup"), "j4")
    plant.mate(empty_a, empty_b)
    assert _groups(plant) == {frozenset({lone})}


def test_a_link_whose_first_template_has_no_port_anywhere_never_iterates() -> None:
    """A link's first template with no port on any item joins nothing, and never raises."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, LinkKind.CONDUCTIVE)
    item = plant.item("k1", part=part.id)
    function = plant.function(item, "fn", template=template.id)
    lone = plant.port(function, "2", template=second.id)
    assert _groups(plant) == {frozenset({lone})}


def test_condition_needs_nothing_for_a_both_link() -> None:
    """A switched link of a non-contact function is `link_state` `"both"`: no condition."""
    plant, _ports = _fuse(LinkKind.SWITCHED, "g1")
    model = plant.model()
    (group,) = vocab_closure.link_groups(model, frozenset({LinkKind.SWITCHED}))
    assert vocab_closure._condition(model, group) == vocab_closure._ALWAYS


def test_condition_needs_the_items_state_for_a_real_contact() -> None:
    """A normally-open contact needs its item operated; a normally-closed one, at rest."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, LinkKind.SWITCHED)
    no_item = plant.item("no1", part=part.id)
    no_function = plant.function(no_item, "fn", template=template.id, kind=FunctionKind.CONTACT_NO)
    plant.port(no_function, "1", template=first.id)
    plant.port(no_function, "2", template=second.id)
    nc_item = plant.item("nc1", part=part.id)
    nc_function = plant.function(nc_item, "fn", template=template.id, kind=FunctionKind.CONTACT_NC)
    plant.port(nc_function, "1", template=first.id)
    plant.port(nc_function, "2", template=second.id)
    model = plant.model()
    by_function = {
        group.function: group
        for group in vocab_closure.link_groups(model, frozenset({LinkKind.SWITCHED}))
    }
    assert vocab_closure._condition(model, by_function[no_function]) == frozenset(
        {(no_item, "operated")}
    )
    assert vocab_closure._condition(model, by_function[nc_function]) == frozenset(
        {(nc_item, "rest")}
    )


def test_a_changeovers_own_throws_stand_across_its_open_gap() -> None:
    """Rail A on the break, rail B on the make: `rail_pairs` still pairs them (CS4)."""
    plant = Plant()
    part_id = plant.part("co")
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("co", "fn")),
        key=("co", "fn"),
        part=part_id,
        name="fn",
        kind=FunctionKind.CONTACT_CO,
    )
    common_t = PortTemplate(
        id=make_id(PortTemplate, ("co", "fn", "c")),
        key=("co", "fn", "c"),
        function=template.id,
        name="c",
        role=PortRole.COMMON,
    )
    break_t = PortTemplate(
        id=make_id(PortTemplate, ("co", "fn", "b")),
        key=("co", "fn", "b"),
        function=template.id,
        name="b",
        role=PortRole.BREAK,
    )
    make_t = PortTemplate(
        id=make_id(PortTemplate, ("co", "fn", "m")),
        key=("co", "fn", "m"),
        function=template.id,
        name="m",
        role=PortRole.MAKE,
    )
    plant.add(template, common_t, break_t, make_t)
    plant.link(common_t, break_t, LinkKind.SWITCHED, key="rest")
    plant.link(common_t, make_t, LinkKind.SWITCHED, key="operated")
    item = plant.item("k1", part=part_id)
    function = plant.function(item, "fn", template=template.id, kind=FunctionKind.CONTACT_CO)
    plant.port(function, "c", template=common_t.id)
    brk = plant.port(function, "b", template=break_t.id)
    mk = plant.port(function, "m", template=make_t.id)
    plant.add(
        SupplySystem(
            id=make_id(SupplySystem, ("co-supply",)),
            key=("co-supply",),
            name="co-supply",
            current=Current.DC,
            rails=frozendict({"A": _rail("24"), "B": _rail("24")}),
        )
    )
    plant.net("na", (brk,), potential="A")
    plant.net("nb", (mk,), potential="B")
    model = plant.model()
    assert rail_pairs(model, function) == frozenset({("A", "B")})


def test_two_rails_at_one_port_are_never_a_pair_with_themselves() -> None:
    """A port fed by two rails is not, on its own, a pair: `rail_pairs` needs two ports."""
    plant = Plant()
    common = plant.pin("dev", "f", "1")
    source_a = plant.pin("sa", "f", "1")
    source_b = plant.pin("sb", "f", "1")
    plant.wire(source_a, common, key="wa")
    plant.wire(source_b, common, key="wb")
    plant.add(
        SupplySystem(
            id=make_id(SupplySystem, ("dev-supply",)),
            key=("dev-supply",),
            name="dev-supply",
            current=Current.DC,
            rails=frozendict({"A": _rail("24"), "B": _rail("24")}),
        )
    )
    plant.net("na", (source_a,), potential="A")
    plant.net("nb", (source_b,), potential="B")
    model = plant.model()
    function = plant.function_id("dev", "f")
    assert port_rails(model, common) == frozenset({"A", "B"})
    assert rail_pairs(model, function) == frozenset()


# ---- the shape of the result -------------------------------------------------------------


def _busy() -> Plant:
    plant = Plant()
    ports = [plant.pin(name, "f", "1") for name in "hgfedcba"]
    plant.wire(ports[0], ports[3], key="w1")
    plant.wire(ports[5], ports[1], key="w2")
    plant.wire(ports[3], ports[6], key="w3")
    return plant


def test_nets_and_their_ports_are_sorted() -> None:
    """Sorted by id inside a net, and nets by their port tuples."""
    nets = physical_nets(_busy().model())
    for net in nets:
        assert list(net.ports) == sorted(net.ports)
    assert [net.ports for net in nets] == sorted(net.ports for net in nets)


def test_the_result_does_not_depend_on_the_order_of_a_models_tables() -> None:
    """Tables backwards, under another digest so the cache is not used: the same nets."""
    model = _busy().model()
    backwards = dataclasses.replace(
        model,
        digest="reversed-tables-test-closure-model",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert list(backwards.tables) != list(model.tables)
    assert physical_nets(backwards) == physical_nets(model)


def test_net_of_finds_the_net_of_a_port_and_none_for_an_absent_one() -> None:
    """`None` for an id that is not a port of the model: nothing is invented."""
    plant = Plant()
    a, b = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    plant.wire(a, b, key="w")
    model = plant.model()
    assert net_of(model, a) == PhysicalNet(ports=tuple(sorted((a, b))))
    assert net_of(model, make_id(Port, ("nowhere",))) is None
    not_a_port: Any = make_id(Item, ("a",))
    assert net_of(model, not_a_port) is None


def test_a_physical_net_is_immutable_and_hashable() -> None:
    """A `@value`: a set of them works and nothing can be assigned."""
    plant = Plant()
    lone = plant.pin("a", "f", "1")
    (net,) = physical_nets(plant.model())
    assert {net} == {PhysicalNet(ports=(lone,))}
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast("Any", net).ports = ()


# ---- the cache ---------------------------------------------------------------------------


def _distinct(number: int) -> Model:
    plant = Plant()
    plant.pin(f"cache{number}", "f", "1")
    return plant.model()


def test_equal_digests_share_one_result() -> None:
    """The same records from another draft are the same closure, computed once."""
    assert physical_nets(_busy().model()) is physical_nets(_busy().model())


def test_the_cache_is_bounded_and_an_evicted_closure_is_rebuilt_equal() -> None:
    """A long session does not keep every model it ever closed."""
    models = [_distinct(n) for n in range(DIGEST_CACHE_SIZE + 1)]
    first = physical_nets(models[0])
    for model in models[1:]:
        physical_nets(model)
    again = physical_nets(models[0])
    assert again is not first
    assert again == first


def test_derive_re_exports_the_vocab_closure() -> None:
    """One implementation, two import paths (decision 0019)."""
    assert closure.physical_nets is vocab_closure.physical_nets
    assert closure.net_of is vocab_closure.net_of
    assert closure.PhysicalNet is vocab_closure.PhysicalNet


def test_the_most_recently_used_closure_survives_a_full_cache() -> None:
    """Least recently used goes first: a closure asked for again stays."""
    models = [_distinct(100 + n) for n in range(DIGEST_CACHE_SIZE + 1)]
    kept = physical_nets(models[0])
    for model in models[1:DIGEST_CACHE_SIZE]:
        physical_nets(model)
    assert physical_nets(models[0]) is kept
    physical_nets(models[DIGEST_CACHE_SIZE])
    assert physical_nets(models[0]) is kept
