"""WP13 tests: `check_plc_wiring`, a binding against the wiring (decision model-0068)."""

import dataclasses
import re
from typing import TYPE_CHECKING

from plant import Plant
from query_builders import make_channels

from fransys_model.kernel import Id, Model, Severity, make_id
from fransys_model.vocab import ALL_VALIDATORS
from fransys_model.vocab.enums import LinkKind, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.validators.plc import PLC_BINDING_WIRING_MISMATCH, check_plc_wiring

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


def test_a_request_wired_to_another_channel_than_its_bound_one_is_an_error() -> None:
    """Rule (i): wired to channel B, bound to channel A; the message names both channels."""
    plant = Plant()
    bound, _ = _channel(plant, "mod-a")
    _, wired_pin = _channel(plant, "mod-b")
    request, request_pin = _request(plant, "sensor")
    binding = _bind(plant, request, bound)
    plant.wire(request_pin, wired_pin, key="w")
    (finding,) = check_plc_wiring(plant.model())
    assert (finding.code, finding.severity) == (PLC_BINDING_WIRING_MISMATCH, Severity.ERROR)
    assert finding.subjects == tuple(sorted((binding, request, bound)))
    assert finding.message == (
        "sensor/fn is wired to channel mod-b/ch1 but bound to channel mod-a/ch1"
    )


def test_a_bound_channel_wired_to_another_device_than_its_bound_one_is_an_error() -> None:
    """Rule (ii): the bound request is unwired, the channel's pin goes to another device."""
    plant = Plant()
    bound, bound_pin = _channel(plant, "mod-a")
    request, _ = _request(plant, "sensor")
    _, other_pin = _request(plant, "other")
    _bind(plant, request, bound)
    plant.wire(bound_pin, other_pin, key="w")
    (finding,) = check_plc_wiring(plant.model())
    assert finding.code == PLC_BINDING_WIRING_MISMATCH
    assert (
        finding.message == "channel mod-a/ch1 is wired to other/fn but bound to request sensor/fn"
    )


def test_a_swapped_pair_gives_one_finding_per_rule_per_binding() -> None:
    """Each of the two bindings breaks both rules, and each message names its own sides."""
    plant = Plant()
    (channel_a, pin_a), (channel_b, pin_b) = _channel(plant, "mod-a"), _channel(plant, "mod-b")
    (request_x, pin_x), (request_y, pin_y) = _request(plant, "x"), _request(plant, "y")
    _bind(plant, request_x, channel_b)
    _bind(plant, request_y, channel_a)
    plant.wire(pin_x, pin_a, key="wx")
    plant.wire(pin_y, pin_b, key="wy")
    findings = check_plc_wiring(plant.model())
    assert sorted(f.message for f in findings) == sorted(
        [
            "x/fn is wired to channel mod-a/ch1 but bound to channel mod-b/ch1",
            "channel mod-b/ch1 is wired to y/fn but bound to request x/fn",
            "y/fn is wired to channel mod-b/ch1 but bound to channel mod-a/ch1",
            "channel mod-a/ch1 is wired to x/fn but bound to request y/fn",
        ]
    )


def test_an_unwired_request_gives_nothing() -> None:
    """A half-finished design still builds: the channel's side is unwired too."""
    plant = Plant()
    channel, _ = _channel(plant, "mod-a")
    request, _ = _request(plant, "sensor")
    _bind(plant, request, channel)
    assert check_plc_wiring(plant.model()) == ()


def test_an_unwired_channel_gives_nothing_even_when_the_request_is_wired_elsewhere() -> None:
    """The request is wired to a plain part, not to a channel; the channel's pin is bare."""
    plant = Plant()
    channel, _ = _channel(plant, "mod-a")
    request, request_pin = _request(plant, "sensor")
    _bind(plant, request, channel)
    plant.wire(request_pin, plant.pin("plain", "fn", "1"), key="w")
    assert check_plc_wiring(plant.model()) == ()


def test_a_correctly_wired_binding_gives_nothing() -> None:
    """The request's pin is wired to the bound channel's pin."""
    plant = Plant()
    channel, channel_pin = _channel(plant, "mod-a")
    request, request_pin = _request(plant, "sensor")
    _bind(plant, request, channel)
    plant.wire(request_pin, channel_pin, key="w")
    assert check_plc_wiring(plant.model()) == ()


