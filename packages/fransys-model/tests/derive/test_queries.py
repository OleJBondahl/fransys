"""WP16 tests: `derive.queries` (ROADMAP WP16, design/derive-queries.md).

One test per row of the design/derive-queries.md query table. `physical_nets`/`net_of`
(closure.py) and `unconnected_ports`/`unused_terminals`, `subtree`/`items_at` share one row each
there, so they share one test here too; their depth is otherwise covered by `test_closure.py`.
"""

from decimal import Decimal

from derive_helpers import add_all

from fransys_model.derive import (
    BoardNetlist,
    BomLine,
    CableRow,
    DesignationRow,
    TerminalRow,
    board_netlist,
    bom_lines,
    cable_rows,
    conductors_on_item,
    designation_list,
    ext_usage,
    first_leg,
    items_at,
    net_of,
    physical_nets,
    plc_channel_rows,
    subtree,
    terminal_rows,
    unconnected_ports,
    unused_terminals,
    wire_rows,
)
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor, Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    Aspect,
    ConductorKind,
    FunctionKind,
    NetClass,
    PartCategory,
    PortRole,
    SignalType,
)
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.facets.pcb import FootprintFacet, PcbFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import FunctionTemplate, Part


def _item(  # noqa: PLR0913 -- one param per Item field, kept explicit for ty (see hand-back)
    v: str,
    key: tuple[str, ...],
    *,
    part: Id[Part] | None = None,
    parent: Id[Item] | None = None,
    position: int | None = None,
    designation: str | None = None,
    description: str = "",
    installed: bool = True,
) -> Item:
    return Item(
        id=Id(kind="item", value=v * 32),
        key=key,
        part=part,
        parent=parent,
        position=position,
        tag=designation,
        description=description,
        installed=installed,
    )


def _function(  # noqa: PLR0913 -- one param per Function field, kept explicit for ty
    v: str,
    key: tuple[str, ...],
    item: Item,
    *,
    name: str,
    kind: FunctionKind,
    template: Id[FunctionTemplate] | None = None,
) -> Function:
    return Function(
        id=Id(kind="function", value=v * 32),
        key=key,
        item=item.id,
        template=template,
        name=name,
        kind=kind,
    )


def _port(  # noqa: PLR0913 -- one param per Port field, kept explicit for ty
    v: str,
    key: tuple[str, ...],
    function: Function,
    *,
    name: str,
    role: PortRole,
    template: None = None,
) -> Port:
    return Port(
        id=Id(kind="port", value=v * 32),
        key=key,
        function=function.id,
        template=template,
        name=name,
        role=role,
    )


