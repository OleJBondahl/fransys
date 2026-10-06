"""WP12 tests: `validators.connectivity`, the validator half of WP12 (design/connectivity.md)."""

from decimal import Decimal

from plant import Plant

from fransys_model.kernel import Draft, Id, Model, Origin, Record, Severity, freeze
from fransys_model.vocab.closure import net_of
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    NetClass,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.templates import Part
from fransys_model.vocab.validators.connectivity import (
    CONDUCTOR_ON_UNINSTALLED,
    NET_POTENTIAL_CONFLICT,
    NET_SHORTED,
    NET_UNREALISED,
    PORT_UNCONNECTED,
    check_connectivity,
)

_SCAFFOLD_ITEM = Id(kind="item", value="0" * 32)
_SCAFFOLD_FUNCTION = Id(kind="function", value="0" * 32)


def _scaffold(records: tuple[Record, ...]) -> tuple[Record, ...]:
    """Setup only: the records `records` refer to but do not define.

    A `Net` or `Conductor` names ports and a `Port` names a function; `freeze()` resolves
    every reference, so each undefined one gets a bare installed `Item`, `Function` or `Port`.
    """
    present = {record.id for record in records}
    port_refs: set[Id[Port]] = set()
    function_refs: set[Id[Function]] = set()
    for record in records:
        if isinstance(record, Net):
            port_refs.update(record.ports)
        elif isinstance(record, Conductor):
            port_refs.update((record.a, record.b))
        elif isinstance(record, Port):
            function_refs.add(record.function)
    missing_ports = sorted(port_refs - present)
    missing_functions = set(function_refs - present)
    if missing_ports and _SCAFFOLD_FUNCTION not in present:
        missing_functions.add(_SCAFFOLD_FUNCTION)
    added: list[Record] = []
    if missing_functions and _SCAFFOLD_ITEM not in present:
        added.append(
            Item(
                id=_SCAFFOLD_ITEM,
                key=("scaffold", "item"),
                part=None,
                parent=None,
                position=None,
                tag=None,
                description="Scaffold for the fixture",
                installed=True,
            )
        )
    added.extend(
        Function(
            id=function,
            key=("scaffold", "function", str(number)),
            item=_SCAFFOLD_ITEM,
            template=None,
            name=f"f{number}",
            kind=FunctionKind.GENERIC,
        )
        for number, function in enumerate(sorted(missing_functions))
    )
    added.extend(
        Port(
            id=port,
            key=("scaffold", "port", str(number)),
            function=_SCAFFOLD_FUNCTION,
            template=None,
            name=f"p{number}",
            role=PortRole.GENERIC,
        )
        for number, port in enumerate(missing_ports)
    )
    return tuple(added)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_validator_connectivity.py", line=1, note="fixture")
    draft.extend((*records, *_scaffold(records)), origin=origin)
    return freeze(draft)


def _port(value: str) -> Id[Port]:
    return Id(kind="port", value=value * 32)


