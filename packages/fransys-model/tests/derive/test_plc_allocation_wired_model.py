"""PLC-WIRED tests (PW1 to PW4): a wired request takes its wired channel.

Before any queue is served, a request whose function shares a physical net with a channel
function is bound to that channel, whatever unit the channel is in (PW1); a channel two requests
share is not booked by wiring (PW2); a request wired to nothing is allocated as PLC-SCOPE rules
(PW3); where PW3 finds no unit on the request's chain that declares its signal, a request whose
net reaches a boundary port of a standalone unit on that chain gets no finding instead of
`PLC_REQUEST_UNSERVABLE` (PW4, it never changes a binding). Invented data. The helpers `Site`,
`_site` and `_bound` come from the PLC-SCOPE test file next to this one.
"""

from typing import TYPE_CHECKING

from plant import Plant
from test_plc_allocation_units_model import Site, _bound, _site

from fransys_model.derive.passes.plc_allocation import PLC_REQUEST_UNSERVABLE, allocate_plc
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.validators.plc import (
    PLC_BINDING_SIGNAL_MISMATCH,
    PLC_BINDING_WIRING_MISMATCH,
    check_plc,
    check_plc_wiring,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port, Unit


def _request(  # noqa: PLR0913 -- one param per thing the scenarios vary, kept explicit
    plant: Plant,
    name: str,
    unit: Id[Unit] | None,
    *,
    to: Id[Port] | None = None,
    signal: SignalType = SignalType.DI,
    priority: int = 1,
) -> Id[Function]:
    """A field device `name` with a `signal` request; its port "1" is wired to `to` if given."""
    item = plant.item(name, designation=f"B-{name}", unit=unit)
    function = plant.function(item, "signal")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, (name, "signal", "request")),
            key=(name, "signal", "request"),
            subject=function,
            signal=signal,
            signal_name=f"tag_{name}",
            priority=priority,
        )
    )
    if to is not None:
        plant.wire(plant.port(function, "1"), to, key=f"wire-{name}")
    return function


def _plain(plant: Plant, name: str, unit: Id[Unit] | None) -> tuple[Id[Function], Id[Port]]:
    """An item with one plain function (no channel, no request) and its port "1"."""
    item = plant.item(name, designation=f"X-{name}", unit=unit)
    function = plant.function(item, "fn")
    return function, plant.port(function, "1")


def test_pw1_a_request_wired_to_a_channel_of_another_unit_binds_to_it() -> None:
    """PW1: unit A has its own channel `ch_a` (rack sorts first) but the request is wired to unit
    B's `ch_b`: it binds there, `ch_a` stays free for the next unwired request, nothing mismatches.
    """
    plant = Plant()
    unit_a = plant.unit("unit-a", name="unit A")
    unit_b = plant.unit("unit-b", name="unit B")
    (ch_a,) = _site(plant, Site("rack-a1", "mod-a", "A1", 1, unit_a))
    (ch_b,) = _site(plant, Site("rack-b2", "mod-b", "B1", 1, unit_b))
    wired = _request(plant, "dev-1", unit_a, to=plant.port(ch_b, "1"))
    unwired = _request(plant, "dev-2", unit_a)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model)[wired] == ch_b
    assert check_plc_wiring(model) == ()
    assert _bound(model) == {wired: ch_b, unwired: ch_a}


