"""Acceptance test for decision model-0052 ("the dash is always there", owner ruling 2026-09-24):
a terminal, a connector pin, or any port named on its own prints `-<item>:<port designation>`,
the same everywhere. One fixture -- terminal `L1:1` on strip `X1`, pin `1` of connector `J1` --
read through every list and derive output the ruling names.
"""

import dataclasses
from decimal import Decimal
from typing import Any

from connector_builders import make_connector
from plant import Plant
from query_builders import bind_device, make_channels, make_core, make_part, make_terminal

from fransys_model.derive import (
    bom_lines,
    cable_list_rows,
    cable_rows,
    connector_rows,
    designation_list,
    overview_graph,
    plc_channel_rows,
    terminal_rows,
    top_level_cables,
    wire_rows,
)
from fransys_model.derive.designation import port_designation, terminal_designation
from fransys_model.derive.drawing_text import label_text
from fransys_model.kernel import Draft, Id, Origin, freeze, make_id
from fransys_model.layout import DrawingSet, Label, LabelKind, Page, PageRole, SheetFormat
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, Gender, PartCategory, PortRole, SignalType
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import Part


def _with_part(plant: Plant, item_id: Id[Item], part_id: Id[Any]) -> None:
    """Give an already-added item a `part` (records are frozen; `with_ext`'s own pattern)."""
    record = next(r for r in plant.records if r.id == item_id)
    plant.records.remove(record)
    plant.add(dataclasses.replace(record, part=part_id))


