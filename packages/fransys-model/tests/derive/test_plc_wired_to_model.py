"""Decision model-0065: the PLC list is a wiring list, `PlcChannelRow.wired_to` says where.

`wired_to` is the far end of every conductor at the channel function's ports, printed by the
lists' end rule (`port_designation_in` in the list's context, the nested-outside-empty rule of
model-0056). Distinct ends print once each, sorted by `bom_sort_key` and joined with `"; "`;
`None` when nothing is printed. Invented data.
"""

import dataclasses
from typing import TYPE_CHECKING

from plant import Plant
from query_builders import make_channels, make_node, make_pin, make_placement, make_terminal

from fransys_model.derive import plc_channel_rows
from fransys_model.derive.passes._plc_wired import wired_requests
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.facets.plc import PlcRequestFacet

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.core import Function, Port, Unit


def _set_unit(plant: Plant, item_id: Id[Item], unit: Id[Unit]) -> None:
    """Give an already-added item `unit` (records are frozen; replaced in place)."""
    record = next(r for r in plant.records if r.id == item_id)
    plant.records.remove(record)
    plant.add(dataclasses.replace(record, unit=unit))


def _wired_to(model: Model, channel: Id[Function]) -> str | None:
    """`wired_to` of the one row of `channel`, the whole model's list."""
    (row,) = (r for r in plc_channel_rows(model) if r.channel == channel)
    return row.wired_to


def test_a_channel_wired_to_a_nested_units_connector_names_the_connector() -> None:
    """The cabinet's `-DO1:1` reads `-J1:1`: the input connector, not the relay, not the board."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    board = plant.unit("board", name="relay-board", parent=cabinet)
    (channel,) = make_channels(plant, "do1", "DO1", (SignalType.DI,))
    _set_unit(plant, make_id(Item, ("do1",)), cabinet)
    board_item = plant.item("board-item", designation="U2", unit=board)
    connector = make_pin(plant, "j1", "J1", parent=board_item)
    relay = make_pin(plant, "k1", "K1", parent=board_item)
    for key in ("j1", "k1"):
        _set_unit(plant, make_id(Item, (key,)), board)
    plant.wire(plant.port(channel, "1"), connector, key="chan-wire")
    plant.wire(connector, relay, key="inside-the-board")  # not at the channel's port
    model = plant.model()
    (row,) = (r for r in plc_channel_rows(model, unit=cabinet) if r.channel == channel)
    assert row.channel_designation == "-DO1:1"
    assert row.wired_to == "-J1:1"


def test_several_ends_sort_by_bom_sort_key_not_as_strings() -> None:
    """Two terminals of one strip, `L1:2` and `L1:10`: numeric index order, not string order."""
    plant = Plant()
    plant.item("x1", designation="X1")
    t10 = make_terminal(plant, "x1", "t-l10", group="L1", index=10)
    t2 = make_terminal(plant, "x1", "t-l2", group="L1", index=2)
    (channel,) = make_channels(plant, "mod", "A1", (SignalType.DI,))
    port = plant.port(channel, "1")
    plant.wire(port, t10.external, key="w-ten")
    plant.wire(port, t2.external, key="w-two")
    assert _wired_to(plant.model(), channel) == "-X1:L1:2; -X1:L1:10"


def test_two_conductors_to_the_same_far_port_print_it_once() -> None:
    """Two conductors reaching the same far port (e.g. a splice) print that end once."""
    plant = Plant()
    (channel,) = make_channels(plant, "mod", "A1", (SignalType.DI,))
    port_a, port_b = plant.port(channel, "1"), plant.port(channel, "2")
    far = make_pin(plant, "far", "B9")
    plant.wire(port_a, far, key="w-a")
    plant.wire(port_b, far, key="w-b")
    assert _wired_to(plant.model(), channel) == "-B9:1"


def test_the_ends_of_every_port_of_the_channel_function_are_read() -> None:
    """A channel function with two ports, each wired: both far ends are listed."""
    plant = Plant()
    (channel,) = make_channels(plant, "mod", "A1", (SignalType.DI,))
    plant.wire(plant.port(channel, "1"), make_pin(plant, "a", "B1"), key="w-a")
    plant.wire(plant.port(channel, "2"), make_pin(plant, "b", "B2"), key="w-b")
    assert _wired_to(plant.model(), channel) == "-B1:1; -B2:1"


def test_an_unwired_channel_has_no_wired_to() -> None:
    """Nothing at the channel's ports (or no port at all) gives `None`, never `""`."""
    plant = Plant()
    unwired, bare = make_channels(plant, "mod", "A1", (SignalType.DI, SignalType.DI))
    plant.port(unwired, "1")
    model = plant.model()
    assert _wired_to(model, unwired) is None
    assert _wired_to(model, bare) is None


