"""The wired PLC pick (model-0211): signal kind (W2), then direct conductor (W3), never silent (W4).

Candidates are the free channels on the request's net whose own net holds only that request.
Each test builds a request whose pin reaches channels two ways: by one conductor (direct) or
through a plain terminal-like function (indirect). Invented data; the helpers come from the
two sibling test modules. Rack keys order the channels: "rack-a" serves before "rack-b".
"""

from typing import TYPE_CHECKING

from plant import Plant
from test_plc_allocation_units_model import Site, _bound, _site
from test_plc_allocation_wired_model import _plain, _request

from fransys_model.derive.passes._plc_ambiguous import PLC_REQUEST_AMBIGUOUS
from fransys_model.derive.passes.plc_allocation import allocate_plc
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.validators.plc import PLC_BINDING_SIGNAL_MISMATCH, check_plc

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function


def _reach(plant: Plant, request: Id[Function], channel: Id[Function], *, direct: bool) -> None:
    """Join `request`'s pin to `channel`'s pin by one conductor, or through a plain function."""
    pin = plant.port(channel, "1")
    if direct:
        plant.wire(plant.port(request, "1"), pin, key=f"direct-{channel.value[:6]}")
        return
    _, mid = _plain(plant, f"mid-{channel.value[:6]}", None)
    plant.wire(plant.port(request, "1"), mid, key=f"in-{channel.value[:6]}")
    plant.wire(mid, pin, key=f"out-{channel.value[:6]}")


def _two(first: SignalType, second: SignalType) -> tuple[Plant, Id[Function], Id[Function]]:
    """Plant with one channel in "rack-a" of kind `first` and one in "rack-b" of kind `second`."""
    plant = Plant()
    (a,) = _site(plant, Site("rack-a", "mod-a", "A1", 1, signal=first))
    (b,) = _site(plant, Site("rack-b", "mod-b", "B1", 1, signal=second))
    return plant, a, b


def test_w3_the_direct_channel_wins_over_an_earlier_one_reached_through_a_terminal() -> None:
    plant, early, late = _two(SignalType.DI, SignalType.DI)
    request = _request(plant, "dev", None)
    _reach(plant, request, early, direct=False)
    _reach(plant, request, late, direct=True)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {request: late}


def test_w2_the_asked_kind_wins_over_a_direct_channel_of_another_kind() -> None:
    plant, other, wanted = _two(SignalType.DO, SignalType.DI)
    request = _request(plant, "dev", None)
    _reach(plant, request, other, direct=True)
    _reach(plant, request, wanted, direct=False)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {request: wanted}
    assert check_plc(model) == ()


def test_w2_with_no_channel_of_the_asked_kind_it_binds_and_the_mismatch_names_both_fixes() -> None:
    plant, channel, _ = _two(SignalType.DO, SignalType.DO)
    request = _request(plant, "dev", None)
    _reach(plant, request, channel, direct=True)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {request: channel}
    (mismatch,) = check_plc(model)
    assert mismatch.code == PLC_BINDING_SIGNAL_MISMATCH
    assert "rewire it to a di channel, or ask for do" in mismatch.message


def test_w4_two_direct_channels_are_an_error_and_bind_nothing_not_even_by_queue() -> None:
    plant, first, second = _two(SignalType.DI, SignalType.DI)
    (spare,) = _site(plant, Site("rack-c", "mod-c", "C1", 1))
    request = _request(plant, "dev", None)
    _reach(plant, request, first, direct=True)
    _reach(plant, request, second, direct=True)
    model, findings = allocate_plc(plant.model())
    (ambiguous,) = findings
    assert ambiguous.code == PLC_REQUEST_AMBIGUOUS
    assert {request, first, second} <= set(ambiguous.subjects)
    assert "channels A1:1, B1:1" in ambiguous.message
    assert _bound(model) == {}
    assert spare not in _bound(model).values()


def test_w4_two_indirect_channels_are_ambiguous_too() -> None:
    plant, first, second = _two(SignalType.DI, SignalType.DI)
    request = _request(plant, "dev", None)
    _reach(plant, request, first, direct=False)
    _reach(plant, request, second, direct=False)
    _, findings = allocate_plc(plant.model())
    assert [f.code for f in findings] == [PLC_REQUEST_AMBIGUOUS]
