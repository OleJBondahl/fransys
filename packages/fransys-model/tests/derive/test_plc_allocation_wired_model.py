"""Wired-request tests for PLC allocation: a wired request takes its wired channel.

Before any queue is served, a request whose function shares a physical net with a channel
function is bound to that channel, whatever unit the channel is in; a channel two requests
share is not booked by wiring; a request wired to nothing is allocated by the scope rules;
where the scope rules find no unit on the request's chain that declares its signal, a request
whose net reaches a boundary port of a standalone unit on that chain gets no finding instead of
`PLC_REQUEST_UNSERVABLE` (it never changes a binding). Invented data. The helpers `Site`,
`_site` and `_bound` come from `test_plc_allocation_units_model.py` next to this one.
"""

from typing import TYPE_CHECKING

from plant import Plant
from test_plc_allocation_units_model import Site, _bound, _site

from fransys_model.derive import plc_channel_rows
from fransys_model.derive.numbering_pins import name_findings
from fransys_model.derive.passes.plc_allocation import PLC_REQUEST_UNSERVABLE, allocate_plc
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.validators.plc import (
    PLC_BINDING_SIGNAL_MISMATCH,
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


def test_a_request_wired_to_a_channel_of_another_unit_binds_to_it() -> None:
    """Unit A has its own channel `ch_a` (rack sorts first) but the request is wired to unit
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


def test_a_relay_board_built_alone_gives_no_binding_and_no_finding() -> None:
    """The board's request reaches the board's own boundary port and no channel exists in
    the model, so it is served outside the board: no binding, no finding, both checks empty.
    """
    model, findings = allocate_plc(_board(with_cab_channel=False)[0])
    assert findings == ()
    assert _bound(model) == {}
    assert check_plc_wiring(model) == ()
    assert check_plc(model) == ()


def test_the_same_board_in_the_parent_build_binds_to_the_channel_on_its_boundary() -> None:
    """With the cab's channel wired to the boundary function the request binds to
    it, not to the cab's spare channel that would be served first by the unit chain.
    """
    built, request, wired = _board(with_cab_channel=True)
    model, findings = allocate_plc(built)
    assert wired is not None
    assert findings == ()
    assert _bound(model) == {request: wired}
    assert check_plc_wiring(model) == ()
    assert check_plc(model) == ()


def test_wiring_never_changes_a_binding_a_wired_out_request_takes_its_units_free_channel() -> None:
    """The boundary rule only replaces a finding: the request is wired out through the board's
    boundary and reaches no channel, but the board holds a free DI channel, so the scope rules
    bind it there exactly as before, with no finding.
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


def test_a_nested_request_with_no_declaring_unit_is_unservable_in_the_parent_build() -> None:
    """The rule needs a standalone unit: `cab` also holds an item of its own outside `board`, so
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


def test_an_exhausted_serving_unit_stays_unservable_in_a_standalone_build() -> None:
    """The rule needs a unit that declares no channel of the signal: `board` declares one, an
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


def test_a_request_that_is_itself_a_boundary_function_is_not_outside() -> None:
    """Boundary rule: a function is not "another function" to itself, so a request that is the
    boundary function of its own unit and is wired to nothing else is unservable.
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


def test_the_boundary_check_is_narrow_a_plain_function_is_not_a_boundary() -> None:
    """Boundary guard (passes on the base too): wired to a plain non-boundary function, with no
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


def test_a_request_wired_to_nothing_in_a_unit_with_no_channel_is_unservable() -> None:
    """Scope guard (passes on the base too): no wiring, no channel on the chain, even with a
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


def test_the_boundary_check_is_narrow_a_sibling_units_boundary_is_not_on_the_chain() -> None:
    """Boundary guard (passes on the base too): the request in `board-x` reaches the boundary of
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


def test_a_do_request_wired_to_a_di_channel_binds_there_and_the_signal_check_reports_it() -> None:
    """The wiring is the fact; `allocate_plc` binds the DO request to the wired DI channel
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


def test_a_channel_an_existing_binding_names_is_not_booked_twice() -> None:
    """`dev-hand` is hand-bound to `ch1`; `dev-w` is wired to `ch1` too. The taken channel is
    not booked again: `dev-w` falls to the scope rules and takes `ch2`; no channel has two bindings.
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


def test_same_signal_contacts_on_a_shared_return_each_bind_their_directly_wired_channel() -> None:
    """Shared return: `dev-1` and `dev-2` (both DI) and both channels sit on one return net, so
    every channel's net holds a same-signal rival. W1b keeps both channels for each request, W3
    keeps the one it has a direct conductor to, and the two picks differ: each binds by wiring,
    here the reverse of the key order, which the free queue would not give.
    """
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    first = _request(plant, "dev-1", unit, to=plant.port(ch2, "1"))
    second = _request(plant, "dev-2", unit, to=plant.port(ch1, "1"))
    common = plant.function(plant.item("common", designation="X-common", unit=unit), "return")
    for index, function in enumerate((first, second, ch1, ch2)):
        plant.wire(plant.port(function, "2"), plant.port(common, "r"), key=f"return-{index}")
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {first: ch2, second: ch1}
    assert check_plc_wiring(model) == ()


def _misbound(
    plant: Plant, name: str, unit: Id[Unit], wired: Id[Port], bound: Id[Function]
) -> None:
    """A request wired to port `wired` but hand-bound to channel `bound`: a wiring mismatch."""
    function = _request(plant, name, unit, to=wired)
    key = (name, "signal", "plc_binding")
    plant.add(
        PlcBindingFacet(id=make_id(PlcBindingFacet, key), key=key, subject=function, channel=bound)
    )


def test_a_wiring_mismatch_names_each_channel_by_its_pin_not_by_its_module() -> None:
    """Field case: both channels sit on one module, so the module-only text read "wired to channel
    -U1 but bound to channel -U1". A channel prints as the PLC list prints its pins.
    """
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    ch1_port = plant.port(ch1, "1")
    plant.port(ch2, "2")
    _misbound(plant, "dev-1", unit, ch1_port, ch2)
    model, _ = allocate_plc(plant.model())
    (mismatch,) = name_findings(model, check_plc_wiring(model))
    assert mismatch.message.endswith("is wired to channel -U1:1 but bound to channel -U1:2")


def test_a_multi_pin_channel_is_named_by_the_pins_the_plc_list_prints() -> None:
    """The message's pins for a channel are its `PlcChannelRow.pin` texts, joined by ", "."""
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    ch1_port = plant.port(ch1, "10")
    for name in ("2", "1"):
        plant.port(ch1, name)
    plant.port(ch2, "1")
    _misbound(plant, "dev-1", unit, ch1_port, ch2)
    model, _ = allocate_plc(plant.model())
    pins = [row.pin for row in plc_channel_rows(model) if row.channel == ch1]
    assert len(pins) == 3
    (mismatch,) = name_findings(model, check_plc_wiring(model))
    assert f"wired to channel {', '.join(pins)} but" in mismatch.message
