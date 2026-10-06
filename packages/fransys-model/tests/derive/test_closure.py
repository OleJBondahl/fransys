"""WP12 tests: `derive.closure`, the union-find mechanism (ROADMAP WP12, design/connectivity.md).

The validator half (`validators.connectivity`) is tested in tests/vocab.
"""

from derive_helpers import add_all

from fransys_model.derive.closure import PhysicalNet, net_of, physical_nets, port_groups
from fransys_model.kernel import Draft, Id, Origin, UnionFind, freeze, make_id
from fransys_model.vocab.closure import _nets_from
from fransys_model.vocab.connectivity import Conductor, Mate
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    LinkKind,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate


def test_closure_joins_ports_through_a_conductor(origin: Origin) -> None:
    """Two ports on unrelated items, joined by one `Conductor`, are one physical net."""
    draft = Draft()
    item_a = Item(
        id=Id(kind="item", value="a" * 32),
        key=("a",),
        part=None,
        parent=None,
        position=None,
        tag="-B1",
        description="pressure transmitter",
    )
    item_b = Item(
        id=Id(kind="item", value="b" * 32),
        key=("b",),
        part=None,
        parent=None,
        position=None,
        tag="X1",
        description="terminal",
    )
    func_a = Function(
        id=Id(kind="function", value="a" * 32),
        key=("a", "signal"),
        item=item_a.id,
        template=None,
        name="signal",
        kind=FunctionKind.SENSOR,
    )
    func_b = Function(
        id=Id(kind="function", value="b" * 32),
        key=("b", "terminal"),
        item=item_b.id,
        template=None,
        name="terminal",
        kind=FunctionKind.TERMINAL,
    )
    port_a = Port(
        id=Id(kind="port", value="a" * 32),
        key=("a", "signal", "+"),
        function=func_a.id,
        template=None,
        name="+",
        role=PortRole.GENERIC,
    )
    port_b = Port(
        id=Id(kind="port", value="b" * 32),
        key=("b", "terminal", "external"),
        function=func_b.id,
        template=None,
        name="external",
        role=PortRole.EXTERNAL,
    )
    conductor = Conductor(
        id=Id(kind="conductor", value="1" * 32),
        key=("w1", "1"),
        a=port_a.id,
        b=port_b.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    add_all(draft, item_a, item_b, func_a, func_b, port_a, port_b, conductor, origin=origin)
    model = freeze(draft)
    assert net_of(model, port_a.id) == net_of(model, port_b.id)
    assert {port_a.id, port_b.id} <= set(next(iter(physical_nets(model))).ports)


def test_closure_joins_ports_through_a_conductive_internal_link(origin: Origin) -> None:
    """Two ports of one function, linked `CONDUCTIVE` on the part template, are one net.

    No `Conductor` exists between them at all: the join comes only from resolving the
    part's `InternalLink` through each port's `PortTemplate`.
    """
    draft = Draft()
    part = Part(
        id=Id(kind="part", value="1" * 32),
        key=("fuse",),
        mpn="SIM-FUSE-2A",
        manufacturer="Synthetic Parts Co",
        description="2A fuse",
        category=PartCategory.PROTECTION,
        class_code="F",
    )
    func_template = FunctionTemplate(
        id=Id(kind="function_template", value="1" * 32),
        key=("fuse", "element"),
        part=part.id,
        name="element",
        kind=FunctionKind.PROTECTION,
    )
    port_template_1 = PortTemplate(
        id=Id(kind="port_template", value="1" * 32),
        key=("fuse", "element", "1"),
        function=func_template.id,
        name="1",
        role=PortRole.GENERIC,
    )
    port_template_2 = PortTemplate(
        id=Id(kind="port_template", value="2" * 32),
        key=("fuse", "element", "2"),
        function=func_template.id,
        name="2",
        role=PortRole.GENERIC,
    )
    link = InternalLink(
        id=Id(kind="internal_link", value="1" * 32),
        key=("fuse", "element", "1-2"),
        a=port_template_1.id,
        b=port_template_2.id,
        kind=LinkKind.CONDUCTIVE,
    )
    item = Item(
        id=Id(kind="item", value="1" * 32),
        key=("f1",),
        part=part.id,
        parent=None,
        position=None,
        tag="-F1",
        description="main fuse",
    )
    func = Function(
        id=Id(kind="function", value="1" * 32),
        key=("f1", "element"),
        item=item.id,
        template=func_template.id,
        name="element",
        kind=FunctionKind.PROTECTION,
    )
    port_1 = Port(
        id=Id(kind="port", value="1" * 32),
        key=("f1", "element", "1"),
        function=func.id,
        template=port_template_1.id,
        name="1",
        role=PortRole.GENERIC,
    )
    port_2 = Port(
        id=Id(kind="port", value="2" * 32),
        key=("f1", "element", "2"),
        function=func.id,
        template=port_template_2.id,
        name="2",
        role=PortRole.GENERIC,
    )
    add_all(
        draft,
        part,
        func_template,
        port_template_1,
        port_template_2,
        link,
        item,
        func,
        port_1,
        port_2,
        origin=origin,
    )
    model = freeze(draft)
    assert net_of(model, port_1.id) == net_of(model, port_2.id)


def test_closure_joins_equal_named_ports_through_a_mate(origin: Origin) -> None:
    """Two connector functions joined by a `Mate` conduct through their equal-named ports."""
    draft = Draft()
    item_a = Item(
        id=Id(kind="item", value="a" * 32),
        key=("jb1",),
        part=None,
        parent=None,
        position=None,
        tag="JB1",
        description="board",
    )
    item_b = Item(
        id=Id(kind="item", value="b" * 32),
        key=("h1",),
        part=None,
        parent=None,
        position=None,
        tag="H1",
        description="harness housing",
    )
    func_a = Function(
        id=Id(kind="function", value="a" * 32),
        key=("jb1", "j1"),
        item=item_a.id,
        template=None,
        name="J1",
        kind=FunctionKind.CONNECTOR,
    )
    func_b = Function(
        id=Id(kind="function", value="b" * 32),
        key=("h1", "p1"),
        item=item_b.id,
        template=None,
        name="P1",
        kind=FunctionKind.CONNECTOR,
    )
    port_a = Port(
        id=Id(kind="port", value="a" * 32),
        key=("jb1", "j1", "1"),
        function=func_a.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    port_b = Port(
        id=Id(kind="port", value="b" * 32),
        key=("h1", "p1", "1"),
        function=func_b.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    mate = Mate(id=Id(kind="mate", value="1" * 32), key=("j1-p1",), a=func_a.id, b=func_b.id)
    add_all(draft, item_a, item_b, func_a, func_b, port_a, port_b, mate, origin=origin)
    model = freeze(draft)
    assert net_of(model, port_a.id) == net_of(model, port_b.id)


def test_closure_does_not_join_through_a_switched_internal_link(origin: Origin) -> None:
    """A `SWITCHED` internal link (a contact) never joins net closure, unlike `CONDUCTIVE`."""
    draft = Draft()
    part = Part(
        id=Id(kind="part", value="2" * 32),
        key=("relay",),
        mpn="SIM-RELAY-1CO",
        manufacturer="Synthetic Parts Co",
        description="1 changeover relay",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    func_template = FunctionTemplate(
        id=Id(kind="function_template", value="2" * 32),
        key=("relay", "co_1"),
        part=part.id,
        name="co_1",
        kind=FunctionKind.CONTACT_CO,
    )
    port_template_11 = PortTemplate(
        id=Id(kind="port_template", value="11" + "1" * 30),
        key=("relay", "co_1", "11"),
        function=func_template.id,
        name="11",
        role=PortRole.GENERIC,
    )
    port_template_14 = PortTemplate(
        id=Id(kind="port_template", value="14" + "1" * 30),
        key=("relay", "co_1", "14"),
        function=func_template.id,
        name="14",
        role=PortRole.GENERIC,
    )
    link = InternalLink(
        id=Id(kind="internal_link", value="2" * 32),
        key=("relay", "co_1", "11-14"),
        a=port_template_11.id,
        b=port_template_14.id,
        kind=LinkKind.SWITCHED,
    )
    item = Item(
        id=Id(kind="item", value="2" * 32),
        key=("k1",),
        part=part.id,
        parent=None,
        position=None,
        tag="-K1",
        description="pump starter",
    )
    func = Function(
        id=Id(kind="function", value="2" * 32),
        key=("k1", "co_1"),
        item=item.id,
        template=func_template.id,
        name="co_1",
        kind=FunctionKind.CONTACT_CO,
    )
    port_11 = Port(
        id=Id(kind="port", value="11" + "1" * 30),
        key=("k1", "co_1", "11"),
        function=func.id,
        template=port_template_11.id,
        name="11",
        role=PortRole.GENERIC,
    )
    port_14 = Port(
        id=Id(kind="port", value="14" + "1" * 30),
        key=("k1", "co_1", "14"),
        function=func.id,
        template=port_template_14.id,
        name="14",
        role=PortRole.GENERIC,
    )
    add_all(
        draft,
        part,
        func_template,
        port_template_11,
        port_template_14,
        link,
        item,
        func,
        port_11,
        port_14,
        origin=origin,
    )
    model = freeze(draft)
    assert net_of(model, port_11.id) != net_of(model, port_14.id)


def test_physical_nets_and_port_groups_share_one_sorted_tail(origin: Origin) -> None:
    """Both callers return `PhysicalNet`s with sorted `ports`, the nets sorted by `ports`.

    The wiring is given in scrambled order; `physical_nets` reads it from conductors and
    `port_groups` from the same pairs as groups, and the two agree.
    """
    item = Item(
        id=make_id(Item, ("i",)),
        key=("i",),
        part=None,
        parent=None,
        position=None,
        tag="-X1",
        description="terminal block",
    )
    func = Function(
        id=make_id(Function, ("i", "f")),
        key=("i", "f"),
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.TERMINAL,
    )
    names = ("p1", "p2", "p3", "p4", "p5", "p6")
    port = {
        name: Port(
            id=make_id(Port, ("i", "f", name)),
            key=("i", "f", name),
            function=func.id,
            template=None,
            name=name,
            role=PortRole.GENERIC,
        )
        for name in names
    }
    pairs = (("p5", "p2"), ("p4", "p1"), ("p3", "p4"))
    conductors = [
        Conductor(
            id=make_id(Conductor, ("w", str(number))),
            key=("w", str(number)),
            a=port[a].id,
            b=port[b].id,
            kind=ConductorKind.WIRE,
            carrier=None,
        )
        for number, (a, b) in enumerate(pairs)
    ]
    add_all(draft := Draft(), item, func, *port.values(), *conductors, origin=origin)
    model = freeze(draft)
    groups = [(port[a].id, port[b].id) for a, b in pairs] + [(port["p6"].id,)]

    expected = tuple(
        sorted(
            (
                PhysicalNet(ports=tuple(sorted(port[name].id for name in members)))
                for members in (("p2", "p5"), ("p1", "p3", "p4"), ("p6",))
            ),
            key=lambda net: net.ports,
        )
    )
    from_model = physical_nets(model)
    from_groups = port_groups(groups)
    assert from_model == expected
    assert from_groups == expected
    for nets in (from_model, from_groups):
        assert isinstance(nets, tuple)
        assert all(isinstance(net, PhysicalNet) for net in nets)
        assert all(net.ports == tuple(sorted(net.ports)) for net in nets)
        assert [net.ports for net in nets] == sorted(net.ports for net in nets)


def test_the_net_tail_sorts_whatever_order_the_sets_were_registered_in() -> None:
    """Members registered in descending id order still give sorted ports and sorted nets.

    The registration order is fixed here (no hash order), so dropping either `sorted` fails.
    """
    ids = sorted(make_id(Port, ("i", "f", f"p{n}")) for n in range(6))
    sets = UnionFind(reversed(ids))
    sets.union(ids[4], ids[5])
    sets.union(ids[0], ids[3])
    assert _nets_from(sets) == (
        PhysicalNet(ports=(ids[0], ids[3])),
        PhysicalNet(ports=(ids[1],)),
        PhysicalNet(ports=(ids[2],)),
        PhysicalNet(ports=(ids[4], ids[5])),
    )