def test_net_realised_by_a_conductor_has_no_finding() -> None:
    """A declared `Net` whose two ports are also joined by a `Conductor` is realised."""
    p1, p2 = _port("1"), _port("2")
    net = Net(
        id=Id(kind="net", value="3" * 32),
        key=("examples", "supply-24v"),
        name="24V",
        net_class=NetClass.POWER,
        ports=(p1, p2),
    )
    wire = Conductor(
        id=Id(kind="conductor", value="4" * 32),
        key=("examples", "supply-24v", "wire"),
        a=p1,
        b=p2,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    findings = check_connectivity(_freeze((net, wire)))
    assert not [f for f in findings if f.code == NET_UNREALISED]


def test_net_with_no_conductor_yields_net_unrealised() -> None:
    """A declared `Net` whose ports are never physically joined yields `NET_UNREALISED`."""
    net = Net(
        id=Id(kind="net", value="5" * 32),
        key=("examples", "supply-24v"),
        name="24V",
        net_class=NetClass.POWER,
        ports=(_port("1"), _port("2")),
    )
    findings = check_connectivity(_freeze((net,)))
    assert any(f.code == NET_UNREALISED for f in findings)


def test_two_separate_nets_yield_no_net_shorted() -> None:
    """Two declared `Net`s with no conductor bridging them are not shorted."""
    net_a = Net(
        id=Id(kind="net", value="6" * 32),
        key=("examples", "net-a"),
        name="A",
        net_class=NetClass.SIGNAL,
        ports=(_port("1"), _port("2")),
    )
    net_b = Net(
        id=Id(kind="net", value="7" * 32),
        key=("examples", "net-b"),
        name="B",
        net_class=NetClass.SIGNAL,
        ports=(_port("3"), _port("4")),
    )
    findings = check_connectivity(_freeze((net_a, net_b)))
    assert not [f for f in findings if f.code == NET_SHORTED]


def test_conductor_bridging_two_declared_nets_yields_net_shorted() -> None:
    """A `Conductor` joining a port from each of two declared `Net`s yields `NET_SHORTED`."""
    p2, p3 = _port("2"), _port("3")
    net_a = Net(
        id=Id(kind="net", value="8" * 32),
        key=("examples", "net-a"),
        name="A",
        net_class=NetClass.SIGNAL,
        ports=(_port("1"), p2),
    )
    net_b = Net(
        id=Id(kind="net", value="9" * 32),
        key=("examples", "net-b"),
        name="B",
        net_class=NetClass.SIGNAL,
        ports=(p3, _port("4")),
    )
    bridge = Conductor(
        id=Id(kind="conductor", value="a" * 32),
        key=("examples", "accidental-bridge"),
        a=p2,
        b=p3,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    findings = check_connectivity(_freeze((net_a, net_b, bridge)))
    assert any(f.code == NET_SHORTED for f in findings)


def test_connected_port_has_no_port_unconnected_finding() -> None:
    """A `Port` carrying a `Conductor` is not unconnected."""
    p1, p2 = _port("1"), _port("2")
    wire = Conductor(
        id=Id(kind="conductor", value="f" * 32),
        key=("examples", "wire"),
        a=p1,
        b=p2,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    findings = check_connectivity(_freeze((wire,)))
    assert not [f for f in findings if f.code == PORT_UNCONNECTED]


def test_port_with_no_conductor_or_net_yields_port_unconnected() -> None:
    """A `Port` named by no `Conductor` and no `Net` yields `PORT_UNCONNECTED`."""
    function_id = Id(kind="function", value="1" * 32)
    lone_port = Port(
        id=_port("2"),
        key=("examples", "lone-port"),
        function=function_id,
        template=None,
        name="LONE",
        role=PortRole.GENERIC,
    )
    findings = check_connectivity(_freeze((lone_port,)))
    assert any(f.code == PORT_UNCONNECTED for f in findings)


def test_conductor_on_an_installed_item_has_no_uninstalled_finding() -> None:
    """A `Conductor` whose ports sit on an installed item's function is not flagged."""
    p1, p2 = _port("1"), _port("2")
    wire = Conductor(
        id=Id(kind="conductor", value="3" * 32),
        key=("examples", "wire"),
        a=p1,
        b=p2,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    findings = check_connectivity(_freeze((wire,)))
    assert not [f for f in findings if f.code == CONDUCTOR_ON_UNINSTALLED]


def test_conductor_on_an_uninstalled_items_port_yields_conductor_on_uninstalled() -> None:
    """A conductor landing on a port of an item with `installed=False` (design/connectivity.md)."""
    item = Item(
        id=Id(kind="item", value="4" * 32),
        key=("examples", "pulled-device"),
        part=None,
        parent=None,
        position=None,
        tag="-K99",
        description="",
        installed=False,
    )
    function = Function(
        id=Id(kind="function", value="5" * 32),
        key=("examples", "pulled-device", "fn"),
        item=item.id,
        template=None,
        name="fn",
        kind=FunctionKind.GENERIC,
    )
    port = Port(
        id=_port("6"),
        key=("examples", "pulled-device", "fn", "port"),
        function=function.id,
        template=None,
        name="P",
        role=PortRole.GENERIC,
    )
    wire = Conductor(
        id=Id(kind="conductor", value="7" * 32),
        key=("examples", "wire-to-pulled-device"),
        a=port.id,
        b=_port("8"),
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    findings = check_connectivity(_freeze((item, function, port, wire)))
    assert any(f.code == CONDUCTOR_ON_UNINSTALLED for f in findings)


def test_board_realised_net_produces_no_net_unrealised() -> None:
    """A `Net` whose ports sit under one `pcb`-facet ancestor item needs no conductors."""
    board_part = Part(
        id=Id(kind="part", value="9" * 32),
        key=("examples", "harness-board"),
        mpn="EXAMPLE-BOARD-1",
        manufacturer="Example Co",
        description="",
        category=PartCategory.BOARD,
        class_code="A",
    )
    pcb_facet = PcbFacet(
        id=Id(kind="facet.pcb", value="a" * 32),
        key=("examples", "harness-board", "pcb"),
        subject=board_part.id,
        revision="B",
    )
    board = Item(
        id=Id(kind="item", value="b" * 32),
        key=("examples", "harness-board-1"),
        part=board_part.id,
        parent=None,
        position=None,
        tag="JB1",
        description="",
    )
    r1 = Item(
        id=Id(kind="item", value="c" * 32),
        key=("examples", "harness-board-1", "r1"),
        part=None,
        parent=board.id,
        position=None,
        tag="R1",
        description="",
    )
    function = Function(
        id=Id(kind="function", value="d" * 32),
        key=("examples", "harness-board-1", "r1", "fn"),
        item=r1.id,
        template=None,
        name="fn",
        kind=FunctionKind.GENERIC,
    )
    p1, p2 = _port("e"), _port("f")
    ports = tuple(
        Port(
            id=port,
            key=("examples", "harness-board-1", "r1", "fn", name),
            function=function.id,
            template=None,
            name=name,
            role=PortRole.GENERIC,
        )
        for port, name in ((p1, "1"), (p2, "2"))
    )
    net = Net(
        id=Id(kind="net", value="1" * 32),
        key=("examples", "board-net"),
        name="board-net",
        net_class=NetClass.GENERIC,
        ports=(p1, p2),
    )
    findings = check_connectivity(
        _freeze((board_part, pcb_facet, board, r1, function, *ports, net))
    )
    assert not [f for f in findings if f.code == NET_UNREALISED]


def test_a_harness_realises_no_net_unlike_a_board() -> None:
    """H3: a declared net between two pins of one harness plug, with no conductor, still
    yields `NET_UNREALISED` -- a harness is not a board (`enclosing_boards` is untouched, H3;
    decision model-0043, spec `2026-09-23-harness-designation.md` acceptance 3)."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    cable_part = Part(
        id=Id(kind="part", value="6" * 32),
        key=("wh1", "w1", "part"),
        mpn="MPN-W1",
        manufacturer="Example Co",
        description="Invented cable",
        category=PartCategory.CABLE,
        class_code="W",
    )
    plant.add(cable_part)
    plant.add(
        CableProductFacet(
            id=Id(kind="facet.cable_product", value="5" * 32),
            key=("wh1", "w1", "part", "product"),
            subject=cable_part.id,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        )
    )
    plant.add(
        CableFacet(
            id=Id(kind="facet.cable", value="9" * 32),
            key=("wh1", "w1", "cable"),
            subject=plant.item("w1", parent=harness, part=cable_part.id, designation="W1"),
            length_mm=None,
        )
    )
    plug = plant.item("x1", parent=harness, designation="X1")
    function = plant.function(plug, "fn")
    p1 = plant.port(function, "1")
    p2 = plant.port(function, "2")
    net = plant.net("n1", (p1, p2))
    findings = check_connectivity(plant.model())
    assert any(f.code == NET_UNREALISED and f.subjects == (net,) for f in findings)


def _rail(value: str, potential: str | None, ports: tuple[Id[Port], ...]) -> Net:
    return Net(
        id=Id(kind="net", value=value * 32),
        key=("examples", "rail", value),
        name=potential,
        net_class=NetClass.POWER,
        ports=ports,
        potential=potential,
    )


def _bridge(a: Id[Port], b: Id[Port]) -> Conductor:
    return Conductor(
        id=Id(kind="conductor", value="f" * 32),
        key=("examples", "rail", "bridge"),
        a=a,
        b=b,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def test_bridged_rails_of_different_potential_yield_net_potential_conflict() -> None:
    """A conductor joining a `24V` net and a `0V` net yields `NET_POTENTIAL_CONFLICT`."""
    plus = _rail("a", "24V", (_port("1"), _port("2")))
    minus = _rail("b", "0V", (_port("3"), _port("4")))
    findings = check_connectivity(_freeze((plus, minus, _bridge(_port("2"), _port("3")))))
    assert any(f.code == NET_POTENTIAL_CONFLICT for f in findings)


def test_bridged_rail_and_ordinary_net_yield_no_net_potential_conflict() -> None:
    """A rail bridged to a net with `potential=None` is shorted, but not a potential conflict."""
    plus = _rail("a", "24V", (_port("1"), _port("2")))
    plain = _rail("b", None, (_port("3"), _port("4")))
    findings = check_connectivity(_freeze((plus, plain, _bridge(_port("2"), _port("3")))))
    assert not [f for f in findings if f.code == NET_POTENTIAL_CONFLICT]


def _mated_pair(*, with_mate: bool) -> tuple[Record, ...]:
    """U8: two connector functions, each with one port named `P`, on rails `24V` and `0V`.

    `with_mate=True` also joins the two functions with a `Mate`, so `_join_mates` unions
    the ports (equal name) into one physical net, per the model's own connectivity: a mate
    joins its pins into one physical net (units spec U8).
    """
    item_a = Item(
        id=Id(kind="item", value="a" * 32),
        key=("examples", "mate-a"),
        part=None,
        parent=None,
        position=None,
        tag="-X1",
        description="",
    )
    item_b = Item(
        id=Id(kind="item", value="b" * 32),
        key=("examples", "mate-b"),
        part=None,
        parent=None,
        position=None,
        tag="-X2",
        description="",
    )
    function_a = Function(
        id=Id(kind="function", value="a" * 32),
        key=("examples", "mate-a", "fn"),
        item=item_a.id,
        template=None,
        name="fn",
        kind=FunctionKind.CONNECTOR,
    )
    function_b = Function(
        id=Id(kind="function", value="b" * 32),
        key=("examples", "mate-b", "fn"),
        item=item_b.id,
        template=None,
        name="fn",
        kind=FunctionKind.CONNECTOR,
    )
    port_a = Port(
        id=_port("a"),
        key=("examples", "mate-a", "fn", "P"),
        function=function_a.id,
        template=None,
        name="P",
        role=PortRole.GENERIC,
    )
    port_b = Port(
        id=_port("b"),
        key=("examples", "mate-b", "fn", "P"),
        function=function_b.id,
        template=None,
        name="P",
        role=PortRole.GENERIC,
    )
    plus = _rail("c", "24V", (port_a.id,))
    minus = _rail("d", "0V", (port_b.id,))
    records: tuple[Record, ...] = (
        item_a,
        item_b,
        function_a,
        function_b,
        port_a,
        port_b,
        plus,
        minus,
    )
    if with_mate:
        mate = Mate(
            id=Id(kind="mate", value="1" * 32),
            key=("examples", "mate"),
            a=function_a.id,
            b=function_b.id,
        )
        records = (*records, mate)
    return records


def test_rails_joined_by_a_mate_yield_net_potential_conflict() -> None:
    """U8: a mate joins its pins into one physical net, so `24V` and `0V` across it conflict."""
    model = _freeze(_mated_pair(with_mate=True))
    # examined: the mate really does union the two rails' ports into one physical net
    assert net_of(model, _port("a")) == net_of(model, _port("b"))
    findings = check_connectivity(model)
    conflicts = [f for f in findings if f.code == NET_POTENTIAL_CONFLICT]
    assert len(conflicts) == 1
    (conflict,) = conflicts
    assert conflict.severity is Severity.ERROR
    assert set(conflict.subjects) == {
        Id(kind="net", value="c" * 32),
        Id(kind="net", value="d" * 32),
    }


def test_rails_not_joined_by_a_mate_yield_no_net_potential_conflict() -> None:
    """Clean twin: the same two rails and functions, but no `Mate` between them."""
    model = _freeze(_mated_pair(with_mate=False))
    # examined: with no mate, the two rails' ports stay in separate physical nets
    assert net_of(model, _port("a")) != net_of(model, _port("b"))
    findings = check_connectivity(model)
    assert not [f for f in findings if f.code == NET_POTENTIAL_CONFLICT]
