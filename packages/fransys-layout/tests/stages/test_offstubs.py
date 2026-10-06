"""The off stub rules (C21, D10, layout-0080): hand-made values, no model.

Units: `P` and `Q` are top-level, `N` is nested in `P`. Function `n` has ports `n1` and `n2`
(`samples.function_spec`) and stands in location 100, or the one a test names; `_TOP` is what
`OffReads.top_unit` says of a unit. `connection(number, upper, lower)` runs from port `upper2`
to port `lower1`.
"""

from dataclasses import replace

import pytest
from samples import connection, function_spec, hid

from fransys_layout.stages.offstubs import (
    OffEnd,
    OffReads,
    PortText,
    _ends_in_stubs,
    bridge,
    by_location,
    crosses_location,
    groups_by_location,
    mate_stub,
)
from fransys_layout.stages.types import (
    EDGE_KIND,
    Connection,
    FunctionSpec,
    NetGroup,
    PortRef,
    Role,
    StubText,
)
from fransys_model.kernel import Id

_P, _Q, _N = hid("unit", 1), hid("unit", 2), hid("unit", 3)
_TOP = {None: None, _P: _P, _Q: _Q, _N: _P}


def _port(n: int, side: int):
    return hid("port", n * 10 + side)


def _spec(n: int, *, location: int | None = 100, unit=None, pin_function=None) -> FunctionSpec:
    """Function `n` in `location` (`None`: in none), in `unit`, a pin view of `pin_function`."""
    return replace(
        function_spec(n),
        location_path=() if location is None else (hid("aspect_node", location),),
        unit=unit,
        pin_function=pin_function,
    )


def _end_text(c, near, _at=None):
    """A fake `end_text`: the text names the conductor, the `OffEnd` its near port."""
    text = StubText(cable="", far=f"far-of-{c.handle.value[-2:]}", port="")
    return PortText(port=near, text=text), OffEnd(port=near, text=text, carrier=None, far=near)


def _reads(edges=(), *, designations=None, end_text=_end_text) -> OffReads:
    """`OffReads` over `edges`, `_TOP`, `designations` (port -> text) and `end_text`."""
    return OffReads(
        edges=frozenset(hid("function", n) for n in edges),
        top_unit=_TOP.__getitem__,
        end_text=end_text,
        designation=(designations or {}).__getitem__,
    )


def test_two_top_level_locations_of_two_units_cross() -> None:
    """Both stand in a location, the first ones differ, the drawing sets differ."""
    # UNDO: stages/offstubs.py `crosses_location`: `a.location_path[0] != b.location_path[0]`
    #   -> `a.location_path[0] == b.location_path[0]`
    assert crosses_location(_spec(1, location=100), _spec(2, location=200))
    assert not crosses_location(_spec(1, location=100), _spec(2, location=100))


def test_two_ends_of_one_unit_are_never_across() -> None:
    """One unit is one drawing: two locations, one unit, one drawing set (layout-0081, LD7)."""
    # UNDO: stages/offstubs.py `crosses_location`: drop `and a.drawing_set_key != b.drawing_set_key`
    one = _spec(1, location=100, unit=_P)
    other = _spec(2, location=200, unit=_P)
    assert one.location_path[0] != other.location_path[0]
    assert not crosses_location(one, other)


@pytest.mark.parametrize("other", [None, "no location"])
def test_an_end_that_is_missing_or_in_no_location_crosses_nothing(other) -> None:
    """`None` and an empty location path, on either side."""
    # UNDO: stages/offstubs.py `crosses_location`: drop `not a.location_path or not b.location_path`
    #   (an IndexError on the empty path)
    there = _spec(1, location=100)
    nowhere = None if other is None else _spec(2, location=None)
    assert not crosses_location(there, nowhere)
    assert not crosses_location(nowhere, there)


