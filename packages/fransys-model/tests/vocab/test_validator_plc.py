"""WP13 tests: `validators.plc` (ROADMAP WP13, design/facets.md)."""

from scaffold import scaffold

from fransys_model.kernel import Draft, Id, Model, Origin, Record, freeze
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import FunctionKind, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.templates import FunctionTemplate
from fransys_model.vocab.validators.plc import PLC_BINDING_SIGNAL_MISMATCH, check_plc


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_validator_plc.py", line=1, note="fixture")
    draft.extend((*records, *scaffold(records)), origin=origin)
    return freeze(draft)


def _channel(signal: SignalType) -> tuple[FunctionTemplate, Function, PlcChannelFacet]:
    template = FunctionTemplate(
        id=Id(kind="function_template", value="1" * 32),
        key=("examples", "di-module", "fn", "ch3"),
        part=Id(kind="part", value="2" * 32),
        name="ch3",
        kind=FunctionKind.PLC_CHANNEL,
    )
    channel_fn = Function(
        id=Id(kind="function", value="3" * 32),
        key=("examples", "di-module-1", "fn", "ch3"),
        item=Id(kind="item", value="4" * 32),
        template=template.id,
        name="ch3",
        kind=FunctionKind.PLC_CHANNEL,
    )
    facet = PlcChannelFacet(
        id=Id(kind="facet.plc_channel", value="5" * 32),
        key=("examples", "di-module", "fn", "ch3", "plc_channel"),
        subject=template.id,
        signal=signal,
        channel=3,
    )
    return template, channel_fn, facet


def test_binding_matching_the_channels_signal_has_no_finding() -> None:
    """A `DI` request bound to a `DI` channel is consistent."""
    template, channel_fn, channel_facet = _channel(SignalType.DI)
    request = Function(
        id=Id(kind="function", value="6" * 32),
        key=("examples", "sensor-1", "fn"),
        item=Id(kind="item", value="7" * 32),
        template=None,
        name="fn",
        kind=FunctionKind.SENSOR,
    )
    request_facet = PlcRequestFacet(
        id=Id(kind="facet.plc_request", value="8" * 32),
        key=("examples", "sensor-1", "fn", "plc_request"),
        subject=request.id,
        signal=SignalType.DI,
        signal_name="Sensor1",
        priority=1,
    )
    binding = PlcBindingFacet(
        id=Id(kind="facet.plc_binding", value="9" * 32),
        key=("examples", "sensor-1", "fn", "plc_binding"),
        subject=request.id,
        channel=channel_fn.id,
    )
    records = (
        template,
        channel_fn,
        channel_facet,
        request,
        request_facet,
        binding,
    )
    findings = check_plc(_freeze(records))
    assert not [f for f in findings if f.code == PLC_BINDING_SIGNAL_MISMATCH]


def test_binding_to_a_channel_of_a_different_signal_yields_plc_binding_signal_mismatch() -> None:
    """An `AI_CURRENT` request bound to a `DI` channel yields `PLC_BINDING_SIGNAL_MISMATCH`."""
    template, channel_fn, channel_facet = _channel(SignalType.DI)
    request = Function(
        id=Id(kind="function", value="a" * 32),
        key=("examples", "transmitter-1", "fn"),
        item=Id(kind="item", value="b" * 32),
        template=None,
        name="fn",
        kind=FunctionKind.SENSOR,
    )
    request_facet = PlcRequestFacet(
        id=Id(kind="facet.plc_request", value="c" * 32),
        key=("examples", "transmitter-1", "fn", "plc_request"),
        subject=request.id,
        signal=SignalType.AI_CURRENT,
        signal_name="Pos",
        priority=1,
    )
    binding = PlcBindingFacet(
        id=Id(kind="facet.plc_binding", value="d" * 32),
        key=("examples", "transmitter-1", "fn", "plc_binding"),
        subject=request.id,
        channel=channel_fn.id,
    )
    records = (
        template,
        channel_fn,
        channel_facet,
        request,
        request_facet,
        binding,
    )
    findings = check_plc(_freeze(records))
    assert any(f.code == PLC_BINDING_SIGNAL_MISMATCH for f in findings)
