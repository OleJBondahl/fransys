"""`item_kind` and `signal_kind` (model-0197) over the two synthetic designs merged."""

from cabinet import build_cabinet
from harness_board import build_harness_board

from fransys_model.derive import ItemKind, SignalKind, item_kind, printed_designation, signal_kind
from fransys_model.kernel import Model, freeze, merge
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of, functions, items


def _model() -> Model:
    return freeze(merge(build_cabinet(), build_harness_board()))


def _kinds() -> dict[str, ItemKind]:
    model = _model()
    return {printed_designation(model, item): item_kind(model, item) for item in items(model)}


def test_each_designation_reads_its_own_kind() -> None:
    """A strip, a cable, a harness, its plug, a board, a PLC module and a plain device."""
    kinds = _kinds()
    assert kinds["-X1"] is ItemKind.STRIP
    assert kinds["-W1"] is ItemKind.CABLE
    assert kinds["-WH1"] is ItemKind.HARNESS
    assert kinds["-WH1-H1"] is ItemKind.CONNECTOR
    assert kinds["-JB1"] is ItemKind.BOARD
    assert kinds["-A1-1"] is ItemKind.PLC_MODULE
    assert kinds["-K1"] is ItemKind.DEVICE


def test_every_kind_is_reached_and_a_terminal_is_a_terminal() -> None:
    """Every kind but BAR (neither design has a bar); a strip's children are terminals."""
    kinds = _kinds()
    assert set(kinds.values()) == set(ItemKind) - {ItemKind.BAR}
    assert {k for name, k in kinds.items() if ":" in name} == {ItemKind.TERMINAL}


def test_signal_kind_maps_every_signal_type() -> None:
    """Each of the eight types has a kind, and the four kinds are all used."""
    got = {signal: signal_kind(signal) for signal in SignalType}
    assert got[SignalType.DI] is SignalKind.DIGITAL_IN
    assert got[SignalType.RELAY] is SignalKind.DIGITAL_OUT
    assert got[SignalType.RTD] is SignalKind.ANALOGUE_IN
    assert got[SignalType.AO_CURRENT] is SignalKind.ANALOGUE_OUT
    assert set(got.values()) == set(SignalKind)


def test_a_bound_channel_and_the_request_it_serves_give_one_kind() -> None:
    """Reading the channel's facet and the field request's facet agree on every binding."""
    model = _model()
    channel_facets = {f.subject: f for f in facets_of(model, PlcChannelFacet).values()}
    requests = {f.subject: f for f in facets_of(model, PlcRequestFacet).values()}
    bindings = list(facets_of(model, PlcBindingFacet).values())
    assert bindings
    for binding in bindings:
        template = functions(model)[binding.channel].template
        assert template is not None
        channel = channel_facets[template]
        assert signal_kind(channel.signal) is signal_kind(requests[binding.subject].signal)
