"""WP15 tests: the allocation pass follows the wiring, `check_plc_wiring` holds a binding to it.

Two DI requests are wired to the two channels of one module. Allocation binds each request to
the channel it is wired to whatever the priorities (decision model-0083, PW1); a binding
that disagrees with the wiring, made by hand, is what the validator reports (decision
model-0068).
"""

from plant import Plant
from query_builders import make_channels

from fransys_model.derive.passes.plc_allocation import allocate_plc
from fransys_model.kernel import Model, Origin, evolve, make_id
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of, functions
from fransys_model.vocab.validators.plc import PLC_BINDING_WIRING_MISMATCH, check_plc_wiring


def _wired_plant(priority_a: int, priority_b: int) -> Model:
    """Module `mod` with channels 1 and 2; `dev-a` wired to channel 1, `dev-b` to channel 2."""
    plant = Plant()
    channels = make_channels(plant, "mod", None, (SignalType.DI, SignalType.DI))
    for name, priority, channel in (
        ("dev-a", priority_a, channels[0]),
        ("dev-b", priority_b, channels[1]),
    ):
        function = plant.function(plant.item(name), "signal")
        plant.add(
            PlcRequestFacet(
                id=make_id(PlcRequestFacet, (name, "request")),
                key=(name, "request"),
                subject=function,
                signal=SignalType.DI,
                signal_name=name,
                priority=priority,
            )
        )
        plant.wire(plant.port(function, "1"), plant.port(channel, "1"), key=f"wire-{name}")
    return plant.model()


def test_an_allocation_that_follows_the_wiring_gives_no_wiring_finding() -> None:
    """`dev-a` is served first and gets channel 1, as wired."""
    bound, findings = allocate_plc(_wired_plant(1, 1))
    assert findings == ()
    assert len(facets_of(bound, PlcBindingFacet)) == 2
    assert check_plc_wiring(bound) == ()


def test_swapped_priorities_do_not_move_a_request_off_its_wired_channel() -> None:
    """PW1: `dev-b` is served first, yet each request takes the channel it is wired to."""
    model = _wired_plant(2, 1)
    bound, findings = allocate_plc(model)
    assert findings == ()
    channel_of = {
        functions(model)[b.subject].key: functions(model)[b.channel].key
        for b in facets_of(bound, PlcBindingFacet).values()
    }
    assert channel_of == {("dev-a", "signal"): ("mod", "ch1"), ("dev-b", "signal"): ("mod", "ch2")}
    assert check_plc_wiring(bound) == ()


def test_a_hand_binding_that_disagrees_with_the_wiring_is_caught() -> None:
    """`dev-a` is bound to channel 2 and `dev-b` to channel 1 by hand: four findings."""
    model = _wired_plant(1, 1)
    by_key = {function.key: function.id for function in functions(model).values()}
    swapped = []
    for request, channel in (("dev-a", ("mod", "ch2")), ("dev-b", ("mod", "ch1"))):
        key = (request, "signal", "plc_binding")
        swapped.append(
            PlcBindingFacet(
                id=make_id(PlcBindingFacet, key),
                key=key,
                subject=by_key[(request, "signal")],
                channel=by_key[channel],
            )
        )
    bound, findings = allocate_plc(
        evolve(model, put=swapped, origin=Origin(file="<test>", line=1, note="binding"))
    )
    assert findings == ()
    wiring = check_plc_wiring(bound)
    assert len(wiring) == 4
    assert {f.code for f in wiring} == {PLC_BINDING_WIRING_MISMATCH}
    for request in ("dev-a/signal", "dev-b/signal"):
        assert any(request in f.message for f in wiring)