def test_a_request_wired_to_several_channels_including_the_bound_one_gives_nothing() -> None:
    """The bound channel is among the wired ones: not a disagreement."""
    plant = Plant()
    channel, channel_pin = _channel(plant, "mod-a")
    _, other_pin = _channel(plant, "mod-b")
    request, request_pin = _request(plant, "sensor")
    _bind(plant, request, channel)
    plant.wire(request_pin, channel_pin, key="w1")
    plant.wire(request_pin, other_pin, key="w2")
    assert check_plc_wiring(plant.model()) == ()


def _through_terminal(*, bound_is_wired: bool) -> tuple[Model, Id[Function], Id[Function]]:
    """Request pin to a terminal's external port, its internal port to channel B's pin."""
    plant = Plant()
    wired, wired_pin = _channel(plant, "mod-b")
    other, _ = _channel(plant, "mod-a")
    request, request_pin = _request(plant, "sensor")
    internal, external = _terminal(plant)
    plant.wire(request_pin, external, key="w-out")
    plant.wire(internal, wired_pin, key="w-in")
    bound = wired if bound_is_wired else other
    _bind(plant, request, bound)
    return plant.model(), request, bound


def test_wiring_through_a_terminal_counts_when_the_binding_agrees() -> None:
    """The conductive link between the terminal's ports joins the two conductors."""
    model, _, _ = _through_terminal(bound_is_wired=True)
    assert check_plc_wiring(model) == ()


def test_wiring_through_a_terminal_counts_when_the_binding_disagrees() -> None:
    """Bound to channel A while the terminal leads to channel B: rule (i)."""
    model, request, _ = _through_terminal(bound_is_wired=False)
    (finding,) = check_plc_wiring(model)
    assert request in finding.subjects
    assert "mod-b/ch1" in finding.message


def _through_mate(*, bound_is_wired: bool) -> Model:
    """The request function is mated to a plug whose port `1` is wired to channel B's pin."""
    plant = Plant()
    wired, wired_pin = _channel(plant, "mod-b")
    other, _ = _channel(plant, "mod-a")
    request, _ = _request(plant, "sensor")
    plug = plant.function(plant.item("plug"), "fn")
    plant.wire(plant.port(plug, "1"), wired_pin, key="w")
    plant.mate(request, plug)
    _bind(plant, request, wired if bound_is_wired else other)
    return plant.model()


def test_wiring_through_a_mate_counts_when_the_binding_agrees() -> None:
    """Ports of equal name on mated functions are one net."""
    assert check_plc_wiring(_through_mate(bound_is_wired=True)) == ()


def test_wiring_through_a_mate_counts_when_the_binding_disagrees() -> None:
    """Bound to channel A while the mated plug leads to channel B: rule (i)."""
    (finding,) = check_plc_wiring(_through_mate(bound_is_wired=False))
    assert finding.code == PLC_BINDING_WIRING_MISMATCH
    assert "mod-b/ch1" in finding.message


def test_a_binding_on_a_function_with_no_request_gives_nothing() -> None:
    """Nothing says what was asked, so the wiring has nothing to disagree with."""
    plant = Plant()
    channel_a, _ = _channel(plant, "mod-a")
    _, pin_b = _channel(plant, "mod-b")
    function = plant.function(plant.item("orphan"), "fn")
    plant.wire(plant.port(function, "1"), pin_b, key="w")
    _bind(plant, function, channel_a)
    assert check_plc_wiring(plant.model()) == ()


def _rotated_model() -> Model:
    """Three devices, each wired to its own channel and bound to the next one's."""
    plant = Plant()
    channels = [_channel(plant, f"mod-{n}") for n in range(3)]
    for number in range(3):
        request, request_pin = _request(plant, f"dev-{number}")
        plant.wire(request_pin, channels[number][1], key=f"w{number}")
        _bind(plant, request, channels[(number + 1) % 3][0])
    return plant.model()