def _board(*, with_cab_channel: bool) -> tuple[Model, Id[Function], Id[Function] | None]:
    """A relay board `board` (nested in `cab`) whose request is wired to its boundary function.

    The relay `dev-k1` is in `board`; its request is wired through a conductor to connector
    function `x1`, the boundary of `board`. With `with_cab_channel` the cab also holds a spare
    channel (rack sorts first, unwired) and a channel wired to `x1` (the parent build); without,
    the model holds no channel at all (the board built alone). Returns the model, the request
    function and the wired channel (None when alone).
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board = plant.unit("board", name="board", parent=cab)
    connector = plant.item("conn-x1", designation="X1", unit=board)
    x1 = plant.function(connector, "x1")
    x1_port = plant.port(x1, "1")
    plant.boundary(board, x1)
    request = _request(plant, "dev-k1", board, to=x1_port)
    wired = None
    if with_cab_channel:
        _site(plant, Site("rack-a1", "mod-spare", "S1", 1, cab))
        (wired,) = _site(plant, Site("rack-b2", "mod-wired", "W1", 1, cab))
        plant.wire(plant.port(wired, "1"), x1_port, key="wire-ch")
    return plant.model(), request, wired


def test_pw4_a_relay_board_built_alone_gives_no_binding_and_no_finding() -> None:
    """PW4: the board's request reaches the board's own boundary port and no channel exists in
    the model, so it is served outside the board: no binding, no finding, both checks empty.
    """
    model, findings = allocate_plc(_board(with_cab_channel=False)[0])
    assert findings == ()
    assert _bound(model) == {}
    assert check_plc_wiring(model) == ()
    assert check_plc(model) == ()


def test_pw1_the_same_board_in_the_parent_build_binds_to_the_channel_on_its_boundary() -> None:
    """PW1 and PW4: with the cab's channel wired to the boundary function the request binds to
    it, not to the cab's spare channel that would be served first by the unit chain.
    """
    built, request, wired = _board(with_cab_channel=True)
    model, findings = allocate_plc(built)
    assert wired is not None
    assert findings == ()
    assert _bound(model) == {request: wired}
    assert check_plc_wiring(model) == ()
    assert check_plc(model) == ()


def test_pw4_never_changes_a_binding_a_wired_out_request_takes_its_units_free_channel() -> None:
    """PW4 only replaces a finding (known limit 1): the request is wired out through the board's
    boundary and reaches no channel, but the board holds a free DI channel, so PW3 binds it
    there exactly as before, with no finding.
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board = plant.unit("board", name="board", parent=cab)
    connector = plant.item("conn-x1", designation="X1", unit=board)
    x1 = plant.function(connector, "x1")
    plant.boundary(board, x1)
    (own,) = _site(plant, Site("rack-b", "mod-b", "B1", 1, board))
    request = _request(plant, "dev-k1", board, to=plant.port(x1, "1"))
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {request: own}


def test_pw4_a_nested_request_with_no_declaring_unit_is_unservable_in_the_parent_build() -> None:
    """PW4 needs a standalone unit: `cab` also holds an item of its own outside `board`, so
    `board` is not standalone and its boundary is not open. The request is wired out, no unit
    on its chain declares a channel, and it is `PLC_REQUEST_UNSERVABLE` as before.
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board = plant.unit("board", name="board", parent=cab)
    connector = plant.item("conn-x1", designation="X1", unit=board)
    x1 = plant.function(connector, "x1")
    plant.boundary(board, x1)
    plant.item("cab-item", designation="C1", unit=cab)
    request = _request(plant, "dev-k1", board, to=plant.port(x1, "1"))
    model, (finding,) = allocate_plc(plant.model())
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert request in finding.subjects
    assert _bound(model) == {}


def test_pw4_an_exhausted_serving_unit_stays_unservable_in_a_standalone_build() -> None:
    """PW4 needs a unit that declares no channel of the signal: `board` declares one, an
    unwired request takes it, and the wired-out request behind it is unservable although
    `board` is standalone and the request reaches its boundary.
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board = plant.unit("board", name="board", parent=cab)
    connector = plant.item("conn-x1", designation="X1", unit=board)
    x1 = plant.function(connector, "x1")
    plant.boundary(board, x1)
    (own,) = _site(plant, Site("rack-b", "mod-b", "B1", 1, board))
    first = _request(plant, "dev-a", board)
    second = _request(plant, "dev-b", board, to=plant.port(x1, "1"))
    model, (finding,) = allocate_plc(plant.model())
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert second in finding.subjects
    assert _bound(model) == {first: own}


def test_pw4_a_request_that_is_itself_a_boundary_function_is_not_outside() -> None:
    """PW4 guard: a function is not "another function" to itself, so a request that is the
    boundary function of its own unit and is wired to nothing else goes to PW3 (unservable).
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board = plant.unit("board", name="board", parent=cab)
    request = _request(plant, "dev-k1", board)
    plant.boundary(board, request)
    model, (finding,) = allocate_plc(plant.model())
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert request in finding.subjects
    assert _bound(model) == {}


def test_pw4_is_narrow_a_plain_function_is_not_a_boundary() -> None:
    """PW4 guard (passes on the base too): wired to a plain non-boundary function, with no
    channel anywhere, the request is still unservable.
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board = plant.unit("board", name="board", parent=cab)
    _, plain_port = _plain(plant, "conn-x1", board)
    request = _request(plant, "dev-k1", board, to=plain_port)
    model, (finding,) = allocate_plc(plant.model())
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert request in finding.subjects
    assert _bound(model) == {}