def test_a_crossing_needs_no_boundary_to_end_in_stubs() -> None:
    """Two locations: stubbed at each end though no edge is named."""
    # UNDO: stages/offstubs.py `ends_in_stubs`: drop the `if crosses_location(a, b): return True`
    #   (with no edge, nothing else says stub)
    reads = _reads()
    assert _ends_in_stubs(
        _spec(1, location=100), _spec(2, location=200), reads.edges, reads.top_unit
    )


def test_a_top_level_units_boundary_pin_is_stubbed_towards_another_unit_or_none() -> None:
    """Function 1 (an edge, in `P`): stubbed to `Q`'s function and to one in no unit."""
    # UNDO: stages/offstubs.py `ends_in_stubs`: `top_unit(far.unit) != top_unit(near.unit)`
    #   -> `top_unit(far.unit) == top_unit(near.unit)`
    reads = _reads(edges=(1,))
    pin = _spec(1, unit=_P)
    for far in (_spec(2, unit=_Q), _spec(2, unit=None)):
        assert _ends_in_stubs(pin, far, reads.edges, reads.top_unit)
        assert _ends_in_stubs(far, pin, reads.edges, reads.top_unit)


def test_a_pin_stays_drawn_towards_its_own_top_level_unit() -> None:
    """A boundary pin of `P` and a function of `N`, nested in `P`: one top-level unit, no stub."""
    # UNDO: stages/offstubs.py `ends_in_stubs`: replace the `!=` test on the two `top_unit`s
    #   by `far.unit != near.unit` (the units themselves differ here)
    reads = _reads(edges=(1,))
    assert not _ends_in_stubs(_spec(1, unit=_P), _spec(2, unit=_N), reads.edges, reads.top_unit)


def test_a_pin_views_real_function_makes_it_a_boundary_pin() -> None:
    """The pin view (function 5) is no edge itself; its `pin_function` (function 1) is."""
    # UNDO: stages/offstubs.py `ends_in_stubs`: drop `near.pin_function in edges or`
    reads = _reads(edges=(1,))
    view = _spec(5, unit=_P, pin_function=hid("function", 1))
    assert _ends_in_stubs(view, _spec(2, unit=_Q), reads.edges, reads.top_unit)


def test_two_non_boundary_ends_and_a_missing_end_are_not_stubbed() -> None:
    """Two units, no edge: the conductor bypasses the boundaries. A missing end: not stubbed."""
    # UNDO: stages/offstubs.py `ends_in_stubs`: drop `near.pin_function in edges or near.function
    #   in edges` from the `and` (no boundary test)
    reads = _reads()
    one, other = _spec(1, unit=_P), _spec(2, unit=_Q)
    assert not _ends_in_stubs(one, other, reads.edges, reads.top_unit)
    assert not _ends_in_stubs(one, None, reads.edges, reads.top_unit)
    assert not _ends_in_stubs(None, one, reads.edges, reads.top_unit)


def test_by_location_splits_the_connections_keeping_their_order() -> None:
    """Connection 1 to a function in another location is stubbed; 2 and 3 stay within."""
    # UNDO: stages/offstubs.py `by_location`: `(crossing if stubbed else within)` ->
    #   `(within if stubbed else crossing)`
    specs = [_spec(1), _spec(2, location=200), _spec(3), _spec(4)]
    wires = [connection(1, 1, 2), connection(2, 3, 4), connection(3, 1, 3)]
    within, crossing = by_location(specs, wires, _reads())
    assert crossing == (wires[0],)
    assert within == (wires[1], wires[2])


def test_a_connection_to_a_function_with_no_spec_is_within() -> None:
    """A function that is not drawn has no spec: no stub."""
    # UNDO: stages/offstubs.py `by_location`: `spec_of.get(c.b.function)` -> `spec_of[c.b.function]`
    #   (a KeyError)
    wire = connection(1, 1, 9)
    assert by_location([_spec(1)], [wire], _reads()) == ((wire,), ())


def _group(*numbers: int) -> NetGroup:
    """Net 9 over port `n1` of each function `n`."""
    return NetGroup(
        net=hid("net", 9),
        physical_net=hid("net", 90),
        role=Role.SIGNAL,
        ports=tuple(PortRef(function=hid("function", n), port=_port(n, 1)) for n in numbers),
    )