def test_findings_are_sorted_and_independent_of_table_order() -> None:
    """Sorted by `(code, subjects, message)`, the same with tables backwards."""
    model = _rotated_model()
    findings = check_plc_wiring(model)
    assert len(findings) == 6
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    backwards: Model = dataclasses.replace(
        model,
        digest="reversed-tables-test-plc-wiring-findings",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert check_plc_wiring(backwards) == findings


def test_no_message_prints_an_id() -> None:
    """Messages name function keys."""
    findings = check_plc_wiring(_rotated_model())
    assert findings
    for finding in findings:
        assert not re.search(r"[0-9a-f]{32}", finding.message)


def test_an_empty_model_has_no_finding() -> None:
    """Nothing bound."""
    assert check_plc_wiring(Plant().model()) == ()


def test_a_channel_wired_to_several_devices_including_the_bound_one_gives_nothing() -> None:
    """Rule (ii): the bound request is among the wired devices."""
    plant = Plant()
    channel, channel_pin = _channel(plant, "mod-a")
    request, request_pin = _request(plant, "sensor")
    _, other_pin = _request(plant, "other")
    _bind(plant, request, channel)
    plant.wire(channel_pin, request_pin, key="w1")
    plant.wire(channel_pin, other_pin, key="w2")
    assert check_plc_wiring(plant.model()) == ()


def test_several_wired_channels_are_sorted_and_joined_with_a_comma() -> None:
    """Created `mod-c` first: the message still lists `mod-b/ch1, mod-c/ch1`."""
    plant = Plant()
    bound, _ = _channel(plant, "mod-a")
    _, pin_c = _channel(plant, "mod-c")
    _, pin_b = _channel(plant, "mod-b")
    request, request_pin = _request(plant, "sensor")
    _bind(plant, request, bound)
    plant.wire(request_pin, pin_c, key="w-c")
    plant.wire(request_pin, pin_b, key="w-b")
    (finding,) = check_plc_wiring(plant.model())
    assert finding.message == (
        "sensor/fn is wired to channel mod-b/ch1, mod-c/ch1 but bound to channel mod-a/ch1"
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


def test_a_channel_wired_to_another_device_through_a_terminal_is_an_error() -> None:
    """Rule (ii) through a terminal: channel pin to the internal port, device at the external."""
    plant = Plant()
    bound, bound_pin = _channel(plant, "mod-a")
    request, _ = _request(plant, "sensor")
    _, other_pin = _request(plant, "other")
    internal, external = _terminal(plant)
    _bind(plant, request, bound)
    plant.wire(bound_pin, internal, key="w-in")
    plant.wire(external, other_pin, key="w-out")
    (finding,) = check_plc_wiring(plant.model())
    assert (
        finding.message == "channel mod-a/ch1 is wired to other/fn but bound to request sensor/fn"
    )


def test_a_channel_wired_to_another_device_through_a_mate_is_an_error() -> None:
    """Rule (ii) through a mate: the channel pin goes to a plug mated to the other device."""
    plant = Plant()
    bound, bound_pin = _channel(plant, "mod-a")
    request, _ = _request(plant, "sensor")
    other, _ = _request(plant, "other")
    plug = plant.function(plant.item("plug"), "fn")
    plant.wire(bound_pin, plant.port(plug, "1"), key="w")
    plant.mate(other, plug)
    _bind(plant, request, bound)
    (finding,) = check_plc_wiring(plant.model())
    assert (
        finding.message == "channel mod-a/ch1 is wired to other/fn but bound to request sensor/fn"
    )


def test_a_request_and_a_channel_without_ports_give_nothing() -> None:
    """Nothing can be wired to a function that has no port."""
    plant = Plant()
    (channel,) = make_channels(plant, "mod-a", None, (SignalType.DI,))
    _bind(plant, _bare_request(plant, "sensor"), channel)
    assert check_plc_wiring(plant.model()) == ()


def _dual_function(plant: Plant) -> tuple[Id[Function], Id[Port]]:
    """A channel function that also carries a `plc_request`, and its pin."""
    (dual,) = make_channels(plant, "mod-f", None, (SignalType.DI,))
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, ("mod-f", "request")),
            key=("mod-f", "request"),
            subject=dual,
            signal=SignalType.DI,
            signal_name="mod-f",
            priority=1,
        )
    )
    return dual, plant.port(dual, "1")


def test_a_function_that_is_both_request_and_channel_is_not_wired_to_itself() -> None:
    """Its own port is on its own net: nothing wired means nothing to say."""
    plant = Plant()
    dual, _ = _dual_function(plant)
    channel, _ = _channel(plant, "mod-c")
    _bind(plant, dual, channel)
    assert check_plc_wiring(plant.model()) == ()


def test_a_function_that_is_both_request_and_channel_is_checked_against_other_wiring() -> None:
    """Wired to channel D while bound to channel C: rule (i), naming D and not itself."""
    plant = Plant()
    dual, dual_pin = _dual_function(plant)
    channel, _ = _channel(plant, "mod-c")
    _, wired_pin = _channel(plant, "mod-d")
    _bind(plant, dual, channel)
    plant.wire(dual_pin, wired_pin, key="w")
    (finding,) = check_plc_wiring(plant.model())
    assert finding.message == (
        "mod-f/ch1 is wired to channel mod-d/ch1 but bound to channel mod-c/ch1"
    )


def test_the_wiring_check_is_one_of_all_validators() -> None:
    """A caller running every validator sees the finding."""
    assert check_plc_wiring in ALL_VALIDATORS
