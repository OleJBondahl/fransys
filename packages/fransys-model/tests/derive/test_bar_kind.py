"""A conductor bar: its `ItemKind`, `bar_items` and `is_bar_port` (PE-BAR B1)."""

from typing import Any

from plant import Plant

from fransys_model.checks import ALL_VALIDATORS
from fransys_model.derive import ItemKind, item_kind, port_designation
from fransys_model.derive.facts.bars import bar_items, is_bar_port
from fransys_model.kernel import Id, Model, Severity, make_id
from fransys_model.vocab.core import Function, Port
from fransys_model.vocab.enums import FunctionKind, PortRole
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import ports


def _pe_port(plant: Plant, function: Id[Function], name: str) -> Id[Port]:
    """One bar screw: a port of role `pe` (`Plant.port` writes `generic`)."""
    key = ("pe-bar", "pe", name)
    port = Port(
        id=make_id(Port, key),
        key=key,
        function=function,
        template=None,
        name=name,
        role=PortRole.PE,
    )
    plant.add(port)
    return port.id


def _model_with_bar(bar_ports: int) -> tuple[Model, dict[str, Any]]:
    """A PE bar with `bar_ports` ports, a device with a coil and a strip's one terminal."""
    plant = Plant()
    bar = plant.item("pe-bar", designation="PE1")
    bar_fn = plant.function(bar, "pe", kind=FunctionKind.BAR)
    screws = [_pe_port(plant, bar_fn, str(n)) for n in range(1, bar_ports + 1)]
    bar_port = screws[0] if screws else None
    device = plant.item("k1", designation="K1")
    device_port = plant.port(plant.function(device, "coil", kind=FunctionKind.COIL), "a1")
    strip = plant.item("strip", designation="X1")
    terminal = plant.item("strip-t1", parent=strip, part=plant.part("X"))
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("strip", "1")),
            key=("strip", "1"),
            subject=terminal,
            group="",
            index=1,
        )
    )
    return plant.model(), {
        "bar": bar,
        "device": device,
        "terminal": terminal,
        "bar_port": bar_port,
        "device_port": device_port,
    }


def test_each_item_reads_its_own_kind() -> None:
    """The bar is a BAR, the device stays a DEVICE, and a strip's terminal is still a TERMINAL."""
    model, named = _model_with_bar(bar_ports=20)
    assert item_kind(model, named["bar"]) is ItemKind.BAR
    assert item_kind(model, named["device"]) is ItemKind.DEVICE
    assert item_kind(model, named["terminal"]) is ItemKind.TERMINAL


def test_bar_items_holds_the_bar_and_not_the_device() -> None:
    """`bar_items` is exactly the items holding a BAR function."""
    model, named = _model_with_bar(bar_ports=20)
    assert bar_items(model) == {named["bar"]}
    assert named["device"] not in bar_items(model)


def test_is_bar_port_follows_the_function_kind() -> None:
    """A port of the bar's function is a bar port; a port of the coil is not."""
    model, named = _model_with_bar(bar_ports=20)
    assert is_bar_port(model, named["bar_port"])
    assert not is_bar_port(model, named["device_port"])


def test_a_cut_to_length_bar_with_no_ports_is_accepted() -> None:
    """A bar with no port freezes and raises no ERROR; its kind is still BAR."""
    model, named = _model_with_bar(bar_ports=0)
    assert item_kind(model, named["bar"]) is ItemKind.BAR
    errors = [f for check in ALL_VALIDATORS for f in check(model) if f.severity is Severity.ERROR]
    assert errors == []


def test_a_bar_port_prints_the_bar_alone_and_a_device_port_its_name() -> None:
    """B4: every screw of the bar prints `-PE1`; a device port still prints `-K1:a1`."""
    model, named = _model_with_bar(bar_ports=3)
    screws = [p for p in ports(model) if is_bar_port(model, p)]
    assert len(screws) == 3
    assert {port_designation(model, screw) for screw in screws} == {"-PE1"}
    assert port_designation(model, named["device_port"]) == "-K1:a1"
