"""Tests: `check_plc_wiring`, a binding against the wiring (decision model-0068)."""

from typing import TYPE_CHECKING

from plant import Plant
from query_builders import make_channels

from fransys_model.checks.plc import PLC_SIGNAL_NAME_TWICE, check_plc_names, check_plc_wiring
from fransys_model.elecdef import LinkKind
from fransys_model.kernel import Id, Severity, make_id, natural_join
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import facets_of, functions
from fransys_model.vocab.templates import FunctionTemplate, Part

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function, Item, Port


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
    """The message names both devices and the channel by reference, never by key."""
    plant = Plant()
    bound, bound_pin = _channel(plant, "mod-a")
    request, _ = _request(plant, "sensor")
    fn_z, pin_z = _request(plant, "z")
    fn_y, pin_y = _request(plant, "y")
    _bind(plant, request, bound)
    plant.wire(bound_pin, pin_z, key="w-z")
    plant.wire(bound_pin, pin_y, key="w-y")
    (finding,) = check_plc_wiring(plant.model())
    assert finding.message == (f"channel {ref(bound)} is wired to {natural_join([ref(fn_y), ref(fn_z)])} but bound to request {ref(request)}")
    assert "/" not in finding.message


def _named_request(plant: Plant, key: str, name: str | None, *, signal: SignalType | None = SignalType.DI) -> Id[Function]:
    """A function with a `plc_request`: a device's (a `signal`) or a spare channel's settings (`signal=None`)."""
    function = plant.function(plant.item(key), "fn")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, (key, "request")), key=(key, "request"), subject=function, signal=signal, signal_name=name, priority=1
        )
    )
    return function


def _bound_in(plant: Plant, rack: Id[Item], key: str, name: str) -> Id[Function]:
    """A device named `name`, bound to the one channel of a DI module under `rack`."""
    part = Part(
        id=make_id(Part, (key, "part")),
        key=(key, "part"),
        mpn=f"EXAMPLE-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    template = FunctionTemplate(id=make_id(FunctionTemplate, (key, "ch")), key=(key, "ch"), part=part.id, name="ch1", kind=FunctionKind.PLC_CHANNEL)
    facet = PlcChannelFacet(id=make_id(PlcChannelFacet, (key, "facet")), key=(key, "facet"), subject=template.id, signal=SignalType.DI, channel=1)
    plant.add(part, template, facet)
    channel = plant.function(plant.item(key, parent=rack, part=part.id), "ch1", template=template.id)
    device = _named_request(plant, f"dev-{key}", name)
    _bind(plant, device, channel)
    return device


def test_two_devices_of_one_controller_with_one_signal_name_are_refused_naming_both() -> None:
    plant = Plant()
    rack = plant.item("rack")
    first, second = _bound_in(plant, rack, "a", "Door"), _bound_in(plant, rack, "b", "Door")
    (found,) = check_plc_names(plant.model())
    assert (found.code, found.severity) == (PLC_SIGNAL_NAME_TWICE, Severity.ERROR)
    model = plant.model()
    bound = {b.subject: b.channel for b in facets_of(model, PlcBindingFacet).values()}
    for device in (first, second):
        channel = bound[device]
        assert f"channel {ref(channel)} of module {ref(functions(model)[channel].item)} (device {ref(device)})" in found.message
    assert "rename one with .plc(signal, name)" in found.message


def test_one_signal_name_on_two_controllers_is_allowed() -> None:
    plant = Plant()
    _bound_in(plant, plant.item("rack-1"), "a", "Door")
    _bound_in(plant, plant.item("rack-2"), "b", "Door")
    assert check_plc_names(plant.model()) == ()


def test_a_spare_channels_name_is_no_signal_name_and_may_repeat() -> None:
    plant = Plant()
    rack = plant.item("rack")
    _bound_in(plant, rack, "a", "Door")
    _named_request(plant, "s1", "unused", signal=None)
    _named_request(plant, "s2", "unused", signal=None)
    assert check_plc_names(plant.model()) == ()