def _join(net: NetGroup, upper: int, lower: int) -> Connection:
    """The join `groups_by_location` makes between ports `upper1` and `lower1` of `net`."""
    return Connection(
        handle=net.net,
        physical_net=net.physical_net,
        role=net.role,
        a=PortRef(function=hid("function", upper), port=_port(upper, 1)),
        b=PortRef(function=hid("function", lower), port=_port(lower, 1)),
    )


def test_a_net_group_in_one_location_part_comes_back_as_it_was_with_no_join() -> None:
    """Three ports in location 100, and a group of one port: each group itself, no join."""
    # UNDO: stages/offstubs.py `groups_by_location`: drop the `if len(parts) == 1:` branch
    #   (the one-port group is a lone part and is dropped)
    net, lone = _group(1, 2, 3), replace(_group(5), net=hid("net", 8))
    specs = [_spec(1), _spec(2), _spec(3), _spec(5)]
    assert groups_by_location(specs, [net, lone], _reads()) == ((net, lone), ())


def test_a_net_group_across_two_locations_keeps_its_pair_and_joins_the_lowest_ports() -> None:
    """Functions 1 and 3 in location 100, 2 in 200: the group of 1 and 3, one join 1 to 2."""
    # UNDO: stages/offstubs.py `groups_by_location`: `a=before[0], b=after[0]` ->
    #   `a=before[-1], b=after[-1]` (the join starts at port 31)
    net = _group(1, 2, 3)
    specs = [_spec(1), _spec(2, location=200), _spec(3)]
    within, joins = groups_by_location(specs, [net], _reads())
    assert within == (replace(net, ports=(net.ports[0], net.ports[2])),)
    assert joins == (_join(net, 1, 2),)


def test_a_net_group_across_three_locations_joins_consecutive_parts_by_their_lowest_port() -> None:
    """Parts {1}, {2, 4} and {3} by lowest port: joins 1-2 and 2-3; port 21 ends both."""
    # UNDO: stages/offstubs.py `_location_parts`: `key=lambda part: part[0].port` ->
    #   `key=lambda part: part[-1].port` (parts by highest port: joins 1-3 and 3-2)
    net = _group(1, 2, 3, 4)
    specs = [_spec(1), _spec(2, location=200), _spec(3, location=300), _spec(4, location=200)]
    within, joins = groups_by_location(specs, [net], _reads())
    assert within == (replace(net, ports=(net.ports[1], net.ports[3])),)
    assert joins == (_join(net, 1, 2), _join(net, 2, 3))


def test_a_net_group_part_is_joined_through_a_member_that_stubs_to_neither() -> None:
    """One location: pin 1 (an edge of `P`), 2 in `P`, 3 in no unit. 1 to 3 would stub, but 1-2
    and 2-3 do not, so the three are one part: `ends_in_stubs` is not transitive."""
    # UNDO: stages/offstubs.py `_location_parts`: `combinations(ports, 2)` ->
    #   `((ports[0], other) for other in ports[1:])` (each port asked against the lowest only,
    #   so port 31 stands alone)
    reads = _reads(edges=(1,))
    specs = [_spec(1, unit=_P), _spec(2, unit=_P), _spec(3)]
    assert _ends_in_stubs(specs[0], specs[2], reads.edges, reads.top_unit)
    net = _group(1, 2, 3)
    assert groups_by_location(specs, [net], reads) == ((net,), ())


def test_bridge_ends_at_the_pin_and_a_stand_in_named_for_the_mates_port() -> None:
    """The stand-in is an `EDGE_KIND` id `<far value>-off`; the other fields are kept."""
    # UNDO: stages/offstubs.py `bridge`: `f"{far.value}-off"` -> `f"{near.value}-off"`
    wire = connection(1, 3, 2)
    near, far = _port(1, 1), _port(2, 1)
    bridged = bridge(wire, near, far)
    stand_in = Id(kind=EDGE_KIND, value=f"{far.value}-off")
    # the ends come back in port order, so compare them as a set
    assert {bridged.a, bridged.b} == {
        PortRef(function=near, port=near),
        PortRef(function=stand_in, port=stand_in),
    }
    assert (bridged.handle, bridged.physical_net, bridged.role) == (
        wire.handle,
        wire.physical_net,
        wire.role,
    )