def _nested_plant() -> tuple[Plant, Id[Unit], Id[Unit], list[Id[Function]]]:
    """A module `-A1` of nested unit `inner` (in `outer`), channels 1 and 2 to 3.

    Channel 1 is wired to `-Q1` (in `inner`), channel 2 to `-Q2` (in `outer`, outside `inner`),
    channel 3 to both.
    """
    plant = Plant()
    outer = plant.unit("outer", name="cabinet")
    inner = plant.unit("inner", name="board", parent=outer)
    channels = make_channels(plant, "mod", "A1", (SignalType.DI,) * 3)
    _set_unit(plant, make_id(Item, ("mod",)), inner)
    inside = make_pin(plant, "q1", "Q1")
    outside = make_pin(plant, "q2", "Q2")
    _set_unit(plant, make_id(Item, ("q1",)), inner)
    _set_unit(plant, make_id(Item, ("q2",)), outer)
    plant.wire(plant.port(channels[0], "1"), inside, key="w1")
    plant.wire(plant.port(channels[1], "1"), outside, key="w2")
    plant.wire(plant.port(channels[2], "1"), inside, key="w3-in")
    plant.wire(plant.port(channels[2], "2"), outside, key="w3-out")
    return plant, outer, inner, channels


def test_a_nested_unit_prints_an_end_outside_it_as_nothing() -> None:
    """Model-0056: the far end outside a NESTED unit is skipped; all ends outside is `None`."""
    plant, _outer, inner, channels = _nested_plant()
    rows = {r.channel: r.wired_to for r in plc_channel_rows(plant.model(), unit=inner)}
    assert rows[channels[0]] == "-Q1:1"
    assert rows[channels[1]] is None
    assert rows[channels[2]] == "-Q1:1"  # no dangling separator for the skipped end


def test_without_a_unit_every_end_is_printed() -> None:
    """The nested-outside rule is the nested unit's alone: `unit=None` prints them all."""
    plant, _outer, _inner, channels = _nested_plant()
    rows = {r.channel: r.wired_to for r in plc_channel_rows(plant.model())}
    assert rows[channels[1]] == "-Q2:1"
    assert rows[channels[2]] == "-Q1:1; -Q2:1"


def test_a_top_level_unit_prints_an_end_outside_it() -> None:
    """A top-level unit names its neighbours (`end_outside_nested_unit` is False for it)."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    (channel,) = make_channels(plant, "mod", "A1", (SignalType.DI,))
    _set_unit(plant, make_id(Item, ("mod",)), cabinet)
    plant.wire(plant.port(channel, "1"), make_pin(plant, "far", "Q9"), key="w")
    (row,) = plc_channel_rows(plant.model(), unit=cabinet)
    assert row.wired_to == "-Q9:1"


def _located_plant() -> tuple[Plant, Id[Function], Id[AspectNode], Id[AspectNode]]:
    """Module `-A1` at `C1`, its channel wired to `-B12` at `C1` and to `-M1` at `EXT`."""
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    (channel,) = make_channels(plant, "mod", "A1", (SignalType.DI,))
    near, far = make_pin(plant, "b12", "B12"), make_pin(plant, "m1", "M1")
    plant.add(
        make_placement("mod-loc", make_id(Item, ("mod",)), c1.id),
        make_placement("b12-loc", make_id(Item, ("b12",)), c1.id),
        make_placement("m1-loc", make_id(Item, ("m1",)), ext.id),
    )
    plant.wire(plant.port(channel, "1"), near, key="w-near")
    plant.wire(plant.port(channel, "1"), far, key="w-far")
    return plant, channel, c1.id, ext.id


def test_an_end_outside_the_context_prints_its_location_path_in_front() -> None:
    """From `C1`, `-M1` at `EXT` reads `+EXT-M1:1` and `-B12` in `C1` stays short."""
    plant, _channel, c1, _ext = _located_plant()
    (row,) = plc_channel_rows(plant.model(), context=c1)
    assert row.wired_to == "-B12:1; +EXT-M1:1"


def test_no_context_prints_every_located_end_with_its_whole_path() -> None:
    """`context=None` (the default) is the empty context path, as for the wire-label list."""
    plant, channel, _c1, _ext = _located_plant()
    assert _wired_to(plant.model(), channel) == "+C1-B12:1; +EXT-M1:1"


def test_an_end_beside_the_unit_prints_its_whole_path() -> None:
    """FAR-END-ONE-HOME A2: a unit's own list knows only below it (owner 2026-09-24).

    `-B12` is outside the unit, so it prints `+C1-B12` although it sits at the unit's location;
    the unit's location still replaces the caller's `context` (`unit_list_context`, model-0056).
    """
    plant, channel, _c1, ext = _located_plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    _set_unit(plant, make_id(Item, ("mod",)), cabinet)
    model = plant.model()
    (own,) = plc_channel_rows(model, unit=cabinet)
    (given,) = plc_channel_rows(model, unit=cabinet, context=ext)
    assert own.wired_to == given.wired_to == "+C1-B12:1; +EXT-M1:1"
    assert own.channel == channel


# ---- wired_requests (PW1, PW2): which request binds to which channel by wiring alone ----------


def _bare(plant: Plant, key: str) -> tuple[Id[Function], Id[Port]]:
    """A function `key` with a single port `1`, no PLC facet: enough to wire a net."""
    function = plant.function(plant.item(key), "f")
    return function, plant.port(function, "1")


def _request(subject: Id[Function], name: str, *, priority: int = 1) -> PlcRequestFacet:
    """A bare PLC request facet for `subject`; not added to the model, only passed by hand."""
    return PlcRequestFacet(
        id=make_id(PlcRequestFacet, (name, "request")),
        key=(name, "request"),
        subject=subject,
        signal=SignalType.DI,
        signal_name=f"tag-{name}",
        priority=priority,
    )


def test_a_request_with_no_ports_at_all_reaches_nothing_but_does_not_crash() -> None:
    """A request subject with zero ports of its own has no entry in `ports_by_function`, so
    `by_function.get(subject, ())`'s default must actually be reached, not `None`."""
    plant = Plant()
    subject = plant.function(plant.item("req"), "f")  # no port added: zero ports
    channel, _channel_port = _bare(plant, "ch")
    model = plant.model()
    bound = wired_requests(model, [_request(subject, "req")], skip=(), taken=(), rank={channel: 0})
    assert bound == {}


