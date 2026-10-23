"""The facts behind the PLC and rating checks (EL-4)."""

from decimal import Decimal
from typing import TYPE_CHECKING

from current_plant import device, fuse, wire
from plant import Plant
from query_builders import make_channels
from rating_plant import rail, supply

from fransys_model.derive.facts.current.load_limits import bounded_loads
from fransys_model.derive.facts.current.worst import worst_bounds
from fransys_model.derive.facts.plc_wiring import (
    binding_wiring,
    channel_functions,
    plc_requests,
    request_functions,
)
from fransys_model.derive.facts.rail_reach import function_reach
from fransys_model.derive.facts.roles import function_channel
from fransys_model.kernel import make_id
from fransys_model.vocab import Operating, OperatingFacet
from fransys_model.vocab.enums import Current, FunctionKind, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.templates import FunctionTemplate

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function


def _request(plant: Plant, name: str) -> tuple:
    function = plant.function(plant.item(name), "fn")
    key = (name, "request")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, key),
            key=key,
            subject=function,
            signal=SignalType.DI,
            signal_name=name,
            priority=1,
        )
    )
    return function, plant.port(function, "1")


def _bind(plant: Plant, request: Id[Function], channel: Id[Function]) -> None:
    key = ("bind", request.value)
    plant.add(
        PlcBindingFacet(id=make_id(PlcBindingFacet, key), key=key, subject=request, channel=channel)
    )


def _plc_plant() -> tuple:
    plant = Plant()
    (channel,) = make_channels(plant, "mod", None, (SignalType.DI,))
    request, _ = _request(plant, "sensor")
    other, other_pin = _request(plant, "other")
    _bind(plant, request, channel)
    plant.wire(plant.port(channel, "1"), other_pin, key="w")
    return plant, request, channel, other


def test_function_channel_is_the_facet_of_a_channel_template_only() -> None:
    plant, request, channel, _ = _plc_plant()
    model = plant.model()
    found = function_channel(model, channel)
    assert found is not None
    assert found.signal is SignalType.DI
    assert function_channel(model, request) is None


def test_requests_and_channels_are_told_apart() -> None:
    plant, request, channel, other = _plc_plant()
    model = plant.model()
    assert set(plc_requests(model)) == {request, other}
    assert request_functions(model) == {request, other}
    assert channel_functions(model) == {channel}


def test_binding_wiring_names_the_request_wired_to_the_bound_channel() -> None:
    plant, request, channel, other = _plc_plant()
    model = plant.model()
    (binding,) = facets_of(model, PlcBindingFacet).values()
    assert binding_wiring(model, binding) == (frozenset(), frozenset({other}))
    assert request not in binding_wiring(model, binding)[1]
    assert channel not in binding_wiring(model, binding)[0]


def _dc_loop() -> Model:
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("24"), "DC-": rail("0")}, current=Current.DC)
    source = device(plant, "S", limit="186", kind=FunctionKind.SUPPLY, rails=[["DC+"], ["DC-"]])
    protection = fuse(plant, "F", "2")
    load = device(plant, "D", amps="3", kind=FunctionKind.LOAD, rails=[[], []])
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], load[0])
    wire(plant, load[1], source[1])
    plant.add(
        OperatingFacet(
            id=make_id(OperatingFacet, ("Dn",)),
            key=("Dn",),
            subject=make_id(FunctionTemplate, ("D", "f")),
            operating=Operating(nominal_current_a=Decimal("2.5")),
        )
    )
    return plant.model()


def test_function_reach_stands_on_the_rails_of_its_ports() -> None:
    model = _dc_loop()
    reach = function_reach(model, Plant.function_id("S", "f"))
    assert reach.stands(ac=True) is None
    stands = reach.stands(ac=False)
    assert stands is not None
    (stand,) = stands
    assert {r.name for r in stand.rails} <= {"DC+", "DC-"}


def test_worst_bounds_and_bounded_loads_pair_a_function_with_its_limit() -> None:
    model = _dc_loop()
    load = Plant.function_id("D", "f")
    assert worst_bounds(model)[load, Current.DC].value == Decimal(2)
    pairs = bounded_loads(model)
    ((entry, bound),) = pairs
    assert entry.draw_a == Decimal("2.5")
    assert bound is entry.bound
    assert bound.value == Decimal(2)
