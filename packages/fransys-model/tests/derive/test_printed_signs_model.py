"""Acceptance test for decision model-0054: every designation a list prints carries its sign.

One small model -- a terminal strip, a relay, a board with a component inside a nested unit,
a PLC channel bound to a field device, a mate between connectors, a wire-labelled conductor
-- read through every list-row query. Each designation-typed field must start with `-`, `+`
or `=`; a bare tag (`K1`, `A1:1`) is the defect.
"""

import dataclasses
from typing import Any

import pytest
from connector_builders import make_connector
from plant import Plant
from query_builders import (
    bind_device,
    make_core,
    make_labelled,
    make_part,
    make_pin,
    make_strip,
    make_terminal,
)
from rack_builders import make_module

from fransys_model.derive import (
    TOP_LEVEL,
    bom_lines,
    connector_rows,
    designation_list,
    overview_graph,
    plc_channel_rows,
    plc_rack_modules,
    terminal_rows,
    wire_rows,
)
from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import SignalType

SIGNS = ("-", "+", "=")
LISTS = (
    "bom",
    "bom_top_level",
    "bom_unit",
    "plc_channels",
    "plc_rack",
    "designation_list",
    "connectors",
    "wire_labels",
    "terminals",
    "overview",
)


def _with_part(plant: Plant, item_id: Id[Item], part_id: Id[Any]) -> None:
    """Give an already-added item a `part` (records are frozen)."""
    at = next(n for n, record in enumerate(plant.records) if record.id == item_id)
    plant.records[at] = dataclasses.replace(plant.records[at], part=part_id)


def _plant() -> Plant:
    """The plant: strip `X1`, nested unit `inner` with board `U2`, rack `R1`, board `A9`."""
    plant = Plant()
    top = plant.unit("top", name="cabinet")
    inner = plant.unit("inner", name="relay-board", parent=top)
    relay = make_part(plant, "relay", "R-1")
    board = plant.item("board", part=plant.board_part(), designation="U2", unit=inner)
    plant.item("k2", parent=board, part=relay, designation="K2", unit=inner)
    plant.item("k5", part=relay, designation="K5", unit=top)

    _, terminals = make_strip(plant)
    term_part = make_part(plant, "term", "T-1")
    for terminal in terminals:
        _with_part(plant, terminal.item, term_part)

    rack = plant.item("rack", designation="R1")
    _, channels = make_module(
        plant, rack, "m-1", part="di", signals=(SignalType.DI,), position=1, designation="A1"
    )
    device = bind_device(plant, "dev", "B7", channels[0])
    plant.item("x2", designation="X2")
    field_terminal = make_terminal(plant, "x2", "t1", group="S", index=1)
    plant.wire(plant.port(device, "1"), field_terminal.external, key="dev-wire")
    plant.wire(plant.port(channels[0], "1"), field_terminal.internal, key="channel-wire")

    cboard = plant.item("cboard", designation="A9")
    for key, designation in (("j1", "J1"), ("p1", "P1"), ("jb1", "JB1")):
        plant.item(key, parent=cboard, designation=designation)
    j1, _ = make_connector(plant, ("j1", "x"), ("1", "2"))
    p1, _ = make_connector(plant, ("p1", "x"), ("1",))
    make_connector(plant, ("jb1", "J1"), ("1",))
    make_connector(plant, ("jb1", "J3"), ("1",))
    plant.mate(j1, p1)

    make_labelled(plant, "lab", make_pin(plant, "la", "B3"), make_pin(plant, "lb", "B4"), "W1-1")
    return plant


def _model() -> Model:
    """The model of `_plant`."""
    return _plant().model()


def _overview_model() -> Model:
    """`_plant` plus a cable `W1` carrying one core, and an item with no designation yet."""
    plant = _plant()
    cable = plant.item("w1", designation="W1")
    ends = (make_pin(plant, "oa", "OA1"), make_pin(plant, "ob", "OB1"))
    make_core(plant, "core", cable, ends, index=1)
    plant.item("bare", designation=None)
    return plant.model()