def test_a_request_binds_the_first_eligible_channel_in_rank_order_not_any_eligible_one() -> None:
    """PW1: two channels reach the request; rank order decides, not id order or arbitrariness."""
    plant = Plant()
    subject, subject_port = _bare(plant, "req")
    low, low_port = _bare(plant, "ch-low")
    high, high_port = _bare(plant, "ch-high")
    plant.wire(subject_port, low_port, key="w-low")
    plant.wire(subject_port, high_port, key="w-high")
    model = plant.model()
    # Rank the channel that sorts LAST by id first in serving order, so a mutation that falls
    # back to id order (dropping `key=rank.__getitem__`) would pick the other one.
    first_by_id, second_by_id = sorted((low, high))
    rank = {first_by_id: 1, second_by_id: 0}
    bound = wired_requests(model, [_request(subject, "req")], skip=(), taken=(), rank=rank)
    assert bound == {subject: second_by_id}


def test_a_channel_two_requests_share_binds_neither_of_them() -> None:
    """PW2: a channel on one net with two requests' ports binds nobody by wiring."""
    plant = Plant()
    a_subject, a_port = _bare(plant, "req-a")
    b_subject, b_port = _bare(plant, "req-b")
    shared, shared_port = _bare(plant, "shared")
    plant.wire(a_port, shared_port, key="w-a")
    plant.wire(b_port, shared_port, key="w-b")
    model = plant.model()
    requests = [_request(a_subject, "req-a"), _request(b_subject, "req-b")]
    bound = wired_requests(model, requests, skip=(), taken=(), rank={shared: 0})
    assert bound == {}


def test_a_request_in_skip_is_never_processed_but_a_later_one_still_is() -> None:
    """`skip` drops a request before it is even looked at; it does not stop the whole walk."""
    plant = Plant()
    skipped, skipped_port = _bare(plant, "skipped")
    skipped_channel, skipped_channel_port = _bare(plant, "skipped-channel")
    normal, normal_port = _bare(plant, "normal")
    normal_channel, normal_channel_port = _bare(plant, "normal-channel")
    plant.wire(skipped_port, skipped_channel_port, key="w-skip")
    plant.wire(normal_port, normal_channel_port, key="w-normal")
    model = plant.model()
    requests = [_request(skipped, "skipped"), _request(normal, "normal", priority=2)]
    rank = {skipped_channel: 0, normal_channel: 1}
    bound = wired_requests(model, requests, skip={skipped}, taken=(), rank=rank)
    assert bound == {normal: normal_channel}
