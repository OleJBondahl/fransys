"""Tests: `check_plc_wiring`, a binding against the wiring (decision model-0068)."""

from typing import TYPE_CHECKING

from plant import Plant
from query_builders import make_channels

from fransys_model.kernel import Id, make_id
from fransys_model.vocab.enums import LinkKind, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.validators.plc import check_plc_wiring

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function, Port


def _channel(plant: Plant, name: str) -> tuple[Id[Function], Id[Port]]:
    """A one-channel DI module and its channel function's pin."""
    (channel,) = make_channels(plant, name, None, (SignalType.DI,))
    return channel, plant.port(channel, "1")


def _bare_request(plant: Plant, name: str) -> Id[Function]:
    """A DI request function with no port."""
    function = plant.function(plant.item(name), "fn")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, (name, "request")),
            key=(name, "request"),
            subject=function,
            signal=SignalType.DI,
            signal_name=name,
            priority=1,
        )
    )
    return function


def _request(plant: Plant, name: str) -> tuple[Id[Function], Id[Port]]:
    """A DI request function and its pin."""
    function = _bare_request(plant, name)
    return function, plant.port(function, "1")


def _bind(plant: Plant, request: Id[Function], channel: Id[Function]) -> Id[PlcBindingFacet]:
    binding = PlcBindingFacet(
        id=make_id(PlcBindingFacet, ("bind", request.value)),
        key=("bind", request.value),
        subject=request,
        channel=channel,
    )
    plant.add(binding)
    return binding.id


def _terminal(plant: Plant) -> tuple[Id[Port], Id[Port]]:
    """A terminal whose internal and external ports a conductive link joins."""
    part, template, pin1, pin2 = plant.relay_part()
    plant.link(pin1, pin2, LinkKind.CONDUCTIVE)
    function = plant.function(plant.item("x1", part=part.id), "fn", template=template.id)
    return (
        plant.port(function, "1", template=pin1.id),
        plant.port(function, "2", template=pin2.id),
    )


def test_several_wired_devices_are_sorted_and_joined_with_a_comma() -> None:
    """Created `z` first: the message still lists `y/fn, z/fn`."""
    plant = Plant()
    bound, bound_pin = _channel(plant, "mod-a")
    request, _ = _request(plant, "sensor")
    _, pin_z = _request(plant, "z")
    _, pin_y = _request(plant, "y")
    _bind(plant, request, bound)
    plant.wire(bound_pin, pin_z, key="w-z")
    plant.wire(bound_pin, pin_y, key="w-y")
    (finding,) = check_plc_wiring(plant.model())
    assert finding.message == (
        "channel mod-a/ch1 is wired to y/fn, z/fn but bound to request sensor/fn"
    )