def _all_texts() -> dict[str, list[str]]:
    """`_texts` of the list model, with the overview read from its own model."""
    return _texts(_model(), _overview_model())


def _texts(model: Model, overview: Model) -> dict[str, list[str]]:
    """Every designation-typed field each list prints, by list name (`overview`: its graph's)."""
    found: dict[str, list[str]] = {name: [] for name in LISTS}
    graph = overview_graph(overview)
    found["overview"] += [node.designation for node in graph.nodes if node.designation is not None]
    found["overview"] += [
        link.via_designation for link in graph.links if link.via_designation is not None
    ]
    top, inner = make_id(Unit, ("top",)), make_id(Unit, ("inner",))
    for key, lines in (
        ("bom", bom_lines(model)),
        ("bom_top_level", bom_lines(model, TOP_LEVEL)),
        ("bom_unit", bom_lines(model, inner) + bom_lines(model, top)),
    ):
        found[key] += [text for line in lines for text in line.designations]
    for plc in plc_channel_rows(model):
        found["plc_channels"] += [plc.channel_designation]
        found["plc_channels"] += [
            text for text in (plc.field_device_designation, plc.wired_to) if text is not None
        ]
    for module in plc_rack_modules(model, make_id(Item, ("rack",))):
        found["plc_rack"] += [module.designation]
        found["plc_rack"] += [
            channel.field_device_designation
            for channel in module.channels
            if channel.field_device_designation is not None
        ]
    for row in designation_list(model):
        found["designation_list"] += [row.designation, row.reference]
    for connector in connector_rows(model, make_id(Item, ("cboard",))):
        found["connectors"] += [connector.designation]
        if connector.mate_designation is not None:
            found["connectors"] += [connector.mate_designation]
        found["connectors"] += [
            pin.mate_port_designation for pin in connector.pins if pin.mate_port_designation
        ]
    for wire in wire_rows(model):
        found["wire_labels"] += [wire.from_, wire.to]
    for terminal in terminal_rows(model, make_id(Item, ("x1",))):
        found["terminals"] += [
            terminal.designation,
            *terminal.internal_ends,
            *terminal.external_ends,
        ]
    return found


def _unsigned(texts: list[str]) -> list[str]:
    """The texts that do not start with a sign."""
    return [text for text in texts if not text.startswith(SIGNS)]


@pytest.mark.parametrize("name", LISTS)
def test_every_designation_a_list_prints_carries_its_sign(name: str) -> None:
    """No field of any list-row query prints a bare tag; each list has fields to check."""
    texts = _all_texts()[name]
    assert len(texts) >= 2
    assert _unsigned(texts) == []


def test_the_overview_signs_a_cable_and_a_terminal_and_keeps_none_for_an_unnumbered_item() -> None:
    """A cable link and a strip terminal read signed; the unnumbered item stays `None`."""
    graph = overview_graph(_overview_model())
    assert [link.via_designation for link in graph.links if link.via is not None] == ["-W1"]
    designations = {node.item: node.designation for node in graph.nodes}
    assert designations[make_id(Item, ("bare",))] is None
    assert "-X1:L:1" in designations.values()
    assert "-U2-K2" in designations.values()


def test_the_fields_the_ruling_names_read_as_written() -> None:
    """The ruling's own examples: `-K5`, `-U2`, `-U2-K2`, `-B7`, `-A1:1`, `-J1`, `-JB1-J1`."""
    texts = _all_texts()
    assert {"-K5", "-U2", "-U2-K2"} <= set(texts["bom"])
    assert "-U2" in texts["bom_unit"]
    assert {"-A1:1", "-B7"} <= set(texts["plc_channels"])
    assert {"-A1", "-B7"} <= set(texts["plc_rack"])
    assert {"-J1", "-P1", "-JB1-J1", "-JB1-J3"} <= set(texts["connectors"])


def test_the_checker_can_fail_on_a_bare_tag() -> None:
    """Can-fail twin of the sign check: it reports a bare tag among signed ones."""
    assert _unsigned(["-K1", "K2", "+C1", "=A1", "A1:1"]) == ["K2", "A1:1"]