def test_conductors_on_item_groups_by_terminal_and_role(origin: Origin) -> None:
    """`conductors_on_item` groups a strip's conductors by terminal, then by `PortRole`."""
    strip = _item("1", ("x1",), designation="X1", description="terminal strip")
    terminal = _item("2", ("x1", "l1"), parent=strip.id, designation="L1:1")
    term_facet = TerminalFacet(
        id=Id(kind="facet.terminal", value="1" * 32),
        key=("x1", "l1", "facet"),
        subject=terminal.id,
        group="L1",
        index=1,
    )
    term_func = _function(
        "3", ("x1", "l1", "terminal"), terminal, name="terminal", kind=FunctionKind.TERMINAL
    )
    ext_port = _port(
        "1", ("x1", "l1", "external"), term_func, name="external", role=PortRole.EXTERNAL
    )
    field_item = _item("4", ("field",), designation="-B1")
    field_func = _function(
        "5", ("field", "signal"), field_item, name="signal", kind=FunctionKind.SENSOR
    )
    field_port = _port("2", ("field", "signal", "1"), field_func, name="1", role=PortRole.GENERIC)
    conductor = Conductor(
        id=Id(kind="conductor", value="1" * 32),
        key=("w1", "1"),
        a=field_port.id,
        b=ext_port.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    draft = Draft()
    add_all(
        draft,
        strip,
        terminal,
        term_facet,
        term_func,
        ext_port,
        field_item,
        field_func,
        field_port,
        conductor,
        origin=origin,
    )
    model = freeze(draft)
    grouped = conductors_on_item(model, strip.id)
    assert conductor.id in grouped[terminal.id][PortRole.EXTERNAL]


def test_terminal_rows_includes_unused_terminals(origin: Origin) -> None:
    """`terminal_rows` lists every terminal of a strip, used or not."""
    strip = _item("1", ("x2",), designation="X2", description="terminal strip")
    used = _item("2", ("x2", "l1"), parent=strip.id, designation="L1:1")
    unused = _item("3", ("x2", "l2"), parent=strip.id, designation="L2:1")
    used_facet = TerminalFacet(
        id=Id(kind="facet.terminal", value="1" * 32),
        key=("x2", "l1", "facet"),
        subject=used.id,
        group="L1",
        index=1,
    )
    unused_facet = TerminalFacet(
        id=Id(kind="facet.terminal", value="2" * 32),
        key=("x2", "l2", "facet"),
        subject=unused.id,
        group="L2",
        index=1,
    )
    draft = Draft()
    add_all(draft, strip, used, unused, used_facet, unused_facet, origin=origin)
    model = freeze(draft)
    rows = terminal_rows(model, strip.id)
    assert all(isinstance(r, TerminalRow) for r in rows)
    assert {r.terminal for r in rows} == {used.id, unused.id}
    assert any(r.terminal == unused.id and not r.internal and not r.external for r in rows)


def test_bom_lines_groups_by_part_installed_only(origin: Origin) -> None:
    """`bom_lines` counts only `installed=True` items, grouped by `Part`."""
    part = Part(
        id=Id(kind="part", value="1" * 32),
        key=("contactor",),
        mpn="SIM-CONTACTOR-9A",
        manufacturer="Synthetic Parts Co",
        description="9A contactor",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    installed = _item("1", ("k1",), part=part.id, designation="K1", installed=True)
    spare = _item("2", ("k2",), part=part.id, designation="K2", installed=False)
    draft = Draft()
    add_all(draft, part, installed, spare, origin=origin)
    model = freeze(draft)
    lines = bom_lines(model)
    assert all(isinstance(r, BomLine) for r in lines)
    (matching,) = (r for r in lines if r.part == part.id)
    assert matching.count == 1
    assert "-K1" in matching.designations
    assert "-K2" not in matching.designations


def test_plc_channel_rows_names_channel_signal_and_field_device(origin: Origin) -> None:
    """`plc_channel_rows` reports one row per channel: signal, field device, and binding."""
    module_part = Part(
        id=Id(kind="part", value="1" * 32),
        key=("di8",),
        mpn="SIM-DI8-024",
        manufacturer="Synthetic Parts Co",
        description="8ch digital input module",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    channel_template = FunctionTemplate(
        id=Id(kind="function_template", value="1" * 32),
        key=("di8", "ch_1"),
        part=module_part.id,
        name="ch_1",
        kind=FunctionKind.PLC_CHANNEL,
    )
    channel_facet = PlcChannelFacet(
        id=Id(kind="facet.plc_channel", value="1" * 32),
        key=("di8", "ch_1", "facet"),
        subject=channel_template.id,
        signal=SignalType.DI,
        channel=1,
    )
    module_item = _item("1", ("a1",), part=module_part.id, designation="A1-1")
    channel_func = _function(
        "1",
        ("a1", "ch_1"),
        module_item,
        template=channel_template.id,
        name="ch_1",
        kind=FunctionKind.PLC_CHANNEL,
    )
    field_item = _item("2", ("dev",), designation="-B1")
    field_func = _function(
        "2", ("dev", "signal"), field_item, name="signal", kind=FunctionKind.SENSOR
    )
    request = PlcRequestFacet(
        id=Id(kind="facet.plc_request", value="1" * 32),
        key=("dev", "signal", "request"),
        subject=field_func.id,
        signal=SignalType.DI,
        signal_name="Start_PB",
        priority=1,
    )
    binding = PlcBindingFacet(
        id=Id(kind="facet.plc_binding", value="1" * 32),
        key=("dev", "signal", "binding"),
        subject=field_func.id,
        channel=channel_func.id,
    )
    draft = Draft()
    add_all(
        draft,
        module_part,
        channel_template,
        channel_facet,
        module_item,
        channel_func,
        field_item,
        field_func,
        request,
        binding,
        origin=origin,
    )
    model = freeze(draft)
    (row,) = (r for r in plc_channel_rows(model) if r.channel == channel_func.id)
    assert row.signal == SignalType.DI
    assert row.field_device == field_func.id


def test_cable_rows_one_row_per_core_both_ends(origin: Origin) -> None:
    """`cable_rows` lists one `CableRow` per core, sorted by core index."""
    cable_part = Part(
        id=Id(kind="part", value="1" * 32),
        key=("cable",),
        mpn="SIM-CABLE-2X0.75",
        manufacturer="Synthetic Parts Co",
        description="2-core shielded cable",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product_facet = CableProductFacet(
        id=Id(kind="facet.cable_product", value="1" * 32),
        key=("cable", "product"),
        subject=cable_part.id,
        core_colours=("brown",),
        gauge_mm2=Decimal("0.75"),
        shielded=True,
    )
    cable_item = _item("1", ("w1",), part=cable_part.id, designation="W1")
    item_a = _item("2", ("dev-a",), designation="-B1")
    item_b = _item("3", ("dev-b",), designation="X1")
    func_a = _function("1", ("dev-a", "signal"), item_a, name="signal", kind=FunctionKind.SENSOR)
    func_b = _function(
        "2", ("dev-b", "terminal"), item_b, name="terminal", kind=FunctionKind.TERMINAL
    )
    port_a = _port("1", ("dev-a", "signal", "+"), func_a, name="+", role=PortRole.GENERIC)
    port_b = _port(
        "2", ("dev-b", "terminal", "external"), func_b, name="external", role=PortRole.EXTERNAL
    )
    core = Conductor(
        id=Id(kind="conductor", value="1" * 32),
        key=("w1", "core1"),
        a=port_a.id,
        b=port_b.id,
        kind=ConductorKind.CORE,
        carrier=cable_item.id,
    )
    core_facet = CoreFacet(
        id=Id(kind="facet.core", value="1" * 32),
        key=("w1", "core1", "facet"),
        subject=core.id,
        index=1,
    )
    draft = Draft()
    add_all(
        draft,
        cable_part,
        product_facet,
        cable_item,
        item_a,
        item_b,
        func_a,
        func_b,
        port_a,
        port_b,
        core,
        core_facet,
        origin=origin,
    )
    model = freeze(draft)
    rows = cable_rows(model, cable_item.id)
    assert [r.index for r in rows] == sorted(r.index for r in rows)
    assert all(isinstance(r, CableRow) for r in rows)
    assert rows[0].conductor == core.id


def test_wire_rows_one_per_wire(origin: Origin) -> None:
    """`wire_rows` lists every `wire`-faceted WIRE conductor, with its colour, size and label."""
    item_a = _item("1", ("k1",), designation="-K1")
    item_b = _item("2", ("x1",), designation="X1")
    func_a = _function("1", ("k1", "coil"), item_a, name="coil", kind=FunctionKind.COIL)
    func_b = _function("2", ("x1", "terminal"), item_b, name="terminal", kind=FunctionKind.TERMINAL)
    port_a = _port("1", ("k1", "coil", "A1"), func_a, name="A1", role=PortRole.GENERIC)
    port_b = _port(
        "2", ("x1", "terminal", "internal"), func_b, name="internal", role=PortRole.INTERNAL
    )
    wire = Conductor(
        id=Id(kind="conductor", value="1" * 32),
        key=("w5", "1"),
        a=port_a.id,
        b=port_b.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    wire_facet = WireFacet(
        id=Id(kind="facet.wire", value="1" * 32),
        key=("w5", "1", "facet"),
        subject=wire.id,
        colour="blue",
        gauge_mm2=Decimal("0.75"),
        length_mm=250,
        label="W5",
    )
    draft = Draft()
    add_all(draft, item_a, item_b, func_a, func_b, port_a, port_b, wire, wire_facet, origin=origin)
    model = freeze(draft)
    (row,) = wire_rows(model)
    assert row.conductor == wire.id
    assert (row.colour, row.cross_section_mm2) == ("blue", Decimal("0.75"))
    assert row.label == f"{row.from_} {row.to}"


def test_designation_list_one_row_per_item(origin: Origin) -> None:
    """`designation_list` lists every item, sorted by `designation`."""
    item_a = _item("1", ("k1",), designation="K1", description="pump starter")
    item_b = _item("2", ("k2",), designation="K2", description="pump starter")
    draft = Draft()
    add_all(draft, item_a, item_b, origin=origin)
    model = freeze(draft)
    rows = designation_list(model)
    assert all(isinstance(r, DesignationRow) for r in rows)
    assert [r.designation for r in rows] == sorted(r.designation for r in rows)
    assert {r.item for r in rows} == {item_a.id, item_b.id}


def test_physical_nets_and_net_of_agree(origin: Origin) -> None:
    """`net_of` on either end of a conductor returns the same `PhysicalNet` `physical_nets` lists.

    Depth (which mechanisms join, which don't) is `test_closure.py`'s job (WP12); this is
    only the WP16 query-table row.
    """
    item_a = _item("1", ("a",), designation="-B1")
    item_b = _item("2", ("b",), designation="X1")
    func_a = _function("1", ("a", "signal"), item_a, name="signal", kind=FunctionKind.SENSOR)
    func_b = _function("2", ("b", "terminal"), item_b, name="terminal", kind=FunctionKind.TERMINAL)
    port_a = _port("1", ("a", "signal", "+"), func_a, name="+", role=PortRole.GENERIC)
    port_b = _port(
        "2", ("b", "terminal", "external"), func_b, name="external", role=PortRole.EXTERNAL
    )
    conductor = Conductor(
        id=Id(kind="conductor", value="1" * 32),
        key=("w1", "1"),
        a=port_a.id,
        b=port_b.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    draft = Draft()
    add_all(draft, item_a, item_b, func_a, func_b, port_a, port_b, conductor, origin=origin)
    model = freeze(draft)
    net = net_of(model, port_a.id)
    assert net is not None
    assert net in physical_nets(model)


def test_first_leg_returns_the_directly_joined_port(origin: Origin) -> None:
    """`first_leg` returns the other port on `net` directly joined to `from_item`'s own port."""
    item_a = _item("1", ("a",), designation="-B1")
    item_b = _item("2", ("b",), designation="X1")
    func_a = _function("1", ("a", "signal"), item_a, name="signal", kind=FunctionKind.SENSOR)
    func_b = _function("2", ("b", "terminal"), item_b, name="terminal", kind=FunctionKind.TERMINAL)
    port_a = _port("1", ("a", "signal", "+"), func_a, name="+", role=PortRole.GENERIC)
    port_b = _port(
        "2", ("b", "terminal", "external"), func_b, name="external", role=PortRole.EXTERNAL
    )
    net = Net(
        id=Id(kind="net", value="1" * 32),
        key=("n1",),
        name="N1",
        net_class=NetClass.SIGNAL,
        ports=(port_a.id, port_b.id),
    )
    draft = Draft()
    add_all(draft, item_a, item_b, func_a, func_b, port_a, port_b, net, origin=origin)
    model = freeze(draft)
    assert first_leg(model, net.id, from_item=item_a.id) == port_b.id


def test_unconnected_ports_and_unused_terminals(origin: Origin) -> None:
    """A floating port is `unconnected`; an unwired terminal is `unused`."""
    strip = _item("1", ("x3",), designation="X3")
    terminal = _item("2", ("x3", "l1"), parent=strip.id, designation="L1:1")
    facet = TerminalFacet(
        id=Id(kind="facet.terminal", value="1" * 32),
        key=("x3", "l1", "facet"),
        subject=terminal.id,
        group="L1",
        index=1,
    )
    func = _function(
        "1", ("x3", "l1", "terminal"), terminal, name="terminal", kind=FunctionKind.TERMINAL
    )
    port = _port("1", ("x3", "l1", "external"), func, name="external", role=PortRole.EXTERNAL)
    draft = Draft()
    add_all(draft, strip, terminal, facet, func, port, origin=origin)
    model = freeze(draft)
    assert port.id in unconnected_ports(model)
    assert terminal.id in unused_terminals(model, strip.id)


def test_board_netlist_parts_footprints_nets(origin: Origin) -> None:
    """`board_netlist` lists the board's parts, footprints and nets."""
    board_part = Part(
        id=Id(kind="part", value="1" * 32),
        key=("board",),
        mpn="SIM-BOARD-IOEXP",
        manufacturer="Synthetic Parts Co",
        description="IO expansion board",
        category=PartCategory.BOARD,
        class_code="A",
    )
    pcb_facet = PcbFacet(
        id=Id(kind="facet.pcb", value="1" * 32),
        key=("board", "pcb"),
        subject=board_part.id,
        revision="A",
    )
    board_item = _item("1", ("jb1",), part=board_part.id, designation="JB1")
    component_part = Part(
        id=Id(kind="part", value="2" * 32),
        key=("resistor",),
        mpn="SIM-R-0603",
        manufacturer="Synthetic Parts Co",
        description="0603 resistor",
        category=PartCategory.GENERIC,
        class_code="R",
    )
    footprint_facet = FootprintFacet(
        id=Id(kind="facet.footprint", value="1" * 32),
        key=("resistor", "footprint"),
        subject=component_part.id,
        library="Resistor_SMD",
        name="R_0603_1608Metric",
    )
    component_item = _item(
        "2", ("jb1", "r1"), part=component_part.id, parent=board_item.id, designation="R1"
    )
    draft = Draft()
    add_all(
        draft,
        board_part,
        pcb_facet,
        board_item,
        component_part,
        footprint_facet,
        component_item,
        origin=origin,
    )
    model = freeze(draft)
    netlist = board_netlist(model, board_item.id)
    assert isinstance(netlist, BoardNetlist)
    assert netlist.board == board_item.id
    assert any(p.item == component_item.id for p in netlist.parts)


def test_subtree_and_items_at(origin: Origin) -> None:
    """`items_at` a node includes items placed anywhere in `subtree` of that node."""
    root = AspectNode(
        id=Id(kind="aspect_node", value="1" * 32),
        key=("loc", "c1"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="enclosure",
    )
    child = AspectNode(
        id=Id(kind="aspect_node", value="2" * 32),
        key=("loc", "c1", "c2"),
        aspect=Aspect.LOCATION,
        parent=root.id,
        label="C2",
        description="sub-panel",
    )
    item = _item("1", ("k1",), designation="-K1")
    placement = Placement(
        id=Id(kind="placement", value="1" * 32), key=("k1", "loc"), item=item.id, node=child.id
    )
    draft = Draft()
    add_all(draft, root, child, item, placement, origin=origin)
    model = freeze(draft)
    assert subtree(model, root.id) == (child.id,)
    assert item.id in items_at(model, root.id)


def test_ext_usage_lists_every_ext_key(origin: Origin) -> None:
    """`ext_usage` finds a fact still stashed in an item's escape-hatch `ext` field."""
    item = Item(
        id=Id(kind="item", value="1" * 32),
        key=("k1",),
        part=None,
        parent=None,
        position=None,
        tag="-K1",
        description="pump starter",
        ext=frozendict({"legacy_note": "kept for now"}),
    )
    draft = Draft()
    add_all(draft, item, origin=origin)
    model = freeze(draft)
    usage = ext_usage(model)
    assert any(u.kind == "item" and u.key == "legacy_note" for u in usage)