def test_the_one_port_text_format_reads_the_same_everywhere() -> None:  # noqa: PLR0915 -- one statement per output this decision covers, deliberately not split
    # one statement per output this decision covers, deliberately not split (the work order's
    # own acceptance criterion is ONE test over every list and derive output)
    """`-X1:L1:1` (a terminal) and `-J1:1` (a connector pin), read through the BOM, the
    terminal list, the connector list, the cable CSV, the wire labels, the PLC list, the
    designation list, the overview graph, and the harness cable's own ends/cores -- every
    consumer `terminal_designation`/`port_designation` feed (decision model-0052).
    `cable_list_rows` is checked too, but it carries no port text at all (`from_label`/
    `to_label` are `HarnessEnd.designation`, an item or unit name, never a port) -- noted here
    rather than forced to show text it structurally cannot carry.
    """
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    l1 = make_terminal(plant, "x1", "t-l1", group="L1", index=1)
    term_part = make_part(plant, "term-part", "SIM-TERM")
    _with_part(plant, l1.item, term_part)

    board = plant.item("board", designation="BOARD")
    plant.item("j1", designation="J1", parent=board)
    j1_fn, j1_ports = make_connector(plant, ("j1", "x"), ("1",))
    plant.item("p1", designation="P1", parent=board)
    p1_fn, _p1_ports = make_connector(plant, ("p1", "x"), ("1",), gender=Gender.FEMALE)
    plant.mate(j1_fn, p1_fn)

    cable_part = Part(
        id=make_id(Part, ("w1", "cable-part")),
        key=("w1", "cable-part"),
        mpn="MPN-w1",
        manufacturer="Example Co",
        description="Invented w1",
        category=PartCategory.CABLE,
        class_code="",
    )
    plant.add(
        cable_part,
        CableProductFacet(
            id=make_id(CableProductFacet, ("w1", "product")),
            key=("w1", "product"),
            subject=cable_part.id,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        ),
    )
    cable = plant.item("w1", designation="W1", part=cable_part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    core = make_core(plant, "core-1", cable, (l1.external, j1_ports["1"]), index=1)
    plant.add(
        WireFacet(
            id=make_id(WireFacet, ("core-1", "wire")),
            key=("core-1", "wire"),
            subject=core,
            colour="black",
            gauge_mm2=Decimal("0.75"),
            length_mm=None,
            label="W1-1",
        )
    )

    channels = make_channels(plant, "mod", "A1", (SignalType.DI,))
    device = bind_device(plant, "dev", "B7", channels[0])
    plant.wire(plant.port(device, "1"), l1.internal, key="dev-wire")
    plant.wire(plant.port(channels[0], "1"), l1.internal, key="channel-wire")

    model = plant.model()

    both = {"-X1:L1:1", "-J1:1"}

    # The two base functions everything else routes through.
    assert terminal_designation(model, l1.item) == "-X1:L1:1"
    assert port_designation(model, l1.external) == "-X1:L1:1"
    assert port_designation(model, j1_ports["1"]) == "-J1:1"

    # BOM: `printed_designation` (decision model-0050, amended by model-0052).
    term_line = next(line for line in bom_lines(model) if line.mpn == "SIM-TERM")
    assert term_line.designations == ("-X1:L1:1",)

    # Terminal list rows: `TerminalRow.designation`, full even under the strip's own heading.
    (row,) = terminal_rows(model, strip)
    assert row.designation == "-X1:L1:1"

    # Connector list: a pin's `mate_port_designation` names the far pin, dashed; the bare
    # `marking` (decision model-0049) is untouched.
    p1_row = next(r for r in connector_rows(model, board) if r.designation == "-P1")
    assert p1_row.pins[0].marking == "1"
    assert p1_row.pins[0].mate_port_designation == "-J1:1"

    # Cable CSV: both ends of the one core, whichever the cable's own end order puts first.
    (cable_row,) = cable_rows(model, cable)
    assert {cable_row.end_a_designation, cable_row.end_b_designation} == both

    # Wire list: a cable core is not a WIRE, so it prints no row there.
    assert wire_rows(model) == ()

    # Harness cable ends/cores: `HarnessCore` reads `cable_rows`' own fields unchanged; the
    # strip end's own `designation` is `product_designation` ("-X1"), already dashed before
    # this decision and unaffected by it.
    (harness_cable,) = top_level_cables(model)
    (core_row,) = harness_cable.cores
    assert {core_row.end_a_designation, core_row.end_b_designation} == both
    assert {end.designation for end in harness_cable.ends} == {"-X1", "-J1"}

    # Cable list: item/unit-level text only, never a port -- "-X1:L1:1"/"-J1:1" cannot appear.
    (list_row,) = cable_list_rows(model)
    assert {list_row.from_label, list_row.to_label} == {"-X1", "-J1"}

    # PLC list: `plc_channel_rows`' `wired_to` field, the far end of the channel's own port.
    plc_row = next(r for r in plc_channel_rows(model) if r.channel == channels[0])
    assert plc_row.wired_to == "-X1:L1:1"

    # Designation list: a terminal's own row, full and dashed (decision model-0052 amendment).
    designation_row = next(r for r in designation_list(model) if r.item == l1.item)
    assert designation_row.designation == "-X1:L1:1"

    # Overview graph: a terminal's own node, same amendment; a connector's own node reads as a
    # list prints an item (`printed_designation`, dashed -- decision model-0054, follow-up F3).
    overview = overview_graph(model)
    terminal_node = next(n for n in overview.nodes if n.item == l1.item)
    assert terminal_node.designation == "-X1:L1:1"
    j1_node = next(n for n in overview.nodes if n.item == make_id(Item, ("j1",)))
    assert j1_node.designation == "-J1"

    # drawing_text: the one port-text-carrying reader, `label_text`'s TAG dispatch for a
    # terminal function (`tag_text`, via `port_designation`); MARKING stays the port's raw
    # name (decision model-0049's own convention, untouched by this one); `marker_text` and
    # `cross_reference_text` carry no port text at all (`/page.column` only) -- asserting a
    # negative there would not exercise anything this decision changed.
    tag_text, marking_text = _terminal_labels()
    assert tag_text == "-X1:L1:1"
    assert marking_text == "external"


def _terminal_labels() -> tuple[str, str]:
    """A second, minimal model: strip `X1`, terminal `L1:1`, read through `label_text`."""
    origin = Origin(file="test_port_text_format_model.py", line=1, note="fixture")
    draft = Draft()
    sheet = SheetFormat(
        id=Id(kind="layout.sheet_format", value="1" * 32),
        key=("sheet",),
        name="test sheet",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=257,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal(2),
    )
    drawing_set = DrawingSet(
        id=Id(kind="layout.drawing_set", value="2" * 32),
        key=("ds",),
        location=None,
        number=1,
        produced_by="test-engine 0.0.0",
    )
    page = Page(
        id=Id(kind="layout.page", value="3" * 32),
        key=("page",),
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=sheet.id,
        groups=(),
        produced_by="test-engine 0.0.0",
    )
    strip = Item(
        id=Id(kind="item", value="4" * 32),
        key=("x1",),
        part=None,
        parent=None,
        position=None,
        tag="X1",
        description="Invented",
    )
    terminal = Item(
        id=Id(kind="item", value="5" * 32),
        key=("x1", "l1-1"),
        part=None,
        parent=strip.id,
        position=None,
        tag=None,
        description="Invented",
    )
    function = Function(
        id=Id(kind="function", value="6" * 32),
        key=("x1", "l1-1", "terminal"),
        item=terminal.id,
        template=None,
        name="terminal",
        kind=FunctionKind.TERMINAL,
    )
    facet = TerminalFacet(
        id=Id(kind="facet.terminal", value="7" * 32),
        key=("x1", "l1-1", "facet"),
        subject=terminal.id,
        group="L1",
        index=1,
    )
    internal = Port(
        id=Id(kind="port", value="8" * 32),
        key=("x1", "l1-1", "internal"),
        function=function.id,
        template=None,
        name="internal",
        role=PortRole.INTERNAL,
    )
    external = Port(
        id=Id(kind="port", value="9" * 32),
        key=("x1", "l1-1", "external"),
        function=function.id,
        template=None,
        name="external",
        role=PortRole.EXTERNAL,
    )
    for record in (sheet, drawing_set, page, strip, terminal, function, facet, internal, external):
        draft.add(record, origin=origin)
    model = freeze(draft)

    tag = Label(
        id=Id(kind="layout.label", value="a" * 32),
        key=("tag",),
        page=page.id,
        function=function.id,
        port=None,
        conductor=None,
        kind=LabelKind.TAG,
        slot="tag",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by="test-engine 0.0.0",
    )
    marking = Label(
        id=Id(kind="layout.label", value="b" * 32),
        key=("marking",),
        page=page.id,
        function=None,
        port=external.id,
        conductor=None,
        kind=LabelKind.MARKING,
        slot="marking",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by="test-engine 0.0.0",
    )
    return label_text(model, tag), label_text(model, marking)