def test_pw3_a_request_wired_to_nothing_in_a_unit_with_no_channel_is_unservable() -> None:
    """PW3 guard (passes on the base too): no wiring, no channel on the chain, even with a
    boundary in the unit: one PLC_REQUEST_UNSERVABLE, no binding.
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board = plant.unit("board", name="board", parent=cab)
    connector = plant.item("conn-x1", designation="X1", unit=board)
    plant.boundary(board, plant.function(connector, "x1"))
    request = _request(plant, "dev-k1", board)
    model, (finding,) = allocate_plc(plant.model())
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert request in finding.subjects
    assert _bound(model) == {}


def test_pw4_is_narrow_a_sibling_units_boundary_is_not_on_the_chain() -> None:
    """PW4 guard (passes on the base too): the request in `board-x` reaches the boundary of
    sibling `board-y`, which is not on its chain (board-x, cab): still unservable.
    """
    plant = Plant()
    cab = plant.unit("cab", name="cab")
    board_x = plant.unit("board-x", name="board X", parent=cab)
    board_y = plant.unit("board-y", name="board Y", parent=cab)
    connector = plant.item("conn-y1", designation="Y1", unit=board_y)
    y1 = plant.function(connector, "y1")
    plant.boundary(board_y, y1)
    request = _request(plant, "dev-k1", board_x, to=plant.port(y1, "1"))
    model, (finding,) = allocate_plc(plant.model())
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert request in finding.subjects
    assert _bound(model) == {}


def test_pw2_two_requests_on_one_channels_net_fall_to_pw3_and_the_wiring_check_reports_it() -> None:
    """PW2 (may pass on the base): `dev-1` and `dev-2` are both wired to `ch1`, so neither is
    bound by wiring; PW3 serves them in key order (`ch1`, `ch2`); the wiring check reports the
    request that went to `ch2` as today; no channel has two bindings.
    """
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    ch1_port = plant.port(ch1, "1")
    first = _request(plant, "dev-1", unit, to=ch1_port)
    second = _request(plant, "dev-2", unit, to=ch1_port)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {first: ch1, second: ch2}
    bindings = list(facets_of(model, PlcBindingFacet).values())
    assert len({binding.channel for binding in bindings}) == len(bindings)
    by_subject = {binding.subject: binding for binding in bindings}
    (mismatch,) = check_plc_wiring(model)
    assert mismatch.code == PLC_BINDING_WIRING_MISMATCH
    assert set(mismatch.subjects) == {by_subject[second].id, second, ch2}
    assert "dev-2/signal is wired to channel mod-u/ch1 but bound to channel mod-u/ch2" in (
        mismatch.message
    )


def test_pw2_two_requests_wired_to_the_second_channel_neither_takes_it_by_wiring() -> None:
    """PW2 proof: both requests are wired to `ch2`. Were `dev-1` bound by wiring it would take
    `ch2` and `dev-2` would be the mismatch; with PW2 both fall to PW3 (`dev-1` gets `ch1`,
    `dev-2` gets `ch2`), so the one mismatch names `dev-1`, as before the change.
    """
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    ch2_port = plant.port(ch2, "1")
    first = _request(plant, "dev-1", unit, to=ch2_port)
    second = _request(plant, "dev-2", unit, to=ch2_port)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {first: ch1, second: ch2}
    (mismatch,) = check_plc_wiring(model)
    assert mismatch.code == PLC_BINDING_WIRING_MISMATCH
    assert first in mismatch.subjects
    assert second not in mismatch.subjects


def test_pw1_a_do_request_wired_to_a_di_channel_binds_there_and_the_signal_check_reports_it() -> (
    None
):
    """PW1: the wiring is the fact; `allocate_plc` binds the DO request to the wired DI channel
    with no finding, and `check_plc` alone reports one PLC_BINDING_SIGNAL_MISMATCH for it.
    """
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    (channel,) = _site(plant, Site("rack-u", "mod-u", "U1", 1, unit))
    request = _request(plant, "dev-1", unit, to=plant.port(channel, "1"), signal=SignalType.DO)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {request: channel}
    (mismatch,) = check_plc(model)
    assert mismatch.code == PLC_BINDING_SIGNAL_MISMATCH
    assert request in mismatch.subjects
    assert channel in mismatch.subjects
    assert check_plc_wiring(model) == ()


def test_pw1_a_channel_an_existing_binding_names_is_not_booked_twice() -> None:
    """PW1: `dev-hand` is hand-bound to `ch1`; `dev-w` is wired to `ch1` too. The taken channel is
    not booked again: `dev-w` falls to PW3 and takes `ch2`; no channel has two bindings.
    """
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    hand = _request(plant, "dev-hand", unit)
    wired = _request(plant, "dev-w", unit, to=plant.port(ch1, "1"))
    key = ("dev-hand", "signal", "plc_binding")
    plant.add(PlcBindingFacet(id=make_id(PlcBindingFacet, key), key=key, subject=hand, channel=ch1))
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {hand: ch1, wired: ch2}
    bindings = list(facets_of(model, PlcBindingFacet).values())
    assert len({binding.channel for binding in bindings}) == len(bindings)