def _refuse(*_args):
    """A read the rule must not make."""
    raise AssertionError


def _stubbed_pair() -> tuple[FunctionSpec, FunctionSpec]:
    """A boundary pin (function 1, in `P`) and its mate (function 2, in no unit)."""
    return _spec(1, unit=_P), _spec(2)


def test_a_mate_that_is_not_stubbed_gives_no_stub_and_reads_nothing_more() -> None:
    """The pin is no edge: `None`, and the designation and the end text are never asked."""
    # UNDO: stages/offstubs.py `mate_stub`: drop the `if not ends_in_stubs(...): return None`
    #   (the `designation` below then raises)
    reads = replace(_reads(edges=(), end_text=_refuse), designation=_refuse)
    wire = connection(1, 3, 2)
    assert mate_stub([wire], _stubbed_pair(), (_port(1, 1), _port(2, 1)), reads) is None


def test_a_stubbed_mate_with_no_conductor_at_its_pin_gives_none() -> None:
    """`within` has no conductor ending at the mate's port."""
    # UNDO: stages/offstubs.py `mate_stub`: drop the `if not ending: return None` (an IndexError)
    reads = _reads(edges=(1,))
    elsewhere = connection(1, 3, 4)
    assert mate_stub([elsewhere], _stubbed_pair(), (_port(1, 1), _port(2, 1)), reads) is None
    assert mate_stub([], _stubbed_pair(), (_port(1, 1), _port(2, 1)), reads) is None


def test_a_mate_stub_takes_the_conductor_with_the_first_designation_at_its_other_end() -> None:
    """Conductors 5 and 6 end at the mate's port 21; the far ends are ports 32 ("B") and 42
    ("A"): 6 wins by designation though 5 has the lower handle; equal designations: the handle."""
    # UNDO: stages/offstubs.py `mate_stub`: the sort key `(reads.designation(...), c.handle)`
    #   -> `(c.handle,)`
    reads = _reads(edges=(1,), designations={_port(3, 2): "B", _port(4, 2): "A"})
    five, six = connection(5, 3, 2), connection(6, 4, 2)
    ends = (_port(1, 1), _port(2, 1))
    found = mate_stub([five, six], _stubbed_pair(), ends, reads)
    assert found is not None
    assert found[0] == bridge(six, *ends)
    same = _reads(edges=(1,), designations={_port(3, 2): "A", _port(4, 2): "A"})
    found = mate_stub([six, five], _stubbed_pair(), ends, same)
    assert found is not None
    assert found[0] == bridge(five, *ends)


def test_a_mate_stub_carries_the_conductors_end_text_moved_to_the_pin() -> None:
    """`end_text` is asked for the chosen conductor at the mate's port; the text and the
    `OffEnd` it returns are the pin's: their port is replaced by the pin's, nothing else."""
    # UNDO: stages/offstubs.py `mate_stub`: `dataclasses.replace(end, port=near)` -> `end`
    asked = []

    def spy(c, near, at):
        asked.append((c.handle, near, at))
        return _end_text(c, near)

    reads = _reads(edges=(1,), designations={_port(3, 2): "B"}, end_text=spy)
    wire = connection(5, 3, 2)
    near, far = _port(1, 1), _port(2, 1)
    found = mate_stub([wire], _stubbed_pair(), (near, far), reads)
    assert found is not None
    connection_, text, end = found
    assert asked == [(wire.handle, far, near)]
    assert connection_ == bridge(wire, near, far)
    named = StubText(cable="", far="far-of-05", port="")
    assert text == PortText(port=near, text=named)
    assert end == OffEnd(port=near, text=named, carrier=None, far=far)
