"""WP13 tests: `check_plc`, the signal of a binding against its request (design/facets.md)."""

import dataclasses
import re
from typing import TYPE_CHECKING, Any

from plant import Plant

from fransys_model.kernel import Id, Model, Severity, make_id
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.templates import FunctionTemplate, Part
from fransys_model.vocab.validators.plc import PLC_BINDING_SIGNAL_MISMATCH, check_plc

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function


def _module(plant: Plant, name: str, signal: SignalType | None) -> Id[Function]:
    """A module channel: a part, a template, a function; `plc_channel` unless `signal` is None."""
    part = Part(
        id=make_id(Part, (name,)),
        key=(name,),
        mpn=f"EXAMPLE-{name}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (name, "ch")),
        key=(name, "ch"),
        part=part.id,
        name="ch",
        kind=FunctionKind.PLC_CHANNEL,
    )
    plant.add(part, template)
    if signal is not None:
        plant.add(
            PlcChannelFacet(
                id=make_id(PlcChannelFacet, (name, "channel")),
                key=(name, "channel"),
                subject=template.id,
                signal=signal,
                channel=1,
            )
        )
    return plant.function(plant.item(name, part=part.id), "ch", template=template.id)


def _request(plant: Plant, name: str, signal: SignalType) -> Id[Function]:
    function = plant.function(plant.item(name), "fn")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, (name, "request")),
            key=(name, "request"),
            subject=function,
            signal=signal,
            signal_name=name,
            priority=1,
        )
    )
    return function


def _bind(plant: Plant, request: Id[Function], channel: Id[Function], key: str) -> Id[Any]:
    binding = PlcBindingFacet(
        id=make_id(PlcBindingFacet, (key,)),
        key=(key,),
        subject=request,
        channel=channel,
    )
    plant.add(binding)
    return binding.id


def test_a_binding_to_a_channel_of_the_requested_signal_is_no_finding() -> None:
    """DI to DI."""
    plant = Plant()
    channel = _module(plant, "di-module", SignalType.DI)
    _bind(plant, _request(plant, "sensor", SignalType.DI), channel, "b1")
    assert check_plc(plant.model()) == ()


def test_a_binding_to_another_signal_is_an_error_naming_all_three() -> None:
    """Subjects: the binding, the requesting function and the channel function."""
    plant = Plant()
    channel = _module(plant, "di-module", SignalType.DI)
    request = _request(plant, "transmitter", SignalType.AI_CURRENT)
    binding = _bind(plant, request, channel, "b1")
    (finding,) = check_plc(plant.model())
    assert (finding.code, finding.severity) == (PLC_BINDING_SIGNAL_MISMATCH, Severity.ERROR)
    assert finding.subjects == tuple(sorted((binding, request, channel)))
    assert "ai_current" in finding.message
    assert "is di" in finding.message


def test_a_channel_with_no_plc_channel_declaration_is_a_mismatch_too() -> None:
    """The target is not a channel of any type: it cannot be of the requested one."""
    plant = Plant()
    channel = _module(plant, "bare-module", None)
    _bind(plant, _request(plant, "sensor", SignalType.DI), channel, "b1")
    (finding,) = check_plc(plant.model())
    assert "is not declared a channel" in finding.message


def test_a_channel_function_with_no_template_is_a_mismatch_too() -> None:
    """A hand-made function is not a module channel."""
    plant = Plant()
    hand_made = plant.function(plant.item("hand"), "ch")
    _bind(plant, _request(plant, "sensor", SignalType.DI), hand_made, "b1")
    (finding,) = check_plc(plant.model())
    assert "is not declared a channel" in finding.message


def test_a_binding_without_a_request_gives_no_finding() -> None:
    """Nothing to compare: the request facet is what says what was asked."""
    plant = Plant()
    channel = _module(plant, "di-module", SignalType.DI)
    function = plant.function(plant.item("orphan"), "fn")
    _bind(plant, function, channel, "b1")
    assert check_plc(plant.model()) == ()


def test_only_the_bad_binding_of_several_is_reported() -> None:
    """Two bindings, one wrong."""
    plant = Plant()
    good_channel = _module(plant, "di-module", SignalType.DI)
    bad_channel = _module(plant, "do-module", SignalType.DO)
    good = _request(plant, "sensor", SignalType.DI)
    bad = _request(plant, "transmitter", SignalType.AI_CURRENT)
    _bind(plant, good, good_channel, "b1")
    _bind(plant, bad, bad_channel, "b2")
    (finding,) = check_plc(plant.model())
    assert bad in finding.subjects
    assert good not in finding.subjects


def test_findings_are_sorted_and_independent_of_table_order() -> None:
    """Sorted by `(code, subjects, message)`, the same with tables backwards."""
    plant = Plant()
    channel = _module(plant, "di-module", SignalType.DI)
    for number in range(3):
        _bind(plant, _request(plant, f"t{number}", SignalType.AI_CURRENT), channel, f"b{number}")
    model = plant.model()
    findings = check_plc(model)
    assert len(findings) == 3
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    backwards: Model = dataclasses.replace(
        model,
        digest="reversed-tables-test-plc-findings",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert check_plc(backwards) == findings


def test_no_message_prints_an_id() -> None:
    """Messages name function keys and signals."""
    plant = Plant()
    channel = _module(plant, "di-module", SignalType.DI)
    _bind(plant, _request(plant, "transmitter", SignalType.AI_CURRENT), channel, "b1")
    for finding in check_plc(plant.model()):
        assert not re.search(r"[0-9a-f]{32}", finding.message)


def test_an_empty_model_has_no_finding() -> None:
    """Nothing bound."""
    assert check_plc(Plant().model()) == ()
